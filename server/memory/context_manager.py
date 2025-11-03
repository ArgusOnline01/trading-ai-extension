"""
Context Manager - Phase 5F.2 F3
Tracks current trade index for navigation commands (previous/next).
"""
from pathlib import Path
from typing import Optional, Dict, Any
from .utils import load_json, save_json
import threading

# === 5F.2 FIX ===
# File path for context storage
DATA_DIR = Path(__file__).parent.parent / "data"
CONTEXT_FILE = DATA_DIR / "session_contexts.json"

# In-memory cache for current trade index [5F.2 FIX F3]
_current_trade_index_lock = threading.Lock()
_current_trade_index_cache: Optional[int] = None


def get_current_trade_index() -> int:
    """
    Get current trade index from cache or file [5F.2 FIX F3].
    
    Returns:
        Current trade index (0-based), defaults to 0
    """
    global _current_trade_index_cache
    
    with _current_trade_index_lock:
        if _current_trade_index_cache is not None:
            return _current_trade_index_cache
        
        # Load from file
        try:
            ctx = load_json(str(CONTEXT_FILE), {})
            if isinstance(ctx, dict):
                index = ctx.get("current_trade_index", 0)
                _current_trade_index_cache = index
                return index
        except Exception:
            pass
        
        _current_trade_index_cache = 0
        return 0


def set_current_trade_index(index: int) -> None:
    """
    Set current trade index [5F.2 FIX F3].
    
    Args:
        index: Trade index (0-based)
    """
    global _current_trade_index_cache
    
    with _current_trade_index_lock:
        _current_trade_index_cache = index
        
        # Persist to file
        try:
            ctx = load_json(str(CONTEXT_FILE), {})
            if not isinstance(ctx, dict):
                ctx = {}
            ctx["current_trade_index"] = index
            save_json(str(CONTEXT_FILE), ctx)
            print(f"[CONTEXT_MANAGER] Set current_trade_index to {index}")
        except Exception as e:
            print(f"[CONTEXT_MANAGER] Failed to save index: {e}")


def increment_trade_index() -> int:
    """
    Increment current trade index [5F.2 FIX F3].
    
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

