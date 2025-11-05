from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import Trade


def backfill_trades(db: Session) -> dict:
    """Backfill missing outcome and entry_time for existing trades.
    - outcome: derive from pnl if missing (win/loss/breakeven)
    - entry_time: set to created_at if missing
    """
    updated_outcome = 0
    updated_entry_time = 0

    for t in db.query(Trade).all():
        changed = False
        if t.outcome is None and t.pnl is not None:
            if t.pnl > 0:
                t.outcome = "win"
            elif t.pnl < 0:
                t.outcome = "loss"
            else:
                t.outcome = "breakeven"
            updated_outcome += 1
            changed = True

        if t.entry_time is None and t.created_at is not None:
            t.entry_time = t.created_at
            updated_entry_time += 1
            changed = True

        if changed:
            db.add(t)

    db.commit()
    return {"outcome": updated_outcome, "entry_time": updated_entry_time}


