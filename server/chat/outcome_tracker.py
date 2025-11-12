"""
Phase 4E: Outcome Tracking Logic
Tracks outcomes of entry suggestions (WIN/LOSS/SKIPPED)
"""
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import EntryOutcome, EntrySuggestion


def save_outcome(
    db: Session,
    suggestion_id: int,
    outcome: str,  # 'win' | 'loss' | 'skipped'
    actual_entry_price: Optional[float] = None,
    actual_exit_price: Optional[float] = None,
    r_multiple: Optional[float] = None,
    notes: Optional[str] = None,
    chart_sequence: Optional[list] = None
) -> EntryOutcome:
    """Save outcome for an entry suggestion"""
    # Verify suggestion exists
    suggestion = db.query(EntrySuggestion).filter(EntrySuggestion.id == suggestion_id).first()
    if not suggestion:
        raise ValueError(f"Entry suggestion {suggestion_id} not found")
    
    # Create outcome
    entry_outcome = EntryOutcome(
        suggestion_id=suggestion_id,
        outcome=outcome,
        actual_entry_price=actual_entry_price,
        actual_exit_price=actual_exit_price,
        r_multiple=r_multiple,
        notes=notes,
        chart_sequence=chart_sequence
    )
    
    db.add(entry_outcome)
    db.commit()
    db.refresh(entry_outcome)
    
    return entry_outcome


def get_outcome_stats(db: Session, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Get statistics about entry suggestion outcomes"""
    query = db.query(EntryOutcome)
    
    if session_id:
        # Filter by session
        query = query.join(EntrySuggestion).filter(EntrySuggestion.session_id == session_id)
    
    outcomes = query.all()
    
    if not outcomes:
        return {
            "total": 0,
            "wins": 0,
            "losses": 0,
            "skipped": 0,
            "win_rate": 0.0,
            "avg_r_multiple": 0.0
        }
    
    wins = [o for o in outcomes if o.outcome == "win"]
    losses = [o for o in outcomes if o.outcome == "loss"]
    skipped = [o for o in outcomes if o.outcome == "skipped"]
    
    r_values = [o.r_multiple for o in outcomes if o.r_multiple is not None]
    avg_r = sum(r_values) / len(r_values) if r_values else 0.0
    
    total_traded = len(wins) + len(losses)
    win_rate = (len(wins) / total_traded * 100) if total_traded > 0 else 0.0
    
    return {
        "total": len(outcomes),
        "wins": len(wins),
        "losses": len(losses),
        "skipped": len(skipped),
        "win_rate": round(win_rate, 2),
        "avg_r_multiple": round(avg_r, 2)
    }

