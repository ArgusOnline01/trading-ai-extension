from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from db.session import get_db
from db.models import Trade


router = APIRouter(prefix="/trades", tags=["trades"])


def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(val, fmt)
        except Exception:
            continue
    return None


@router.get("")
def list_trades(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    outcome: Optional[str] = Query(None, description="win|loss|breakeven"),
    symbol: Optional[str] = Query(None),
    direction: Optional[str] = Query(None, description="long|short"),
    start_time: Optional[str] = Query(None, description="Filter entry_time from inclusive (YYYY-MM-DD or ISO)"),
    end_time: Optional[str] = Query(None, description="Filter entry_time to inclusive (YYYY-MM-DD or ISO)"),
    min_pnl: Optional[float] = Query(None),
    max_pnl: Optional[float] = Query(None),
    min_r: Optional[float] = Query(None),
    max_r: Optional[float] = Query(None),
    session_id: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("entry_time", description="id|entry_time|exit_time|pnl|r_multiple"),
    sort_dir: Optional[str] = Query("asc", description="asc|desc"),
):
    q = db.query(Trade)
    if outcome:
        o = (outcome or '').lower()
        if o == 'win':
            q = q.filter(or_(Trade.outcome == 'win', and_(Trade.outcome == None, Trade.pnl != None, Trade.pnl > 0)))
        elif o == 'loss':
            q = q.filter(or_(Trade.outcome == 'loss', and_(Trade.outcome == None, Trade.pnl != None, Trade.pnl < 0)))
        elif o == 'breakeven':
            q = q.filter(or_(Trade.outcome == 'breakeven', and_(Trade.outcome == None, Trade.pnl != None, Trade.pnl == 0)))
    if symbol:
        like = f"%{symbol}%"
        q = q.filter(Trade.symbol.ilike(like))
    if direction:
        q = q.filter(Trade.direction == direction)
    if session_id:
        q = q.filter(Trade.session_id == session_id)
    st = _parse_dt(start_time)
    et = _parse_dt(end_time)
    if st:
        q = q.filter(or_(and_(Trade.entry_time != None, Trade.entry_time >= st), and_(Trade.exit_time != None, Trade.exit_time >= st)))
    if et:
        q = q.filter(or_(and_(Trade.entry_time != None, Trade.entry_time <= et), and_(Trade.exit_time != None, Trade.exit_time <= et)))
    if min_pnl is not None:
        q = q.filter(Trade.pnl != None).filter(Trade.pnl >= min_pnl)
    if max_pnl is not None:
        q = q.filter(Trade.pnl != None).filter(Trade.pnl <= max_pnl)
    if min_r is not None:
        q = q.filter(Trade.r_multiple != None).filter(Trade.r_multiple >= min_r)
    if max_r is not None:
        q = q.filter(Trade.r_multiple != None).filter(Trade.r_multiple <= max_r)
    # Sorting
    sort_map = {
        "id": Trade.id,
        "entry_time": Trade.entry_time,
        "exit_time": Trade.exit_time,
        "pnl": Trade.pnl,
        "r_multiple": Trade.r_multiple,
    }
    sort_col = sort_map.get((sort_by or "entry_time").lower(), Trade.entry_time)
    if (sort_dir or "asc").lower() == "desc":
        # Put rows with null sort keys last
        q = q.order_by((sort_col.is_(None)).asc(), sort_col.desc())
    else:
        q = q.order_by((sort_col.is_(None)).asc(), sort_col.asc())
    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "trade_id": r.trade_id,
                "symbol": r.symbol,
                "entry_time": r.entry_time,
                "exit_time": r.exit_time,
                "direction": r.direction,
                "outcome": r.outcome,
                "pnl": r.pnl,
                "r_multiple": r.r_multiple,
            }
            for r in rows
        ],
    }


@router.get("/{trade_id}")
def get_trade(trade_id: str, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {
        "trade_id": trade.trade_id,
        "symbol": trade.symbol,
        "entry_time": trade.entry_time,
        "exit_time": trade.exit_time,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "direction": trade.direction,
        "outcome": trade.outcome,
        "pnl": trade.pnl,
        "r_multiple": trade.r_multiple,
        "chart_url": trade.chart_url,
        "session_id": trade.session_id,
        "created_at": trade.created_at,
    }


# Basic CRUD (POST/PUT/DELETE) - minimal for Phase 4A
from pydantic import BaseModel


class TradeCreate(BaseModel):
    trade_id: str
    symbol: Optional[str] = None
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    direction: Optional[str] = None
    outcome: Optional[str] = None
    pnl: Optional[float] = None
    r_multiple: Optional[float] = None
    chart_url: Optional[str] = None
    session_id: Optional[str] = None


@router.post("")
def create_trade(payload: TradeCreate, db: Session = Depends(get_db)):
    if db.query(Trade).filter(Trade.trade_id == payload.trade_id).first():
        raise HTTPException(status_code=400, detail="trade_id already exists")
    t = Trade(
        trade_id=payload.trade_id,
        symbol=payload.symbol,
        entry_price=payload.entry_price,
        exit_price=payload.exit_price,
        direction=payload.direction,
        outcome=payload.outcome,
        pnl=payload.pnl,
        r_multiple=payload.r_multiple,
        chart_url=payload.chart_url,
        session_id=payload.session_id,
    )
    db.add(t)
    db.commit()
    return {"ok": True, "trade_id": t.trade_id}


class TradeUpdate(BaseModel):
    symbol: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    direction: Optional[str] = None
    outcome: Optional[str] = None
    pnl: Optional[float] = None
    r_multiple: Optional[float] = None
    chart_url: Optional[str] = None
    session_id: Optional[str] = None


@router.put("/{trade_id}")
def update_trade(trade_id: str, payload: TradeUpdate, db: Session = Depends(get_db)):
    t = db.query(Trade).filter(Trade.trade_id == trade_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Trade not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(t, field, value)
    db.commit()
    return {"ok": True}


@router.delete("/{trade_id}")
def delete_trade(trade_id: str, db: Session = Depends(get_db)):
    t = db.query(Trade).filter(Trade.trade_id == trade_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(t)
    db.commit()
    return {"ok": True}


@router.post("/{trade_id}/link-setup")
def link_trade_to_setup(
    trade_id: str,
    setup_id: Optional[int] = Query(None),
    entry_method_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Phase 4B: Link a trade to a setup and/or entry method"""
    trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    
    if setup_id is not None:
        from db.models import Setup
        setup = db.query(Setup).filter(Setup.id == setup_id).first()
        if not setup:
            raise HTTPException(status_code=404, detail=f"Setup {setup_id} not found")
        trade.setup_id = setup_id
    
    if entry_method_id is not None:
        from db.models import EntryMethod
        entry_method = db.query(EntryMethod).filter(EntryMethod.id == entry_method_id).first()
        if not entry_method:
            raise HTTPException(status_code=404, detail=f"Entry method {entry_method_id} not found")
        trade.entry_method_id = entry_method_id
    
    db.commit()
    db.refresh(trade)
    
    return {
        "message": "Trade linked successfully",
        "trade_id": trade_id,
        "setup_id": trade.setup_id,
        "entry_method_id": trade.entry_method_id
    }


