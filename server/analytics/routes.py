"""
Phase 4C: Analytics Module
Provides statistics and analysis endpoints for entry methods, time patterns, and direction patterns.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, time, timezone
from db.session import get_db
from db.models import Trade, EntryMethod, Setup

router = APIRouter(prefix="/analytics", tags=["analytics"])


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


def calculate_entry_method_stats(trades: List[Trade]) -> Dict[str, Any]:
    """Calculate statistics for a list of trades."""
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": None,
            "avg_pnl": None,
            "avg_r_multiple": None,
            "wins": 0,
            "losses": 0,
            "breakevens": 0,
            "total_pnl": None
        }
    
    wins = [t for t in trades if t.outcome == "win"]
    losses = [t for t in trades if t.outcome == "loss"]
    breakevens = [t for t in trades if t.outcome == "breakeven"]
    
    total_trades = len(trades)
    completed_trades = len(wins) + len(losses) + len(breakevens)
    win_rate = (len(wins) / completed_trades * 100) if completed_trades > 0 else None
    
    pnl_values = [t.pnl for t in trades if t.pnl is not None]
    avg_pnl = sum(pnl_values) / len(pnl_values) if pnl_values else None
    total_pnl = sum(pnl_values) if pnl_values else None
    
    r_values = [t.r_multiple for t in trades if t.r_multiple is not None]
    avg_r_multiple = sum(r_values) / len(r_values) if r_values else None
    
    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2) if win_rate is not None else None,
        "avg_pnl": round(avg_pnl, 2) if avg_pnl is not None else None,
        "avg_r_multiple": round(avg_r_multiple, 2) if avg_r_multiple is not None else None,
        "wins": len(wins),
        "losses": len(losses),
        "breakevens": len(breakevens),
        "total_pnl": round(total_pnl, 2) if total_pnl is not None else None
    }


@router.get("/entry-methods")
def get_entry_method_stats(
    db: Session = Depends(get_db)
):
    """Get statistics for all entry methods."""
    entry_methods = db.query(EntryMethod).all()
    
    result = []
    for em in entry_methods:
        trades = db.query(Trade).filter(Trade.entry_method_id == em.id).all()
        stats = calculate_entry_method_stats(trades)
        
        result.append({
            "entry_method_id": em.id,
            "entry_method_name": em.name,
            "description": em.description,
            **stats
        })
    
    return {"entry_methods": result}


@router.get("/entry-methods/{entry_method_id}")
def get_entry_method_detail(
    entry_method_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed statistics for a specific entry method."""
    entry_method = db.query(EntryMethod).filter(EntryMethod.id == entry_method_id).first()
    if not entry_method:
        raise HTTPException(status_code=404, detail="Entry method not found")
    
    trades = db.query(Trade).filter(Trade.entry_method_id == entry_method_id).all()
    stats = calculate_entry_method_stats(trades)
    
    # Additional details
    bullish_trades = [t for t in trades if t.direction == "long"]
    bearish_trades = [t for t in trades if t.direction == "short"]
    
    bullish_stats = calculate_entry_method_stats(bullish_trades)
    bearish_stats = calculate_entry_method_stats(bearish_trades)
    
    return {
        "entry_method": {
            "id": entry_method.id,
            "name": entry_method.name,
            "description": entry_method.description
        },
        "overall_stats": stats,
        "bullish_stats": bullish_stats,
        "bearish_stats": bearish_stats
    }


@router.get("/comparison")
def compare_entry_methods(
    entry_method_ids: Optional[str] = Query(None, description="Comma-separated entry method IDs"),
    db: Session = Depends(get_db)
):
    """Compare entry methods side-by-side."""
    if not entry_method_ids:
        # Compare all entry methods
        entry_methods = db.query(EntryMethod).all()
        ids = [em.id for em in entry_methods]
    else:
        ids = [int(id.strip()) for id in entry_method_ids.split(",")]
    
    comparison = []
    for em_id in ids:
        entry_method = db.query(EntryMethod).filter(EntryMethod.id == em_id).first()
        if not entry_method:
            continue
        
        trades = db.query(Trade).filter(Trade.entry_method_id == em_id).all()
        stats = calculate_entry_method_stats(trades)
        
        comparison.append({
            "entry_method_id": em_id,
            "entry_method_name": entry_method.name,
            **stats
        })
    
    return {"comparison": comparison}


@router.get("/time-patterns")
def get_time_patterns(
    db: Session = Depends(get_db)
):
    """Get entry method performance by trading session (London, NY, Asian)."""
    entry_methods = db.query(EntryMethod).all()
    
    result = []
    for em in entry_methods:
        trades = db.query(Trade).filter(Trade.entry_method_id == em.id).all()
        
        # Group by session
        london_trades = []
        ny_trades = []
        asian_trades = []
        
        for trade in trades:
            if not trade.entry_time:
                continue
            session = detect_trading_session(trade.entry_time)
            if session == "london":
                london_trades.append(trade)
            elif session == "ny":
                ny_trades.append(trade)
            elif session == "asian":
                asian_trades.append(trade)
        
        result.append({
            "entry_method_id": em.id,
            "entry_method_name": em.name,
            "london": calculate_entry_method_stats(london_trades),
            "ny": calculate_entry_method_stats(ny_trades),
            "asian": calculate_entry_method_stats(asian_trades)
        })
    
    return {"time_patterns": result}


@router.get("/direction-patterns")
def get_direction_patterns(
    db: Session = Depends(get_db)
):
    """Get entry method performance by direction (bullish/bearish)."""
    entry_methods = db.query(EntryMethod).all()
    
    result = []
    for em in entry_methods:
        trades = db.query(Trade).filter(Trade.entry_method_id == em.id).all()
        
        bullish_trades = [t for t in trades if t.direction == "long"]
        bearish_trades = [t for t in trades if t.direction == "short"]
        
        result.append({
            "entry_method_id": em.id,
            "entry_method_name": em.name,
            "bullish": calculate_entry_method_stats(bullish_trades),
            "bearish": calculate_entry_method_stats(bearish_trades)
        })
    
    return {"direction_patterns": result}


@router.get("/overview")
def get_analytics_overview(
    db: Session = Depends(get_db)
):
    """Get overview statistics for the analytics dashboard."""
    all_trades = db.query(Trade).all()
    
    # Overall stats
    overall_stats = calculate_entry_method_stats(all_trades)
    
    # Trades with entry methods linked
    trades_with_entry_method = db.query(Trade).filter(Trade.entry_method_id.isnot(None)).count()
    trades_without_entry_method = len(all_trades) - trades_with_entry_method
    
    # Entry method count
    entry_method_count = db.query(EntryMethod).count()
    
    # Best/worst performing entry methods
    entry_methods = db.query(EntryMethod).all()
    method_performance = []
    for em in entry_methods:
        trades = db.query(Trade).filter(Trade.entry_method_id == em.id).all()
        stats = calculate_entry_method_stats(trades)
        if stats["total_trades"] > 0:
            method_performance.append({
                "entry_method_id": em.id,
                "entry_method_name": em.name,
                "win_rate": stats["win_rate"],
                "avg_r_multiple": stats["avg_r_multiple"],
                "total_trades": stats["total_trades"]
            })
    
    # Sort by win rate (descending)
    method_performance.sort(key=lambda x: x["win_rate"] if x["win_rate"] is not None else 0, reverse=True)
    
    best_method = method_performance[0] if method_performance else None
    worst_method = method_performance[-1] if method_performance else None
    
    return {
        "overall_stats": overall_stats,
        "trades_with_entry_method": trades_with_entry_method,
        "trades_without_entry_method": trades_without_entry_method,
        "entry_method_count": entry_method_count,
        "best_entry_method": best_method,
        "worst_entry_method": worst_method
    }

