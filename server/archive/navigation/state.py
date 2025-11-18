from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from db.models import Trade


_current_trade_id: Optional[str] = None


def get_current_trade(db: Session) -> Optional[Trade]:
    global _current_trade_id
    if _current_trade_id:
        t = db.query(Trade).filter(Trade.trade_id == _current_trade_id).first()
        if t:
            return t
    # default to first trade by id
    return db.query(Trade).order_by(Trade.id.asc()).first()


def set_current_trade(trade_id: Optional[str]) -> None:
    global _current_trade_id
    _current_trade_id = trade_id


def get_next_trade(db: Session) -> Optional[Trade]:
    t = get_current_trade(db)
    if not t:
        return None
    next_t = db.query(Trade).filter(Trade.id > t.id).order_by(Trade.id.asc()).first()
    if next_t:
        set_current_trade(next_t.trade_id)
        return next_t
    return t


def get_previous_trade(db: Session) -> Optional[Trade]:
    t = get_current_trade(db)
    if not t:
        return None
    prev_t = db.query(Trade).filter(Trade.id < t.id).order_by(Trade.id.desc()).first()
    if prev_t:
        set_current_trade(prev_t.trade_id)
        return prev_t
    return t


