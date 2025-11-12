"""
Phase 4E: Pattern Extraction System
Lets the model define what patterns to look for from outcomes
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from db.models import EntrySuggestion, EntryOutcome
from ai.rag.entry_learning import retrieve_similar_entries
from openai_client import get_client
import json
import asyncio


async def extract_patterns_from_outcomes(
    db: Session,
    min_outcomes: int = 10
) -> Dict[str, Any]:
    """
    Extract patterns from entry outcomes using AI
    
    The model analyzes outcomes and identifies:
    - What makes entries successful
    - What makes entries fail
    - Common patterns in winning vs losing entries
    """
    # Get all outcomes with suggestions
    outcomes = db.query(EntryOutcome).join(EntrySuggestion).all()
    
    if len(outcomes) < min_outcomes:
        return {
            "patterns": [],
            "message": f"Need at least {min_outcomes} outcomes to extract patterns. Currently have {len(outcomes)}."
        }
    
    # Build dataset for analysis
    dataset = []
    for outcome in outcomes:
        suggestion = outcome.suggestion
        dataset.append({
            "entry_price": suggestion.entry_price,
            "stop_loss": suggestion.stop_loss,
            "stop_loss_type": suggestion.stop_loss_type,
            "confluences_met": suggestion.confluences_met or [],
            "reasoning": suggestion.reasoning,
            "outcome": outcome.outcome,
            "r_multiple": outcome.r_multiple
        })
    
    # Prepare prompt for pattern extraction
    dataset_summary = json.dumps(dataset[:50], indent=2)  # Limit to 50 for token efficiency
    
    prompt = f"""Analyze these entry suggestion outcomes and extract patterns.

Dataset ({len(dataset)} entries):
{dataset_summary}

Identify patterns such as:
1. What confluences are most common in winning entries?
2. What entry methods (based on reasoning) work best?
3. What stop loss strategies are most effective?
4. What patterns lead to losses?
5. What patterns lead to wins?

Return your analysis as JSON:
{{
    "winning_patterns": [
        {{
            "pattern": "description",
            "frequency": X,
            "avg_r_multiple": Y,
            "examples": ["example1", "example2"]
        }}
    ],
    "losing_patterns": [
        {{
            "pattern": "description",
            "frequency": X,
            "avg_r_multiple": Y,
            "examples": ["example1", "example2"]
        }}
    ],
    "insights": [
        "insight 1",
        "insight 2"
    ]
}}"""
    
    client = get_client()
    
    try:
        response = await asyncio.to_thread(
            lambda: client.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a trading pattern analyst. Extract meaningful patterns from trading entry outcomes."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
        )
        
        result_text = response.choices[0].message.content
        patterns = json.loads(result_text)
        
        return {
            "patterns": patterns,
            "total_outcomes_analyzed": len(dataset),
            "extracted_at": "now"
        }
    except Exception as e:
        return {
            "patterns": [],
            "error": str(e),
            "message": "Failed to extract patterns"
        }


async def get_patterns_for_similar_setup(
    query_text: str,
    db: Optional[Session] = None,
    n_results: int = 5
) -> Dict[str, Any]:
    """
    Get patterns from similar past setups
    
    Uses RAG to find similar entries, then extracts patterns from those
    """
    # Retrieve similar entries
    similar_entries = retrieve_similar_entries(
        query_text=query_text,
        n_results=n_results,
        filter_outcomes=["win", "loss"]  # Only get completed outcomes
    )
    
    if not similar_entries:
        return {
            "patterns": [],
            "message": "No similar entries found"
        }
    
    # Extract patterns from similar entries
    wins = [e for e in similar_entries if e['metadata'].get('outcome') == 'win']
    losses = [e for e in similar_entries if e['metadata'].get('outcome') == 'loss']
    
    win_rate = (len(wins) / len(similar_entries) * 100) if similar_entries else 0
    
    avg_r_win = 0
    if wins:
        r_values = [float(e['metadata'].get('r_multiple', 0)) for e in wins if e['metadata'].get('r_multiple')]
        avg_r_win = sum(r_values) / len(r_values) if r_values else 0
    
    return {
        "similar_entries_found": len(similar_entries),
        "win_rate": round(win_rate, 2),
        "wins": len(wins),
        "losses": len(losses),
        "avg_r_multiple_win": round(avg_r_win, 2),
        "patterns": {
            "common_confluences_win": _extract_common_confluences(wins),
            "common_confluences_loss": _extract_common_confluences(losses)
        }
    }


def _extract_common_confluences(entries: List[Dict[str, Any]]) -> List[str]:
    """Extract most common confluences from entries"""
    confluence_counts = {}
    for entry in entries:
        confluences = json.loads(entry['metadata'].get('confluences_met', '[]'))
        for conf in confluences:
            confluence_counts[conf] = confluence_counts.get(conf, 0) + 1
    
    # Sort by frequency
    sorted_confluences = sorted(confluence_counts.items(), key=lambda x: x[1], reverse=True)
    return [conf for conf, count in sorted_confluences[:5]]  # Top 5

