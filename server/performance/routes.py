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
    delete_trade
)


router = APIRouter(prefix="/performance", tags=["performance"])


@router.post("/log")
async def log_trade(trade: TradeRecord):
    """
    Log a new trade (real or backtested)
    Phase 4C: Auto-update learning profile every 5 trades
    """
    result = save_trade(trade)
    
    # Phase 4C: Auto-update learning profile every 5 trades
    try:
        from .learning import generate_learning_profile
        from .utils import read_logs
        
        logs = read_logs()
        if len(logs) % 5 == 0:
            print(f"[LEARNING] 🎓 Milestone reached: {len(logs)} trades logged. Updating learning profile...")
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
    """Return the last N saved trades (raw list) from performance_logs.json"""
    from .utils import read_logs
    logs = read_logs()
    # Return the last N entries (keeps original order of those entries)
    return logs[-limit:]


@router.get("/trades/{session_id}")
async def get_trade(session_id: str):
    """
    Get a specific trade by session ID
    """
    trade = get_trade_by_session(session_id)
    
    if trade:
        return trade
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

