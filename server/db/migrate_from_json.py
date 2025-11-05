from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .models import Base, Trade
from .session import engine, SessionLocal


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def migrate_performance_logs(json_path: Path) -> Dict[str, Any]:
    if not json_path.exists():
        return {"migrated": 0, "skipped": 0, "reason": "file_not_found"}

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # data can be a list of trades or an object with a key
    trades: List[Dict[str, Any]]
    if isinstance(data, dict):
        trades = data.get("trades", []) or data.get("logs", []) or []
    else:
        trades = data

    Base.metadata.create_all(bind=engine)

    migrated = 0
    skipped = 0
    with SessionLocal() as db:
        for t in trades:
            trade_id = str(t.get("id") or t.get("trade_id") or "")
            if not trade_id:
                skipped += 1
                continue

            # Skip if exists
            if db.query(Trade).filter(Trade.trade_id == trade_id).first():
                skipped += 1
                continue

            trade = Trade(
                trade_id=trade_id,
                symbol=t.get("symbol"),
                entry_time=_parse_dt(t.get("entry_time")),
                exit_time=_parse_dt(t.get("exit_time")),
                entry_price=_safe_float(t.get("entry_price")),
                exit_price=_safe_float(t.get("exit_price")),
                direction=t.get("direction"),
                outcome=t.get("outcome") or t.get("result"),
                pnl=_safe_float(t.get("pnl")),
                r_multiple=_safe_float(t.get("r_multiple") or t.get("rMultiple")),
                chart_url=t.get("chart_url") or t.get("chartUrl"),
                session_id=str(t.get("session_id") or t.get("sessionId") or ""),
            )
            db.add(trade)
            migrated += 1

        db.commit()

    return {"migrated": migrated, "skipped": skipped, "reason": None}


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


if __name__ == "__main__":
    server_dir = Path(__file__).resolve().parent.parent
    json_path = server_dir / "data" / "performance_logs.json"
    result = migrate_performance_logs(json_path)
    print(f"Migration result: {result}")


