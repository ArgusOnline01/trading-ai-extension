from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from .models import Trade


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    # Handle values like: 10/29/2025 02:34:55 -05:00
    # Strip timezone for now; future: apply tz if needed
    try:
        if ' -' in value:
            value = value.split(' -')[0]
        return datetime.strptime(value, "%m/%d/%Y %H:%M:%S")
    except Exception:
        pass
    # Fallback simple date
    try:
        return datetime.strptime(value, "%m/%d/%Y")
    except Exception:
        return None


def import_from_csv(db: Session, csv_path: Path) -> dict:
    """Update existing trades with values from CSV by matching Id -> trade_id.
    Fields: entry_time, exit_time, entry_price, exit_price, direction, pnl.
    """
    if not csv_path.exists():
        return {"updated": 0, "skipped": 0, "reason": "file_not_found"}

    updated = 0
    skipped = 0
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to handle BOM or casing
            row_norm = { (k or '').strip().lstrip('\ufeff'): v for k, v in row.items() }
            tid = (row_norm.get("Id") or row_norm.get("id") or "").strip()
            if not tid:
                skipped += 1
                continue
            t = db.query(Trade).filter(Trade.trade_id == tid).first()
            if not t:
                # Create new trade if missing
                from .models import Trade as TradeModel
                t = TradeModel(trade_id=tid)
                db.add(t)
                db.flush()

            changed = False
            et = _parse_dt(row_norm.get("EnteredAt") or row_norm.get("enteredat"))
            xt = _parse_dt(row_norm.get("ExitedAt") or row_norm.get("exitedat"))
            if et:
                t.entry_time = et
                changed = True
            if xt:
                t.exit_time = xt
                changed = True

            def _safe_float(v: Optional[str]) -> Optional[float]:
                try:
                    return float(v) if v not in (None, "") else None
                except Exception:
                    return None

            ep = _safe_float(row_norm.get("EntryPrice") or row_norm.get("entryprice"))
            if ep is not None:
                t.entry_price = ep
                changed = True
            xp = _safe_float(row_norm.get("ExitPrice") or row_norm.get("exitprice"))
            if xp is not None:
                t.exit_price = xp
                changed = True

            pnl = _safe_float(row_norm.get("PnL") or row_norm.get("pnl"))
            if pnl is not None:
                t.pnl = pnl
                changed = True

            direction = (row_norm.get("Type") or row_norm.get("type") or "").strip().lower()
            if direction in ("long", "short"):
                t.direction = direction
                changed = True

            if changed:
                db.add(t)
                updated += 1

    db.commit()
    return {"updated": updated, "skipped": skipped}


