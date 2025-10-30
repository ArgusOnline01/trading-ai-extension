"""
System Command Recognition
Parses and executes system-level commands like "show my stats", "delete last trade"
"""

import difflib
from typing import Dict, Any, Optional, Tuple
from .utils import get_memory_status, load_json, save_json
from performance.learning import _load_json, LOG_PATH, PROFILE_PATH, generate_learning_profile


# Command patterns (lowercase for fuzzy matching)
COMMAND_PATTERNS = {
    "stats": ["show my stats", "show stats", "my performance", "how am i doing", "my results"],
    "delete_last": ["delete last trade", "remove last trade", "undo last trade", "delete recent trade"],
    "clear_memory": ["clear memory", "reset memory", "delete all data", "wipe memory"],
    "model_info": ["what model", "which model", "current model", "what ai", "which gpt"],
    "list_sessions": ["list sessions", "show sessions", "my sessions", "active sessions"],
    "help": ["help", "commands", "what can you do", "available commands"]
}


def detect_command(user_input: str) -> Optional[str]:
    """
    Detect if user input is a system command using fuzzy matching
    Returns command key if detected, None otherwise
    """
    user_lower = user_input.lower().strip()
    
    # Direct pattern matching first
    for cmd_key, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            # Use difflib for fuzzy matching (80% similarity)
            similarity = difflib.SequenceMatcher(None, user_lower, pattern).ratio()
            if similarity > 0.8:
                return cmd_key
            
            # Also check if pattern is contained in user input
            if pattern in user_lower and len(pattern) > 5:
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
    
    elif command == "clear_memory":
        return execute_clear_memory_command()
    
    elif command == "model_info":
        return execute_model_info_command(context)
    
    elif command == "list_sessions":
        return execute_list_sessions_command()
    
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
        
        # Save updated logs
        save_json(LOG_PATH, logs)
        
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


def execute_list_sessions_command() -> Dict[str, Any]:
    """Execute 'list sessions' command"""
    try:
        from .utils import SESSION_CONTEXTS_PATH, load_json
        
        sessions = load_json(SESSION_CONTEXTS_PATH, [])
        
        if not sessions:
            return {
                "success": True,
                "command": "list_sessions",
                "message": "📂 No active sessions found",
                "data": []
            }
        
        message = f"📂 **Active Sessions** ({len(sessions)})\n\n"
        
        for i, session in enumerate(sessions[:5], 1):  # Show first 5
            symbol = session.get("symbol", "Unknown")
            title = session.get("title", "Untitled")
            updated = session.get("last_updated", "Unknown")[:10]
            message += f"{i}. {title} - {symbol} (updated: {updated})\n"
        
        if len(sessions) > 5:
            message += f"\n... and {len(sessions) - 5} more"
        
        return {
            "success": True,
            "command": "list_sessions",
            "message": message,
            "data": sessions
        }
    
    except Exception as e:
        return {
            "success": False,
            "command": "list_sessions",
            "message": f"⚠️ Error listing sessions: {str(e)}"
        }


def execute_help_command() -> Dict[str, Any]:
    """Execute 'help' command - show available commands"""
    message = "🤖 **Visual Trade Copilot - System Commands**\n\n"
    message += "**Performance:**\n"
    message += "• `show my stats` - View trading performance\n"
    message += "• `delete last trade` - Remove most recent trade\n\n"
    message += "**System:**\n"
    message += "• `what model are you using` - View current AI model\n"
    message += "• `list sessions` - Show active chat sessions\n"
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

