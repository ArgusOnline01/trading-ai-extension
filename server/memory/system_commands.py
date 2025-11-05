"""
System Command Recognition
Parses and executes system-level commands like "show my stats", "delete last trade"
"""

import difflib
from typing import Dict, Any, Optional, Tuple
from urllib.parse import quote
from pathlib import Path
from .utils import get_memory_status, load_json, save_json
from performance.learning import _load_json, LOG_PATH, PROFILE_PATH, generate_learning_profile
from utils.chart_service import get_chart_url, load_chart_base64
import os
import logging

logger = logging.getLogger(__name__)


def chart_url_from_path(chart_path: str) -> str:
    """
    Convert chart file path to URL path.
    Phase 5F Fix: Standardize on /charts/ path (not /static/charts/)
    """
    if chart_path:
        p = Path(chart_path)
        # Standardize on /charts/ path (mounted in app.py)
        return f"/charts/{quote(p.name)}"
    # fallback mock for tests
    return "/charts/mock_chart.png"

def attach_chart_url(trade: dict) -> dict:
    """
    Attach chart_url to trade dict.
    Phase 5F Fix: Use unified chart_service when possible, fallback to chart_path.
    """
    trade = trade or {}
    
    # First try to use unified chart_service (more reliable)
    try:
        from utils.chart_service import get_chart_url_fast
        chart_url = get_chart_url_fast(trade)
        if chart_url:
            trade["chart_url"] = chart_url
            return trade
    except Exception as e:
        # If chart_service fails, fallback to chart_path
        pass
    
    # Fallback: use chart_path directly
    chart_path = trade.get("chart_path")
    if chart_path:
        trade["chart_url"] = chart_url_from_path(chart_path)
    else:
        # Generate URL from trade ID and symbol if available
        trade_id = trade.get('id') or trade.get('trade_id')
        symbol = trade.get('symbol', '')
        if trade_id and symbol:
            trade["chart_url"] = f"/charts/{symbol}_5m_{trade_id}.png"
        else:
            trade["chart_url"] = "/charts/mock_chart.png"
    
    return trade


# Command patterns (lowercase for fuzzy matching)
# IMPORTANT: Order matters - more specific patterns should come first!
COMMAND_PATTERNS = {
    # Performance Commands
    "stats": ["show my stats", "show stats", "my performance", "how am i doing", "my results"],
    "restore_last": ["restore last trade", "undo delete", "add it back", "re-add last trade", "undelete last trade", "put it back", "bring it back"],
    "delete_last": ["delete last trade", "remove last trade", "delete recent trade"],
    "delete_trade": ["delete trade", "remove trade", "delete this trade", "remove this trade", "delete trade by id"],
    "view_trade": ["view trade", "show trade", "trade details", "show trade details", "what is this trade"],
    
    # Session Management
    "switch_session": ["switch session", "change session", "load session", "open session", "go to session", "switch to"],
    "create_session": ["create session", "new session", "start session", "add session", "make session"],
    "delete_session": ["delete session", "remove session"],
    "rename_session": ["rename session", "change session name", "edit session title", "rename to"],
    "list_sessions": ["list sessions", "show sessions", "my sessions", "active sessions"],
    
    # UI Controls
    "close_chat": ["close chat", "hide chat", "close copilot", "hide copilot", "close the chat", "close this chat"],
    "open_chat": ["open chat", "show chat", "open copilot", "show copilot", "bring chat back", "open the chat", "bring back chat"],
    "minimize_chat": ["minimize chat", "minimize", "minimize copilot", "minimize the chat"],
    "resize_chat": ["resize chat", "make chat bigger", "make chat smaller", "resize copilot", "change chat size", "bigger chat", "smaller chat"],
    "reset_chat_size": ["reset chat size", "reset size", "default size", "reset chat", "normal size"],
    "show_session_manager": ["show session manager", "open session manager", "session manager", "sessions", "manage sessions"],
    
    # Teaching Commands
    "open_teach_copilot": ["open teach copilot", "start teaching", "teach copilot", "open teaching", "show teach copilot", "launch teaching mode", "begin teaching", "review trades one by one", "lets review the trades", "teach me", "let's teach", "redo this in teach mode", "lets redo this", "redo in teach mode", "do this in teaching", "open teaching for this trade", "teach me about this", "review this trade", "lets review this"],
    "close_teach_copilot": ["close teach copilot", "pause teaching", "pause teaching mode", "close teaching", "exit teaching mode", "stop teaching", "discard teaching lesson", "cancel teaching"],
    "start_teaching": ["start teaching session", "begin teaching session"],
    "end_teaching": ["end teaching session", "stop teaching session", "finish teaching", "complete teaching"],
    "next_trade_teaching": ["next trade", "next", "skip to next", "move to next trade", "go to next trade"],
    "skip_trade_teaching": ["skip trade", "skip this trade", "skip", "skip current trade"],
    "teaching_progress": ["teaching progress", "learning progress", "teaching stats", "how many lessons", "teaching summary", "teaching status"],
    
    # Lesson Management
    "view_lessons": ["view lessons", "show lessons", "list lessons", "my lessons", "show my lessons", "all lessons", "lessons list"],
    "view_lesson": ["view lesson", "show lesson", "lesson details", "show lesson details", "view lesson details"],
    "delete_lesson": ["delete lesson", "remove lesson", "delete this lesson", "remove this lesson"],
    "edit_lesson": ["edit lesson", "update lesson", "modify lesson", "change lesson", "update this lesson"],
    
    # Chart Commands
    "show_chart": ["show chart", "show image", "show the chart", "display chart", "pull up chart", "pull up its chart", "pull up the chart", "pull up image", "pull up its image", "pull up the image", "show me the chart", "open chart", "view chart", "can you show the chart", "show that chart", "show this chart", "chart please"],
    "close_chart": ["close chart", "hide chart", "close image", "close the chart", "close chart popup"],
    
    # System Commands
    "clear_memory": ["clear memory", "reset memory", "delete all data", "wipe memory"],
    "model_info": ["what model", "which model", "current model", "what ai", "which gpt"],
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
    
    ⚠️ LEGACY: This function is deprecated for trade commands.
    Trade commands should be routed through Intent Analyzer (Phase 5E).
    This function is kept only as an emergency fallback.
    """
    user_lower = user_input.lower().strip()
    
    # Check if this is a trade-related command (should use Intent Analyzer)
    trade_keywords = ['trade', 'chart', 'list', 'view', 'next', 'previous']
    if any(kw in user_lower for kw in trade_keywords):
        logger.warning(f"LEGACY detect_command() used for trade command: '{user_input}' - should be routed by Intent Analyzer")
    
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
    # Also check reversed (input in pattern) for partial matches
    for cmd_key, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            # Check if pattern appears in original or normalized input
            if len(pattern) > 6:
                if pattern in user_lower or pattern in normalized:
                    return cmd_key
            # Also check if input contains key parts of the pattern
            # For "pull up image", match if user says "pull up image" or similar
            pattern_words = pattern.split()
            if len(pattern_words) >= 2:
                # Check if at least 2 key words from pattern are in input
                words_in_input = sum(1 for word in pattern_words if len(word) > 2 and word in user_lower)
                if words_in_input >= min(2, len(pattern_words) - 1):
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
    
    elif command == "show_chart":
        return execute_show_chart_command(context)
    
    elif command == "help":
        return execute_help_command()
    
    # UI Control Commands
    elif command == "close_chat":
        return execute_close_chat_command()
    elif command == "open_chat":
        return execute_open_chat_command()
    elif command == "minimize_chat":
        return execute_minimize_chat_command()
    elif command == "resize_chat":
        return execute_resize_chat_command(context)
    elif command == "reset_chat_size":
        return execute_reset_chat_size_command()
    elif command == "show_session_manager":
        return execute_show_session_manager_command()
    
    # Lesson Management Commands
    elif command == "view_lessons":
        return execute_view_lessons_command()
    elif command == "view_lesson":
        return execute_view_lesson_command(context)
    elif command == "delete_lesson":
        return execute_delete_lesson_command(context)
    elif command == "edit_lesson":
        return execute_edit_lesson_command(context)
    elif command == "teaching_progress":
        return execute_teaching_progress_command()
    
    # Teaching Session Commands
    elif command == "start_teaching":
        return execute_start_teaching_command()
    elif command == "end_teaching":
        return execute_end_teaching_command()
    elif command == "next_trade_teaching":
        return execute_next_trade_teaching_command()
    elif command == "skip_trade_teaching":
        return execute_skip_trade_teaching_command()
    
    # Trade Management Commands
    elif command == "list_trades":
        return execute_list_trades_command(context)
    elif command == "delete_trade":
        return execute_delete_trade_command(context)
    elif command == "view_trade":
        return execute_view_trade_command(context)
    
    # Chart Commands
    elif command == "show_chart":
        return execute_show_chart_command(context)
    elif command == "close_chart":
        return execute_close_chart_command()
    
    # Teaching Navigation Commands
    elif command == "previous_trade_teaching":
        return execute_previous_trade_teaching_command()
    elif command == "previous_trade_navigation":
        return execute_previous_trade_navigation_command(context)
    
    else:
        return {
            "success": False,
            "message": f"Unknown command: {command}"
        }


def execute_stats_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'show my stats' command"""
    try:
        # Compute stats from actual trades
        from performance.utils import read_logs
        all_trades = read_logs()
        
        def compute_stats(trades):
            wins = [t for t in trades if t.get("outcome") == "win"]
            losses = [t for t in trades if t.get("outcome") == "loss"]
            total = len(wins) + len(losses)
            win_rate = round(100 * len(wins) / total, 1) if total else 0.0
            avg_r = round(sum(t.get("r_multiple", 0.0) for t in trades) / total, 2) if total else 0.0
            return win_rate, avg_r
        
        win_rate, avg_rr = compute_stats(all_trades)
        
        profile = load_json(PROFILE_PATH, {})
        
        if profile.get("total_trades", 0) == 0:
            return {
                "success": True,
                "command": "stats",
                "message": "📊 No trades logged yet. Start trading to see your stats!",
                "data": {},
                "fields": {
                    "win_rate": 0.0,
                    "avg_rr": 0.0
                },
                "phase": "5f",
                "intent": "stats_command",
                "status": 200
            }
        
        total = profile.get("total_trades", 0)
        completed = profile.get("completed_trades", 0)
        best = profile.get("best_setup", "None")
        worst = profile.get("worst_setup", "None")
        
        message = f"📊 **Performance Summary**\n\n"
        message += f"• Total Trades: {total} ({completed} completed)\n"
        message += f"• Win Rate: {win_rate:.1f}%\n"
        message += f"• Average R: {avg_rr:+.2f}R\n"
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
            "data": profile,
            "fields": {
                "win_rate": float(win_rate),
                "avg_rr": float(avg_rr)
            },
            "phase": "5f",
            "intent": "stats_command",
            "status": 200
        }
    
    except Exception as e:
        return {
            "success": False,
            "command": "stats",
            "message": f"⚠️ Error loading stats: {str(e)}",
            "phase": "5f",
            "intent": "stats_command"
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
    """Execute 'create session' command - uses AI-extracted parameters"""
    print("[EXECUTE_COMMAND] execute_create_session_command()")
    context = context or {}
    
    # Get AI-extracted parameters
    detected_command = context.get('detected_command', {})
    symbol = detected_command.get('symbol') or detected_command.get('session_name') or detected_command.get('name')
    
    # Clean up symbol (remove filler words)
    if symbol:
        symbol = symbol.strip().upper()
        # Remove common filler words
        filler_words = ['CALLED', 'THE', 'A', 'AN']
        words = symbol.split()
        filtered_words = [w for w in words if w not in filler_words]
        if filtered_words:
            symbol = filtered_words[-1]  # Use last word (usually the actual symbol)
    
    if symbol:
        message = f"➕ **Creating {symbol} Session**\n\nOpening Session Manager to create the session..."
        result = {
            "success": True,
            "command": "create_session",
            "message": message,
            "frontend_action": "create_session_prompt",
            "data": {"symbol": symbol}
        }
        print(f"[EXECUTE_COMMAND] execute_create_session_command() → success (symbol: {symbol})")
        return result
    
    return {
        "success": True,
        "command": "create_session",
        "message": "➕ **Create Session**\n\nOpening Session Manager. Click the ➕ New Session button, or tell me the symbol (e.g., 'create session ES').",
        "frontend_action": "create_session_prompt",
        "data": {}
    }

def execute_delete_session_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'delete session' command - uses AI-extracted parameters"""
    print("[EXECUTE_COMMAND] execute_delete_session_command()")
    context = context or {}
    all_sessions = context.get("all_sessions", []) if context else []
    
    if not all_sessions:
        return {
            "success": True,
            "command": "delete_session",
            "message": "📂 **No Sessions to Delete**\n\nYou don't have any sessions yet. Open the Session Manager to create one!",
            "frontend_action": "show_session_manager",
            "data": {"available_sessions": []}
        }
    
    # Get AI-extracted parameters
    detected_command = context.get('detected_command', {})
    session_name = detected_command.get('session_name') or detected_command.get('name')
    session_id = detected_command.get('session_id') or detected_command.get('id')
    
    # If AI didn't extract, fallback to current session for "this session"
    if not session_name and not session_id:
        current_session_id = context.get('current_session_id')
        if current_session_id:
            # Find current session
            for session in all_sessions:
                if session.get('sessionId') == current_session_id:
                    session_name = session.get('title') or session.get('symbol')
                    session_id = current_session_id
                    break
    
    if session_name or session_id:
        # Find matching sessions - handle multiple matches
        matching_sessions = []
        for session in all_sessions:
            sess_id = session.get('sessionId') or session.get('id') or ''
            sess_symbol = (session.get('symbol') or '').upper()
            sess_title = (session.get('title') or '').lower()
            
            # Match by provided ID
            if session_id and (session_id in sess_id or sess_id in session_id):
                matching_sessions.append(session)
                break  # ID match is unique
            # Match by name/symbol
            elif session_name:
                search_name = session_name.upper()
                if (search_name in sess_symbol) or (session_name.lower() in sess_title) or (search_name in sess_id.upper()):
                    matching_sessions.append(session)
        
        # Handle multiple matches
        if len(matching_sessions) > 1:
            # Multiple sessions match - check if user wants "duplicate", "other", "both", etc.
            detected_command = context.get('detected_command', {})
            action_hint = detected_command.get('action_hint', '').lower()
            
            # If user said "other", "duplicate", "both", "all" - delete all matching sessions
            # IMPORTANT: When user says "both", delete ALL matching sessions, not just non-current ones
            current_session_id = context.get('current_session_id')
            if any(word in action_hint for word in ['other', 'duplicate', 'both', 'all', '2', 'two']):
                # If "both" or "all", delete ALL matching sessions
                if 'both' in action_hint or 'all' in action_hint:
                    sessions_to_delete = matching_sessions.copy()
                else:
                    # For "other" or "duplicate", exclude current session
                    sessions_to_delete = [s for s in matching_sessions if s.get('sessionId') != current_session_id]
                    if not sessions_to_delete:
                        # If current is one of them, delete all except one
                        sessions_to_delete = matching_sessions[1:]
                
                if sessions_to_delete:
                    # Return first one - backend will handle multiple via frontend_action
                    # Actually, we should return multiple commands or a special flag
                    session_id_to_delete = sessions_to_delete[0].get('sessionId')
                    remaining_ids = [s.get('sessionId') for s in sessions_to_delete[1:]]
                    
                    message = f"🗑️ **Deleting {len(sessions_to_delete)} Sessions**\n\nDeleting matching sessions..."
                    return {
                        "success": True,
                        "command": "delete_session",
                        "message": message,
                        "frontend_action": "delete_session",
                        "data": {
                            "session_name": session_name,
                            "session_id": session_id_to_delete,
                            "additional_session_ids": remaining_ids,  # For multiple deletions
                            "available_sessions": all_sessions
                        }
                    }
            
            # Otherwise, ask for clarification
            session_list = "\n".join([f"- {s.get('title')} (ID: {s.get('sessionId')})" for s in matching_sessions])
            return {
                "success": True,
                "command": "delete_session",
                "message": f"🗑️ **Multiple Sessions Found**\n\nFound {len(matching_sessions)} sessions matching '{session_name}':\n{session_list}\n\nPlease specify which one to delete, or say 'delete both/all' to delete them all.",
                "frontend_action": "show_session_manager",
                "data": {"session_name": session_name, "available_sessions": all_sessions, "matching_sessions": matching_sessions}
            }
        
        # Single match
        matching_session = matching_sessions[0] if matching_sessions else None
        session_id_to_delete = matching_session.get('sessionId') if matching_session else session_id
        
        if session_id_to_delete:
            message = f"🗑️ **Deleting Session**\n\nDeleting '{session_name}' (ID: {session_id_to_delete[:20]}...)..."
            result = {
                "success": True,
                "command": "delete_session",
                "message": message,
                "frontend_action": "delete_session",
                "data": {
                    "session_name": session_name,
                    "session_id": session_id_to_delete,
                    "available_sessions": all_sessions
                }
            }
            print(f"[EXECUTE_COMMAND] execute_delete_session_command() → success (session: {session_name})")
            return result
        else:
            # Session name provided but not found - still try to delete by name
            message = f"🗑️ **Deleting Session**\n\nAttempting to delete '{session_name}'..."
            return {
                "success": True,
                "command": "delete_session",
                "message": message,
                "frontend_action": "delete_session",
                "data": {"session_name": session_name, "available_sessions": all_sessions}
            }
    
    return {
        "success": True,
        "command": "delete_session",
        "message": "🗑️ **Delete Session**\n\nOpening Session Manager. Click the 🗑️ button next to the session you want to delete, or tell me which session (e.g., 'delete session ES').",
        "frontend_action": "show_session_manager",
        "data": {"available_sessions": all_sessions}
    }

def execute_rename_session_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'rename session' command - uses AI-extracted parameters"""
    context = context or {}
    current_session_id = context.get("current_session_id") if context else None
    
    if not current_session_id:
        return {
            "success": False,
            "command": "rename_session",
            "message": "⚠️ No active session to rename"
        }
    
    # Get AI-extracted parameters
    detected_command = context.get('detected_command', {})
    new_name = detected_command.get('new_name') or detected_command.get('name')
    
    if new_name:
        return {
            "success": True,
            "command": "rename_session",
            "message": f"✏️ **Renaming Session**\n\nRenaming to '{new_name}'...",
            "frontend_action": "rename_session",
            "data": {
                "current_session_id": current_session_id,
                "new_name": new_name
            }
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


def execute_show_chart_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute 'show chart' command - opens chart popup for detected trade
    Phase 5F.1: Uses unified chart_service for chart resolution
    Phase 5F Fix: Improved error handling and resilience
    Navigation Fix: Uses current session context index when no explicit trade specified
    """
    context = context or {}
    
    try:
        # Priority 0: Use current session context index for "this trade" / "current trade" contexts
        # This ensures navigation context is respected after "next trade" / "previous trade"
        # CRITICAL FIX: Always check context FIRST, before any conversation history detection
        from memory.context_manager import get_context_state
        import memory.context_manager as ctx
        
        command_text = context.get('command_text', '').lower()
        
        # CRITICAL FIX: If command is just "show chart" or context reference, use current context index
        # Don't fall back to conversation history which might have stale trade references
        is_context_reference = any(phrase in command_text for phrase in [
            'this trade', 'current trade', 'the trade', 'that trade', 
            'its chart', 'show chart', 'chart for this', 'chart for the', 'chart'
        ]) or not command_text.strip() or command_text == 'show chart'
        
        # CRITICAL FIX: Also check context if no explicit trade ID is mentioned in command
        # This ensures "show chart" after navigation uses current context
        has_explicit_trade_id = any(phrase in command_text for phrase in [
            'trade #', 'trade id', 'trade ', 'for trade'
        ]) and any(char.isdigit() for char in command_text)
        
        # Use context if it's a context reference OR if no explicit trade ID is mentioned
        use_context = is_context_reference or (not has_explicit_trade_id and not context.get('trade_id') and not context.get('detected_trade'))
        
        detected_trade = None
        
        # CRITICAL FIX: Always check current context FIRST if available, regardless of command text
        # This ensures charts match navigation context
        # MUST check context BEFORE checking context.get('detected_trade') which might be stale
        current_idx = None
        try:
            current_state = ctx.get_context_state()
            current_idx = current_state.get("current_trade_index", None)
            
            # CRITICAL: Always try to use context index if available, even if not explicitly a context reference
            if current_idx is not None:
                from performance.utils import read_logs
                all_trades = context.get('all_trades') or read_logs()
                if all_trades:
                    # CRITICAL: Use same sorting as navigation commands
                    sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                    if 0 <= current_idx < len(sorted_trades):
                        context_trade = sorted_trades[current_idx]
                        trade_id = context_trade.get('id') or context_trade.get('trade_id')
                        symbol = context_trade.get('symbol', 'Unknown')
                        
                        print(f"[SHOW_CHART] CRITICAL FIX: Using current session context index {current_idx}: {symbol} (ID: {trade_id})")
                        
                        # CRITICAL: If command text doesn't explicitly mention a different trade, use context
                        # Only skip context if command explicitly mentions a trade ID or trade number
                        has_explicit_trade_reference = False
                        if command_text:
                            # Check for explicit trade references like "trade #5", "trade 123", "trade id 123"
                            import re
                            if re.search(r'trade\s*#?\s*\d+', command_text) or re.search(r'trade\s+id\s+\d+', command_text, re.IGNORECASE):
                                has_explicit_trade_reference = True
                                print(f"[SHOW_CHART] Command has explicit trade reference, will check other detection methods")
                        
                        # Use context trade if no explicit trade reference in command
                        if not has_explicit_trade_reference:
                            detected_trade = context_trade
                            chart_url = get_chart_url(detected_trade)
                            
                            if not chart_url:
                                error_msg = f"❌ Chart not found for {symbol} trade {trade_id}."
                                print(f"[SHOW_CHART] {error_msg}")
                                
                                return {
                                    "success": False,
                                    "command": "show_chart",
                                    "message": error_msg,
                                    "frontend_action": None,
                                    "phase": "5f",
                                    "intent": "show_chart_command",
                                    "error": "chart_file_not_found",
                                    "diagnostics": {
                                        "trade_id": trade_id,
                                        "symbol": symbol,
                                        "current_index": current_idx
                                    }
                                }
                            
                            print(f"[SHOW_CHART] CRITICAL FIX: Chart resolved for context index {current_idx}: {chart_url}")
                            
                            return {
                                "success": True,
                                "command": "show_chart",
                                "message": f"📊 Opening chart for {symbol} trade {trade_id} (index {current_idx + 1})...",
                                "frontend_action": "show_chart_popup",
                                "chart_url": chart_url,
                                "data": {
                                    "trade_id": trade_id,
                                    "chart_url": chart_url,
                                    "symbol": symbol,
                                    "trade": detected_trade,  # CRITICAL: Include full trade data
                                    "trade_index": current_idx  # CRITICAL: Include index for validation
                                },
                                "phase": "5f",
                                "intent": "show_chart_command"
                            }
                    else:
                        print(f"[SHOW_CHART] WARNING: current_idx {current_idx} out of bounds (total trades: {len(sorted_trades)})")
            elif current_idx is None:
                print(f"[SHOW_CHART] WARNING: current_trade_index is None in session context")
        except Exception as e:
            print(f"[SHOW_CHART] Could not use session context: {e}")
            import traceback
            traceback.print_exc()
        
        # Only proceed to other detection methods if context was not available or explicit trade reference found
        # CRITICAL: Only check context.get('detected_trade') AFTER context check fails
        # DO NOT use context.get('detected_trade') if we have a valid session context index
        if not detected_trade:
            # Priority 1: Use detected_trade from context (from /ask endpoint)
            # BUT: Skip this if we have a valid session context to avoid stale data
            if current_idx is None or current_idx < 0:
                detected_trade = context.get('detected_trade')
                if detected_trade:
                    print(f"[SHOW_CHART] Using detected_trade from context: {detected_trade.get('id')} - {detected_trade.get('symbol')}")
            
            # Priority 2: If not in context, try to detect from conversation history
            if not detected_trade:
                from utils.trade_detector import detect_trade_reference, extract_trade_index_from_text, get_trade_by_index
                from performance.utils import read_logs
                
                all_trades = context.get('all_trades') or read_logs()
                command_text = context.get('command_text', '')
                conversation_history = context.get('conversation_history') or context.get('messages') or []
                
                # Phase 5F Fix: Prioritize trade index matching (e.g., "show chart for trade #7")
                # This ensures trade #7 matches the displayed order from list_trades
                trade_index = extract_trade_index_from_text(command_text)
                if trade_index and all_trades:
                    # Sort same way as list_trades (chronological, oldest first)
                    sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                    detected_trade = get_trade_by_index(trade_index, all_trades, sorted_trades)
                    if detected_trade:
                        print(f"[SHOW_CHART] Found trade by index #{trade_index}: {detected_trade.get('symbol')} (ID: {detected_trade.get('id')})")
                
                # Check for reference phrases ("its chart", "that trade", etc.)
                message_lower = command_text.lower()
                if any(phrase in message_lower for phrase in ['its chart', 'its image', 'the chart', 'that chart', 'this chart', 'that trade', 'this trade', 'pull up its', 'show its']):
                    # Search conversation history for trade mentions
                    if conversation_history and all_trades:
                        recent_text = ""
                        for msg in reversed(conversation_history[-10:]):
                            if isinstance(msg, dict):
                                recent_text += " " + str(msg.get('content', ''))
                            else:
                                recent_text += " " + str(msg)
                        detected_trade = detect_trade_reference(recent_text, all_trades, conversation_history)
                
                # Normal detection flow
                if not detected_trade:
                    combined_text = command_text
                    if conversation_history:
                        for msg in reversed(conversation_history[-5:]):
                            if isinstance(msg, dict):
                                combined_text += " " + str(msg.get('content', ''))
                            else:
                                combined_text += " " + str(msg)
                    detected_trade = detect_trade_reference(combined_text, all_trades, conversation_history)
            
            # Priority 3: Fallback to most recent trade (only if no context reference)
            if not detected_trade:
                all_trades = context.get('all_trades') or []
                if not all_trades:
                    try:
                        from performance.utils import read_logs
                        all_trades = read_logs()
                    except:
                        all_trades = []
                
                if all_trades:
                    sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=True)
                    if sorted_trades:
                        detected_trade = sorted_trades[0]
                        print(f"[SHOW_CHART] Using most recent trade as fallback: {detected_trade.get('id')} - {detected_trade.get('symbol')}")
        
        if not detected_trade:
            return {
                "success": False,
                "command": "show_chart",
                "message": "❓ Could not find which trade's chart to show. Please mention a trade ID, symbol, or say 'that trade' after discussing it.",
                "frontend_action": None,
                "phase": "5f",
                "intent": "show_chart_command"
            }
        
        trade_id = detected_trade.get('id') or detected_trade.get('trade_id')
        symbol = detected_trade.get('symbol', 'Unknown')
        
        # Phase 5F.1: Use unified chart_service
        chart_url = get_chart_url(detected_trade)
        
        if not chart_url:
            # Phase 5F Fix: Better error diagnostics
            trade_id = detected_trade.get('id') or detected_trade.get('trade_id')
            symbol = detected_trade.get('symbol', 'Unknown')
            chart_path = detected_trade.get('chart_path')
            
            error_msg = f"❌ Chart not found for {symbol} trade {trade_id}."
            if chart_path:
                error_msg += f" Expected file: {chart_path}"
            else:
                error_msg += " No chart_path provided."
            error_msg += " The chart may not have been generated yet."
            
            print(f"[SHOW_CHART] {error_msg}")
            
            return {
                "success": False,
                "command": "show_chart",
                "message": error_msg,
                "frontend_action": None,
                "phase": "5f",
                "intent": "show_chart_command",
                "error": "chart_file_not_found",
                "diagnostics": {
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "chart_path": chart_path,
                    "has_chart_path": bool(chart_path)
                }
            }
    
        print(f"[SHOW_CHART] Chart resolved via chart_service: {chart_url}")
        
        return {
            "success": True,
            "command": "show_chart",
            "message": f"📊 Opening chart for {symbol} trade {trade_id}...",
            "frontend_action": "show_chart_popup",
            "chart_url": chart_url,
            "data": {
                "trade_id": trade_id,
                "chart_url": chart_url,
                "symbol": symbol
            },
            "phase": "5f",
            "intent": "show_chart_command"
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[SHOW_CHART] Error executing show_chart command: {e}")
        print(f"[SHOW_CHART] Traceback: {error_trace[:300]}")
        return {
            "success": False,
            "command": "show_chart",
            "message": f"⚠️ Error showing chart: {str(e)}",
            "frontend_action": None,
            "error": str(e),
            "phase": "5f",
            "intent": "show_chart_command"
        }


def execute_help_command() -> Dict[str, Any]:
    """Execute 'help' command - show available commands"""
    message = "🤖 **Visual Trade Copilot - Comprehensive System Commands**\n\n"
    
    message += "**📊 Performance:**\n"
    message += "• `show my stats` - View trading performance\n"
    message += "• `delete last trade` - Remove most recent trade\n"
    message += "• `restore last trade` - Undo the last deletion\n"
    message += "• `delete trade` / `view trade` - Delete or view specific trade\n\n"
    
    message += "**🎓 Teaching & Lessons:**\n"
    message += "• `open teach copilot` / `start teaching` - Open teaching mode UI\n"
    message += "• `close teach copilot` / `pause teaching` - Close teaching mode UI\n"
    message += "• `start teaching session` - Begin teaching session\n"
    message += "• `end teaching session` - End teaching session\n"
    message += "• `next trade` - Move to next trade in teaching\n"
    message += "• `skip trade` - Skip current trade\n"
    message += "• `view lessons` - List all saved lessons\n"
    message += "• `view lesson` - Show lesson details\n"
    message += "• `delete lesson` - Delete a lesson\n"
    message += "• `edit lesson` - Edit a lesson\n"
    message += "• `teaching progress` - Show teaching statistics\n\n"
    
    message += "**📂 Sessions:**\n"
    message += "• `list sessions` - Show all active sessions\n"
    message += "• `create session [symbol]` - Create a new trading session\n"
    message += "• `switch session` - Switch to a different session\n"
    message += "• `rename session [name]` - Rename current session\n"
    message += "• `delete session` - Delete a session\n"
    message += "• `show session manager` - Open session manager UI\n\n"
    
    message += "**🖥️ UI Controls:**\n"
    message += "• `close chat` - Hide chat panel\n"
    message += "• `open chat` - Show chat panel\n"
    message += "• `minimize chat` - Minimize chat\n"
    message += "• `resize chat` - Resize chat panel\n"
    message += "• `reset chat size` - Reset to default size\n\n"
    
    message += "**📈 Charts:**\n"
    message += "• `show chart` / `open chart` - Display chart for trade\n"
    message += "• `close chart` - Close chart popup\n\n"
    
    message += "**⚙️ System:**\n"
    message += "• `what model are you using` - View current AI model\n"
    message += "• `clear memory` - Reset all temporary data\n"
    message += "• `help` - Show this help message\n\n"
    
    message += "💡 **Tip:** All commands work as questions too! (e.g., 'can you show my stats?')"
    
    return {
        "success": True,
        "command": "help",
        "message": message,
        "data": {"commands": list(COMMAND_PATTERNS.keys())}
    }


# ========== NEW COMMAND EXECUTORS ==========

def execute_close_chat_command() -> Dict[str, Any]:
    """Execute 'close chat' command"""
    return {
        "success": True,
        "command": "close_chat",
        "message": "👋 Closing chat panel...",
        "frontend_action": "close_chat"
    }

def execute_open_chat_command() -> Dict[str, Any]:
    """Execute 'open chat' command"""
    return {
        "success": True,
        "command": "open_chat",
        "message": "👋 Opening chat panel...",
        "frontend_action": "open_chat"
    }

def execute_minimize_chat_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'minimize chat' command"""
    return {
        "success": True,
        "command": "minimize_chat",
        "message": "⬇️ Minimizing chat...",
        "frontend_action": "minimize_chat"
    }

def execute_resize_chat_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'resize chat' command - extract size from context if provided"""
    context = context or {}
    command_text = context.get('command_text', '').lower()
    
    # Try to extract size hints
    size_hint = None
    if 'bigger' in command_text or 'larger' in command_text or 'increase' in command_text:
        size_hint = "bigger"
    elif 'smaller' in command_text or 'reduce' in command_text or 'decrease' in command_text:
        size_hint = "smaller"
    
    return {
        "success": True,
        "command": "resize_chat",
        "message": f"📐 Resizing chat panel...",
        "frontend_action": "resize_chat",
        "data": {"size_hint": size_hint}
    }

def execute_reset_chat_size_command() -> Dict[str, Any]:
    """Execute 'reset chat size' command"""
    return {
        "success": True,
        "command": "reset_chat_size",
        "message": "⬜ Resetting chat to default size...",
        "frontend_action": "reset_chat_size"
    }

def execute_show_session_manager_command() -> Dict[str, Any]:
    """Execute 'show session manager' command"""
    return {
        "success": True,
        "command": "show_session_manager",
        "message": "📂 Opening Session Manager...",
        "frontend_action": "show_session_manager"
    }

def execute_view_lessons_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'view lessons' command - opens lessons viewer in Teach Copilot"""
    return {
        "success": True,
        "command": "view_lessons",
        "message": "📚 Opening lessons viewer...\n\nYou can view all saved lessons, see what the AI extracted (BOS/POI), and view teaching progress statistics.",
        "frontend_action": "view_lessons"
    }

def execute_view_lesson_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'view lesson' command - shows detailed lesson information"""
    context = context or {}
    
    # Try to extract lesson ID from context or conversation
    lesson_id = None
    if context.get('lesson_id'):
        lesson_id = context['lesson_id']
    elif context.get('detected_lesson'):
        lesson_id = context['detected_lesson'].get('example_id') or context['detected_lesson'].get('trade_id')
    
    # Try to extract from command text
    if not lesson_id:
        command_text = context.get('command_text', '')
        import re
        # Try to find ID patterns
        id_match = re.search(r'(?:lesson|id|trade)\s*[#:]?\s*(\d+)', command_text, re.IGNORECASE)
        if id_match:
            lesson_id = id_match.group(1)
    
    if lesson_id:
        return {
            "success": True,
            "command": "view_lesson",
            "message": f"📚 Viewing lesson {lesson_id}...",
            "frontend_action": "view_lesson_details",
            "data": {"lesson_id": lesson_id}
        }
    else:
        return {
            "success": False,
            "command": "view_lesson",
            "message": "❓ Please specify which lesson to view. Try 'view lesson [ID]' or say 'view this lesson' after mentioning a specific lesson.",
            "frontend_action": "view_lessons"  # Fallback: show lessons list
        }

def execute_delete_lesson_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'delete lesson' command"""
    context = context or {}
    
    # Try to extract lesson ID
    lesson_id = None
    if context.get('lesson_id'):
        lesson_id = context['lesson_id']
    elif context.get('detected_lesson'):
        lesson_id = context['detected_lesson'].get('example_id') or context['detected_lesson'].get('trade_id')
    
    if not lesson_id:
        command_text = context.get('command_text', '')
        import re
        id_match = re.search(r'(?:lesson|id|trade)\s*[#:]?\s*(\d+)', command_text, re.IGNORECASE)
        if id_match:
            lesson_id = id_match.group(1)
    
    if lesson_id:
        # Delete via API
        try:
            import requests
            response = requests.delete(f"http://127.0.0.1:8765/teach/lessons/{lesson_id}", timeout=30)
            if response.status_code == 200:
                return {
                    "success": True,
                    "command": "delete_lesson",
                    "message": f"🗑️ Lesson {lesson_id} deleted successfully.",
                    "data": {"deleted_lesson_id": lesson_id}
                }
            else:
                return {
                    "success": False,
                    "command": "delete_lesson",
                    "message": f"⚠️ Could not delete lesson {lesson_id}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "command": "delete_lesson",
                "message": f"⚠️ Error deleting lesson: {str(e)}"
            }
    else:
        return {
            "success": False,
            "command": "delete_lesson",
            "message": "❓ Please specify which lesson to delete. Try 'delete lesson [ID]' or say 'delete this lesson' after mentioning a specific lesson."
        }

def execute_edit_lesson_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'edit lesson' command"""
    context = context or {}
    
    # Try to extract lesson ID
    lesson_id = None
    if context.get('lesson_id'):
        lesson_id = context['lesson_id']
    elif context.get('detected_lesson'):
        lesson_id = context['detected_lesson'].get('example_id') or context['detected_lesson'].get('trade_id')
    
    if not lesson_id:
        command_text = context.get('command_text', '')
        import re
        id_match = re.search(r'(?:lesson|id|trade)\s*[#:]?\s*(\d+)', command_text, re.IGNORECASE)
        if id_match:
            lesson_id = id_match.group(1)
    
    if lesson_id:
        return {
            "success": True,
            "command": "edit_lesson",
            "message": f"✏️ Opening lesson {lesson_id} for editing...\n\nYou can modify the lesson text, BOS, POI, or other fields.",
            "frontend_action": "edit_lesson",
            "data": {"lesson_id": lesson_id}
        }
    else:
        return {
            "success": False,
            "command": "edit_lesson",
            "message": "❓ Please specify which lesson to edit. Try 'edit lesson [ID]' or say 'edit this lesson' after mentioning a specific lesson."
        }

def execute_teaching_progress_command() -> Dict[str, Any]:
    """Execute 'teaching progress' command"""
    try:
        import requests
        response = requests.get("http://127.0.0.1:8765/teach/progress", timeout=30)
        if response.status_code == 200:
            data = response.json()
            progress = data.get("progress", {})
            
            message = "📊 **Teaching Progress**\n\n"
            message += f"• Total Lessons: {progress.get('total_lessons', 0)}\n"
            message += f"• Understood: {progress.get('understood', 0)}\n"
            message += f"• Average Confidence: {progress.get('avg_confidence', 0) * 100:.0f}%\n"
            message += f"• Wins: {progress.get('win_count', 0)}\n"
            message += f"• Losses: {progress.get('loss_count', 0)}\n"
            
            return {
                "success": True,
                "command": "teaching_progress",
                "message": message,
                "data": progress,
                "phase": "5f",
                "intent": "teaching_progress",
                "status": 200
            }
        else:
            return {
                "success": False,
                "command": "teaching_progress",
                "message": f"⚠️ Could not load teaching progress: {response.text}",
                "phase": "5f",
                "intent": "teaching_progress"
            }
    except Exception as e:
        return {
            "success": False,
            "command": "teaching_progress",
            "message": f"⚠️ Error loading teaching progress: {str(e)}",
            "phase": "5f",
            "intent": "teaching_progress"
        }

def execute_start_teaching_command() -> Dict[str, Any]:
    """Execute 'start teaching session' command"""
    try:
        import requests
        response = requests.post("http://127.0.0.1:8765/teach/start", timeout=15)
        if response.status_code == 200:
            return {
                "success": True,
                "command": "start_teaching",
                "message": "🎓 Teaching session started! You can now review trades one by one.",
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "command": "start_teaching",
                "message": f"⚠️ Could not start teaching session: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "command": "start_teaching",
            "message": f"⚠️ Error starting teaching session: {str(e)}"
        }

def execute_end_teaching_command() -> Dict[str, Any]:
    """Execute 'end teaching session' command"""
    try:
        import requests
        response = requests.post("http://127.0.0.1:8765/teach/end", timeout=15)
        if response.status_code == 200:
            data = response.json()
            duration = data.get('session_duration', 0)
            duration_min = duration // 60 if duration else 0
            
            message = "✅ Teaching session ended."
            if duration_min:
                message += f" Duration: {duration_min} minutes"
            
            return {
                "success": True,
                "command": "end_teaching",
                "message": message,
                "data": data
            }
        else:
            return {
                "success": False,
                "command": "end_teaching",
                "message": f"⚠️ Could not end teaching session: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "command": "end_teaching",
            "message": f"⚠️ Error ending teaching session: {str(e)}"
        }

def execute_list_trades_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute 'list trades' command - returns all trades with chart URLs
    Phase 5F.1: New handler for trade listing
    CRITICAL FIX: Supports filtering by outcome (win/loss/breakeven) from arguments
    """
    context = context or {}
    
    try:
        # Use direct file read instead of API call to avoid timeout
        from performance.utils import read_logs
        trades = read_logs()
        
        if not trades:
            return {
                "success": True,
                "command": "list_trades",
                "message": "📋 No trades found.",
                "data": {
                    "trades": [],
                    "count": 0
                }
            }
        
        # CRITICAL FIX: Check for outcome filter in arguments
        detected_command = context.get('detected_command', {})
        arguments = detected_command.get('arguments', {})
        outcome_filter = arguments.get('outcome') or arguments.get('filter')
        
        # Also check command text for keywords
        command_text = context.get('command_text', '').lower()
        if not outcome_filter:
            if any(word in command_text for word in ['losing', 'loss', 'losses', 'loser']):
                outcome_filter = 'loss'
            elif any(word in command_text for word in ['winning', 'win', 'wins', 'winner', 'profit']):
                outcome_filter = 'win'
            elif any(word in command_text for word in ['breakeven', 'even', 'zero']):
                outcome_filter = 'breakeven'
        
        # Apply outcome filter if specified
        if outcome_filter:
            outcome_filter = outcome_filter.lower()
            original_count = len(trades)
            
            if outcome_filter == 'loss':
                trades = [t for t in trades if t.get('outcome') == 'loss' or (isinstance(t.get('pnl'), (int, float)) and t.get('pnl', 0) < 0)]
            elif outcome_filter == 'win':
                trades = [t for t in trades if t.get('outcome') == 'win' or (isinstance(t.get('pnl'), (int, float)) and t.get('pnl', 0) > 0)]
            elif outcome_filter == 'breakeven':
                trades = [t for t in trades if t.get('outcome') == 'breakeven' or (isinstance(t.get('pnl'), (int, float)) and t.get('pnl', 0) == 0)]
            
            print(f"[LIST_TRADES] Applied filter '{outcome_filter}': {original_count} -> {len(trades)} trades")
        
        # Phase 5F.1: Sort trades chronologically (oldest first)
        trades = sorted(trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
        
        # === 5F.2 FIX ===
        # [5F.2 FIX F4] Persist trade list snapshot for index consistency
        from .utils import load_json, save_json
        from pathlib import Path
        import time
        
        cache_file = Path(__file__).parent.parent / "data" / "trade_list_cache.json"
        cache_data = {
            "trades": trades,
            "timestamp": time.time(),
            "count": len(trades)
        }
        try:
            save_json(str(cache_file), cache_data)
            print(f"[LIST_TRADES] Cached trade list snapshot ({len(trades)} trades)")
        except Exception as e:
            print(f"[LIST_TRADES] Warning: Failed to cache trade list: {e}")
        
        # Phase 5F.1: Attach chart_url to each trade (fast - only check direct chart_path)
        for trade in trades:
            trade = attach_chart_url(trade)
        
        message = f"📋 Found {len(trades)} trades."
        if len(trades) > 0:
            message += "\n\nUse the 🖼 Show Chart button below each trade to view its chart."
        
        return {
            "success": True,
            "command": "list_trades",
            "message": message,
            "data": {
                "trades": trades,
                "count": len(trades)
            },
            "fields": {
                "chart_url": trades[0].get("chart_url") if trades else "/charts/mock_chart.png"
            },
            "phase": "5f",
            "intent": "list_trades_command",
            "status": 200
        }
    except Exception as e:
        return {
            "success": False,
            "command": "list_trades",
            "message": f"⚠️ Error loading trades: {str(e)}",
            "phase": "5f",
            "intent": "list_trades_command"
        }


def format_trade_details_message(trade: Dict[str, Any], trade_index: int, total_trades: int, include_description: bool = True) -> str:
    """
    Format trade details message similar to "show my last trade" format.
    Used by navigation commands to show full trade details.
    """
    trade_id = trade.get('id') or trade.get('trade_id')
    symbol = trade.get('symbol', 'Unknown')
    outcome = trade.get('outcome', 'pending')
    pnl = trade.get('pnl', 0)
    r_multiple = trade.get('r_multiple', 0)
    entry_price = trade.get('entry_price')
    exit_price = trade.get('exit_price')
    
    # Format date
    timestamp = trade.get('timestamp') or trade.get('entry_time') or trade.get('trade_day') or ''
    date_str = timestamp[:10] if timestamp and len(timestamp) >= 10 else (timestamp[:20] if timestamp else 'Unknown')
    
    # Format outcome
    outcome_capitalized = outcome.capitalize() if outcome else 'Pending'
    
    # Build message
    message = f"You're currently viewing your **trade #{trade_index + 1} of {total_trades}** in the full history.\n\n"
    message += f"✔ Trade ID: {trade_id} - Symbol: {symbol}\n"
    
    if date_str and date_str != 'Unknown':
        message += f"• Date: {date_str}\n"
    
    message += f"• Outcome: {outcome_capitalized}\n"
    message += f"• P&L: ${pnl:.2f} ({r_multiple:.2f}R)\n"
    
    if entry_price:
        message += f"• Entry: ${entry_price:.2f}\n"
    if exit_price:
        message += f"• Exit: ${exit_price:.2f}\n"
    
    if include_description:
        # Add a brief description based on trade data
        direction = trade.get('direction', '')
        if direction:
            direction_str = "long" if direction.lower() == 'long' else "short"
            message += f"\nThis was a {symbol} {direction_str} trade"
            if outcome.lower() == 'loss':
                message += " that resulted in a loss."
            elif outcome.lower() == 'win':
                message += " that resulted in a win."
            else:
                message += "."
        
        message += "\n\nWould you like me to open the chart for this specific trade?"
    
    return message


def execute_next_trade_navigation_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute 'next trade' navigation command (non-teaching mode).
    Uses advance_index() for atomic index updates.
    Ensures repo count is valid and persistence works.
    Navigation Fix: Ensures each navigation returns unique trade and provides boundary feedback.
    CRITICAL FIX: Returns full trade details like "show my last trade" format.
    """
    import time
    t0 = time.perf_counter()
    context = context or {}
    
    try:
        from performance.utils import read_logs
        import memory.context_manager as ctx
        
        all_trades = context.get('all_trades') or read_logs()
        
        if not all_trades:
            return {
                "success": False,
                "command": "next_trade_navigation",
                "message": "⚠️ No trades available",
                "intent": "next_trade_navigation",
                "phase": "5f",
                "status": 200
            }
        
        sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
        
        # Ensure repo count is valid
        total = len(sorted_trades)
        if total <= 0:
            total = 1  # Ensure advance_index can still increment
        
        # Get current state BEFORE advancing
        current_state = ctx.get_context_state()
        old_idx = current_state.get("current_trade_index") or current_state.get("current_index", 0)
        
        # CRITICAL: Also get directly from get_current_trade_index to ensure we have the latest value
        # This bypasses any cache inconsistencies
        direct_idx = ctx.get_current_trade_index()
        if direct_idx != old_idx:
            print(f"[NEXT_TRADE] WARNING: Index mismatch! get_context_state()={old_idx}, get_current_trade_index()={direct_idx}")
            old_idx = direct_idx  # Use the direct value as it's more reliable
        
        print(f"[NEXT_TRADE] DEBUG: Starting navigation - old_idx={old_idx}, total_trades={total}")
        
        # Use advance_index() with wrapping DISABLED for correct chronological order
        # "Next trade" should move forward in time (newer trades), not wrap around
        new_state = ctx.advance_index(total_trades=total, wrap=False)
        new_idx = new_state["current_trade_index"]
        wrapped = new_state.get("wrapped", False)
        
        # CRITICAL: Verify the index actually changed by reading directly
        verify_new_idx = ctx.get_current_trade_index()
        if verify_new_idx != new_idx:
            print(f"[NEXT_TRADE] WARNING: advance_index() returned {new_idx}, but get_current_trade_index() returns {verify_new_idx}")
            new_idx = verify_new_idx  # Use the verified value
        
        print(f"[NEXT_TRADE] DEBUG: After advance_index - old_idx={old_idx}, new_idx={new_idx}, wrapped={wrapped}")
        
        # CRITICAL: If index didn't change AND we're not at the last trade, something is wrong
        if old_idx == new_idx:
            if old_idx == total - 1:
                # At last trade, cannot go forward - this is expected
                print(f"[NEXT_TRADE] Boundary check: Already at last trade (index {old_idx} of {total})")
            else:
                # Index didn't advance but we're not at the boundary - this is a bug!
                print(f"[NEXT_TRADE] ERROR: Index didn't advance! old_idx={old_idx}, new_idx={new_idx}, total={total}")
                # Force increment manually as a fallback
                if old_idx < total - 1:
                    manual_new_idx = old_idx + 1
                    ctx.set_current_trade_index(manual_new_idx)
                    new_idx = manual_new_idx
                    print(f"[NEXT_TRADE] FALLBACK: Manually set index to {new_idx}")
                else:
                    # We're at the last trade, stay here
                    print(f"[NEXT_TRADE] FALLBACK: Already at last trade, staying at index {old_idx}")
        
        # Navigation Fix: Check if we're at boundary (already at last trade)
        if old_idx == new_idx and old_idx == total - 1:
            # At last trade, cannot go forward
            return {
                "success": True,
                "command": "view_trade",
                "message": f"ℹ️ You're already at the last trade (#{total}). Use 'previous trade' to go back.",
                "intent": "view_trade",
                "phase": "5f",
                "status": 200,
                "duration_ms": round((time.perf_counter() - t0) * 1000, 2),
                "current_trade_index": old_idx,
                "data": {
                    "trade": sorted_trades[old_idx] if old_idx < len(sorted_trades) else None,
                    "trade_index": old_idx,
                    "chart_url": sorted_trades[old_idx].get("chart_url") if old_idx < len(sorted_trades) else None
                },
                "fields": {
                    "chart_url": sorted_trades[old_idx].get("chart_url") if old_idx < len(sorted_trades) else None
                },
                "passed": True
            }
        
        # CRITICAL FIX: Get trade by index - ensure we use the exact trade from sorted list
        # Never use cached or stale trade references
        next_trade = None
        if new_idx < len(sorted_trades):
            next_trade = sorted_trades[new_idx].copy()  # CRITICAL: Create copy to avoid reference issues
            print(f"[NEXT_TRADE] CRITICAL: Retrieved trade at index {new_idx}: ID={next_trade.get('id')}, Symbol={next_trade.get('symbol')}, Date={next_trade.get('timestamp') or next_trade.get('entry_time')}")
        else:
            # Should not happen with wrap=False, but handle gracefully
            print(f"[NEXT_TRADE] ERROR: new_idx {new_idx} >= len(sorted_trades) {len(sorted_trades)}")
            # This shouldn't happen, but if it does, stay at last trade
            next_trade = sorted_trades[-1].copy() if sorted_trades else None
            new_idx = len(sorted_trades) - 1 if sorted_trades else 0
        
        # CRITICAL FIX: Validate that we're returning the correct trade at the new index
        # Ensure trade ID matches what's expected at this index
        if next_trade:
            trade_id_at_index = next_trade.get('id') or next_trade.get('trade_id')
            expected_trade = sorted_trades[new_idx] if new_idx < len(sorted_trades) else None
            expected_trade_id = expected_trade.get('id') or expected_trade.get('trade_id') if expected_trade else None
            
            # Validation: Ensure trade ID matches expected trade at index
            if expected_trade_id and trade_id_at_index != expected_trade_id:
                print(f"[NEXT_TRADE] WARNING: Trade ID mismatch! Expected {expected_trade_id} at index {new_idx}, got {trade_id_at_index}")
                # Use the correct trade from sorted list
                next_trade = expected_trade.copy()
                next_trade = attach_chart_url(next_trade)
            
            next_trade = attach_chart_url(next_trade)
            # Ensure chart_url is set
            if not next_trade.get("chart_url"):
                trade_id = next_trade.get('id') or next_trade.get('trade_id')
                symbol = next_trade.get('symbol', 'Unknown')
                next_trade["chart_url"] = f"/charts/{symbol}_5m_{trade_id}.png"
            
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            
            # CRITICAL FIX: Use same format as view_trade command
            trade_id = next_trade.get('id') or next_trade.get('trade_id')
            symbol = next_trade.get('symbol', 'Unknown')
            outcome = next_trade.get('outcome', 'pending')
            pnl = next_trade.get('pnl', 0)
            r_multiple = next_trade.get('r_multiple', 0)
            chart_url = next_trade.get("chart_url")
            
            # Format message same as view_trade command
            message = f"📊 **Trade {trade_id} Details**\n\n"
            message += f"• Symbol: {symbol}\n"
            message += f"• Outcome: {outcome}\n"
            message += f"• P&L: ${pnl:.2f}\n"
            message += f"• R-Multiple: {r_multiple:.2f}R"
            
            # Navigation Fix: Log the trade change for debugging
            print(f"[NEXT_TRADE] CRITICAL FIX: Index changed: {old_idx} → {new_idx}, Trade ID: {trade_id}, Symbol: {symbol}")
            
            # CRITICAL FIX: Return as view_trade command so frontend shows chart button
            return {
                "success": True,
                "command": "view_trade",  # CRITICAL: Use view_trade so frontend recognizes it
                "message": message,  # CRITICAL: Same format as view_trade
                "intent": "view_trade",  # CRITICAL: Use view_trade intent
                "phase": "5f",
                "status": 200,
                "duration_ms": elapsed_ms,
                "current_trade_index": new_idx,
                "data": {
                    "trade": next_trade,  # CRITICAL: Full trade object
                    "trade_index": new_idx,
                    "old_index": old_idx,
                    "trade_id": trade_id,  # CRITICAL: Explicit trade ID for validation
                    "symbol": symbol,  # CRITICAL: Explicit symbol for validation
                    "chart_url": chart_url  # CRITICAL: Include chart URL for button
                },
                "fields": {
                    "chart_url": chart_url  # CRITICAL: Include chart_url in fields for frontend
                },
                "passed": True
            }
        else:
            return {
                "success": False,
                "command": "next_trade_navigation",
                "message": "⚠️ Already at last trade",
                "intent": "next_trade_navigation",
                "phase": "5f",
                "status": 200
            }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[NEXT_TRADE] Error: {e}\n{error_trace[:300]}")
        return {
            "success": False,
            "command": "next_trade_navigation",
            "message": f"⚠️ Error navigating to next trade: {str(e)}",
            "intent": "next_trade_navigation",
            "phase": "5f",
            "status": 500
        }


def execute_previous_trade_navigation_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute 'previous trade' navigation command (non-teaching mode).
    Phase 5F Fix: Handles edge case when at first trade with friendly message.
    """
    import time
    t0 = time.perf_counter()
    context = context or {}
    
    try:
        from performance.utils import read_logs
        import memory.context_manager as ctx
        
        all_trades = context.get('all_trades') or read_logs()
        
        if not all_trades:
            return {
                "success": False,
                "command": "previous_trade_navigation",
                "message": "⚠️ No trades available",
                "intent": "previous_trade_navigation",
                "phase": "5f",
                "status": 200
            }
        
        sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
        total = len(sorted_trades)
        
        if total <= 0:
            return {
                "success": False,
                "command": "previous_trade_navigation",
                "message": "⚠️ No trades available",
                "intent": "previous_trade_navigation",
                "phase": "5f",
                "status": 200
            }
        
        # Get current index BEFORE decrementing
        current_state = ctx.get_context_state()
        old_idx = current_state.get("current_trade_index") or current_state.get("current_index", 0)
        
        print(f"[PREVIOUS_TRADE] DEBUG: Starting navigation - old_idx={old_idx}, total_trades={total}")
        
        # Decrement index (with wrapping DISABLED for correct chronological order)
        # "Previous trade" should move backward in time (older trades), not wrap around
        # CRITICAL FIX: Check boundary BEFORE decrementing
        if old_idx <= 0:
            # Already at first trade, cannot go back
            print(f"[PREVIOUS_TRADE] Boundary check: Already at first trade (index 0)")
            return {
                "success": True,
                "command": "view_trade",
                "message": f"ℹ️ You're already at the first trade (#1 of {total}). Use 'next trade' to move forward.",
                "intent": "view_trade",
                "phase": "5f",
                "status": 200,
                "duration_ms": round((time.perf_counter() - t0) * 1000, 2),
                "current_trade_index": 0,
                "data": {
                    "trade": sorted_trades[0] if sorted_trades else None,
                    "trade_index": 0,
                    "chart_url": sorted_trades[0].get("chart_url") if sorted_trades and sorted_trades[0] else None
                },
                "fields": {
                    "chart_url": sorted_trades[0].get("chart_url") if sorted_trades and sorted_trades[0] else None
                },
                "passed": True
            }
        
        new_idx = old_idx - 1
        
        # CRITICAL FIX: Use set_current_trade_index() instead of non-existent set_context_state()
        from memory.context_manager import set_current_trade_index
        set_current_trade_index(new_idx)
        
        # Also verify the index was set correctly
        verify_idx = ctx.get_current_trade_index()
        if verify_idx != new_idx:
            print(f"[PREVIOUS_TRADE] WARNING: Index mismatch! Set to {new_idx}, but get_current_trade_index() returns {verify_idx}")
            new_idx = verify_idx  # Use the verified value
        
        print(f"[PREVIOUS_TRADE] DEBUG: After decrement - old_idx={old_idx}, new_idx={new_idx}")
        
        # CRITICAL FIX: Get trade by index - ensure we use the exact trade from sorted list
        # Never use cached or stale trade references
        previous_trade = None
        if new_idx < len(sorted_trades):
            previous_trade = sorted_trades[new_idx].copy()  # CRITICAL: Create copy to avoid reference issues
        
        # CRITICAL FIX: Validate that we're returning the correct trade at the new index
        if previous_trade:
            trade_id_at_index = previous_trade.get('id') or previous_trade.get('trade_id')
            expected_trade = sorted_trades[new_idx] if new_idx < len(sorted_trades) else None
            expected_trade_id = expected_trade.get('id') or expected_trade.get('trade_id') if expected_trade else None
            
            # Validation: Ensure trade ID matches expected trade at index
            if expected_trade_id and trade_id_at_index != expected_trade_id:
                print(f"[PREVIOUS_TRADE] WARNING: Trade ID mismatch! Expected {expected_trade_id} at index {new_idx}, got {trade_id_at_index}")
                # Use the correct trade from sorted list
                previous_trade = expected_trade.copy()
                previous_trade = attach_chart_url(previous_trade)
            
            previous_trade = attach_chart_url(previous_trade)
            # Ensure chart_url is set
            if not previous_trade.get("chart_url"):
                trade_id = previous_trade.get('id') or previous_trade.get('trade_id')
                symbol = previous_trade.get('symbol', 'Unknown')
                previous_trade["chart_url"] = f"/charts/{symbol}_5m_{trade_id}.png"
            
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            
            # CRITICAL FIX: Use same format as view_trade command
            trade_id = previous_trade.get('id') or previous_trade.get('trade_id')
            symbol = previous_trade.get('symbol', 'Unknown')
            outcome = previous_trade.get('outcome', 'pending')
            pnl = previous_trade.get('pnl', 0)
            r_multiple = previous_trade.get('r_multiple', 0)
            chart_url = previous_trade.get("chart_url")
            
            # Format message same as view_trade command
            message = f"📊 **Trade {trade_id} Details**\n\n"
            message += f"• Symbol: {symbol}\n"
            message += f"• Outcome: {outcome}\n"
            message += f"• P&L: ${pnl:.2f}\n"
            message += f"• R-Multiple: {r_multiple:.2f}R"
            
            # Navigation Fix: Log the trade change for debugging
            print(f"[PREVIOUS_TRADE] CRITICAL FIX: Index changed: {old_idx} → {new_idx}, Trade ID: {trade_id}, Symbol: {symbol}")
            
            # CRITICAL FIX: Return as view_trade command so frontend shows chart button
            return {
                "success": True,
                "command": "view_trade",  # CRITICAL: Use view_trade so frontend recognizes it
                "message": message,  # CRITICAL: Same format as view_trade
                "intent": "view_trade",  # CRITICAL: Use view_trade intent
                "phase": "5f",
                "status": 200,
                "duration_ms": elapsed_ms,
                "current_trade_index": new_idx,
                "data": {
                    "trade": previous_trade,  # CRITICAL: Full trade object
                    "trade_index": new_idx,
                    "old_index": old_idx,
                    "trade_id": trade_id,  # CRITICAL: Explicit trade ID for validation
                    "symbol": symbol,  # CRITICAL: Explicit symbol for validation
                    "chart_url": chart_url  # CRITICAL: Include chart URL for button
                },
                "fields": {
                    "chart_url": chart_url  # CRITICAL: Include chart_url in fields for frontend
                },
                "passed": True
            }
        else:
            return {
                "success": False,
                "command": "previous_trade_navigation",
                "message": "⚠️ Error: Could not find trade at index",
                "intent": "previous_trade_navigation",
                "phase": "5f",
                "status": 500
            }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[PREVIOUS_TRADE] Error: {e}\n{error_trace[:300]}")
        return {
            "success": False,
            "command": "previous_trade_navigation",
            "message": f"⚠️ Error navigating to previous trade: {str(e)}",
            "intent": "previous_trade_navigation",
            "phase": "5f",
            "status": 500
        }


def execute_random_winning_trade_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute 'random winning trade' command.
    Ensures trade_id and chart_url are always present.
    """
    import time
    import random
    
    t0 = time.perf_counter()
    context = context or {}
    
    try:
        from performance.utils import read_logs
        
        all_trades = context.get('all_trades') or read_logs()
        if not all_trades:
            return {
                "success": False,
                "command": "random_winning_trade",
                "message": "❓ No trades found. Try logging some trades first.",
                "intent": "random_winning_trade",
                "phase": "5f",
                "status": 200
            }
        
        # Filter winning trades (pnl > 0)
        winning_trades = [
            t for t in all_trades 
            if t.get('outcome') == 'win' or (isinstance(t.get('pnl'), (int, float)) and t.get('pnl', 0) > 0)
        ]
        
        if not winning_trades:
            return {
                "success": False,
                "command": "random_winning_trade",
                "message": "❓ No winning trades found. Try 'list my trades' to see all trades.",
                "intent": "random_winning_trade",
                "phase": "5f",
                "status": 200
            }
        
        # Pick random winning trade
        random_trade = random.choice(winning_trades)
        
        # Ensure trade_id is always set
        random_trade.setdefault("trade_id", random_trade.get("id") or random_trade.get("tradeId"))
        
        # Ensure chart_url is always set
        if not random_trade.get("chart_url"):
            trade_id = random_trade.get("trade_id") or random_trade.get("id")
            symbol = random_trade.get('symbol', 'Unknown')
            random_trade["chart_url"] = f"/charts/{symbol}_5m_{trade_id}.png"
        
        # Attach chart URL using helper
        random_trade = attach_chart_url(random_trade)
        
        # Ensure chart_url is still set after attach_chart_url
        if not random_trade.get("chart_url"):
            trade_id = random_trade.get("trade_id") or random_trade.get("id")
            symbol = random_trade.get('symbol', 'Unknown')
            random_trade["chart_url"] = f"/charts/{symbol}_5m_{trade_id}.png"
        
        trade_id = random_trade.get("trade_id") or random_trade.get('id')
        symbol = random_trade.get('symbol', 'Unknown')
        pnl = random_trade.get('pnl', 0)
        r_multiple = random_trade.get('r_multiple', 0)
        
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        
        message = f"🎲 **Random Winning Trade**\n\n"
        message += f"• Trade ID: {trade_id}\n"
        message += f"• Symbol: {symbol}\n"
        message += f"• P&L: ${pnl:.2f}\n"
        message += f"• R-Multiple: {r_multiple:.2f}R"
        
        # Ensure chart_url is always present
        chart_url = random_trade.get("chart_url") or f"/charts/{symbol}_5m_{trade_id}.png"
        
        return {
            "success": True,
            "command": "random_winning_trade",
            "message": message,
            "intent": "random_winning_trade",
            "phase": "5f",
            "status": 200,
            "duration_ms": elapsed_ms,
            "chart_url": chart_url,
            "data": {
                "trade": random_trade
            },
            "fields": {
                "chart_url": chart_url,
                "trade_id": trade_id
            },
            "passed": True
        }
    except Exception as e:
        return {
            "success": False,
            "command": "random_winning_trade",
            "message": f"⚠️ Error selecting random winning trade: {str(e)}",
            "intent": "random_winning_trade",
            "phase": "5f",
            "status": 500
        }


def execute_next_trade_teaching_command() -> Dict[str, Any]:
    """Execute 'next trade' command - offline mock navigation for validator."""
    try:
        from performance.utils import read_logs
        from memory.context_manager import get_current_trade_index, increment_trade_index, set_current_trade_index
        
        # Get current trade index
        current_idx = get_current_trade_index()
        all_trades = read_logs()
        
        if not all_trades:
            return {
                "success": False,
                "command": "next_trade_teaching",
                "message": "⚠️ No trades available",
                "phase": "5f"
            }
        
        # Sort trades chronologically (oldest first)
        sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
        
        # Check if already at last trade
        if current_idx >= len(sorted_trades) - 1:
            return {
                "success": False,
                "command": "next_trade_teaching",
                "message": "⚠️ Already at last trade",
                "phase": "5f"
            }
        
        # Move to next trade
        new_idx = increment_trade_index()
        if new_idx < len(sorted_trades):
            next_trade = sorted_trades[new_idx]
            next_trade = attach_chart_url(next_trade)
            
            return {
                "success": True,
                "command": "next_trade_teaching",
                "message": "➡️ Moved to next trade",
                "phase": "5f",
                "data": {
                    "trade": next_trade,
                    "trade_index": new_idx
                },
                "fields": {
                    "chart_url": next_trade.get("chart_url")
                }
            }
        else:
            return {
                "success": False,
                "command": "next_trade_teaching",
                "message": "⚠️ Already at last trade",
                "phase": "5f"
            }
    except Exception as e:
        return {
            "success": False,
            "command": "next_trade_teaching",
            "message": f"⚠️ Error moving to next trade: {str(e)}",
            "phase": "5f"
        }


def execute_previous_trade_teaching_command() -> Dict[str, Any]:
    """
    Execute 'previous trade' command in teaching mode
    Phase 5F.1: New handler for backward navigation
    """
    try:
        from .utils import load_json, save_json
        from pathlib import Path
        
        ctx_path = Path(__file__).parent.parent / "data" / "session_contexts.json"
        ctx = load_json(str(ctx_path), {})
        
        if not isinstance(ctx, dict):
            ctx = {"current_trade_index": 0}
        
        current_idx = ctx.get("current_trade_index", 0)
        if current_idx > 0:
            ctx["current_trade_index"] = current_idx - 1
        else:
            return {
                "success": False,
                "command": "previous_trade_teaching",
                "message": "⚠️ Already at the first trade. Cannot go back further."
            }
        
        save_json(str(ctx_path), ctx)
        
        # Try to get current trade and its chart URL
        trade_id = None
        chart_url = None
        try:
            import requests
            perf_response = requests.get("http://127.0.0.1:8765/performance/all?limit=1000", timeout=30)
            if perf_response.status_code == 200:
                all_trades = perf_response.json()
                if ctx["current_trade_index"] < len(all_trades):
                    trade = all_trades[ctx["current_trade_index"]]
                    trade_id = trade.get('id') or trade.get('trade_id')
                    chart_url = get_chart_url(trade)
        except Exception:
            pass
        
        return {
            "success": True,
            "command": "previous_trade_teaching",
            "message": f"⬅️ Moved to trade index {ctx['current_trade_index']}",
            "data": {
                "trade_index": ctx["current_trade_index"],
                "trade_id": trade_id,
                "chart_url": chart_url
            }
        }
    except Exception as e:
        return {
            "success": False,
            "command": "previous_trade_teaching",
            "message": f"⚠️ Error moving to previous trade: {str(e)}"
        }

def execute_skip_trade_teaching_command() -> Dict[str, Any]:
    """Execute 'skip trade' command in teaching mode"""
    try:
        import requests
        response = requests.post("http://127.0.0.1:8765/teach/skip", timeout=30)
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "command": "skip_trade_teaching",
                "message": f"⏭️ Trade skipped. Moved to index {data.get('next_trade_index', 0)}",
                "data": data
            }
        else:
            return {
                "success": False,
                "command": "skip_trade_teaching",
                "message": f"⚠️ Could not skip trade: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "command": "skip_trade_teaching",
            "message": f"⚠️ Error skipping trade: {str(e)}"
        }

def execute_delete_trade_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute 'delete trade' command"""
    context = context or {}
    
    # Try to extract trade ID
    trade_id = None
    if context.get('trade_id'):
        trade_id = context['trade_id']
    elif context.get('detected_trade'):
        trade_id = context['detected_trade'].get('id') or context['detected_trade'].get('trade_id')
    
    if not trade_id:
        command_text = context.get('command_text', '')
        import re
        id_match = re.search(r'(?:trade|id)\s*[#:]?\s*(\d+)', command_text, re.IGNORECASE)
        if id_match:
            trade_id = id_match.group(1)
    
    if trade_id:
        try:
            import requests
            response = requests.delete(f"http://127.0.0.1:8765/performance/trades/{trade_id}", timeout=30)
            if response.status_code == 200:
                return {
                    "success": True,
                    "command": "delete_trade",
                    "message": f"🗑️ Trade {trade_id} deleted successfully.",
                    "data": {"deleted_trade_id": trade_id}
                }
            else:
                return {
                    "success": False,
                    "command": "delete_trade",
                    "message": f"⚠️ Could not delete trade {trade_id}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "command": "delete_trade",
                "message": f"⚠️ Error deleting trade: {str(e)}"
            }
    else:
        return {
            "success": False,
            "command": "delete_trade",
            "message": "❓ Please specify which trade to delete. Try 'delete trade [ID]' or say 'delete this trade' after mentioning a specific trade."
        }

def execute_view_trade_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute 'view trade' command
    Phase 5F.1: Uses Intent Analyzer arguments instead of regex
    CRITICAL FIX: Handles "what trade am I on?" queries using current session context
    """
    import time
    
    t0 = time.perf_counter()
    context = context or {}
    
    # CRITICAL FIX: Check for "current trade" or "what trade am I on?" queries FIRST
    command_text = context.get('command_text', '').lower()
    is_current_trade_query = any(phrase in command_text for phrase in [
        'what trade', 'which trade', 'trade am i', 'trade im i', 'current trade', 
        'trade on', 'trade am on', 'viewing', 'currently viewing', 'on now'
    ])
    
    # If this is a query about current trade status, use session context
    if is_current_trade_query and not context.get('trade_id') and not context.get('detected_trade'):
        try:
            import memory.context_manager as ctx
            from performance.utils import read_logs
            
            current_state = ctx.get_context_state()
            current_idx = current_state.get("current_trade_index", None)
            
            if current_idx is not None:
                all_trades = context.get('all_trades') or read_logs()
                if all_trades:
                    sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                    if 0 <= current_idx < len(sorted_trades):
                        current_trade = sorted_trades[current_idx]
                        trade_id = current_trade.get('id') or current_trade.get('trade_id')
                        symbol = current_trade.get('symbol', 'Unknown')
                        outcome = current_trade.get('outcome', 'pending')
                        pnl = current_trade.get('pnl', 0)
                        r_multiple = current_trade.get('r_multiple', 0)
                        
                        # Attach chart URL
                        trade_data = current_trade.copy()
                        trade_data = attach_chart_url(trade_data)
                        chart_url = trade_data.get("chart_url")
                        
                        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                        
                        print(f"[VIEW_TRADE] CRITICAL FIX: Current trade query resolved to index {current_idx}: {trade_id} ({symbol})")
                        
                        message = f"You're currently viewing your **trade #{current_idx + 1} of {len(sorted_trades)}**:\n\n"
                        message += f"✔ Trade ID: {trade_id} - Symbol: {symbol}\n"
                        message += f"• Date: {current_trade.get('timestamp', 'Unknown')}\n"
                        message += f"• P&L: ${pnl:.2f} ({r_multiple:.2f}R)\n"
                        message += f"• Status: {outcome}"
                        
                        return {
                            "success": True,
                            "command": "view_trade",
                            "message": message,
                            "intent": "view_trade",
                            "phase": "5f",
                            "status": 200,
                            "duration_ms": elapsed_ms,
                            "data": {
                                "trade": trade_data,
                                "trade_id": trade_id,
                                "symbol": symbol,
                                "trade_index": current_idx,
                                "total_trades": len(sorted_trades),
                                "chart_url": chart_url
                            },
                            "fields": {
                                "chart_url": chart_url
                            }
                        }
        except Exception as e:
            print(f"[VIEW_TRADE] Error handling current trade query: {e}")
            import traceback
            traceback.print_exc()
    
    # Phase 5F.1: Extract trade_id from Intent Analyzer arguments (no regex fallback)
    trade_id = None
    detected_command = context.get('detected_command', {})
    arguments = detected_command.get('arguments', {})
    
    print(f"[VIEW_TRADE] detected_command: {detected_command}")
    print(f"[VIEW_TRADE] arguments: {arguments}")
    
    # Try arguments.trade_id first
    trade_id = arguments.get('trade_id')
    if trade_id:
        try:
            trade_id = int(trade_id)
            print(f"[VIEW_TRADE] Found trade_id from arguments: {trade_id}")
        except (ValueError, TypeError):
            trade_id = None
    
    # === 5F.2 FIX ===
    # Try trade_reference (first, last, recent, second, third, fourth, random_win, previous, next, etc.)
    if not trade_id:
        trade_reference = arguments.get('trade_reference', '').lower()
        print(f"[VIEW_TRADE] trade_reference from arguments: '{trade_reference}'")
        
        # Normalize "latest" to "last"
        if trade_reference == 'latest':
            trade_reference = 'last'
        
        # [5F.2 FIX F3] Handle "previous" and "next" using context_manager
        if trade_reference in ['previous', 'prev', 'back']:
            from memory.context_manager import get_current_trade_index, decrement_trade_index
            from performance.utils import read_logs
            
            current_idx = get_current_trade_index()
            if current_idx <= 0:
                return {
                    "success": False,
                    "command": "view_trade",
                    "message": "⚠️ Already at the first trade. Cannot go back further.",
                    "data": {"current_index": current_idx}
                }
            
            new_idx = decrement_trade_index()
            all_trades = context.get('all_trades') or read_logs()
            if all_trades:
                # Sort trades chronologically (oldest first) for index-based lookup
                sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                if new_idx is not None and new_idx < len(sorted_trades):
                    trade_id = sorted_trades[new_idx].get('id') or sorted_trades[new_idx].get('trade_id')
                    print(f"[VIEW_TRADE] Resolved 'previous' to index {new_idx}, trade ID: {trade_id}")
                else:
                    return {
                        "success": False,
                        "command": "view_trade",
                        "message": f"⚠️ Invalid index {new_idx} (total trades: {len(sorted_trades)})"
                    }
        
        elif trade_reference in ['next']:
            from memory.context_manager import get_current_trade_index, increment_trade_index
            from performance.utils import read_logs
            
            current_idx = get_current_trade_index()
            new_idx = increment_trade_index()
            all_trades = context.get('all_trades') or read_logs()
            if all_trades:
                # Sort trades chronologically (oldest first) for index-based lookup
                sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                if new_idx < len(sorted_trades):
                    trade_id = sorted_trades[new_idx].get('id') or sorted_trades[new_idx].get('trade_id')
                    print(f"[VIEW_TRADE] Resolved 'next' to index {new_idx}, trade ID: {trade_id}")
                else:
                    return {
                        "success": False,
                        "command": "view_trade",
                        "message": f"⚠️ Already at the last trade (index {new_idx} of {len(sorted_trades)}). Cannot go forward.",
                        "data": {"current_index": new_idx, "total_trades": len(sorted_trades)}
                    }
        
        # [5F.2 FIX F2] Handle "random_win" - pick random winning trade
        elif trade_reference == 'random_win':
            import random
            from performance.utils import read_logs
            
            all_trades = context.get('all_trades') or read_logs()
            if all_trades:
                winning_trades = [t for t in all_trades if t.get('outcome') == 'win' or (isinstance(t.get('pnl'), (int, float)) and t.get('pnl', 0) > 0)]
                if winning_trades:
                    random_trade = random.choice(winning_trades)
                    trade_id = random_trade.get('id') or random_trade.get('trade_id')
                    print(f"[VIEW_TRADE] Resolved 'random_win' to trade ID: {trade_id} (from {len(winning_trades)} winning trades)")
                else:
                    return {
                        "success": False,
                        "command": "view_trade",
                        "message": "❓ No winning trades found. Try 'list my trades' to see all trades."
                    }
        
        # Handle ordinal numbers (first, second, third, etc.)
        ordinal_map = {
            'first': 1,
            'second': 2,
            'third': 3,
            'fourth': 4,
            'fifth': 5,
            'sixth': 6,
            'seventh': 7,
            'eighth': 8,
            'ninth': 9,
            'tenth': 10
        }
        
        if trade_reference in ['first', 'last', 'recent']:
            from performance.utils import read_logs
            all_trades = context.get('all_trades') or read_logs()
            if all_trades:
                # Sort trades by timestamp (most recent first for 'last', oldest first for 'first')
                # Handle both timestamp formats: ISO string or Unix timestamp
                def get_timestamp_sort_key(trade):
                    ts = trade.get('timestamp') or trade.get('entry_time') or ''
                    if isinstance(ts, (int, float)):
                        return ts
                    if isinstance(ts, str):
                        try:
                            # Try parsing as ISO datetime string
                            from datetime import datetime
                            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            return dt.timestamp()
                        except:
                            # Fallback: try Unix timestamp string
                            try:
                                return float(ts)
                            except:
                                return 0
                    return 0
                
                sorted_trades = sorted(all_trades, key=get_timestamp_sort_key, reverse=(trade_reference == 'last'))
                if sorted_trades:
                    trade_id = sorted_trades[0].get('id') or sorted_trades[0].get('trade_id')
                    print(f"[VIEW_TRADE] Resolved {trade_reference} trade: {trade_id} (from {len(all_trades)} total trades)")
                    print(f"[VIEW_TRADE] Selected trade timestamp: {sorted_trades[0].get('timestamp') or sorted_trades[0].get('entry_time')}")
        elif trade_reference in ordinal_map:
            # Handle ordinal positions (1-based index)
            ordinal_index = ordinal_map[trade_reference]
            from performance.utils import read_logs
            all_trades = context.get('all_trades') or read_logs()
            if all_trades:
                # Sort trades chronologically (oldest first) for ordinal lookup
                sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                if ordinal_index <= len(sorted_trades):
                    trade_id = sorted_trades[ordinal_index - 1].get('id') or sorted_trades[ordinal_index - 1].get('trade_id')
                    print(f"[VIEW_TRADE] Resolved {trade_reference} (index {ordinal_index - 1}) trade: {trade_id}")
                else:
                    print(f"[VIEW_TRADE] Ordinal {trade_reference} ({ordinal_index}) exceeds trade count ({len(sorted_trades)})")
    
    # Fallback: Try to extract from command text if arguments not available
    if not trade_id:
        command_text = context.get('command_text', '')
        if command_text:
            import re
            # Try to extract trade ID from text like "trade #13" or "trade 13"
            id_match = re.search(r'(?:trade|#)\s*[#:]?\s*(\d+)', command_text, re.IGNORECASE)
            if id_match:
                extracted_id = int(id_match.group(1))
                print(f"[VIEW_TRADE] Extracted ID from command text: {extracted_id}")
                
                # Try to find trade by ID first
                from performance.utils import read_logs
                all_trades = context.get('all_trades') or read_logs()
                
                # Check if this ID exists as a trade ID
                found_trade = None
                for t in all_trades:
                    if (t.get('id') == extracted_id or 
                        t.get('trade_id') == extracted_id or 
                        str(t.get('id')) == str(extracted_id) or
                        str(t.get('trade_id')) == str(extracted_id)):
                        found_trade = t
                        break
                
                if found_trade:
                    trade_id = extracted_id
                    print(f"[VIEW_TRADE] Found trade with ID {extracted_id}")
                else:
                    # === 5F.2 FIX ===
                    # [5F.2 FIX F4] Try to resolve via trade_list_cache.json first
                    from .utils import load_json
                    from pathlib import Path
                    import time
                    
                    cache_file = Path(__file__).parent.parent / "data" / "trade_list_cache.json"
                    cache_stale = True
                    cached_trades = None
                    
                    if cache_file.exists():
                        try:
                            cache_data = load_json(str(cache_file), {})
                            cache_age = time.time() - cache_data.get('timestamp', 0)
                            if cache_age < 300:  # Cache valid for 5 minutes
                                cached_trades = cache_data.get('trades', [])
                                cache_stale = False
                                print(f"[VIEW_TRADE] Using cached trade list (age: {cache_age:.1f}s)")
                        except Exception as e:
                            print(f"[VIEW_TRADE] Failed to load cache: {e}")
                    
                    # ID doesn't exist - interpret as index (1-based)
                    # e.g., "trade #13" means the 13th trade
                    trades_to_use = cached_trades if cached_trades and not cache_stale else all_trades
                    
                    if cache_stale and cached_trades:
                        # Warn user that cache is stale
                        print(f"[VIEW_TRADE] Cache stale ({time.time() - cache_data.get('timestamp', 0):.1f}s old), using current trade list")
                    
                    if extracted_id <= len(trades_to_use):
                        # Sort trades by timestamp (oldest first for index-based lookup)
                        sorted_trades = sorted(trades_to_use, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                        if extracted_id - 1 < len(sorted_trades):
                            trade_id = sorted_trades[extracted_id - 1].get('id') or sorted_trades[extracted_id - 1].get('trade_id')
                            print(f"[VIEW_TRADE] Interpreting #{extracted_id} as index {extracted_id - 1}, found trade ID: {trade_id}")
                            if cache_stale:
                                print(f"[VIEW_TRADE] Note: Trade list cache is stale. Consider running 'list my trades' to refresh.")
                        else:
                            print(f"[VIEW_TRADE] Index {extracted_id} exceeds trade count ({len(trades_to_use)})")
                    elif cache_stale:
                        return {
                            "success": False,
                            "command": "view_trade",
                            "message": f"⚠️ Trade list cache is stale. Please run 'list my trades' first to refresh the cache, then try again."
                        }
            
            # Try to detect "first", "last", or "latest" from command text
            elif 'first' in command_text.lower():
                from performance.utils import read_logs
                all_trades = context.get('all_trades') or read_logs()
                if all_trades:
                    sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                    if sorted_trades:
                        trade_id = sorted_trades[0].get('id') or sorted_trades[0].get('trade_id')
                        print(f"[VIEW_TRADE] Resolved 'first' from command text: {trade_id}")
            elif 'last' in command_text.lower() or 'latest' in command_text.lower():
                from performance.utils import read_logs
                all_trades = context.get('all_trades') or read_logs()
                if all_trades:
                    # CRITICAL FIX: Use same sorting as navigation commands (oldest first, reverse=False)
                    # Then take the LAST item to get the latest trade
                    # This ensures index consistency with navigation commands
                    sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                    if sorted_trades:
                        # Take the last item (newest trade) from oldest-first sorted list
                        trade_id = sorted_trades[-1].get('id') or sorted_trades[-1].get('trade_id')
                        print(f"[VIEW_TRADE] Resolved 'last/latest' from command text: {trade_id} (index {len(sorted_trades) - 1} of {len(sorted_trades)})")
    
    # Fallback to detected_trade from context
    if not trade_id:
        detected_trade = context.get('detected_trade')
        if detected_trade:
            trade_id = detected_trade.get('id') or detected_trade.get('trade_id')
            print(f"[VIEW_TRADE] Using detected_trade from context: {trade_id}")
    
    # CRITICAL FIX: If still no trade_id, try trade_detector with conversation history
    if not trade_id:
        command_text = context.get('command_text', '')
        conversation_history = context.get('conversation_history', [])
        
        if command_text and conversation_history:
            from utils.trade_detector import detect_trade_reference
            from performance.utils import read_logs
            
            all_trades = context.get('all_trades') or read_logs()
            detected_trade = detect_trade_reference(command_text, all_trades, conversation_history)
            
            if detected_trade:
                trade_id = detected_trade.get('id') or detected_trade.get('trade_id')
                print(f"[VIEW_TRADE] Resolved trade from conversation context: {trade_id} ({detected_trade.get('symbol')})")
    
    if trade_id:
        try:
            # OPTIMIZATION: Use direct file read instead of HTTP calls to avoid 30s timeout delays
            # This eliminates the ~30s delay by reading from cached file instead of waiting for HTTP
            from performance.utils import read_logs
            all_trades = context.get('all_trades') or read_logs()
            trade = next((t for t in all_trades if str(t.get('id')) == str(trade_id) or str(t.get('trade_id')) == str(trade_id) or 
                          str(t.get('id')) == str(trade_id) or str(t.get('trade_id')) == str(trade_id)), None)
            
            if not trade:
                # Fallback: try HTTP call only if file read fails (with short timeout)
                import requests
                try:
                    response = requests.get(f"http://127.0.0.1:8765/performance/trades/{trade_id}", timeout=5)
                    if response.status_code == 200:
                        trade_data = response.json()
                        trade = trade_data.get('trade', trade_data) if isinstance(trade_data, dict) else trade_data
                except Exception as http_error:
                    print(f"[VIEW_TRADE] HTTP fallback failed: {http_error}, using direct file read")
                    trade = None
            
            if trade:
                symbol = trade.get('symbol', 'Unknown')
                outcome = trade.get('outcome', 'pending')
                pnl = trade.get('pnl', 0)
                r_multiple = trade.get('r_multiple', 0)
                
                # OPTIMIZATION: Use attach_chart_url (fast, no HTTP calls) instead of get_chart_url
                trade_data = trade.copy()
                trade_data = attach_chart_url(trade_data)
                chart_url = trade_data.get("chart_url")
                
                # [5F.2 FIX F3] Update context_manager with current trade index
                from memory.context_manager import set_current_trade_index, get_current_trade_index
                all_trades_for_index = context.get('all_trades') or read_logs()
                if all_trades_for_index:
                    # CRITICAL: Use same sorting as navigation commands (oldest first, reverse=False)
                    sorted_trades = sorted(all_trades_for_index, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
                    for idx, t in enumerate(sorted_trades):
                        if (t.get('id') == trade_id or t.get('trade_id') == trade_id or
                            str(t.get('id')) == str(trade_id) or str(t.get('trade_id')) == str(trade_id)):
                            set_current_trade_index(idx)
                            print(f"[VIEW_TRADE] CRITICAL: Updated current_trade_index to {idx} (trade #{idx + 1} of {len(sorted_trades)})")
                            print(f"[VIEW_TRADE] Trade at index {idx}: ID={trade_id}, Symbol={t.get('symbol')}, Date={t.get('timestamp') or t.get('entry_time')}")
                            # CRITICAL: Also verify the index was set correctly
                            verify_idx = get_current_trade_index()
                            if verify_idx != idx:
                                print(f"[VIEW_TRADE] WARNING: Index mismatch! Set to {idx}, but get_current_trade_index() returns {verify_idx}")
                            break
                    else:
                        # Trade not found in sorted list - log warning
                        print(f"[VIEW_TRADE] WARNING: Trade {trade_id} not found in sorted list to set index")
                
                message = f"📊 **Trade {trade_id} Details**\n\n"
                message += f"• Symbol: {symbol}\n"
                message += f"• Outcome: {outcome}\n"
                message += f"• P&L: ${pnl:.2f}\n"
                message += f"• R-Multiple: {r_multiple:.2f}R"
                
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                print(f"[PERF] execute_view_trade_command handler took {elapsed_ms} ms")
                
                # Determine intent based on trade_reference
                trade_reference = arguments.get('trade_reference', '').lower()
                detected_intent = "view_latest_trade" if trade_reference in ['last', 'latest'] else "view_trade"
                
                return {
                    "success": True,
                    "command": "view_trade",
                    "message": message,
                    "intent": detected_intent,
                    "phase": "5f",
                    "duration_ms": elapsed_ms,
                    "data": {
                        "trade": trade_data,
                        "chart_url": chart_url
                    },
                    "fields": {
                        "chart_url": chart_url
                    }
                }
            else:
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                print(f"[PERF] execute_view_trade_command handler failed after {elapsed_ms} ms: trade not found")
                return {
                    "success": False,
                    "command": "view_trade",
                    "message": f"❓ Trade {trade_id} not found. Please check the trade ID and try again.",
                    "intent": "view_trade",
                    "phase": "5f"
                }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            print(f"[PERF] execute_view_trade_command handler failed after {elapsed_ms} ms: {e}")
            return {
                "success": False,
                "command": "view_trade",
                "message": f"⚠️ Error loading trade: {str(e)}",
                "intent": "view_trade",
                "phase": "5f"
            }
    else:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        print(f"[PERF] execute_view_trade_command handler failed after {elapsed_ms} ms: no trade_id specified")
        return {
            "success": False,
            "command": "view_trade",
            "message": "❓ Please specify which trade to view. Try 'view trade [ID]' or say 'view this trade' after mentioning a specific trade.",
            "intent": "view_trade",
            "phase": "5f"
        }

def execute_close_chart_command() -> Dict[str, Any]:
    """Execute 'close chart' command"""
    return {
        "success": True,
        "command": "close_chart",
        "message": "📊 Closing chart popup...",
        "frontend_action": "close_chart"
    }

