"""
Phase 4E: Entry Suggestion Logic
Analyzes chart state and suggests entry points with stop loss
"""
from typing import Dict, Any, Optional, List
from openai_client import get_client
from db.session import SessionLocal
from db.models import Strategy
from ai.rag.entry_learning import retrieve_similar_entries
from ai.rag.pattern_extractor import get_patterns_for_similar_setup
import json


async def analyze_chart_for_entry(
    image_base64: str,
    session_state: Dict[str, Any],
    strategy_id: Optional[int] = None,
    model: str = "gpt-4o"
) -> Dict[str, Any]:
    """
    Analyze chart and suggest entry point based on current state
    
    Returns:
        {
            "entry_price": float,
            "stop_loss": float,
            "stop_loss_type": "strategy_based" | "fixed",
            "stop_loss_reasoning": str,
            "reasoning": str,
            "confluences_met": List[str],
            "ready_to_enter": bool
        }
    """
    # Get strategy if provided
    strategy_context = ""
    if strategy_id:
        with SessionLocal() as db:
            strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
            if strategy:
                strategy_context = f"""
Your Strategy:
- Setup Definitions: {json.dumps(strategy.setup_definitions or {}, indent=2)}
- Entry Methods: {json.dumps(strategy.entry_methods or {}, indent=2)}
- Stop Loss Rules: {json.dumps(strategy.stop_loss_rules or {}, indent=2)}
- Good Entry Criteria: {json.dumps(strategy.good_entry_criteria or {}, indent=2)}
- Bad Entry Criteria: {json.dumps(strategy.bad_entry_criteria or {}, indent=2)}
"""
    
    # Build state context
    state_summary = ""
    if session_state:
        setup_detected = session_state.get('setup_detected', False)
        waiting_for = session_state.get('waiting_for', [])
        confluences_met = session_state.get('confluences_met', [])
        
        state_summary = f"""
Current Session State:
- Setup Detected: {setup_detected}
- Waiting For: {', '.join(waiting_for) if waiting_for else 'None'}
- Confluences Met: {', '.join(confluences_met) if confluences_met else 'None'}
"""
    
    # Retrieve similar past setups and patterns (RAG learning)
    rag_context = ""
    try:
        query_text = f"Setup with confluences: {', '.join(confluences_met) if confluences_met else 'general setup'}"
        # Use a new session for RAG retrieval (will be closed automatically)
        with SessionLocal() as rag_db:
            similar_patterns = await get_patterns_for_similar_setup(
                query_text=query_text,
                db=rag_db,
                n_results=5
            )
        
        if similar_patterns.get('similar_entries_found', 0) > 0:
            rag_context = f"""
[LEARNING FROM PAST OUTCOMES]
Similar setups found: {similar_patterns.get('similar_entries_found', 0)}
Win rate in similar setups: {similar_patterns.get('win_rate', 0)}%
Average R multiple (wins): {similar_patterns.get('avg_r_multiple_win', 0)}
Common winning confluences: {', '.join(similar_patterns.get('patterns', {}).get('common_confluences_win', []))}
Common losing confluences: {', '.join(similar_patterns.get('patterns', {}).get('common_confluences_loss', []))}

Use this information to improve your entry suggestion.
"""
    except Exception as e:
        print(f"[ENTRY_SUGGESTER] RAG retrieval error: {e}")
        rag_context = ""
    
    # Build prompt
    prompt = f"""You are analyzing a trading chart to suggest an optimal entry point.

{strategy_context}

{state_summary}

{rag_context}

Analyze the chart image and determine:
1. Is the setup ready for entry? (all required confluences met?)
2. If ready, suggest an entry price (extract exact price from chart)
3. Suggest a stop loss price (strategy-based: below POI/BOS, or fixed: X pips)
4. Extract chart price range (min_price and max_price visible on chart) for overlay rendering
5. Explain your reasoning

Return your response as JSON:
{{
    "ready_to_enter": true/false,
    "entry_price": 1.1695 (or null if not ready),
    "stop_loss": 1.1680 (or null if not ready),
    "stop_loss_type": "strategy_based" or "fixed",
    "stop_loss_reasoning": "below POI at 1.1680" or "50 pips below entry",
    "reasoning": "All confluences met: liquidity sweep occurred, IFVG present, structure confirmed. Suggest entry at 50% of zone.",
    "confluences_met": ["liquidity_sweep", "IFVG", "structure_confirmed"],
    "waiting_for": ["additional_confirmation"] (if not ready),
    "chart_min_price": 1.1650 (minimum price visible on chart),
    "chart_max_price": 1.1750 (maximum price visible on chart)
}}

If not ready to enter, explain what is still needed.
Always extract chart_min_price and chart_max_price from the price scale/labels visible on the chart."""
    
    client = get_client()
    
    # Use vision model to analyze chart
    try:
        import asyncio
        # Use the client's chat completion method
        response = await asyncio.to_thread(
            lambda: client.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a trading assistant that analyzes charts and suggests optimal entry points based on Smart Money Concepts."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"}
            )
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        return {
            "entry_price": result.get("entry_price"),
            "stop_loss": result.get("stop_loss"),
            "stop_loss_type": result.get("stop_loss_type", "strategy_based"),
            "stop_loss_reasoning": result.get("stop_loss_reasoning", ""),
            "reasoning": result.get("reasoning", ""),
            "confluences_met": result.get("confluences_met", []),
            "waiting_for": result.get("waiting_for", []),
            "ready_to_enter": result.get("ready_to_enter", False),
            "chart_min_price": result.get("chart_min_price"),
            "chart_max_price": result.get("chart_max_price")
        }
    except Exception as e:
        print(f"[ENTRY_SUGGESTER] Error: {e}")
        return {
            "entry_price": None,
            "stop_loss": None,
            "stop_loss_type": "strategy_based",
            "stop_loss_reasoning": "",
            "reasoning": f"Error analyzing chart: {str(e)}",
            "confluences_met": [],
            "waiting_for": [],
            "ready_to_enter": False
        }

