"""
Phase 4E: Entry Learning System
Indexes entry suggestions and outcomes for RAG retrieval
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from db.models import EntrySuggestion, EntryOutcome, ChatSession
from ai.rag.chroma_client import get_chroma_client
from ai.rag.embeddings import get_embedding_service
import json


def index_entry_suggestion_with_outcome(
    db: Session,
    suggestion_id: int,
    collection_name: str = "entry_suggestions"
):
    """
    Index an entry suggestion and its outcome (if available) in Chroma
    
    Creates an embedding from:
    - Chart analysis context
    - Entry suggestion details
    - Outcome (if available)
    - Confluences met
    """
    suggestion = db.query(EntrySuggestion).filter(EntrySuggestion.id == suggestion_id).first()
    if not suggestion:
        return
    
    # Get outcome if available
    outcome = db.query(EntryOutcome).filter(EntryOutcome.suggestion_id == suggestion_id).first()
    
    # Get session state for context
    session = db.query(ChatSession).filter(ChatSession.session_id == suggestion.session_id).first()
    session_state = session.state_json if session else {}
    
    # Build text for embedding
    text_parts = []
    
    # Entry suggestion details
    text_parts.append(f"Entry Suggestion:")
    if suggestion.entry_price:
        text_parts.append(f"Entry Price: {suggestion.entry_price}")
    if suggestion.stop_loss:
        text_parts.append(f"Stop Loss: {suggestion.stop_loss} ({suggestion.stop_loss_type})")
    if suggestion.stop_loss_reasoning:
        text_parts.append(f"Stop Loss Reasoning: {suggestion.stop_loss_reasoning}")
    if suggestion.reasoning:
        text_parts.append(f"Reasoning: {suggestion.reasoning}")
    if suggestion.confluences_met:
        text_parts.append(f"Confluences Met: {', '.join(suggestion.confluences_met)}")
    
    # Session state context
    if session_state:
        waiting_for = session_state.get('waiting_for', [])
        if waiting_for:
            text_parts.append(f"Waiting For: {', '.join(waiting_for)}")
    
    # Outcome (if available)
    if outcome:
        text_parts.append(f"\nOutcome: {outcome.outcome.upper()}")
        if outcome.actual_entry_price:
            text_parts.append(f"Actual Entry: {outcome.actual_entry_price}")
        if outcome.actual_exit_price:
            text_parts.append(f"Actual Exit: {outcome.actual_exit_price}")
        if outcome.r_multiple:
            text_parts.append(f"R Multiple: {outcome.r_multiple}")
        if outcome.notes:
            text_parts.append(f"Notes: {outcome.notes}")
    
    text = "\n".join(text_parts)
    
    # Get embedding
    embedding_service = get_embedding_service()
    embedding = embedding_service.generate_embedding(text)
    
    # Store in Chroma
    chroma_client = get_chroma_client()
    # Use the client's method to get or create collection
    try:
        collection = chroma_client.client.get_collection(name=collection_name)
    except Exception:
        collection = chroma_client.client.create_collection(
            name=collection_name,
            metadata={"description": "Entry suggestions and outcomes for AI learning"}
        )
    
    metadata = {
        "suggestion_id": suggestion_id,
        "session_id": suggestion.session_id,
        "entry_price": suggestion.entry_price or 0,
        "stop_loss": suggestion.stop_loss or 0,
        "outcome": outcome.outcome if outcome else "pending",
        "confluences_met": json.dumps(suggestion.confluences_met or []),
        "created_at": suggestion.created_at.isoformat()
    }
    
    if outcome:
        metadata.update({
            "r_multiple": outcome.r_multiple or 0,
            "outcome_id": outcome.id
        })
    
    collection.add(
        ids=[f"suggestion_{suggestion_id}"],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata]
    )


def retrieve_similar_entries(
    query_text: str,
    collection_name: str = "entry_suggestions",
    n_results: int = 5,
    filter_outcomes: Optional[List[str]] = None  # e.g., ["win"] to only get winning entries
) -> List[Dict[str, Any]]:
    """
    Retrieve similar entry suggestions based on query text
    
    Returns list of similar entries with their outcomes
    """
    embedding_service = get_embedding_service()
    query_embedding = embedding_service.generate_embedding(query_text)
    
    chroma_client = get_chroma_client()
    # Use the client's method to get or create collection
    try:
        collection = chroma_client.client.get_collection(name=collection_name)
    except Exception:
        collection = chroma_client.client.create_collection(
            name=collection_name,
            metadata={"description": "Entry suggestions and outcomes for AI learning"}
        )
    
    # Build where clause if filtering outcomes
    where = None
    if filter_outcomes:
        where = {"outcome": {"$in": filter_outcomes}}
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where
    )
    
    similar_entries = []
    if results['ids'] and len(results['ids'][0]) > 0:
        for i, doc_id in enumerate(results['ids'][0]):
            similar_entries.append({
                "id": doc_id,
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if 'distances' in results else None
            })
    
    return similar_entries

