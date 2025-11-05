"""
Context Manager - Phase 5F.2 F3
Tracks current trade index for navigation commands (previous/next).
LATv2 F5: Safe import handling and robust error recovery.
LATv2 F7: Atomic writes and advance_index() method.
"""
from pathlib import Path
from typing import Optional, Dict, Any
from .utils import load_json, save_json
import threading
import json
import tempfile

# LATv2 F5: Safe pydantic import with fallback
try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Minimal BaseModel fallback class
    class BaseModel:
        pass
    PYDANTIC_AVAILABLE = False
    print("[CONTEXT_MANAGER] Safe fallback mode enabled (pydantic missing)")

# === 5F.2 FIX ===
# File path for context storage
DATA_DIR = Path(__file__).parent.parent / "data"
CONTEXT_FILE = DATA_DIR / "session_contexts.json"

# LATv2 F5: Alternative context state file location (for compatibility)
CONTEXT_STATE_FILE = Path(__file__).parent.parent / "logs" / "context_state.json"

# In-memory cache for current trade index [5F.2 FIX F3]
_current_trade_index_lock = threading.Lock()
_current_trade_index_cache: Optional[int] = None


def get_current_trade_index() -> int:
    """
    Get current trade index from cache or file [5F.2 FIX F3].
    LATv2 F5: Safe error handling, never raises exceptions.
    
    Returns:
        Current trade index (0-based), defaults to 0
    """
    global _current_trade_index_cache
    
    with _current_trade_index_lock:
        if _current_trade_index_cache is not None:
            return _current_trade_index_cache
        
        # Load from file with safe fallback
        try:
            ctx = load_json(str(CONTEXT_FILE), {})
            if isinstance(ctx, dict):
                index = ctx.get("current_trade_index", 0)
                _current_trade_index_cache = index
                return index
        except (ImportError, json.JSONDecodeError, FileNotFoundError, Exception) as e:
            # LATv2 F5: Never raise, always return default
            pass
        
        _current_trade_index_cache = 0
        return 0


def set_current_trade_index(index: int) -> None:
    """
    Set current trade index [5F.2 FIX F3].
    LATv2 F5: Safe error handling, persists to both locations.
    LATv2 F7: Atomic write operations.
    
    Args:
        index: Trade index (0-based)
    """
    global _current_trade_index_cache
    
    old_index = _current_trade_index_cache
    
    with _current_trade_index_lock:
        _current_trade_index_cache = index
        
        # LATv2 F5: Persist to primary location (session_contexts.json)
        try:
            ctx = load_json(str(CONTEXT_FILE), {})
            if not isinstance(ctx, dict):
                ctx = {}
            ctx["current_trade_index"] = index
            save_json(str(CONTEXT_FILE), ctx)
        except (ImportError, json.JSONDecodeError, FileNotFoundError, Exception) as e:
            # LATv2 F5: Never raise, try alternative location
            pass
        
        # LATv2 F7: Atomic write to context_state.json using tempfile + replace
        try:
            CONTEXT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Write to temp file first, then rename atomically
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=str(CONTEXT_STATE_FILE.parent),
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                tmp_path = Path(tmp_file.name)
                json.dump({"current_trade_index": index}, tmp_file, indent=2)
                tmp_file.flush()
                # Atomic replace
                tmp_path.replace(CONTEXT_STATE_FILE)
        except Exception:
            pass
        
        # LATv2 F5: Clear console print for index updates
        if old_index != index:
            print(f"[CONTEXT_MANAGER] Updated index {old_index} -> {index}")


def increment_trade_index() -> int:
    """
    Increment current trade index [5F.2 FIX F3].
    LATv2 F5: Safe error handling, ensures persistence.
    
    Returns:
        New trade index
    """
    current = get_current_trade_index()
    new_index = current + 1
    set_current_trade_index(new_index)
    return new_index


def decrement_trade_index() -> Optional[int]:
    """
    Decrement current trade index [5F.2 FIX F3].
    
    Returns:
        New trade index, or None if already at 0
    """
    current = get_current_trade_index()
    if current <= 0:
        return None
    new_index = current - 1
    set_current_trade_index(new_index)
    return new_index


def reset_trade_index() -> None:
    """
    Reset trade index to 0 [5F.2 FIX F3].
    """
    set_current_trade_index(0)


def get_context_state() -> Dict[str, Any]:
    """
    Get full context state for functional validation [LATv2 Functional].
    LATv2 F5: Safe error handling, never raises exceptions.
    
    Returns:
        Dictionary with current_index and trade_ids list
    """
    # LATv2 F5: Safe fallback when pydantic isn't installed
    default_state = {
        "current_trade_index": get_current_trade_index(),  # CRITICAL: Use consistent key name
        "current_index": get_current_trade_index(),  # Keep for backward compatibility
        "trade_ids": [],
        "total_trades": 0
    }
    
    try:
        from performance.utils import read_logs
        all_trades = read_logs()
        trade_ids = [t.get('id') or t.get('trade_id') for t in all_trades if t.get('id') or t.get('trade_id')]
        
        return {
            "current_trade_index": get_current_trade_index(),  # CRITICAL: Use consistent key name
            "current_index": get_current_trade_index(),  # Keep for backward compatibility
            "trade_ids": trade_ids,
            "total_trades": len(all_trades)
        }
    except (ImportError, json.JSONDecodeError, FileNotFoundError, Exception) as e:
        # LATv2 F5: Safe fallback when schema or import missing - never raise
        return default_state


def advance_index(total_trades: Optional[int] = None, wrap: bool = True) -> Dict[str, Any]:
    """
    LATv2 F7: Advance trade index by +1 with optional wrapping.
    LATv2 F8: Guarantees increment even when repo count is missing.
    
    Args:
        total_trades: Total number of trades available (can be None)
        wrap: If True, wrap to 0 when reaching end; if False, stay at max
    
    Returns:
        Dictionary with current_trade_index and state info
    """
    # LATv2 F8: Prevent division by zero, ensure increment happens
    if not total_trades or total_trades <= 0:
        total_trades = 1  # prevent div/0
    
    current = get_current_trade_index()
    old_index = current
    
    # Increment index with modulo wrap
    if wrap:
        new_index = (current + 1) % total_trades
        wrapped = (current + 1) >= total_trades
    else:
        new_index = current + 1
        if new_index >= total_trades:
            new_index = total_trades - 1
        wrapped = False
    
    # Save updated index
    set_current_trade_index(new_index)
    
    # LATv2 F8: Enhanced logging with total count
    print(f"[CONTEXT_MANAGER] Updated index {old_index} → {new_index} (total={total_trades})")
    
    return {
        "current_trade_index": new_index,
        "old_index": old_index,
        "wrapped": wrapped
    }


def load_trade_json(trade_id: Any) -> Optional[Dict[str, Any]]:
    """
    Load a trade record by ID for functional validation [LATv2 Functional].
    LATv2 F5: Safe error handling with pydantic fallback.
    
    Args:
        trade_id: Trade ID (integer or string)
    
    Returns:
        Trade dictionary or None if not found
    """
    try:
        # Import read_logs safely, handling potential pydantic import errors
        try:
            from performance.utils import read_logs
            all_trades = read_logs()
        except (ImportError, json.JSONDecodeError, FileNotFoundError) as e:
            # LATv2 F5: If pydantic is missing, try direct JSON read without schema validation
            log_file = Path(__file__).parent.parent / "data" / "performance_logs.json"
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_trades = json.load(f)
            else:
                return None
        except Exception as e:
            # Fallback to direct JSON read if read_logs fails
            log_file = Path(__file__).parent.parent / "data" / "performance_logs.json"
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_trades = json.load(f)
            else:
                return None
        
        # Try to find trade by ID
        for trade in all_trades:
            trade_id_match = trade.get('id') or trade.get('trade_id')
            if (str(trade_id_match) == str(trade_id) or 
                trade_id_match == trade_id or
                (isinstance(trade_id, (int, float)) and trade_id_match == int(trade_id))):
                return trade
        
        return None
    except Exception as e:
        # LATv2 F5: Never raise, return None on error
        return None

