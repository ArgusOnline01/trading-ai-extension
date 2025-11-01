"""
Memory Management Routes
Handles persistent memory operations and system commands
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from .utils import (
    get_memory_status,
    save_session_context,
    load_session_context,
    append_conversation_message,
    clear_all_memory
)
from .system_commands import detect_command, execute_command


memory_router = APIRouter(prefix="/memory", tags=["Memory"])


class MessageSave(BaseModel):
    """Model for saving messages"""
    role: str
    content: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionSave(BaseModel):
    """Model for saving session context"""
    session_id: str
    context: Dict[str, Any]


class CommandRequest(BaseModel):
    """Model for system command requests"""
    command: str
    context: Optional[Dict[str, Any]] = None


@memory_router.get("/status")
async def get_status():
    """
    Get comprehensive memory status
    Returns trade count, session count, conversation count, etc.
    """
    try:
        status = get_memory_status()
        return {
            "status": "healthy",
            **status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@memory_router.post("/save")
async def save_message(message: MessageSave):
    """
    Save a conversation message to persistent storage
    Called automatically from frontend after each message
    """
    try:
        append_conversation_message(
            role=message.role,
            content=message.content,
            metadata=message.metadata
        )
        
        return {
            "status": "saved",
            "message": "Message saved to persistent storage"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@memory_router.get("/load/{session_id}")
async def load_session(session_id: str):
    """
    Load a specific session context by ID
    Returns None if session not found
    """
    try:
        session = load_session_context(session_id)
        
        if session is None:
            return {
                "status": "not_found",
                "session_id": session_id,
                "data": None
            }
        
        return {
            "status": "found",
            "session_id": session_id,
            "data": session
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@memory_router.post("/session")
async def save_session(data: SessionSave):
    """
    Save or update a session context
    """
    try:
        save_session_context(data.session_id, data.context)
        
        return {
            "status": "saved",
            "session_id": data.session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@memory_router.post("/clear")
async def clear_memory():
    """
    Clear all persistent memory (reset to defaults)
    Use with caution - this wipes conversations and sessions!
    """
    try:
        result = clear_all_memory()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@memory_router.post("/system/command")
async def system_command(request: CommandRequest):
    """
    Execute a system command
    Detects command intent and executes appropriate action
    """
    try:
        # Detect command from natural language
        detected = detect_command(request.command)
        
        if detected is None:
            return {
                "success": False,
                "message": "❓ Command not recognized. Try 'help' to see available commands.",
                "detected_command": None
            }
        
        # Phase 5B.2: If opening teach copilot, try to detect trade from conversation context
        if detected == "open_teach_copilot" and request.context:
            from utils.trade_detector import detect_trade_reference, extract_trade_id_from_text
            from performance.utils import read_logs
            
            # Try to extract trade from command text or context
            all_trades = read_logs()
            conversation_history = request.context.get('all_sessions') or []
            
            # Check conversation history for recently mentioned trades
            detected_trade = detect_trade_reference(request.command, all_trades, conversation_history)
            if detected_trade:
                request.context['detected_trade'] = detected_trade
                print(f"[SYSTEM_COMMAND] Detected trade {detected_trade.get('id')} for teach copilot")
        
        # Phase 5C: If showing chart, try to detect trade from conversation context
        if detected == "show_chart" and request.context:
            from utils.trade_detector import detect_trade_reference
            from performance.utils import read_logs
            
            all_trades = read_logs()
            conversation_history = request.context.get('all_sessions') or []
            request.context['command_text'] = request.command
            detected_trade = detect_trade_reference(request.command, all_trades, conversation_history)
            if detected_trade:
                request.context['detected_trade'] = detected_trade
                print(f"[SYSTEM_COMMAND] Detected trade {detected_trade.get('id')} for show chart")
        
        # Execute command
        result = execute_command(detected, request.context)
        
        return {
            **result,
            "detected_command": detected,
            "original_input": request.command
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"⚠️ Error executing command: {str(e)}",
            "detected_command": None
        }

