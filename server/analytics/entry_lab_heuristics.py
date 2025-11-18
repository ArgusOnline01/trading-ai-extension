from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
import sys

# Set up path BEFORE imports that depend on it
BASE = Path(__file__).resolve().parent.parent
# Ensure project root is on path for chart_reconstruction imports
sys.path.insert(0, str(BASE))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception as e:
    print(f"[WARN] pandas not available: {e}")
    PANDAS_AVAILABLE = False
    pd = None

try:
    from chart_reconstruction.data_utils import fetch_price_data
    CAN_FETCH = PANDAS_AVAILABLE
except Exception as e:
    print(f"[WARN] Could not import fetch_price_data: {e}")
    CAN_FETCH = False

# Simulation knobs
SL_TP_WINDOW_HOURS = 8  # realistic hold window for forward simulation
MAX_DOLLAR_RISK = 200.0  # cap per-trade loss (approx, using original $/price-unit)
IFVG_RULE_KEY = "R5_ifvg_fractal"  # entry at IFVG mid, SL at IFVG low, TP at fractal_target

DATA = BASE / "data"
TRADES_PATH = DATA / "entry_lab_trades.json"
ANNOTS_PATH = BASE / "analytics" / "entry_lab_annotations.json"
SUMMARY_JSON = DATA / "entry_lab_rules_summary.json"
SUMMARY_MD = DATA / "entry_lab_rules_summary.md"
DECISIONS_JSON = DATA / "entry_lab_rule_decisions.json"

SESSION_ALLOWLIST = {"Asia", "London"}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def merge_trades_annotations(trades: List[dict], annots: List[dict]) -> List[dict]:
    annot_map = {a.get("trade_id"): a for a in annots}
    merged = []
    for t in trades:
        tid = str(t.get("trade_id")) if "trade_id" in t else str(t.get("trade_id") or t.get("Id"))
        a = annot_map.get(tid, {})
        row = {**t, **a}
        row["trade_id"] = tid
        # Compute direction sign
        dir_sign = 1 if (row.get("direction") or "").lower() == "long" else -1 if (row.get("direction") or "").lower() == "short" else 0
        row["dir_sign"] = dir_sign
        # Price delta based on actual exit vs actual entry (for alternate entry simulation we override later)
        if dir_sign != 0 and row.get("entry_price") is not None and row.get("exit_price") is not None:
            row["delta_price"] = (row["exit_price"] - row["entry_price"]) * dir_sign
        else:
            row["delta_price"] = None
        merged.append(row)
    return merged


def metric_row(rows: List[dict]) -> Dict[str, float]:
    total = len(rows)
    wins = [r for r in rows if (r.get("pnl") or 0) > 0]
    losses = [r for r in rows if (r.get("pnl") or 0) < 0]
    breakeven = total - len(wins) - len(losses)
    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0
    return {
        "total": total,
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": breakeven,
        "win_rate": (len(wins) / total * 100) if total else 0.0,
        "avg_pnl": avg([r.get("pnl") or 0 for r in rows]),
        "total_pnl": sum(r.get("pnl") or 0 for r in rows),
        "avg_price_delta": avg([r.get("delta_price") or 0 for r in rows]),
    }


def filter_rule(rows: List[dict], rule: str) -> List[dict]:
    if rule == "baseline":
        return rows
    if rule == "exclude_clean":
        return [r for r in rows if not r.get("exclude")]
    if rule == "R1_ifvg_mitigated":
        return [r for r in rows if r.get("ifvg_present") and r.get("entry_type","ifvg") == "ifvg" and r.get("poi_mitigated_50")]
    if rule == "R2_sweep_before_entry":
        return [r for r in rows if r.get("liquidity_swept")]
    if rule == "R3_session_london_asia":
        return [r for r in rows if (r.get("session") in SESSION_ALLOWLIST)]
    if rule == "R4_counterfactual_poi50":
        # Trades where a POI50 counterfactual is possible (have POI bounds)
        return [r for r in rows if r.get("poi_low") is not None and r.get("poi_high") is not None]
    if rule == IFVG_RULE_KEY:
        return [r for r in rows if r.get("ifvg_low") is not None and r.get("ifvg_high") is not None and r.get("fractal_target") is not None and r.get("entry_type") == "ifvg"]
    return rows


def build_decisions(rows: List[dict], rules: List[str]) -> List[dict]:
    decisions = []
    for r in rows:
        entry = {"trade_id": r.get("trade_id")}
        for rule in rules:
            entry[rule] = r in filter_rule(rows, rule)
        decisions.append(entry)
    return decisions


def apply_poi50_counterfactual(rows: List[dict]) -> List[dict]:
    """
    For trades with POI bounds and exit price, calculate an alternate delta_price
    using POI midpoint entry and POI extreme SL (not enforced) and same exit price.
    This is an approximation: we keep the exit price/time the same, just change entry.
    """
    adjusted = []
    for r in rows:
        r = dict(r)
        if r.get("poi_low") is None or r.get("poi_high") is None:
            adjusted.append(r)
            continue
        if r.get("dir_sign") == 0 or r.get("exit_price") is None:
            adjusted.append(r)
            continue
        # POI midpoint entry
        alt_entry = (r["poi_low"] + r["poi_high"]) / 2.0
        dir_sign = r["dir_sign"]
        # Recompute price delta using same exit price but alternate entry
        r["delta_price"] = (r["exit_price"] - alt_entry) * dir_sign
        r["alt_entry_price"] = alt_entry
        adjusted.append(r)
    return adjusted


from typing import Any


def simulate_poi50_sl_tp(rows: List[dict], cache: Dict[str, Any]) -> List[dict]:
    """
    Use POI midpoint entry, POI extreme SL, and BOS (structural target) as TP.
    Iterate forward through 5m bars to see which is hit first. Uses fetch_price_data.
    Obeys SL_TP_WINDOW_HOURS and MAX_DOLLAR_RISK.
    """
    if not CAN_FETCH:
        print("[WARN] fetch_price_data not available; skipping SL/TP simulation.")
        return rows

    simulated = []
    for r in rows:
        r = dict(r)
        trade_id = r.get("trade_id")
        if r.get("poi_low") is None or r.get("poi_high") is None or r.get("bos_level") is None:
            simulated.append(r)
            continue
        if r.get("dir_sign") == 0:
            simulated.append(r)
            continue

        entry_mid = (r["poi_low"] + r["poi_high"]) / 2.0
        dir_sign = r["dir_sign"]
        # Determine SL/TP
        if dir_sign > 0:  # long
            sl = r["poi_low"]
            tp = r.get("fractal_target") or r["bos_level"]
        else:  # short
            sl = r["poi_high"]
            tp = r.get("fractal_target") or r["bos_level"]

        # Parse entry_time and symbol
        entry_time = r.get("entry_time") or r.get("EnteredAt")
        symbol = r.get("symbol") or r.get("ContractName")
        if not entry_time or not symbol:
            simulated.append(r)
            continue

        # Filter forward bars
        try:
            entry_dt = pd.to_datetime(entry_time)
            # Convert to timezone-naive to match dataframe index (data_utils returns tz-naive)
            if entry_dt.tzinfo is not None:
                import pytz
                CHICAGO_TZ = pytz.timezone("America/Chicago")
                entry_dt = entry_dt.tz_convert(CHICAGO_TZ).tz_localize(None)
            else:
                entry_dt = entry_dt.tz_localize(None) if hasattr(entry_dt, 'tz_localize') else entry_dt
        except Exception as e:
            print(f"[WARN] Failed to parse entry_time {entry_time}: {e}")
            simulated.append(r)
            continue

        # Fetch or reuse price data keyed by symbol + entry_dt to avoid cross-trade contamination
        cache_key = f"{symbol}_{entry_dt.strftime('%Y%m%d%H%M')}"
        if cache_key not in cache:
            df = fetch_price_data(symbol, entry_time, window_hours=SL_TP_WINDOW_HOURS) if CAN_FETCH else pd.DataFrame()
            cache[cache_key] = df
        df = cache.get(cache_key, pd.DataFrame())
        if df.empty:
            simulated.append(r)
            continue

        forward = df[df.index >= entry_dt]
        if forward.empty:
            simulated.append(r)
            continue

        # Compute per-price-unit dollars from original trade (for loss cap)
        per_price_unit = None
        if (
            r.get("pnl") is not None
            and r.get("entry_price") is not None
            and r.get("exit_price") is not None
            and dir_sign != 0
        ):
            orig_delta = (r["exit_price"] - r["entry_price"]) * dir_sign
            if orig_delta != 0:
                per_price_unit = r["pnl"] / orig_delta

        outcome = None
        exit_price = None
        for _, bar in forward.iterrows():
            high = float(bar["High"])
            low = float(bar["Low"])
            # Dollar loss cap based on original $/price-unit
            loss_cap_hit = False
            loss_cap_price = None
            if per_price_unit:
                unit_val = abs(per_price_unit)
                if unit_val > 0:
                    price_cap = MAX_DOLLAR_RISK / unit_val
                    if dir_sign > 0:
                        trigger = entry_mid - price_cap
                        if low <= trigger:
                            loss_cap_hit = True
                            loss_cap_price = trigger
                    else:
                        trigger = entry_mid + price_cap
                        if high >= trigger:
                            loss_cap_hit = True
                            loss_cap_price = trigger

            # Determine hit order conservatively: SL first if both in same bar
            if dir_sign > 0:
                hit_sl = low <= sl
                hit_tp = high >= tp
            else:
                hit_sl = high >= sl
                hit_tp = low <= tp
            if loss_cap_hit:
                outcome = "sl_cap"
                exit_price = loss_cap_price
                break
            if hit_sl:
                outcome = "sl"
                exit_price = sl
                break
            if hit_tp:
                outcome = "tp"
                exit_price = tp
                break

        if outcome is None:
            # Neither hit in window; use last close as exit
            last_bar = forward.iloc[-1]
            exit_price = float(last_bar["Close"])
            outcome = "open"

        # Compute delta from simulated entry
        r["alt_entry_price"] = entry_mid
        r["alt_exit_price"] = exit_price
        r["sim_outcome"] = outcome
        delta_price = (exit_price - entry_mid) * dir_sign
        r["delta_price"] = delta_price

        # Re-scale pnl using the ratio between original pnl and original price delta (if present)
        # so counterfactuals stay in the same monetary units.
        if (
            r.get("pnl") is not None
            and r.get("entry_price") is not None
            and r.get("exit_price") is not None
            and dir_sign != 0
        ):
            orig_delta = (r["exit_price"] - r["entry_price"]) * dir_sign
            if orig_delta != 0:
                per_price_unit = r["pnl"] / orig_delta
                r["pnl"] = per_price_unit * delta_price

        simulated.append(r)

    return simulated


def simulate_ifvg_fractal(rows: List[dict], cache: Dict[str, Any]) -> List[dict]:
    """
    IFVG counterfactual:
    - Entry at IFVG midpoint
    - SL at IFVG low (long) / IFVG high (short)
    - TP at fractal_target
    Uses SL_TP_WINDOW_HOURS and MAX_DOLLAR_RISK.
    """
    if not CAN_FETCH:
        print("[WARN] fetch_price_data not available; skipping IFVG simulation.")
        return rows

    simulated = []
    for r in rows:
        r = dict(r)
        if r.get("ifvg_low") is None or r.get("ifvg_high") is None or r.get("fractal_target") is None:
            simulated.append(r)
            continue
        if r.get("dir_sign") == 0:
            simulated.append(r)
            continue

        entry_mid = (r["ifvg_low"] + r["ifvg_high"]) / 2.0
        dir_sign = r["dir_sign"]
        if dir_sign > 0:
            sl = r["ifvg_low"]
            tp = r["fractal_target"]
        else:
            sl = r["ifvg_high"]
            tp = r["fractal_target"]

        entry_time = r.get("entry_time") or r.get("EnteredAt")
        symbol = r.get("symbol") or r.get("ContractName")
        if not entry_time or not symbol:
            simulated.append(r)
            continue

        try:
            entry_dt = pd.to_datetime(entry_time)
            if entry_dt.tzinfo is not None:
                import pytz
                CHICAGO_TZ = pytz.timezone("America/Chicago")
                entry_dt = entry_dt.tz_convert(CHICAGO_TZ).tz_localize(None)
            else:
                entry_dt = entry_dt.tz_localize(None) if hasattr(entry_dt, 'tz_localize') else entry_dt
        except Exception as e:
            print(f"[WARN] Failed to parse entry_time {entry_time}: {e}")
            simulated.append(r)
            continue

        cache_key = f"{symbol}_{entry_dt.strftime('%Y%m%d%H%M')}_ifvg"
        if cache_key not in cache:
            df = fetch_price_data(symbol, entry_time, window_hours=SL_TP_WINDOW_HOURS) if CAN_FETCH else pd.DataFrame()
            cache[cache_key] = df
        df = cache.get(cache_key, pd.DataFrame())
        if df.empty:
            simulated.append(r)
            continue

        forward = df[df.index >= entry_dt]
        if forward.empty:
            simulated.append(r)
            continue

        per_price_unit = None
        if (
            r.get("pnl") is not None
            and r.get("entry_price") is not None
            and r.get("exit_price") is not None
            and dir_sign != 0
        ):
            orig_delta = (r["exit_price"] - r["entry_price"]) * dir_sign
            if orig_delta != 0:
                per_price_unit = r["pnl"] / orig_delta

        outcome = None
        exit_price = None
        for _, bar in forward.iterrows():
            high = float(bar["High"])
            low = float(bar["Low"])

            loss_cap_hit = False
            loss_cap_price = None
            if per_price_unit:
                unit_val = abs(per_price_unit)
                if unit_val > 0:
                    price_cap = MAX_DOLLAR_RISK / unit_val
                    if dir_sign > 0:
                        trigger = entry_mid - price_cap
                        if low <= trigger:
                            loss_cap_hit = True
                            loss_cap_price = trigger
                    else:
                        trigger = entry_mid + price_cap
                        if high >= trigger:
                            loss_cap_hit = True
                            loss_cap_price = trigger

            if dir_sign > 0:
                hit_sl = low <= sl
                hit_tp = high >= tp
            else:
                hit_sl = high >= sl
                hit_tp = low <= tp
            if loss_cap_hit:
                outcome = "sl_cap"
                exit_price = loss_cap_price
                break
            if hit_sl:
                outcome = "sl"
                exit_price = sl
                break
            if hit_tp:
                outcome = "tp"
                exit_price = tp
                break

        if outcome is None:
            last_bar = forward.iloc[-1]
            exit_price = float(last_bar["Close"])
            outcome = "open"

        r["alt_entry_price"] = entry_mid
        r["alt_exit_price"] = exit_price
        r["sim_outcome"] = outcome
        delta_price = (exit_price - entry_mid) * dir_sign
        r["delta_price"] = delta_price

        if (
            r.get("pnl") is not None
            and r.get("entry_price") is not None
            and r.get("exit_price") is not None
            and dir_sign != 0
        ):
            orig_delta = (r["exit_price"] - r["entry_price"]) * dir_sign
            if orig_delta != 0:
                per_price_unit = r["pnl"] / orig_delta
                r["pnl"] = per_price_unit * delta_price

        simulated.append(r)

    return simulated


def main():
    trades = load_json(TRADES_PATH)
    annots_obj = load_json(ANNOTS_PATH)
    annots = annots_obj.get("annotations", []) if isinstance(annots_obj, dict) else annots_obj
    merged = merge_trades_annotations(trades, annots)

    # Prepare a POI50 counterfactual view (approximate: same exit, POI-mid entry)
    merged_poi50 = apply_poi50_counterfactual(merged)
    # Prepare a POI50 SL/TP simulation using 5m bars if available
    price_cache: Dict[str, pd.DataFrame] = {}
    merged_poi50_sl_tp = simulate_poi50_sl_tp(merged, price_cache)
    # IFVG counterfactual using IFVG bounds and fractal targets
    merged_ifvg = simulate_ifvg_fractal(merged, price_cache)

    # Rule sets
    rules = [
        "baseline",
        "exclude_clean",
        "R1_ifvg_mitigated",
        "R2_sweep_before_entry",
        "R3_session_london_asia",
        "R4_counterfactual_poi50",
        IFVG_RULE_KEY,
    ]

    summaries = {}
    summaries_md_lines = ["# Entry Lab Rule Metrics", ""]

    for rule in rules:
        # Use counterfactual rows for R4, otherwise baseline rows
        # If price data available, prefer SL/TP simulation; else fall back to simple counterfactual
        if rule == "R4_counterfactual_poi50":
            active_rows = merged_poi50_sl_tp if CAN_FETCH else merged_poi50
        elif rule == "R1_ifvg_mitigated":
            # Use IFVG simulated paths for IFVG-mitigated subset
            active_rows = merged_ifvg
        elif rule == IFVG_RULE_KEY:
            active_rows = merged_ifvg
        else:
            active_rows = merged
        subset_all = filter_rule(active_rows, rule)
        subset_clean = [r for r in subset_all if not r.get("exclude")]
        metrics_all = metric_row(subset_all)
        metrics_clean = metric_row(subset_clean)
        summaries[rule] = {"all": metrics_all, "clean": metrics_clean}
        summaries_md_lines.append(f"## {rule}")
        summaries_md_lines.append(f"- All: n={metrics_all['total']}, win={metrics_all['win_rate']:.1f}%, PnL={metrics_all['total_pnl']:.2f}, avg={metrics_all['avg_pnl']:.2f}")
        summaries_md_lines.append(f"- Clean: n={metrics_clean['total']}, win={metrics_clean['win_rate']:.1f}%, PnL={metrics_clean['total_pnl']:.2f}, avg={metrics_clean['avg_pnl']:.2f}")
        summaries_md_lines.append(f"- Avg price delta (clean): {metrics_clean['avg_price_delta']:.5f}")
        if rule == "R4_counterfactual_poi50":
            if CAN_FETCH:
                summaries_md_lines.append("(POI50 counterfactual: POI-mid entry, POI extreme SL, BOS TP. Uses 5m bar simulation to determine which is hit first.)")
            else:
                summaries_md_lines.append("(POI50 counterfactual uses same exit price/time, POI-mid entry. Approximation; no SL/TP path simulation.)")
        if rule == IFVG_RULE_KEY:
            summaries_md_lines.append("(IFVG counterfactual: IFVG-mid entry, IFVG low/high SL, fractal_target TP. Uses 5m bar simulation, 8h window, $200 loss cap.)")
        summaries_md_lines.append("")

    # Decisions table (which trades qualify per rule)
    decisions = build_decisions(merged, rules)

    SUMMARY_JSON.write_text(json.dumps(summaries, indent=2))
    SUMMARY_MD.write_text("\n".join(summaries_md_lines))
    DECISIONS_JSON.write_text(json.dumps(decisions, indent=2))

    print("[ENTRY LAB] Rules evaluated.")
    print(f"Summary saved: {SUMMARY_JSON}")
    print(f"Summary (md): {SUMMARY_MD}")
    print(f"Decisions: {DECISIONS_JSON}")


if __name__ == "__main__":
    main()
