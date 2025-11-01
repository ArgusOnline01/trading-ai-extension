"""
System Command Recognition
Parses and executes system-level commands like "show my stats", "delete last trade"
"""

import difflib
from typing import Dict, Any, Optional, Tuple
from .utils import get_memory_status, load_json, save_json
from performance.learning import _load_json, LOG_PATH, PROFILE_PATH, generate_learning_profile
import os


# Command patterns (lowercase for fuzzy matching)
# IMPORTANT: Order matters - more specific patterns should come first!
COMMAND_PATTERNS = {
    "stats": ["show my stats", "show stats", "my performance", "how am i doing", "my results"],
    "restore_last": ["restore last trade", "undo delete", "add it back", "re-add last trade", "undelete last trade", "put it back", "bring it back"],
    "delete_last": ["delete last trade", "remove last trade", "delete recent trade"],
    "switch_session": ["switch session", "change session", "load session", "open session", "go to session"],
    "create_session": ["create session", "new session", "start session", "add session", "make session"],
    "delete_session": ["delete session", "remove session"],
    "rename_session": ["rename session", "change session name", "edit session title"],
    "clear_memory": ["clear memory", "reset memory", "delete all data", "wipe memory"],
    "model_info": ["what model", "which model", "current model", "what ai", "which gpt"],
    "list_sessions": ["list sessions", "show sessions", "my sessions", "active sessions"],
    "open_teach_copilot": ["open teach copilot", "start teaching", "teach copilot", "open teaching", "show teach copilot", "launch teaching mode", "begin teaching", "review trades one by one", "lets review the trades", "teach me", "let's teach", "redo this in teach mode", "lets redo this", "redo in teach mode", "do this in teaching", "open teaching for this trade", "teach me about this", "review this trade", "lets review this"],
    "close_teach_copilot": ["close teach copilot", "pause teaching", "pause teaching mode", "close teaching", "exit teaching mode", "stop teaching", "discard teaching lesson", "cancel teaching"],
    "help": ["help", "commands", "what can you do", "available commands", "show me commands", "what commands", "list commands", "what can i ask", "how can you help"]
}


def normalize_input(text: str) -> str:
    """
    Normalize user input by removing question words and polite phrases
    Examples: "can you restore" -> "restore", "how about deleting" -> "deleting"
    """
    import re
    # Remove common question/polite prefixes
    prefixes = [
        r"^(can you|could you|would you|please|can we|could we|will you|would you mind) +",
        r"^(how about|what about|let's|let us) +",
        r"^(i want to|i need to|i'd like to|i wish to) +",
        r"^(maybe|perhaps|do you think you can) +",
    ]
    
    normalized = text.lower().strip()
    for prefix_pattern in prefixes:
        normalized = re.sub(prefix_pattern, "", normalized, flags=re.IGNORECASE)
    
    # Remove trailing question marks and extra whitespace
    normalized = normalized.rstrip("?.,! ").strip()
    
    return normalized


def detect_command(user_input: str) -> Optional[str]:
    """
    Detect if user input is a system command using fuzzy matching
    Handles both direct commands and question phrasings
    Returns command key if detected, None otherwise
    """
    user_lower = user_input.lower().strip()
    
    # Normalize input to handle question phrasings
    normalized = normalize_input(user_lower)
    
    # Try exact matches first (highest priority) - both original and normalized
    for cmd_key, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            if user_lower == pattern or normalized == pattern:
                return cmd_key
    
    # Then try fuzzy matching with reasonable threshold
    best_match = None
    best_score = 0.0
    
    # Check both original and normalized input
    inputs_to_check = [user_lower, normalized] if normalized != user_lower else [user_lower]
    
    for check_input in inputs_to_check:
        for cmd_key, patterns in COMMAND_PATTERNS.items():
            for pattern in patterns:
                # Use difflib for fuzzy matching (75% similarity to catch question phrasings)
                similarity = difflib.SequenceMatcher(None, check_input, pattern).ratio()
                if similarity > best_score and similarity > 0.75:
                    best_score = similarity
                    best_match = cmd_key
    
    if best_match:
        return best_match
    
    # Finally, try substring matching - check if pattern is contained in input
    # This catches "can you restore last trade" -> "restore last trade"
    for cmd_key, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            # Check if pattern appears in original or normalized input
            if len(pattern) > 6:
                if pattern in user_lower or pattern in normalized:
                    return cmd_key
    
    return None


def execute_command(command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute a detected system command
    Returns formatted response dict
    """
    context = context or {}
    
    if command == "stats":
        return execute_stats_command()
    
    elif command == "delete_last":
        return execute_delete_last_command()
    
    elif command == "restore_last":
        return execute_restore_last_command()
    
    elif command == "switch_session":
        return execute_switch_session_command(context)
    
    elif command == "create_session":
        return execute_create_session_command(context)
    
    elif command == "delete_session":
        return execute_delete_session_command(context)
    
    elif command == "rename_session":
        return execute_rename_session_command(context)
    
    elif command == "clear_memory":
        return execute_clear_memory_command()
    
    elif command == "model_info":
        return execute_model_info_command(context)
    
    elif command == "list_sessions":
        return execute_list_sessions_command(context)
    
    elif command == "open_teach_copilot":
        # Try to extract trade_id from context or command text
        trade_id = None
        if context:
            # Check for detected trade
            detected_trade = context.get('detected_trade')
            if detected_trade:
                trade_id = detected_trade.get('id') or detected_trade.get('trade_id')
            elif context.get('trade_id'):
                trade_id = context['trade_id']
        
        return execute_open_teach_copilot_command(context, trade_id)
    
    elif command == "close_teach_copilot":
        return execute_close_teach_copilot_command()
    
    elif command == "help":
        return execute_help_command()
    
    else:
        return {
            "success": False,
            "message": f"Unknown command: {command}"
        }


def execute_stats_command() -> Dict[str, Any]:
    """Execute 'show my stats' command"""
    try:
        profile = load_json(PROFILE_PATH, {})
        
        if profile.get("total_trades", 0) == 0:
            return {
                "success": True,
                "command": "stats",
                "message": "📊 No trades logged yet. Start trading to see your stats!",
                "data": {}
            }
        
        total = profile.get("total_trades", 0)
        completed = profile.get("completed_trades", 0)
        win_rate = profile.get("win_rate", 0) * 100
        avg_r = profile.get("avg_rr", 0)
        best = profile.get("best_setup", "None")
        worst = profile.get("worst_setup", "None")
        
        message = f"📊 **Performance Summary**\n\n"
        message += f"• Total Trades: {total} ({completed} completed)\n"
        message += f"• Win Rate: {win_rate:.1f}%\n"
        message += f"• Average R: {avg_r:+.2f}R\n"
        message += f"• Best Setup: {best}\n"
        
        if worst != "None yet":
            worst_r = profile.get("setup_performance", {}).get(worst, 0)
            message += f"• Worst Setup: {worst} ({worst_r:+.2f}R)\n"
        
        trend = profile.get("recent_trend", {})
        if trend.get("rr_change"):
            direction = "improving" if trend["rr_change"] > 0 else "declining"
            message += f"• Recent Trend: {direction} ({trend['rr_change']:+.2f}R change)"
        
        return {
            "success": True,
            "command": "stats",
            "message": message,
            "data": profile
        }
    
    except Exception as e:
        return {
            "success": False,
            "command": "stats",
            "message": f"⚠️ Error loading stats: {str(e)}"
        }


def execute_delete_last_command() -> Dict[str, Any]:
    """Execute 'delete last trade' command"""
    try:
        logs = _load_json(LOG_PATH)
        
        if not logs:
            return {
                "success": False,
                "command": "delete_last",
                "message": "📭 No trades to delete"
            }
        
        last_trade = logs.pop()
        
        # Save updated logs and keep last deleted for potential restore
        save_json(LOG_PATH, logs)
        last_deleted_path = os.path.join(os.path.dirname(LOG_PATH), "last_deleted_trade.json")
        save_json(last_deleted_path, last_trade)
        
        # Regenerate learning profile
        generate_learning_profile()
        
        symbol = last_trade.get("symbol", "Unknown")
        outcome = last_trade.get("outcome", "pending")
        
        message = f"🗑️ **Trade Deleted**\n\n"
        message += f"• Symbol: {symbol}\n"
        message += f"• Outcome: {outcome}\n"
        message += f"• Remaining trades: {len(logs)}"
        
        return {
            "success": True,
            "command": "delete_last",
            "message": message,
            "data": {"deleted_trade": last_trade, "remaining": len(logs)}
        }
    
    except Exception as e:
        return {
            "success": False,
            "command": "delete_last",
            "message": f"⚠️ Error deleting trade: {str(e)}"
        }


def execute_restore_last_command() -> Dict[str, Any]:
    """Execute 'restore last trade' (undo last deletion)"""
    try:
        last_deleted_path = os.path.join(os.path.dirname(LOG_PATH), "last_deleted_trade.json")
        last_trade = load_json(last_deleted_path, {})
        if not last_trade or not isinstance(last_trade, dict):
            return {
                "success": False,
                "command": "restore_last",
                "message": "📭 No recently deleted trade to restore"
            }
        logs = _load_json(LOG_PATH)
        logs.append(last_trade)
        save_json(LOG_PATH, logs)
        # Clear stored last deleted
        save_json(last_deleted_path, {})
        # Regenerate learning profile
        generate_learning_profile()
        symbol = last_trade.get("symbol", "Unknown")
        outcome = last_trade.get("outcome", "pending")
        message = f"♻️ **Trade Restored**\n\n• Symbol: {symbol}\n• Outcome: {outcome}\n• Total trades: {len(logs)}"
        return {
            "success": True,
            "command": "restore_last",
            "message": message,
            "data": {"restored_trade": last_trade, "total": len(logs)}
        }
    except Exception as e:
        return {
            "success": False,
            "command": "restore_last",
            "message": f"⚠️ Error restoring trade: {str(e)}"
        }


def execute_clear_memory_command() -> Dict[str, Any]:
    """Execute 'clear memory' command"""
    try:
        from .utils import clear_all_memory
        result = clear_all_memory()
        
        return {
            "success": True,
            "command": "clear_memory",
            "message": "🗑️ **Memory Cleared**\n\nAll sessions, conversations, and temporary data have been reset.",
            "data": result
        }
    
    except Exception as e:
        return {
            "success": False,
            "command": "clear_memory",
            "message": f"⚠️ Error clearing memory: {str(e)}"
        }


def execute_model_info_command(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute 'what model are you using' command"""
    try:
        from openai_client import MODEL_ALIASES, DEFAULT_MODEL
        
        current_model = context.get("current_model", DEFAULT_MODEL)
        
        # Resolve alias if applicable
        alias_name = "unknown"
        for alias, model_id in MODEL_ALIASES.items():
            if model_id == current_model:
                alias_name = alias
                break
        
        message = f"🤖 **Current AI Model**\n\n"
        message += f"• Model: {current_model}\n"
        
        if alias_name != "unknown":
            message += f"• Alias: {alias_name}\n"
        
        message += f"\n**Available Modes:**\n"
        message += f"• ⚡ Fast: GPT-5 Chat (vision)\n"
        message += f"• 🧠 Balanced: GPT-5 Search (hybrid)\n"
        message += f"• 🔬 Advanced: GPT-4o (vision)"
        
        return {
            "success": True,
            "command": "model_info",
            "message": message,
            "data": {"current_model": current_model, "alias": alias_name}
        }
    
    except Exception as e:
        return {
            "success": False,
            "command": "model_info",
            "message": f"⚠️ Error getting model info: {str(e)}"
        }


def execute_list_sessions_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'list sessions' command - now uses IndexedDB data from context"""
    try:
        # Get sessions from context (injected from frontend IndexedDB)
        all_sessions = context.get("all_sessions") if context else []
        current_session_id = context.get("current_session_id") if context else None
        
        if not all_sessions:
            return {
                "success": True,
                "command": "list_sessions",
                "message": "📂 No sessions found. Create one with 'create session' or use the ➕ New Session button.",
                "data": []
            }
        
        message = f"📂 **Active Sessions** ({len(all_sessions)})\n\n"
        
        for i, session in enumerate(all_sessions[:10], 1):
            title = session.get("title", session.get("symbol", "Unknown"))
            symbol = session.get("symbol", "?")
            is_active = session.get("isActive") or session.get("sessionId") == current_session_id
            active_marker = " 🔵 Active" if is_active else ""
            message += f"{i}. **{title}** ({symbol}){active_marker}\n"
        
        if len(all_sessions) > 10:
            message += f"\n... and {len(all_sessions) - 10} more session(s)"
        
        return {
            "success": True,
            "command": "list_sessions",
            "message": message,
            "data": all_sessions
        }
    
    except Exception as e:
        return {
            "success": False,
            "command": "list_sessions",
            "message": f"⚠️ Error listing sessions: {str(e)}"
        }

def execute_switch_session_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'switch session' command - requires frontend action"""
    # Extract session identifier from context if available
    all_sessions = context.get("all_sessions", []) if context else []
    
    if not all_sessions:
        return {
            "success": False,
            "command": "switch_session",
            "message": "⚠️ No sessions available to switch to",
            "frontend_action": "show_session_manager"  # Fallback to showing manager
        }
    
    # Return instruction for frontend to handle
    return {
        "success": True,
        "command": "switch_session",
        "message": "📂 **Switch Session**\n\nUse the Session Manager (🗂️ button) or say 'switch to [session name]' with the exact name.\n\nAvailable sessions:\n" + 
                   "\n".join([f"• {s.get('title', s.get('symbol'))} ({s.get('symbol')})" for s in all_sessions[:5]]),
        "frontend_action": "show_session_manager",
        "data": {"available_sessions": all_sessions}
    }

def execute_create_session_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'create session' command - requires frontend action"""
    return {
        "success": True,
        "command": "create_session",
        "message": "➕ **Create Session**\n\nI can help you create a new session. Click the ➕ New Session button in the Session Manager (🗂️), or tell me the symbol (e.g., 'create session ES').",
        "frontend_action": "create_session_prompt",
        "data": {}
    }

def execute_delete_session_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'delete session' command - requires frontend action"""
    all_sessions = context.get("all_sessions", []) if context else []
    
    if not all_sessions:
        return {
            "success": False,
            "command": "delete_session",
            "message": "⚠️ No sessions available to delete"
        }
    
    return {
        "success": True,
        "command": "delete_session",
        "message": "🗑️ **Delete Session**\n\nUse the Session Manager (🗂️ button) to delete sessions, or tell me which session to delete by name.",
        "frontend_action": "show_session_manager",
        "data": {"available_sessions": all_sessions}
    }

def execute_rename_session_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'rename session' command - requires frontend action"""
    current_session_id = context.get("current_session_id") if context else None
    
    if not current_session_id:
        return {
            "success": False,
            "command": "rename_session",
            "message": "⚠️ No active session to rename"
        }
    
    return {
        "success": True,
        "command": "rename_session",
        "message": f"✏️ **Rename Session**\n\nClick the session name in the chat header (🧠) to rename the current session, or tell me the new name (e.g., 'rename session to My Trading Session').",
        "frontend_action": "rename_session",
        "data": {"current_session_id": current_session_id}
    }


def execute_open_teach_copilot_command(context: Dict[str, Any] = None, trade_id: int = None) -> Dict[str, Any]:
    """
    Execute 'open teach copilot' command - opens teaching mode UI
    Optionally auto-selects a specific trade if trade_id is provided
    """
    # Try to extract trade_id from context if not provided
    if not trade_id and context:
        # Check if context has a detected trade or trade_id
        if context.get('detected_trade'):
            trade_id = context['detected_trade'].get('id') or context['detected_trade'].get('trade_id')
        elif context.get('trade_id'):
            trade_id = context['trade_id']
    
    message = "🎓 Opening Teach Copilot... You can now review trades one by one and teach the AI your strategy!\n\n"
    
    if trade_id:
        message += f"**Trade {trade_id} will be automatically selected and its chart loaded.**\n\n"
        return {
            "success": True,
            "command": "open_teach_copilot",
            "message": message + "**How it works:**\n1. The chart image will load automatically\n2. Type or voice-dictate your lesson about that trade\n3. Click 'Save Lesson' to extract BOS/POI and save to training dataset",
            "frontend_action": "open_teach_copilot",
            "trade_id": int(trade_id)
        }
    else:
        message += "**How it works:**\n1. Select any trade from the dropdown\n2. The chart image will load automatically (if available)\n3. Type or voice-dictate your lesson about that trade\n4. Click 'Save Lesson' to extract BOS/POI and save to training dataset"
        return {
            "success": True,
            "command": "open_teach_copilot",
            "message": message,
            "frontend_action": "open_teach_copilot"
        }


def execute_close_teach_copilot_command() -> Dict[str, Any]:
    """Execute 'close teach copilot' command - closes teaching mode UI"""
    return {
        "success": True,
        "command": "close_teach_copilot",
        "message": "✅ Teach Copilot closed. Teaching mode paused.",
        "frontend_action": "close_teach_copilot"
    }


def execute_help_command() -> Dict[str, Any]:
    """Execute 'help' command - show available commands"""
    message = "🤖 **Visual Trade Copilot - System Commands**\n\n"
    message += "**Performance:**\n"
    message += "• `show my stats` - View trading performance\n"
    message += "• `delete last trade` - Remove most recent trade\n"
    message += "• `restore last trade` - Undo the last deletion\n\n"
    message += "**Teaching:**\n"
    message += "• `open teach copilot` / `start teaching` - Open teaching mode UI to review trades and teach AI\n"
    message += "• `close teach copilot` / `pause teaching` - Close teaching mode UI\n"
    message += "• `review trades one by one` - Begin teaching session\n\n"
    message += "**Sessions:**\n"
    message += "• `list sessions` - Show all active sessions\n"
    message += "• `create session [symbol]` - Create a new trading session\n"
    message += "• `switch session` - Switch to a different session\n"
    message += "• `rename session [name]` - Rename current session\n"
    message += "• `delete session` - Delete a session\n\n"
    message += "**System:**\n"
    message += "• `what model are you using` - View current AI model\n"
    message += "• `clear memory` - Reset all temporary data\n\n"
    message += "**Analysis:**\n"
    message += "• Upload chart + ask questions\n"
    message += "• Use 📊 Log Trade button to track performance\n"
    message += "• AI learns from your trading history!"
    
    return {
        "success": True,
        "command": "help",
        "message": message,
        "data": {"commands": list(COMMAND_PATTERNS.keys())}
    }

