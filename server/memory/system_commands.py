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
    "show_chart": ["show chart", "show image", "show the chart", "display chart", "pull up chart", "show me the chart", "open chart", "view chart", "can you show the chart", "show that chart", "show this chart", "chart please"],
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
    elif command == "delete_trade":
        return execute_delete_trade_command(context)
    elif command == "view_trade":
        return execute_view_trade_command(context)
    
    # Chart Commands
    elif command == "close_chart":
        return execute_close_chart_command()
    
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


def execute_show_chart_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute 'show chart' command - opens chart popup for detected trade
    """
    context = context or {}
    
    # Try to detect trade from context
    detected_trade = context.get('detected_trade')
    if not detected_trade and context:
        # Try to detect from conversation history
        from utils.trade_detector import detect_trade_reference, extract_trade_id_from_text
        from performance.utils import read_logs
        
        all_trades = read_logs()
        command_text = context.get('command_text', '')
        conversation_history = context.get('all_sessions') or []
        
        # Build combined text from command + recent conversation
        combined_text = command_text
        if conversation_history:
            # Add last few messages to help with detection
            for msg in reversed(conversation_history[-5:]):
                if msg.get('role') == 'assistant':
                    combined_text += " " + str(msg.get('content', ''))
                elif msg.get('role') == 'user':
                    combined_text += " " + str(msg.get('content', ''))
        
        print(f"[SHOW_CHART] Detecting trade from: '{combined_text[:200]}...'")
        print(f"[SHOW_CHART] History length: {len(conversation_history)}")
        
        detected_trade = detect_trade_reference(combined_text, all_trades, conversation_history)
        
        if detected_trade:
            print(f"[SHOW_CHART] Detected trade: {detected_trade.get('id')} - {detected_trade.get('symbol')}")
        else:
            print(f"[SHOW_CHART] No trade detected")
    
    if not detected_trade:
        return {
            "success": False,
            "command": "show_chart",
            "message": "❓ Could not find which trade's chart to show. Please mention a trade ID, symbol, or say 'that trade' after discussing it.",
            "frontend_action": None
        }
    
    trade_id = detected_trade.get('id') or detected_trade.get('trade_id')
    symbol = detected_trade.get('symbol', 'Unknown')
    
    # Find chart path
    chart_path = detected_trade.get('chart_path')
    print(f"[SHOW_CHART] Trade chart_path from object: {chart_path}")
    
    if not chart_path:
        # Try to find via metadata API
        try:
            import requests
            meta_response = requests.get(f"http://127.0.0.1:8765/charts/chart/{trade_id}", timeout=2)
            if meta_response.ok:
                meta = meta_response.json()
                chart_path = meta.get('chart_path')
                print(f"[SHOW_CHART] Found via metadata API: {chart_path}")
        except Exception as e:
            print(f"[SHOW_CHART] Metadata API lookup failed: {e}")
    
    if not chart_path:
        # Try to find via file system
        try:
            from pathlib import Path
            charts_dir = Path(__file__).parent.parent / "data" / "charts"
            print(f"[SHOW_CHART] Searching in: {charts_dir}")
            
            if trade_id and symbol:
                patterns = [
                    f"{symbol}_5m_{trade_id}.png",
                    f"{symbol}_5m_{trade_id}*.png",
                    f"{symbol}_*_{trade_id}.png"
                ]
                for pattern in patterns:
                    matches = list(charts_dir.glob(pattern))
                    if matches:
                        chart_path = str(matches[0])
                        print(f"[SHOW_CHART] Found via pattern {pattern}: {chart_path}")
                        break
        except Exception as e:
            print(f"[SHOW_CHART] File system lookup failed: {e}")
    
    if not chart_path:
        print(f"[SHOW_CHART] Chart not found. Trade: {symbol} {trade_id}")
    
    if not chart_path:
        return {
            "success": False,
            "command": "show_chart",
            "message": f"❌ Chart not found for {symbol} trade {trade_id}. The chart may not have been generated yet.",
            "frontend_action": None
        }
    
    # Extract filename for URL
    import os
    filename = os.path.basename(chart_path)
    
    # Build chart URL (charts are mounted at /charts)
    chart_url = f"/charts/{filename}"
    print(f"[SHOW_CHART] Returning chart_url: {chart_url}")
    print(f"[SHOW_CHART] Full URL will be: http://127.0.0.1:8765{chart_url}")
    
    return {
        "success": True,
        "command": "show_chart",
        "message": f"📊 Opening chart for {symbol} trade {trade_id}...",
        "frontend_action": "show_chart_popup",
        "trade_id": trade_id,
        "chart_url": chart_url,
        "symbol": symbol,
        "debug": {
            "chart_path": chart_path,
            "filename": filename
        }
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

def execute_minimize_chat_command() -> Dict[str, Any]:
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

def execute_view_lessons_command() -> Dict[str, Any]:
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
            response = requests.delete(f"http://127.0.0.1:8765/teach/lessons/{lesson_id}", timeout=5)
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
        response = requests.get("http://127.0.0.1:8765/teach/progress", timeout=5)
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
                "data": progress
            }
        else:
            return {
                "success": False,
                "command": "teaching_progress",
                "message": f"⚠️ Could not load teaching progress: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "command": "teaching_progress",
            "message": f"⚠️ Error loading teaching progress: {str(e)}"
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

def execute_next_trade_teaching_command() -> Dict[str, Any]:
    """Execute 'next trade' command in teaching mode"""
    try:
        import requests
        response = requests.post("http://127.0.0.1:8765/teach/next", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "command": "next_trade_teaching",
                "message": f"➡️ Moved to trade index {data.get('trade_index', 0)}",
                "data": data
            }
        else:
            return {
                "success": False,
                "command": "next_trade_teaching",
                "message": f"⚠️ Could not move to next trade: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "command": "next_trade_teaching",
            "message": f"⚠️ Error moving to next trade: {str(e)}"
        }

def execute_skip_trade_teaching_command() -> Dict[str, Any]:
    """Execute 'skip trade' command in teaching mode"""
    try:
        import requests
        response = requests.post("http://127.0.0.1:8765/teach/skip", timeout=5)
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
            response = requests.delete(f"http://127.0.0.1:8765/performance/trades/{trade_id}", timeout=5)
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
    """Execute 'view trade' command"""
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
            response = requests.get(f"http://127.0.0.1:8765/performance/trades/{trade_id}", timeout=5)
            if response.status_code == 200:
                trade = response.json().get('trade', {})
                symbol = trade.get('symbol', 'Unknown')
                outcome = trade.get('outcome', 'pending')
                pnl = trade.get('pnl', 0)
                r_multiple = trade.get('r_multiple', 0)
                
                message = f"📊 **Trade {trade_id} Details**\n\n"
                message += f"• Symbol: {symbol}\n"
                message += f"• Outcome: {outcome}\n"
                message += f"• P&L: ${pnl:.2f}\n"
                message += f"• R-Multiple: {r_multiple:.2f}R\n"
                
                return {
                    "success": True,
                    "command": "view_trade",
                    "message": message,
                    "data": trade
                }
            else:
                return {
                    "success": False,
                    "command": "view_trade",
                    "message": f"⚠️ Could not load trade {trade_id}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "command": "view_trade",
                "message": f"⚠️ Error loading trade: {str(e)}"
            }
    else:
        return {
            "success": False,
            "command": "view_trade",
            "message": "❓ Please specify which trade to view. Try 'view trade [ID]' or say 'view this trade' after mentioning a specific trade."
        }

def execute_close_chart_command() -> Dict[str, Any]:
    """Execute 'close chart' command"""
    return {
        "success": True,
        "command": "close_chart",
        "message": "📊 Closing chart popup...",
        "frontend_action": "close_chart"
    }

