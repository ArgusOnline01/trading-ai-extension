"""
Session Cache for Visual Trade Copilot
Phase 3C: Hybrid Vision → Reasoning Bridge

In-memory cache for GPT-4o vision summaries.
Persists while server runs, cleared per session or on new chart uploads.
"""

from collections import defaultdict
from typing import Any, Optional
import time


class SessionCache:
    """
    Simple in-memory cache for session data.
    Stores GPT-4o vision summaries to avoid re-analyzing the same chart.
    """
    
    def __init__(self):
        self.data = defaultdict(dict)
        self.timestamps = defaultdict(dict)
        
    def get(self, session_id: str, key: str) -> Optional[Any]:
        """
        Get cached value for a session.
        
        Args:
            session_id: Session identifier
            key: Cache key (e.g., "vision_summary")
            
        Returns:
            Cached value or None if not found
        """
        return self.data[session_id].get(key)
    
    def set(self, session_id: str, key: str, value: Any) -> None:
        """
        Set cached value for a session.
        
        Args:
            session_id: Session identifier
            key: Cache key
            value: Value to cache
        """
        self.data[session_id][key] = value
        self.timestamps[session_id][key] = time.time()
        print(f"[CACHE] Set {key} for session {session_id}")
    
    def clear(self, session_id: str) -> None:
        """
        Clear all cached data for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.data:
            del self.data[session_id]
        if session_id in self.timestamps:
            del self.timestamps[session_id]
        print(f"[CACHE] Cleared session {session_id}")
    
    def clear_key(self, session_id: str, key: str) -> None:
        """
        Clear specific cached key for a session.
        
        Args:
            session_id: Session identifier
            key: Cache key to clear
        """
        if session_id in self.data and key in self.data[session_id]:
            del self.data[session_id][key]
        if session_id in self.timestamps and key in self.timestamps[session_id]:
            del self.timestamps[session_id][key]
        print(f"[CACHE] Cleared {key} for session {session_id}")
    
    def get_age(self, session_id: str, key: str) -> Optional[float]:
        """
        Get age of cached value in seconds.
        
        Args:
            session_id: Session identifier
            key: Cache key
            
        Returns:
            Age in seconds or None if not found
        """
        if session_id in self.timestamps and key in self.timestamps[session_id]:
            return time.time() - self.timestamps[session_id][key]
        return None
    
    def has(self, session_id: str, key: str) -> bool:
        """
        Check if cache has a value.
        
        Args:
            session_id: Session identifier
            key: Cache key
            
        Returns:
            True if cached value exists
        """
        return session_id in self.data and key in self.data[session_id]
    
    def stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_sessions = len(self.data)
        total_keys = sum(len(keys) for keys in self.data.values())
        
        return {
            "total_sessions": total_sessions,
            "total_keys": total_keys,
            "sessions": list(self.data.keys())
        }


# Global cache instance
_cache = SessionCache()


def get_cache() -> SessionCache:
    """Get the global cache instance"""
    return _cache

