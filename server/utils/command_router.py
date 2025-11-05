"""
Phase 5D – Command Grounding Layer

Routes, validates, and executes commands with schema checking + context repair.

This middleware sits between AI extraction and command execution, ensuring:
- Schema validity (required fields present)
- Context repair (fills missing session/trade info)
- Deduplication (removes duplicate commands)
- Clear execution feedback (human-readable summaries)
"""

import json
from typing import Any, Dict, List, Optional
from utils.command_extractor import normalize_command
from memory import system_commands  # existing handlers

# Use centralized command_schema module for validation


# Command schema definition
COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string"},
        "type": {"type": "string"},
        "action": {"type": "string"},
        "name": {"type": ["string", "null"]},
        "session_name": {"type": ["string", "null"]},
        "session_id": {"type": ["string", "null"]},
        "trade_id": {"type": ["string", "null", "integer"]},
        "symbol": {"type": ["string", "null"]},
        "new_name": {"type": ["string", "null"]},
        "trade_reference": {"type": ["string", "null"]},
        "action_hint": {"type": ["string", "null"]},
        "lesson_id": {"type": ["string", "null", "integer"]}
    },
    "required": ["command", "type", "action"]
}


def validate_command_schema(cmd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate command against schema using centralized command_schema module.
    
    Args:
        cmd: Command dictionary to validate
        
    Returns:
        Dict with 'success' bool and optional 'message' error string
    """
    try:
        from utils.command_schema import validate_command_schema as validate_schema_func
        
        is_valid = validate_schema_func(cmd)
        if is_valid:
            return {"success": True}
        else:
            return {"success": False, "message": "Invalid command format: missing required fields or invalid types"}
    except ImportError:
        # Fallback: basic validation if command_schema module not available
        if not isinstance(cmd, dict):
            return {"success": False, "message": "Command must be a dictionary"}
        
        required_fields = ["command", "type", "action"]
        missing_fields = [field for field in required_fields if field not in cmd or cmd[field] is None]
        
        if missing_fields:
            return {"success": False, "message": f"Missing required fields: {', '.join(missing_fields)}"}
        
        return {"success": True}


def fill_missing_fields(cmd: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Repair missing session/trade info using context.
    
    Args:
        cmd: Command dictionary (will be modified)
        context: Execution context with session/trade data
        
    Returns:
        Command dictionary with filled fields
    """
    # Fill session_id if missing and type is session
    if cmd.get("type") == "session" and not cmd.get("session_id"):
        current_session_id = context.get("current_session_id")
        if current_session_id:
            cmd["session_id"] = current_session_id
    
    # Fill trade_id if missing and type is trade/chart
    if cmd.get("type") in ["trade", "chart"] and not cmd.get("trade_id"):
        detected_trade = context.get("detected_trade")
        if detected_trade:
            cmd["trade_id"] = detected_trade.get("id") or detected_trade.get("trade_id")
    
    # Fill symbol from session context if available
    if cmd.get("symbol") is None:
        session_context = context.get("session_context", {})
        if session_context and session_context.get("symbol"):
            cmd["symbol"] = session_context.get("symbol")
        # Also check all_sessions for current session symbol
        elif context.get("current_session_id"):
            all_sessions = context.get("all_sessions", [])
            current_session_id = context.get("current_session_id")
            for session in all_sessions:
                if session.get("sessionId") == current_session_id:
                    cmd["symbol"] = session.get("symbol")
                    break
    
    return cmd


def merge_multi_commands(commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate commands from multi-intent messages.
    
    Args:
        commands: List of command dictionaries
        
    Returns:
        Deduplicated list of commands
    """
    seen = set()
    unique = []
    
    for cmd in commands:
        # Create a unique key based on command identity
        # For session commands, include session_id if available
        # For trade commands, include trade_id if available
        cmd_key_parts = [
            cmd.get("command"),
            cmd.get("type"),
            cmd.get("action")
        ]
        
        # Add identifying fields
        if cmd.get("session_id"):
            cmd_key_parts.append(f"session_id:{cmd['session_id']}")
        elif cmd.get("session_name"):
            cmd_key_parts.append(f"session_name:{cmd['session_name']}")
        
        if cmd.get("trade_id"):
            cmd_key_parts.append(f"trade_id:{cmd['trade_id']}")
        
        if cmd.get("symbol"):
            cmd_key_parts.append(f"symbol:{cmd['symbol']}")
        
        cmd_key = tuple(cmd_key_parts)
        
        if cmd_key not in seen:
            unique.append(cmd)
            seen.add(cmd_key)
    
    return unique


def route_command(raw_cmd: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate, normalize, repair, and execute command.
    
    This is the main entry point for command routing.
    
    Args:
        raw_cmd: Raw command dictionary from extraction
        context: Execution context
        
    Returns:
        Command result dictionary with:
        - success: bool
        - command: str
        - message: str
        - frontend_action: str (optional)
        - data: dict (optional)
    """
    # Step 1: Validate schema
    validation = validate_command_schema(raw_cmd)
    if not validation["success"]:
        return {
            "success": False,
            "command": raw_cmd.get("command", "unknown"),
            "message": validation["message"],
            "frontend_action": None
        }
    
    # Step 2: Normalize command format
    cmd = normalize_command(raw_cmd)
    
    # Step 3: Fill missing fields from context
    cmd = fill_missing_fields(cmd, context)
    
    # Step 4: Find handler function
    cmd_name = cmd.get("command")
    if not cmd_name:
        return {
            "success": False,
            "command": "unknown",
            "message": "Command name missing after normalization",
            "frontend_action": None
        }
    
    # Map command name to handler function
    # Handler functions follow pattern: execute_{command_name}_command
    handler_name = f"execute_{cmd_name}_command"
    handler = getattr(system_commands, handler_name, None)
    
    if not handler:
        # Phase 5F Fix: Friendly error message for unmapped commands
        friendly_commands = {
            "greeting": "Hello! I'm here to help with your trading analysis. Try 'list my trades' or 'show my stats'.",
            "info": "I can help you with trade analysis, chart viewing, and performance tracking. Try 'show my stats' or 'list my trades'.",
            "question": "I understand you're asking a question. For trading commands, try 'list my trades', 'show chart', or 'show my stats'.",
            "unknown": "I didn't recognize that as a trading command. Try 'list my trades', 'show chart', or 'show my stats'."
        }
        
        # Determine if this is a greeting/info request vs unknown command
        cmd_lower = cmd_name.lower()
        if any(word in cmd_lower for word in ["hello", "hi", "hey", "greeting"]):
            friendly_msg = friendly_commands["greeting"]
        elif any(word in cmd_lower for word in ["what", "how", "info", "information"]):
            friendly_msg = friendly_commands["info"]
        elif "?" in str(raw_cmd):
            friendly_msg = friendly_commands["question"]
        else:
            friendly_msg = friendly_commands["unknown"]
        
        return {
            "success": True,  # Success = True to indicate friendly response, not error
            "command": cmd_name or "unknown",
            "message": friendly_msg,
            "frontend_action": None,
            "intent": "fallback_unmapped_handler",  # Phase 5F Polishing: Distinct intent for fallbacks
            "phase": "5f",
            "is_fallback": True  # Mark as fallback response
        }
    
    # Step 5: Execute command with enhanced context
    try:
        import inspect
        # Merge normalized command into context
        enhanced_context = {
            **context,
            "detected_command": cmd
        }
        
        # Check if handler accepts context parameter
        sig = inspect.signature(handler)
        params = list(sig.parameters.keys())
        
        # Call handler with or without context based on signature
        if len(params) > 0:
            result = handler(enhanced_context)
        else:
            result = handler()
        
        # Ensure result has required fields
        result.setdefault("command", cmd_name)
        result.setdefault("success", True)
        result.setdefault("message", "Command executed")
        
        return result
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[COMMAND_ROUTER] Error executing {cmd_name}: {e}")
        print(f"[COMMAND_ROUTER] Traceback: {error_trace}")
        
        return {
            "success": False,
            "command": cmd_name,
            "message": f"Execution error: {str(e)}",
            "frontend_action": None,
            "error": str(e)
        }


def generate_execution_summary(execution_log: List[Dict[str, Any]]) -> str:
    """
    Generate human-readable summary of command execution.
    
    Args:
        execution_log: List of command execution results
        
    Returns:
        Formatted summary string
    """
    if not execution_log:
        return "No commands executed."
    
    summary_lines = []
    for result in execution_log:
        success_icon = "✅" if result.get("success") else "❌"
        cmd_name = result.get("command", "unknown")
        message = result.get("message", "No message")
        
        # Truncate long messages
        if len(message) > 100:
            message = message[:97] + "..."
        
        summary_lines.append(f"{success_icon} **{cmd_name}**: {message}")
    
    return "\n".join(summary_lines)

