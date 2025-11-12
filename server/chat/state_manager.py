"""
Phase 4E: Session State Management
Tracks chat session state across multiple image uploads
"""
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import ChatSession
import json


def get_or_create_session(db: Session, session_id: str, trade_id: Optional[str] = None) -> ChatSession:
    """Get existing session or create new one"""
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        session = ChatSession(
            session_id=session_id,
            trade_id=trade_id,
            state_json={}
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


def get_session_state(db: Session, session_id: str) -> Optional[Dict[str, Any]]:
    """Get current session state"""
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        return None
    return session.state_json or {}


def update_session_state(
    db: Session,
    session_id: str,
    state_updates: Dict[str, Any],
    trade_id: Optional[str] = None
) -> Dict[str, Any]:
    """Update session state with new information"""
    session = get_or_create_session(db, session_id, trade_id)
    
    current_state = session.state_json or {}
    
    # Merge updates
    current_state.update(state_updates)
    current_state['last_updated'] = datetime.utcnow().isoformat()
    
    session.state_json = current_state
    session.updated_at = datetime.utcnow()
    if trade_id:
        session.trade_id = trade_id
    
    db.commit()
    db.refresh(session)
    
    return current_state


def reset_session_state(db: Session, session_id: str) -> Dict[str, Any]:
    """Reset session state to empty"""
    session = get_or_create_session(db, session_id)
    session.state_json = {}
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return {}


def get_state_summary(state: Dict[str, Any]) -> str:
    """Get human-readable summary of current state"""
    if not state:
        return "No active setup detected"
    
    setup_detected = state.get('setup_detected', False)
    if not setup_detected:
        return "No active setup detected"
    
    waiting_for = state.get('waiting_for', [])
    confluences_met = state.get('confluences_met', [])
    
    summary_parts = []
    if waiting_for:
        summary_parts.append(f"Waiting for: {', '.join(waiting_for)}")
    if confluences_met:
        summary_parts.append(f"Met: {', '.join(confluences_met)}")
    
    if summary_parts:
        return " | ".join(summary_parts)
    
    return "Setup detected, analyzing..."

