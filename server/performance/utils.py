import json
import os
from pathlib import Path
from datetime import datetime
import statistics
import statistics
from datetime import datetime
from typing import List, Optional, Dict, Any
from .models import TradeRecord
import time
import threading

# === 5F.2 FIX ===
# Phase 4D.3: Use absolute path anchored to this module to avoid CWD issues
DATA_DIR = Path(__file__).parent.parent / "data"
LOG_FILE = str(DATA_DIR / "performance_logs.json")

# TTL cache for read_logs() [5F.2 FIX F1]
_logs_cache = None
_logs_cache_timestamp = 0
_logs_cache_lock = threading.Lock()
LOGS_CACHE_TTL = 10  # seconds


def ensure_data_dir():
    """Ensure data directory and empty log file exist"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            json.dump([], f)


def read_logs() -> List[Dict[str, Any]]:
    """Read all trade logs from JSON file with TTL cache [5F.2 FIX F1]"""
    global _logs_cache, _logs_cache_timestamp
    
    current_time = time.time()
    
    with _logs_cache_lock:
        # Check if cache is valid
        if _logs_cache is not None and (current_time - _logs_cache_timestamp) < LOGS_CACHE_TTL:
            print(f"[PERFORMANCE] Using cached logs (age: {current_time - _logs_cache_timestamp:.1f}s)")
            return _logs_cache
        
        # Cache expired or not set - read from file
        ensure_data_dir()
        try:
            with open(LOG_FILE, 'r') as f:
                raw = json.load(f)
                _logs_cache = [normalize_trade(trade) for trade in raw]
                _logs_cache_timestamp = current_time
                print(f"[PERFORMANCE] Loaded {len(_logs_cache)} trades from file (cache set)")
                return _logs_cache
        except (FileNotFoundError, json.JSONDecodeError):
            _logs_cache = []
            _logs_cache_timestamp = current_time
            return _logs_cache


def invalidate_logs_cache():
    """Invalidate the logs cache (call after write operations) [5F.2 FIX F1]"""
    global _logs_cache, _logs_cache_timestamp
    with _logs_cache_lock:
        _logs_cache = None
        _logs_cache_timestamp = 0
        print("[PERFORMANCE] Logs cache invalidated")


def write_logs(logs: List[Dict[str, Any]]):
    """Write trade logs to JSON file"""
    ensure_data_dir()
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)
    invalidate_logs_cache()  # [5F.2 FIX F1] Clear cache after write


def _parse_timestamp(entry_time: str) -> str:
    """Parse entry_time like '10/29/2025 02:34:55 -05:00' to ISO string; fallback to original."""
    if not entry_time:
        return None
    try:
        dt = datetime.strptime(entry_time, "%m/%d/%Y %H:%M:%S %z")
        return dt.isoformat()
    except Exception:
        try:
            # Some strings may lack timezone
            dt = datetime.strptime(entry_time, "%m/%d/%Y %H:%M:%S")
            return dt.isoformat()
        except Exception:
            return entry_time


def normalize_trade(trade: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure common fields exist: outcome, r_multiple (if available), timestamp.
    Does not mutate file on disk; only normalizes the returned objects.
    """
    if not isinstance(trade, dict):
        return trade
    normalized = dict(trade)

    # Outcome: prefer explicit outcome, otherwise derive from pnl or label
    outcome = normalized.get("outcome")
    if not outcome:
        pnl = normalized.get("pnl")
        label = str(normalized.get("label", "")).lower()
        if isinstance(pnl, (int, float)):
            if pnl > 0:
                outcome = "win"
            elif pnl < 0:
                outcome = "loss"
            else:
                outcome = "breakeven"
        elif label in ("win", "loss", "breakeven"):
            outcome = label
    if outcome:
        normalized["outcome"] = outcome

    # R multiple: map from rr/expected_r if present
    if normalized.get("r_multiple") is None:
        if normalized.get("rr") is not None:
            normalized["r_multiple"] = normalized.get("rr")
        elif normalized.get("expected_r") is not None:
            normalized["r_multiple"] = normalized.get("expected_r")

    # Timestamp: parse entry_time or use existing
    if not normalized.get("timestamp"):
        ts = _parse_timestamp(normalized.get("entry_time") or normalized.get("trade_day"))
        if ts:
            normalized["timestamp"] = ts

    return normalized


def save_trade(trade: TradeRecord) -> Dict[str, Any]:
    """
    Save a new trade record
    Returns the saved trade with added metadata
    """
    logs = read_logs()
    trade_dict = trade.dict()
    
    # Add metadata
    trade_dict['id'] = len(logs) + 1
    trade_dict['created_at'] = datetime.utcnow().isoformat()
    
    logs.append(trade_dict)
    write_logs(logs)
    
    print(f"[PERFORMANCE] Saved trade #{trade_dict['id']} for {trade.symbol}")
    return trade_dict


def update_trade(session_id: str, outcome: str, r_multiple: float, comments: str = "") -> Optional[Dict[str, Any]]:
    """
    Update an existing trade's outcome
    Returns the updated trade or None if not found
    """
    logs = read_logs()
    
    for trade in logs:
        if trade["session_id"] == session_id:
            trade["outcome"] = outcome
            trade["r_multiple"] = r_multiple
            if comments:
                trade["comments"] = comments
            trade["updated_at"] = datetime.utcnow().isoformat()
            
            write_logs(logs)
            print(f"[PERFORMANCE] Updated trade {session_id}: {outcome} at {r_multiple}R")
            return trade
    
    print(f"[PERFORMANCE] Trade {session_id} not found for update")
    return None


def get_trade_by_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific trade by session ID"""
    logs = read_logs()
    for trade in logs:
        if trade["session_id"] == session_id:
            return trade
    return None


def get_trade_by_id(trade_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific trade by numeric ID"""
    logs = read_logs()
    for trade in logs:
        # Check both 'id' and 'trade_id' fields
        if trade.get('id') == trade_id or trade.get('trade_id') == trade_id:
            return trade
    return None


def calculate_stats(symbol: Optional[str] = None, timeframe: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculate aggregated performance statistics
    Optional filters: symbol, timeframe
    """
    logs = read_logs()
    
    # Apply filters
    if symbol:
        logs = [t for t in logs if t.get("symbol") == symbol]
    if timeframe:
        logs = [t for t in logs if t.get("timeframe") == timeframe]
    
    if not logs:
        return {
            "total_trades": 0,
            "win_rate": None,
            "avg_r": None,
            "profit_factor": None,
            "best_trade": None,
            "worst_trade": None,
            "total_r": None,
            "wins": 0,
            "losses": 0,
            "breakevens": 0
        }
    
    # Categorize trades
    wins = [t for t in logs if t.get("outcome") == "win"]
    losses = [t for t in logs if t.get("outcome") == "loss"]
    breakevens = [t for t in logs if t.get("outcome") == "breakeven"]
    
    # Establish baseline risk from median absolute loss (if explicit R not provided)
    def baseline_risk(trades):
        neg = [abs(t.get("pnl", 0)) for t in trades if isinstance(t.get("pnl"), (int, float)) and t.get("pnl", 0) < 0]
        return statistics.median(neg) if neg else None
    base = baseline_risk(logs)

    # R multiples (explicit or approximated)
    def derive_r(trade):
        r = trade.get("r_multiple")
        if r is None and base and isinstance(trade.get("pnl"), (int, float)):
            r = round(trade["pnl"] / base, 2)
        return r

    r_values = [derive_r(t) for t in logs]
    r_values = [r for r in r_values if r is not None]
    winning_r = [derive_r(t) for t in wins]
    winning_r = [r for r in winning_r if r is not None and r >= 0]
    losing_r = [abs(derive_r(t)) for t in losses]
    losing_r = [r for r in losing_r if r is not None]
    
    # Calculate metrics
    total_trades = len(logs)
    completed_trades = len(wins) + len(losses) + len(breakevens)
    win_rate = (len(wins) / completed_trades * 100) if completed_trades > 0 else None
    avg_r = statistics.mean(r_values) if r_values else None
    total_r = sum(r_values) if r_values else None
    
    # Profit factor: (sum of winning R) / (sum of losing R)
    profit_factor = None
    if winning_r and losing_r:
        total_wins = sum(winning_r)
        total_losses = sum(losing_r)
        profit_factor = total_wins / total_losses if total_losses > 0 else None
    
    best_trade = max(r_values) if r_values else None
    worst_trade = min(r_values) if r_values else None
    
    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1) if win_rate is not None else None,
        "avg_r": round(avg_r, 2) if avg_r is not None else None,
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "best_trade": round(best_trade, 2) if best_trade is not None else None,
        "worst_trade": round(worst_trade, 2) if worst_trade is not None else None,
        "total_r": round(total_r, 2) if total_r is not None else None,
        "wins": len(wins),
        "losses": len(losses),
        "breakevens": len(breakevens)
    }


def backtest_chart(file_bytes: bytes) -> Dict[str, Any]:
    """
    Placeholder for future GPT-powered chart backtesting
    Will analyze uploaded chart images and predict outcomes
    """
    # TODO: Phase 4B - Implement GPT-based chart analysis
    return {
        "status": "analyzed",
        "predicted_outcome": "win",
        "confidence": 0.75,
        "notes": "Backtest analysis coming in Phase 4B"
    }


def get_all_trades(limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get all trades with optional pagination
    """
    logs = read_logs()
    
    # Sort by timestamp (newest first)
    logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    if limit:
        return logs[offset:offset + limit]
    return logs[offset:]


def delete_trade(session_id: str) -> bool:
    """Delete a trade by session ID"""
    logs = read_logs()
    initial_len = len(logs)
    
    logs = [t for t in logs if t["session_id"] != session_id]
    
    if len(logs) < initial_len:
        write_logs(logs)
        print(f"[PERFORMANCE] Deleted trade {session_id}")
        return True
    
    print(f"[PERFORMANCE] Trade {session_id} not found for deletion")
    return False

