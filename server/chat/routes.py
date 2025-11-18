"""
Phase 4E: Enhanced Chat Routes with State Tracking and Entry Suggestions
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json

from db.session import get_db
from db.models import ChatSession
from chat.state_manager import (
    get_or_create_session,
    get_session_state,
    update_session_state,
    reset_session_state,
    get_state_summary,
)
from analytics.advisor import evaluate_setup  # Phase 3 advisor hook
from openai_client import get_client, resolve_model

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStateResponse(BaseModel):
    session_id: str
    state: dict
    state_summary: str


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


def _format_advisor_template(result: dict) -> str:
    """Deterministic fallback message for the advisor result."""
    grade = result.get("grade") or "N/A"
    score = result.get("score")
    rule = result.get("rule") or "N/A"
    decision = result.get("decision") or "wait"
    risk = result.get("risk") or {}
    risk_usd = risk.get("risk_usd")
    r_mult = risk.get("r_multiple")
    reasons = result.get("reason") or []
    parts = [
        f"Decision: {decision}",
        f"Grade: {grade}{f' ({score})' if score is not None else ''}",
        f"Rule: {rule}",
    ]
    if risk_usd is not None:
        parts.append(f"Risk: ${risk_usd:,.2f}")
    if r_mult is not None:
        parts.append(f"R multiple: {r_mult:.2f}")
    if reasons:
        parts.append("Reasons: " + "; ".join(reasons))
    return " | ".join(parts)


def _verbalize_advisor_result(advisor_result: dict, user_payload: dict) -> str:
    """
    Turn the structured advisor result into a short, conversational reply using the LLM.
    Falls back to template on errors.
    """
    client = get_client()
    model = resolve_model(None)
    system_prompt = (
        "You are the Visual Trade Copilot. Given an advisor evaluation, produce a concise, "
        "professional recommendation with a clear structure:\n"
        "1) Lead with the decision (enter/skip/wait), grade, rule, and risk (USD and R).\n"
        "2) Provide 2-4 bullets on confluence/reasons driving the decision.\n"
        "3) If grade < A+, add a short bullet on what would elevate it to A+.\n"
        "4) Keep it crisp (<= 5 lines), no JSON, no markdown headers."
    )
    user_content = (
        "Trader input:\n"
        f"{json.dumps(user_payload, default=str)}\n\n"
        "Advisor output:\n"
        f"{json.dumps(advisor_result, default=str)}"
    )
    completion = client.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=320,
        temperature=0.2,
    )
    return (completion.choices[0].message.content or "").strip()

@router.post("/advisor/evaluate")
def chat_advisor_evaluate(
    payload: dict,
    remaining_drawdown: float = 500.0,
    risk_cap_pct: float = 0.10,
    require_grade: str = "A+",
    require_micro: bool = False,
):
    """
    Lightweight chat hook to run the Phase 3 advisor without needing DB state.
    Accepts the same fields as /analytics/advisor/evaluate (see ANNOTATION_CSV_GUIDE).
    """
    result = evaluate_setup(
        payload,
        remaining_drawdown=remaining_drawdown,
        risk_cap_pct=risk_cap_pct,
        require_grade=require_grade,
        require_micro=require_micro,
    )
    # Try to produce a conversational message; fall back to the deterministic template.
    try:
        message = _verbalize_advisor_result(result, payload)
        result["message"] = message
    except Exception as e:
        fallback = _format_advisor_template(result)
        result["message"] = fallback
        result["verbalize_error"] = str(e)
    # Always include a deterministic formatted string clients can show or log.
    result["formatted"] = _format_advisor_template(result)
    return result

