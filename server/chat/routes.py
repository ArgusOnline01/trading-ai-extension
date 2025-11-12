"""
Phase 4E: Enhanced Chat Routes with State Tracking and Entry Suggestions
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
import base64
import io

from db.session import get_db
from db.models import ChatSession, EntrySuggestion
from chat.state_manager import (
    get_or_create_session,
    get_session_state,
    update_session_state,
    reset_session_state,
    get_state_summary
)
from chat.entry_suggester import analyze_chart_for_entry
from chat.outcome_tracker import save_outcome, get_outcome_stats
from ai.rag.entry_learning import index_entry_suggestion_with_outcome
from chat.visual_markers import get_overlay_coordinates

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStateResponse(BaseModel):
    session_id: str
    state: dict
    state_summary: str


class EntrySuggestionResponse(BaseModel):
    suggestion_id: int
    entry_price: Optional[float]
    stop_loss: Optional[float]
    stop_loss_type: Optional[str]
    stop_loss_reasoning: Optional[str]
    reasoning: Optional[str]
    confluences_met: Optional[list]
    ready_to_enter: bool
    overlay_coordinates: Optional[dict] = None  # For visual markers


class OutcomeCreate(BaseModel):
    suggestion_id: int
    outcome: str  # 'win' | 'loss' | 'skipped'
    actual_entry_price: Optional[float] = None
    actual_exit_price: Optional[float] = None
    r_multiple: Optional[float] = None
    notes: Optional[str] = None
    chart_sequence: Optional[list] = None


class OutcomeResponse(BaseModel):
    id: int
    suggestion_id: int
    outcome: str
    actual_entry_price: Optional[float]
    actual_exit_price: Optional[float]
    r_multiple: Optional[float]
    notes: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.get("/session/{session_id}/state", response_model=ChatStateResponse)
def get_chat_state(session_id: str, db: Session = Depends(get_db)):
    """Get current chat session state"""
    state = get_session_state(db, session_id)
    if state is None:
        state = {}
    
    return ChatStateResponse(
        session_id=session_id,
        state=state,
        state_summary=get_state_summary(state)
    )


@router.post("/session/{session_id}/state")
def update_chat_state(
    session_id: str,
    state_updates: dict,
    trade_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Update chat session state"""
    updated_state = update_session_state(db, session_id, state_updates, trade_id)
    return {
        "session_id": session_id,
        "state": updated_state,
        "state_summary": get_state_summary(updated_state)
    }


@router.delete("/session/{session_id}/state")
def reset_chat_state(session_id: str, db: Session = Depends(get_db)):
    """Reset chat session state"""
    reset_session_state(db, session_id)
    return {"message": f"Session {session_id} state reset"}


@router.post("/session/{session_id}/analyze", response_model=EntrySuggestionResponse)
async def analyze_chart_with_state(
    session_id: str,
    image: UploadFile = File(...),
    strategy_id: Optional[int] = Form(None),
    model: str = Form("gpt-4o"),
    db: Session = Depends(get_db)
):
    """
    Analyze chart image with current session state and suggest entry
    
    This endpoint:
    1. Gets current session state
    2. Analyzes the chart image
    3. Updates state based on analysis
    4. Suggests entry if ready
    """
    # Get current state
    state = get_session_state(db, session_id)
    if state is None:
        state = {}
    
    # Read and encode image
    image_data = await image.read()
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Get image dimensions for overlay coordinates
    from PIL import Image as PILImage
    img = PILImage.open(io.BytesIO(image_data))
    image_width, image_height = img.size
    
    # Analyze chart for entry
    analysis = await analyze_chart_for_entry(
        image_base64=image_base64,
        session_state=state,
        strategy_id=strategy_id,
        model=model
    )
    
    # Generate overlay coordinates if entry is ready
    overlay_coords = None
    if analysis.get("ready_to_enter") and analysis.get("entry_price"):
        # Use price range extracted by AI from chart analysis
        chart_min_price = analysis.get("chart_min_price")
        chart_max_price = analysis.get("chart_max_price")
        
        overlay_coords = get_overlay_coordinates(
            entry_price=analysis.get("entry_price"),
            stop_loss_price=analysis.get("stop_loss"),
            chart_min_price=chart_min_price,
            chart_max_price=chart_max_price,
            image_width=image_width,
            image_height=image_height
        )
    
    # Update session state
    state_updates = {
        "setup_detected": analysis.get("ready_to_enter", False) or state.get("setup_detected", False),
        "confluences_met": analysis.get("confluences_met", []),
        "waiting_for": analysis.get("waiting_for", []),
        "last_analysis": analysis
    }
    updated_state = update_session_state(db, session_id, state_updates)
    
    # Save entry suggestion if ready
    suggestion_id = None
    if analysis.get("ready_to_enter") and analysis.get("entry_price"):
        session = get_or_create_session(db, session_id)
        suggestion = EntrySuggestion(
            session_id=session_id,
            entry_price=analysis.get("entry_price"),
            stop_loss=analysis.get("stop_loss"),
            stop_loss_type=analysis.get("stop_loss_type"),
            stop_loss_reasoning=analysis.get("stop_loss_reasoning"),
            reasoning=analysis.get("reasoning"),
            confluences_met=analysis.get("confluences_met", [])
        )
        db.add(suggestion)
        db.commit()
        db.refresh(suggestion)
        suggestion_id = suggestion.id
    
    return EntrySuggestionResponse(
        suggestion_id=suggestion_id or 0,
        entry_price=analysis.get("entry_price"),
        stop_loss=analysis.get("stop_loss"),
        stop_loss_type=analysis.get("stop_loss_type"),
        stop_loss_reasoning=analysis.get("stop_loss_reasoning"),
        reasoning=analysis.get("reasoning"),
        confluences_met=analysis.get("confluences_met", []),
        ready_to_enter=analysis.get("ready_to_enter", False),
        overlay_coordinates=overlay_coords
    )


@router.post("/outcome", response_model=OutcomeResponse)
def create_outcome(outcome: OutcomeCreate, db: Session = Depends(get_db)):
    """Save outcome for an entry suggestion"""
    try:
        entry_outcome = save_outcome(
            db=db,
            suggestion_id=outcome.suggestion_id,
            outcome=outcome.outcome,
            actual_entry_price=outcome.actual_entry_price,
            actual_exit_price=outcome.actual_exit_price,
            r_multiple=outcome.r_multiple,
            notes=outcome.notes,
            chart_sequence=outcome.chart_sequence
        )
        
        # Index for RAG learning
        try:
            index_entry_suggestion_with_outcome(db, outcome.suggestion_id)
        except Exception as e:
            print(f"[CHAT] Warning: Failed to index outcome for learning: {e}")
        
        return OutcomeResponse(
            id=entry_outcome.id,
            suggestion_id=entry_outcome.suggestion_id,
            outcome=entry_outcome.outcome,
            actual_entry_price=entry_outcome.actual_entry_price,
            actual_exit_price=entry_outcome.actual_exit_price,
            r_multiple=entry_outcome.r_multiple,
            notes=entry_outcome.notes,
            created_at=entry_outcome.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save outcome: {str(e)}")


@router.get("/outcome/stats")
def get_outcome_statistics(session_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Get statistics about entry suggestion outcomes"""
    stats = get_outcome_stats(db, session_id)
    return stats

