from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from .state import get_current_trade, get_next_trade, get_previous_trade, set_current_trade


router = APIRouter(prefix="/navigation", tags=["navigation"])


@router.get("/current")
def current(db: Session = Depends(get_db)):
    t = get_current_trade(db)
    if not t:
        return {"trade": None}
    return {"trade_id": t.trade_id, "symbol": t.symbol, "outcome": t.outcome}


@router.get("/next")
def next_trade(db: Session = Depends(get_db)):
    t = get_next_trade(db)
    if not t:
        return {"trade": None}
    return {"trade_id": t.trade_id, "symbol": t.symbol, "outcome": t.outcome}


@router.get("/previous")
def previous_trade(db: Session = Depends(get_db)):
    t = get_previous_trade(db)
    if not t:
        return {"trade": None}
    return {"trade_id": t.trade_id, "symbol": t.symbol, "outcome": t.outcome}


@router.post("/set/{trade_id}")
def set_current(trade_id: str):
    set_current_trade(trade_id)
    return {"ok": True, "trade_id": trade_id}


