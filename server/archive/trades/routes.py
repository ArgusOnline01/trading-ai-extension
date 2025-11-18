from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from db.session import get_db
from db.models import Trade


router = APIRouter(prefix="/trades", tags=["trades"])


def detect_trading_session(entry_time: datetime) -> Optional[str]:
    """
    Detect trading session from entry_time timestamp.
    Assumes entry_time is already in EST/EDT (local time).
    Returns: 'london', 'ny', 'asian', or None
    
    Session times (EST/EDT):
    - Asia: 5 PM - 2 AM (17:00 - 2:00)
    - London: 2 AM - 11 AM (2:00 - 11:00)
    - NY: 8 AM - 4 PM (8:00 - 16:00)
    """
    if not entry_time:
        return None
    
    # Assume entry_time is already in EST/EDT (local time)
    # If timezone-aware, convert to naive datetime (assume it's already EST/EDT)
    if entry_time.tzinfo:
        # Remove timezone info, assume it's already in EST/EDT
        entry_time_local = entry_time.replace(tzinfo=None)
    else:
        # Already timezone-naive, assume it's in EST/EDT
        entry_time_local = entry_time
    
    hour = entry_time_local.hour
    
    # Asia session: 5 PM - 2 AM (17:00 - 23:59 and 0:00 - 2:00)
    # London session: 2 AM - 11 AM (2:00 - 11:00)
    # NY session: 8 AM - 4 PM (8:00 - 16:00)
    # Note: 8 AM - 11 AM overlaps between London and NY, NY takes priority
    
    if hour >= 17 or hour < 2:
        return "asian"
    elif 2 <= hour < 8:
        return "london"  # London session (2 AM - 8 AM)
    elif 8 <= hour < 16:
        return "ny"  # NY session (8 AM - 4 PM) - takes priority over London
    elif 16 <= hour < 17:
        return "asian"  # 4 PM - 5 PM, transition to Asian
    else:
        return "london"  # Default fallback


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
    session: Optional[str] = Query(None, description="Filter by trading session: london|ny|asian"),
    setup_id: Optional[int] = Query(None, description="Filter by setup ID"),
    entry_method_id: Optional[int] = Query(None, description="Filter by entry method ID"),
    has_entry_method: Optional[bool] = Query(None, description="Filter trades with/without entry method"),
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
    if setup_id is not None:
        q = q.filter(Trade.setup_id == setup_id)
    if entry_method_id is not None:
        q = q.filter(Trade.entry_method_id == entry_method_id)
    if has_entry_method is not None:
        if has_entry_method:
            q = q.filter(Trade.entry_method_id.isnot(None))
        else:
            q = q.filter(Trade.entry_method_id.is_(None))
    if session:
        # Filter by trading session (London, NY, Asian)
        session_lower = session.lower()
        if session_lower in ['london', 'ny', 'asian']:
            # Filter trades based on entry_time hour
            # We'll apply this filter after fetching results
            pass  # Will filter after query
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
    rows = q.offset(offset).limit(limit * 2 if session else limit).all()  # Fetch more if session filtering needed
    
    # Filter by session if requested (post-query filtering)
    if session:
        session_lower = session.lower()
        if session_lower in ['london', 'ny', 'asian']:
            filtered_rows = []
            for trade in rows:
                if trade.entry_time:
                    trade_session = detect_trading_session(trade.entry_time)
                    if trade_session == session_lower:
                        filtered_rows.append(trade)
                else:
                    # If no entry_time, skip session filtering for this trade
                    if session_lower == 'london':  # Default behavior
                        filtered_rows.append(trade)
            rows = filtered_rows[:limit]  # Apply limit after filtering
            total = len(filtered_rows)  # Update total count
    
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
                "setup_id": r.setup_id,
                "entry_method_id": r.entry_method_id,
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
        "setup_id": trade.setup_id,
        "entry_method_id": trade.entry_method_id,
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
    setup_id: Optional[str] = Query(None),  # Changed to str to handle empty string
    entry_method_id: Optional[str] = Query(None),  # Changed to str to handle empty string
    db: Session = Depends(get_db)
):
    """Phase 4B: Link a trade to a setup and/or entry method. Pass empty string to unlink."""
    trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    
    # Handle setup_id: empty string or "None" means unlink, otherwise link
    if setup_id is not None:
        if setup_id == "" or setup_id.lower() == "none":
            trade.setup_id = None  # Unlink
        else:
            try:
                setup_id_int = int(setup_id)
                from db.models import Setup
                setup = db.query(Setup).filter(Setup.id == setup_id_int).first()
                if not setup:
                    raise HTTPException(status_code=404, detail=f"Setup {setup_id_int} not found")
                trade.setup_id = setup_id_int
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid setup_id: {setup_id}")
    
    # Handle entry_method_id: empty string or "None" means unlink, otherwise link
    if entry_method_id is not None:
        if entry_method_id == "" or entry_method_id.lower() == "none":
            trade.entry_method_id = None  # Unlink
        else:
            try:
                entry_method_id_int = int(entry_method_id)
                from db.models import EntryMethod
                entry_method = db.query(EntryMethod).filter(EntryMethod.id == entry_method_id_int).first()
                if not entry_method:
                    raise HTTPException(status_code=404, detail=f"Entry method {entry_method_id_int} not found")
                trade.entry_method_id = entry_method_id_int
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid entry_method_id: {entry_method_id}")
    
    db.commit()
    db.refresh(trade)
    
    return {
        "message": "Trade linked successfully",
        "trade_id": trade_id,
        "setup_id": trade.setup_id,
        "entry_method_id": trade.entry_method_id
    }


