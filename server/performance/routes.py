from fastapi import APIRouter, UploadFile, File, Form, Query
from typing import Optional
from .models import TradeRecord, TradeUpdate, PerformanceStats
from .utils import (
    save_trade, 
    update_trade, 
    calculate_stats, 
    backtest_chart,
    get_all_trades,
    get_trade_by_session,
    get_trade_by_id,
    delete_trade
)
from .learning import generate_learning_profile


router = APIRouter(prefix="/performance", tags=["performance"])


@router.post("/log")
async def log_trade(trade: TradeRecord):
    """
    Log a new trade (real or backtested)
    Phase 4C: Auto-update learning profile every 5 trades
    """
    result = save_trade(trade)
    
    # Phase 4D.3: Always update learning profile after logging
    try:
        generate_learning_profile()
    except Exception as e:
        print(f"[LEARNING] Could not auto-update profile: {e}")
    
    return {
        "status": "logged",
        "trade": result
    }


@router.post("/update")
async def update_trade_route(
    session_id: str = Form(...),
    outcome: str = Form(...),
    r_multiple: float = Form(...),
    comments: str = Form("")
):
    """
    Update an existing trade's outcome
    """
    result = update_trade(session_id, outcome, r_multiple, comments)
    
    if result:
        return {
            "status": "updated",
            "trade": result
        }
    else:
        return {
            "status": "error",
            "message": f"Trade {session_id} not found"
        }


@router.get("/stats", response_model=PerformanceStats)
async def get_stats(
    symbol: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None)
):
    """
    Get aggregated performance statistics
    Optional filters: symbol, timeframe
    """
    return calculate_stats(symbol, timeframe)


@router.get("/trades")
async def get_trades(
    limit: Optional[int] = Query(None),
    offset: int = Query(0)
):
    """
    Get all trades with optional pagination
    """
    trades = get_all_trades(limit, offset)
    return {
        "total": len(trades),
        "trades": trades
    }


# Phase 4D.3: Return raw merged trades directly from performance_logs.json
@router.get("/all")
async def get_all(limit: int = Query(100, ge=1, le=1000)):
    """Return all trades sorted by date (newest first) with r_multiple approximated when missing."""
    from .utils import read_logs
    import statistics
    from datetime import datetime
    logs = read_logs()
    
    # Sort by date (newest first) - use timestamp or entry_time
    def get_trade_date(t):
        date_str = t.get("timestamp") or t.get("entry_time") or t.get("trade_day")
        if not date_str:
            return 0
        try:
            # Parse date string - handle "MM/DD/YYYY HH:MM:SS -HH:MM" format
            if isinstance(date_str, str) and "/" in date_str:
                # Format: "10/29/2025 02:34:55 -05:00" or "10/29/2025 00:00:00 -05:00"
                parts = date_str.split()
                if len(parts) >= 2:
                    date_part = parts[0]  # "10/29/2025"
                    time_part = parts[1] if len(parts) > 1 else "00:00:00"
                    # Parse MM/DD/YYYY
                    month, day, year = date_part.split("/")
                    # Parse HH:MM:SS
                    time_parts = time_part.split(":")
                    hour = int(time_parts[0]) if len(time_parts) > 0 else 0
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    second = int(time_parts[2].split(".")[0]) if len(time_parts) > 2 else 0
                    parsed = datetime(int(year), int(month), int(day), hour, minute, second)
                    return parsed.timestamp()
            # Fallback: try ISO format or return 0
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00")).timestamp()
            except:
                return 0
        except Exception:
            return 0
    
    logs_sorted = sorted(logs, key=get_trade_date, reverse=True)
    
    # Take first N (newest)
    slice_logs = logs_sorted[:limit]
    
    # Compute baseline absolute loss for R approximation
    neg = [abs(t.get("pnl", 0)) for t in logs if isinstance(t.get("pnl"), (int, float)) and t.get("pnl", 0) < 0]
    base = statistics.median(neg) if neg else None
    if base:
        for t in slice_logs:
            if t.get("r_multiple") is None and isinstance(t.get("pnl"), (int, float)):
                t["r_multiple"] = round(t["pnl"] / base, 2)
    return slice_logs


@router.get("/trades/{session_id}")
async def get_trade(session_id: str):
    """
    Get a specific trade by session ID or numeric ID
    If session_id is numeric, try to find by ID first, then by session_id
    """
    # Try to parse as numeric ID first
    try:
        trade_id = int(session_id)
        trade = get_trade_by_id(trade_id)
        if trade:
            return {"trade": trade}
    except ValueError:
        pass
    
    # Fallback to session_id lookup
    trade = get_trade_by_session(session_id)
    
    if trade:
        return {"trade": trade}
    else:
        return {
            "status": "error",
            "message": f"Trade {session_id} not found"
        }


@router.delete("/trades/{session_id}")
async def delete_trade_route(session_id: str):
    """
    Delete a trade by session ID
    """
    success = delete_trade(session_id)
    
    if success:
        try:
            generate_learning_profile()
        except Exception:
            pass
        return {
            "status": "deleted",
            "session_id": session_id
        }
    else:
        return {
            "status": "error",
            "message": f"Trade {session_id} not found"
        }


@router.post("/backtest")
async def backtest_chart_route(file: UploadFile = File(...)):
    """
    Upload a chart for backtesting analysis
    (Placeholder for Phase 4B)
    """
    data = await file.read()
    result = backtest_chart(data)
    
    return {
        "filename": file.filename,
        "size": len(data),
        **result
    }

