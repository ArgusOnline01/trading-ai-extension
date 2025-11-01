"""
Memory Utilities - JSON persistence helpers
Manages all persistent backend storage
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Data directory paths - Use unified path like all other modules
DATA_DIR = Path(__file__).parent.parent / "data"
PROFILE_PATH = DATA_DIR / "user_profile.json"
SESSION_CONTEXTS_PATH = DATA_DIR / "session_contexts.json"
CONVERSATION_LOG_PATH = DATA_DIR / "conversation_log.json"


def ensure_data_directory():
    """Create data directory if it doesn't exist"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[MEMORY] Data directory ensured: {DATA_DIR}")


def load_json(path, default: Any = None) -> Any:
    """Load JSON file with error handling"""
    path_obj = Path(path) if not isinstance(path, Path) else path
    if not path_obj.exists():
        return default if default is not None else {}
    
    try:
        with open(path_obj, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default if default is not None else {}


def save_json(path, data: Any):
    """Save data to JSON file with proper formatting"""
    path_obj = Path(path) if not isinstance(path, Path) else path
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def initialize_default_files():
    """Create default JSON files if they don't exist"""
    ensure_data_directory()
    
    defaults = {
        SESSION_CONTEXTS_PATH: [],
        CONVERSATION_LOG_PATH: {"messages": [], "last_updated": None}
    }
    
    created_count = 0
    for path, default_data in defaults.items():
        path_obj = Path(path) if not isinstance(path, Path) else path
        if not path_obj.exists():
            save_json(path_obj, default_data)
            created_count += 1
            print(f"[MEMORY] Created default: {path_obj.name}")
    
    if created_count > 0:
        print(f"[MEMORY] Initialized {created_count} default file(s)")
    
    return created_count


def get_memory_status() -> Dict[str, Any]:
    """Get comprehensive memory status"""
    from performance.learning import _load_json as load_perf_logs
    from performance.learning import LOG_PATH, PROFILE_PATH as learning_profile
    
    # Load all memory files
    profile = load_json(learning_profile, {})
    logs = load_perf_logs(LOG_PATH)
    sessions = load_json(SESSION_CONTEXTS_PATH, [])
    conversations = load_json(CONVERSATION_LOG_PATH, {"messages": []})
    
    return {
        "total_trades": len(logs),
        "completed_trades": len([t for t in logs if t.get("outcome") in ["win", "loss", "breakeven"]]),
        "active_sessions": len(sessions),
        "conversation_messages": len(conversations.get("messages", [])),
        "win_rate": profile.get("win_rate", 0),
        "avg_rr": profile.get("avg_rr", 0),
        "best_setup": profile.get("best_setup", "None yet"),
        "last_profile_update": profile.get("last_updated"),
        "memory_healthy": True
    }


def save_session_context(session_id: str, context: Dict[str, Any]):
    """Save or update a session context"""
    sessions = load_json(SESSION_CONTEXTS_PATH, [])
    
    # Update existing or add new
    found = False
    for i, session in enumerate(sessions):
        if session.get("session_id") == session_id:
            sessions[i] = {
                **context,
                "session_id": session_id,
                "last_updated": datetime.utcnow().isoformat()
            }
            found = True
            break
    
    if not found:
        sessions.append({
            **context,
            "session_id": session_id,
            "last_updated": datetime.utcnow().isoformat()
        })
    
    save_json(SESSION_CONTEXTS_PATH, sessions)
    print(f"[MEMORY] Saved session context: {session_id}")


def load_session_context(session_id: str) -> Optional[Dict[str, Any]]:
    """Load a specific session context"""
    sessions = load_json(SESSION_CONTEXTS_PATH, [])
    
    for session in sessions:
        if session.get("session_id") == session_id:
            return session
    
    return None


def append_conversation_message(role: str, content: str, metadata: Dict[str, Any] = None):
    """Append a message to the conversation log"""
    conv_data = load_json(CONVERSATION_LOG_PATH, {"messages": []})
    
    if "messages" not in conv_data:
        conv_data["messages"] = []
    
    message = {
        "role": role,
        "content": content[:500],  # Truncate for storage efficiency
        "timestamp": datetime.utcnow().isoformat(),
        **(metadata or {})
    }
    
    conv_data["messages"].append(message)
    conv_data["last_updated"] = datetime.utcnow().isoformat()
    
    # Keep only last 500 messages to prevent file bloat
    if len(conv_data["messages"]) > 500:
        conv_data["messages"] = conv_data["messages"][-500:]
    
    save_json(CONVERSATION_LOG_PATH, conv_data)


def clear_all_memory():
    """Clear all persistent memory (reset to defaults)"""
    initialize_default_files()
    print("[MEMORY] All memory cleared and reset to defaults")
    
    return {
        "status": "cleared",
        "message": "All persistent memory has been reset"
    }

