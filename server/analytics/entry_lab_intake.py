from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "Trading-Images" / "trades_export.csv"
OUTPUT_DATASET = DATA_DIR / "entry_lab_trades.json"
OUTPUT_METRICS = DATA_DIR / "entry_lab_metrics.json"
OUTPUT_SUMMARY = DATA_DIR / "entry_lab_metrics.md"


@dataclass
class TradeRecord:
    trade_id: str
    symbol: str
    entry_time: str | None
    exit_time: str | None
    entry_price: float | None
    exit_price: float | None
    pnl: float | None
    fees: float | None
    size: float | None
    direction: str | None
    trade_day: str | None
    duration_seconds: float | None
    session: str | None
    chart_path: str | None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%m/%d/%Y %H:%M:%S %z")
    except ValueError:
        try:
            return datetime.strptime(value.strip(), "%m/%d/%Y %H:%M:%S")
        except ValueError:
            try:
                return datetime.strptime(value.strip(), "%m/%d/%Y")
            except ValueError:
                return None


def _safe_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _infer_session(entry_dt: datetime | None) -> str | None:
    if entry_dt is None:
        return None
    hour = entry_dt.astimezone(timezone.utc).hour  # normalize before comparison
    # Sessions defined in UTC to avoid DST confusion
    if 0 <= hour < 6:
        return "Asia"
    if 6 <= hour < 12:
        return "London"
    if 12 <= hour < 18:
        return "New York"
    return "Afternoon"


def _chart_path(symbol: str, trade_id: str) -> str | None:
    charts_dir = DATA_DIR / "charts"
    filename = f"{symbol}_5m_{trade_id}.png"
    candidate = charts_dir / filename
    return str(candidate.relative_to(BASE_DIR)) if candidate.exists() else None


def load_trades() -> List[TradeRecord]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")

    records: List[TradeRecord] = []
    with CSV_PATH.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            trade_id = (row.get("Id") or row.get("id") or "").strip()
            if not trade_id:
                continue
            entry_dt = _parse_dt(row.get("EnteredAt"))
            exit_dt = _parse_dt(row.get("ExitedAt"))
            duration = (exit_dt - entry_dt).total_seconds() if entry_dt and exit_dt else None

            record = TradeRecord(
                trade_id=trade_id,
                symbol=(row.get("ContractName") or "").replace("/", "").strip(),
                entry_time=entry_dt.isoformat() if entry_dt else None,
                exit_time=exit_dt.isoformat() if exit_dt else None,
                entry_price=_safe_float(row.get("EntryPrice")),
                exit_price=_safe_float(row.get("ExitPrice")),
                pnl=_safe_float(row.get("PnL")),
                fees=(_safe_float(row.get("Fees")) or 0.0) + (_safe_float(row.get("Commissions")) or 0.0),
                size=_safe_float(row.get("Size")),
                direction=(row.get("Type") or "").strip().lower(),
                trade_day=(entry_dt.date().isoformat() if entry_dt else None),
                duration_seconds=duration,
                session=_infer_session(entry_dt),
                chart_path=_chart_path((row.get("ContractName") or "").replace("/", "").strip(), trade_id),
            )
            records.append(record)
    return records


def compute_metrics(records: List[TradeRecord]) -> Dict[str, object]:
    total = len(records)
    wins = [r for r in records if (r.pnl or 0) > 0]
    losses = [r for r in records if (r.pnl or 0) < 0]
    breakeven = [r for r in records if (r.pnl or 0) == 0]

    def avg(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    summary = {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(breakeven),
        "win_rate": (len(wins) / total * 100) if total else 0.0,
        "avg_pnl": avg([r.pnl or 0 for r in records]),
        "avg_win": avg([r.pnl or 0 for r in wins]),
        "avg_loss": avg([r.pnl or 0 for r in losses]),
        "total_pnl": sum(r.pnl or 0 for r in records),
        "avg_duration_minutes": avg([(r.duration_seconds or 0) / 60 for r in records if r.duration_seconds]),
    }

    per_symbol: Dict[str, Dict[str, float]] = {}
    for r in records:
        sym = r.symbol or "UNKNOWN"
        bucket = per_symbol.setdefault(sym, {"trades": 0, "wins": 0, "pnl": 0.0})
        bucket["trades"] += 1
        if (r.pnl or 0) > 0:
            bucket["wins"] += 1
        bucket["pnl"] += r.pnl or 0.0
    for sym, bucket in per_symbol.items():
        bucket["win_rate"] = (bucket["wins"] / bucket["trades"] * 100) if bucket["trades"] else 0.0

    per_session: Dict[str, Dict[str, float]] = {}
    for r in records:
        session = r.session or "Unknown"
        bucket = per_session.setdefault(session, {"trades": 0, "wins": 0, "pnl": 0.0})
        bucket["trades"] += 1
        if (r.pnl or 0) > 0:
            bucket["wins"] += 1
        bucket["pnl"] += r.pnl or 0.0
    for sess, bucket in per_session.items():
        bucket["win_rate"] = (bucket["wins"] / bucket["trades"] * 100) if bucket["trades"] else 0.0

    summary["per_symbol"] = per_symbol
    summary["per_session"] = per_session
    return summary


def write_outputs(records: List[TradeRecord], metrics: Dict[str, object]) -> None:
    OUTPUT_DATASET.write_text(json.dumps([asdict(r) for r in records], indent=2))
    OUTPUT_METRICS.write_text(json.dumps(metrics, indent=2))

    lines = [
        "# Entry Lab Metrics Summary",
        "",
        f"Total trades: {metrics['total_trades']}",
        f"Win rate: {metrics['win_rate']:.1f}%",
        f"Total PnL: {metrics['total_pnl']:.2f}",
        f"Average duration (min): {metrics['avg_duration_minutes']:.2f}",
        "",
        "## Per Symbol",
    ]
    for sym, bucket in metrics["per_symbol"].items():
        lines.append(f"- {sym}: {bucket['trades']} trades, win {bucket['win_rate']:.1f}%, PnL {bucket['pnl']:.2f}")
    lines.append("")
    lines.append("## Per Session")
    for sess, bucket in metrics["per_session"].items():
        lines.append(f"- {sess}: {bucket['trades']} trades, win {bucket['win_rate']:.1f}%, PnL {bucket['pnl']:.2f}")
    OUTPUT_SUMMARY.write_text("\n".join(lines))


def main() -> None:
    records = load_trades()
    metrics = compute_metrics(records)
    write_outputs(records, metrics)
    print(f"[ENTRY LAB] Processed {len(records)} trades.")
    print(f" Win rate: {metrics['win_rate']:.1f}% | Total PnL: {metrics['total_pnl']:.2f}")
    print(f" Dataset saved to {OUTPUT_DATASET.relative_to(BASE_DIR)}")
    print(f" Metrics saved to {OUTPUT_METRICS.relative_to(BASE_DIR)} and {OUTPUT_SUMMARY.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
