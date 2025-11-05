from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from .models import Trade


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def enrich_trades_from_logs(db: Session, logs_path: Path) -> dict:
    """Update existing trades with entry/exit timestamps and r_multiple from logs file.
    Only fills missing fields.
    """
    if not logs_path.exists():
        return {"updated": 0, "skipped": 0, "reason": "file_not_found"}

    with open(logs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        trades = data.get("trades") or data.get("logs") or []
    else:
        trades = data

    # index by trade_id
    by_id = {}
    for t in trades:
        tid = str(t.get("id") or t.get("trade_id") or "").strip()
        if tid:
            by_id[tid] = t

    updated = 0
    skipped = 0
    for row in db.query(Trade).all():
        src = by_id.get(row.trade_id)
        if not src:
            skipped += 1
            continue
        changed = False
        # entry_time candidates
        et = _parse_dt(src.get("entry_time") or src.get("timestamp") or src.get("trade_day"))
        if row.entry_time is None and et is not None:
            row.entry_time = et
            changed = True
        # exit_time candidate
        xt = _parse_dt(src.get("exit_time") or src.get("exitTimestamp") or None)
        if row.exit_time is None and xt is not None:
            row.exit_time = xt
            changed = True
        # r_multiple
        if row.r_multiple is None and src.get("r_multiple") is not None:
            try:
                row.r_multiple = float(src.get("r_multiple"))
                changed = True
            except Exception:
                pass
        if changed:
            db.add(row)
            updated += 1

    db.commit()
    return {"updated": updated, "skipped": skipped, "reason": None}


