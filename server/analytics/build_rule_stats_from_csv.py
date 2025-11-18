#!/usr/bin/env python3
"""
Rebuild entry_lab_rules_summary.json from a CSV of annotated trades.
Usage:
  PYTHONPATH=trading-ai-extension python3 server/analytics/build_rule_stats_from_csv.py \
    server/data/entry_lab_annotations_template.csv \
    server/data/entry_lab_rules_summary.json
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Local imports (works when PYTHONPATH points to repo root)
from server.analytics.advisor import select_rule  # type: ignore
from server.analytics.risk_utils import compute_risk  # type: ignore


def _to_float(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() == "null":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_bool(val: Optional[str]) -> Optional[bool]:
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def load_rows(csv_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row: Dict[str, Any] = dict(raw)
            # Normalize fields
            row["poi_low"] = _to_float(row.get("poi_low"))
            row["poi_high"] = _to_float(row.get("poi_high"))
            row["fractal_target"] = _to_float(row.get("fractal_target"))
            row["bos_level"] = _to_float(row.get("bos_level"))
            row["ifvg_low"] = _to_float(row.get("ifvg_low"))
            row["ifvg_high"] = _to_float(row.get("ifvg_high"))
            row["entry_price"] = _to_float(row.get("micro_entry_price") or row.get("entry_price"))
            row["sl"] = _to_float(row.get("micro_sl") or row.get("sl"))
            row["tp"] = _to_float(row.get("micro_tp") or row.get("tp"))
            row["contracts"] = _to_float(row.get("contracts")) or 1.0
            row["micro_shift"] = _normalize_bool(row.get("micro_shift"))
            row["ifvg_present"] = _normalize_bool(row.get("ifvg_present"))
            row["outcome"] = (row.get("outcome") or "").strip().lower()
            rows.append(row)
    return rows


def aggregate_by_rule(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        rule = select_rule(r)
        agg = stats.setdefault(rule, {"total": 0, "wins": 0, "losses": 0, "breakeven": 0, "r_values": []})
        agg["total"] += 1

        outcome = r.get("outcome")
        if outcome == "win":
            agg["wins"] += 1
        elif outcome == "loss":
            agg["losses"] += 1
        elif outcome == "breakeven":
            agg["breakeven"] += 1

        # Compute R multiple if possible
        risk = compute_risk(r.get("entry_price"), r.get("sl"), r.get("tp") or r.get("fractal_target"), r.get("symbol", ""), contracts=r.get("contracts", 1.0))
        rr = risk.get("r_multiple")
        if rr is not None:
            if outcome == "loss":
                agg["r_values"].append(-1.0)  # assume full -1R loss
            elif outcome == "win":
                agg["r_values"].append(rr)

    # Finalize metrics
    finalized: Dict[str, Dict[str, Any]] = {}
    for rule, agg in stats.items():
        completed = agg["wins"] + agg["losses"] + agg["breakeven"]
        win_rate = (agg["wins"] / completed * 100.0) if completed else None
        avg_rr = (sum(agg["r_values"]) / len(agg["r_values"])) if agg["r_values"] else None
        finalized[rule] = {
            "total": agg["total"],
            "wins": agg["wins"],
            "losses": agg["losses"],
            "breakeven": agg["breakeven"],
            "win_rate": round(win_rate, 2) if win_rate is not None else None,
            "avg_rr": round(avg_rr, 3) if avg_rr is not None else None,
        }
    return finalized


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    csv_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    rows = load_rows(csv_path)
    stats = aggregate_by_rule(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote stats for {len(stats)} rules to {out_path}")


if __name__ == "__main__":
    main()
