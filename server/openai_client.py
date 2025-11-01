#!/usr/bin/env python3
"""
OpenAI Client Wrapper for Visual Trade Copilot
Handles API calls with budget enforcement and error handling
"""
import os
import openai
from typing import Dict, Any, Optional
import json

# Configuration
DEFAULT_MODEL = "gpt-5-chat-latest"  # Phase 4C.1: Updated default to GPT-5 Chat
MAX_TOKENS = 1000
TEMPERATURE = 0.1

# Budget tracking (simple in-memory for now)
_budget_tracker = {
    "total_cost": 0.0,
    "max_budget": float(os.getenv("MAX_BUDGET", "10.0")),  # $10 default
    "cost_per_1k_tokens": 0.01  # Approximate cost
}

def enforce_budget() -> bool:
    """Check if we're within budget limits"""
    return _budget_tracker["total_cost"] < _budget_tracker["max_budget"]

def add_cost(tokens_used: int) -> None:
    """Add cost to budget tracker"""
    cost = (tokens_used / 1000) * _budget_tracker["cost_per_1k_tokens"]
    _budget_tracker["total_cost"] += cost

def get_budget_status() -> Dict[str, Any]:
    """Get current budget status"""
    return {
        "total_cost": _budget_tracker["total_cost"],
        "max_budget": _budget_tracker["max_budget"],
        "remaining": _budget_tracker["max_budget"] - _budget_tracker["total_cost"],
        "within_budget": enforce_budget()
    }

class OpenAIClient:
    """OpenAI API client with budget enforcement"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key
    
    async def create_response(self, 
                            question: str, 
                            image_base64: str = None,  # Phase 3B.1: Optional for text-only mode
                            model: str = DEFAULT_MODEL,
                            conversation_history: list = None,
                            session_context: dict = None) -> Dict[str, Any]:
        """
        Create a conversational response about a trading chart (Phase 3B.1: Text-only support)
        
        Args:
            question: User's question about the chart
            image_base64: Base64 encoded chart image (optional for text-only mode)
            model: OpenAI model to use
            conversation_history: Optional list of previous messages for context
            session_context: Optional session state (price, bias, POIs, etc.)
            
        Returns:
            Dict with model name and answer
        """
        if not enforce_budget():
            raise Exception("Budget limit exceeded. Please check your spending limits.")
        
        try:
            # Create the system prompt for SMC trading expertise
            system_prompt = """You are an expert trader specializing in Smart Money Concepts (SMC), 
volume profile, and market structure. The user trades short-term setups (5m timeframe, SMC bias, 
POIs, liquidity sweeps, MACD divergence). Answer conversationally, focusing on clarity, reasoning, 
and actionable advice. Be concise but thorough in your analysis.

When the user references previous messages (e.g., "the setup I showed earlier", "that chart", 
"as you mentioned"), use the conversation history to provide coherent, contextual responses."""
            
            # Phase 3B: Inject session context if available
            if session_context:
                context_str = "\n\n[SESSION CONTEXT]:\n"
                if session_context.get("latest_price"):
                    context_str += f"Latest Price: {session_context['latest_price']}\n"
                if session_context.get("bias"):
                    context_str += f"Current Bias: {session_context['bias']}\n"
                if session_context.get("last_poi"):
                    context_str += f"Last POI: {session_context['last_poi']}\n"
                if session_context.get("timeframe"):
                    context_str += f"Timeframe: {session_context['timeframe']}\n"
                if session_context.get("notes"):
                    notes = session_context["notes"]
                    if notes:
                        context_str += f"Notes: {', '.join(notes[:3])}\n"  # Show first 3 notes

                # Phase 4D.3: Include recent trades if provided by the extension background
                recent = session_context.get("recent_trades")
                if isinstance(recent, list) and recent:
                    # Build a compact, token-light list of last up to 10 trades
                    compact = []
                    for t in recent[-10:]:
                        sym = t.get('symbol', 'UNK')
                        outcome = t.get('outcome')
                        if outcome is None and isinstance(t.get('pnl'), (int, float)):
                            outcome = 'win' if t['pnl'] > 0 else ('loss' if t['pnl'] < 0 else 'breakeven')
                        rr = t.get('r_multiple')
                        if rr is None and isinstance(t.get('pnl'), (int, float)):
                            rr = t['pnl']  # as-is; server computes better approximations when needed
                        compact.append(f"{sym} | {outcome or 'pending'} | R:{rr if rr is not None else '-'}")
                    context_str += "Recent Trades (last 10):\n" + "\n".join(compact) + "\n"

                # Phase 4D.3.2: Include command execution result if available
                cmd_result = session_context.get("last_command_result")
                if cmd_result and isinstance(cmd_result, dict):
                    context_str += "\n[COMMAND EXECUTED]:\n"
                    context_str += f"Command: {cmd_result.get('command', 'unknown')}\n"
                    context_str += f"Status: {'Success' if cmd_result.get('success') else 'Failed'}\n"
                    if cmd_result.get('message'):
                        context_str += f"Result: {cmd_result['message']}\n"
                    context_str += "\nIMPORTANT: A system command was just executed. Reference this result in your response. Say 'I've done it' or 'Here's what happened' - NOT 'I can't' or 'simulated'.\n"

                # Phase 4D.4: Include actual system sessions from IndexedDB
                all_sessions = session_context.get("all_sessions")
                current_session_id = session_context.get("current_session_id")
                if isinstance(all_sessions, list) and all_sessions:
                    context_str += "\n[SYSTEM SESSIONS - ACTUAL STATE]:\n"
                    context_str += f"Total sessions in system: {len(all_sessions)}\n"
                    context_str += f"Current active session ID: {current_session_id}\n\n"
                    for i, sess in enumerate(all_sessions[:10], 1):
                        active_marker = " 🔵 ACTIVE" if sess.get("isActive") or sess.get("sessionId") == current_session_id else ""
                        title = sess.get("title", sess.get("symbol", "Unknown"))
                        symbol = sess.get("symbol", "?")
                        context_str += f"{i}. {title} ({symbol}){active_marker} - ID: {sess.get('sessionId', '?')[:20]}...\n"
                    if len(all_sessions) > 10:
                        context_str += f"... and {len(all_sessions) - 10} more sessions\n"
                    context_str += "\nIMPORTANT: These are the ACTUAL sessions stored in IndexedDB. When users ask about sessions, reference this real data.\n"

                system_prompt += context_str
            
            # Phase 4C: Inject learning profile for adaptive advice
            try:
                from performance.learning import get_learning_context
                learning_context = get_learning_context()
                if learning_context:
                    system_prompt += learning_context
                    print("[LEARNING] ✅ Injected performance profile into AI prompt")
            except Exception as e:
                print(f"[LEARNING] Could not load profile: {e}")
            
            # Phase 4C.1: Inject system awareness context
            try:
                from memory.utils import get_memory_status
                from memory.system_commands import COMMAND_PATTERNS
                
                status = get_memory_status()
                
                awareness_context = """

[AI SYSTEM AWARENESS]
You are the Visual Trade Copilot. You live inside a Chrome Extension backed by FastAPI.
You analyze charts, log trades, and learn from user strategy.

Your capabilities:
- All memory persists in backend JSON files (survives browser restarts)
- You have access to {} trades, {} sessions, {} conversation messages
- Current win rate: {:.1f}%, Avg R: {:+.2f}
- You CAN execute system commands — the backend handles them automatically

Available commands you can execute (recognize natural language, including question phrasings):

**Performance:**
- "show my stats" / "how am i doing" → Display actual performance summary
- "delete last trade" → Remove most recent trade entry
- "restore last trade" / "add it back" → Restore last deleted trade

**Sessions:**
- "list sessions" / "show sessions" → List ALL sessions (you have access to the actual IndexedDB data)
- "create session [symbol]" / "new session" → Create a new trading session
- "switch session" / "change session" → Switch to a different session
- "rename session [name]" → Rename the current session
- "delete session" → Delete a session

**System:**
- "what model are you using" → Show current AI model
- "clear memory" → Reset temporary data
- "help" / "what can you do" → Show all available commands

**UI:**
- You can request UI actions like "close chat", "open session manager", etc. (these are handled by the frontend)

COMMAND RECOGNITION:
- Commands work whether phrased as questions ("can you...", "how about...") or statements
- When users ask "what can you do" or "show me commands", you MUST list these capabilities confidently
- When users request these actions, respond confidently. Say "I've done it" or "Here's what I found" — NOT "I can't" or "simulated." The backend executes these commands for real.

For chart analysis, use your SMC expertise combined with their trading history.

[Copilot Bridge]
You have direct API access to:
- /copilot/performance → summarize trading performance
- /copilot/teach/examples → list teaching examples
- /copilot/teach/example/{id} → fetch specific teaching example
When users ask about their stats, performance, teaching data, or specific trades, always reference these endpoints to ensure your responses are accurate and live.
""".format(
                    status.get('total_trades', 0),
                    status.get('active_sessions', 0),
                    status.get('conversation_messages', 0),
                    status.get('win_rate', 0) * 100,
                    status.get('avg_rr', 0)
                )
                
                system_prompt += awareness_context
                print("[SYSTEM] ✅ Injected awareness context")
                
            except Exception as e:
                print(f"[SYSTEM] Could not inject awareness: {e}")
            
            # Build messages array starting with system prompt
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]
            
            # Phase 3B.1: Token truncation - limit conversation history if needed
            if conversation_history:
                # Estimate tokens (rough: 1 token ≈ 4 chars)
                estimated_tokens = sum(len(str(msg.get('content', ''))) // 4 for msg in conversation_history)
                
                if estimated_tokens > 8000:
                    print(f"[Token Optimization] History has ~{estimated_tokens} tokens, truncating to last 20 messages")
                    conversation_history = conversation_history[-20:]
                    estimated_tokens = sum(len(str(msg.get('content', ''))) // 4 for msg in conversation_history)
                    print(f"[Token Optimization] Reduced to ~{estimated_tokens} tokens")
                
                print(f"[DEBUG] Adding {len(conversation_history)} messages to context")
                for i, msg in enumerate(conversation_history):
                    # Only include text content from history (no images from past messages)
                    if msg.get("role") in ["user", "assistant"]:
                        # Safe logging without emojis for Windows console
                        content_preview = msg['content'][:50] if isinstance(msg['content'], str) else str(type(msg['content']))
                        safe_preview = content_preview.encode('ascii', 'ignore').decode('ascii')
                        print(f"[DEBUG] Message {i}: role={msg['role']}, content preview={safe_preview}")
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                    else:
                        print(f"[DEBUG] Skipping message {i} with role: {msg.get('role')}")
            
            # Phase 3B.1: Add current question (with or without image)
            if image_base64:
                # Vision mode: include image
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": question
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                })
            else:
                # Text-only mode: no image
                messages.append({
                    "role": "user",
                    "content": question
                })
            
            # Use the older OpenAI API format for compatibility
            # GPT-5 uses max_completion_tokens instead of max_tokens
            api_params = {
                "model": model,
                "messages": messages
            }
            
            # GPT-5 models use max_completion_tokens, older models use max_tokens
            # GPT-5 also doesn't support custom temperature (only default of 1)
            if 'gpt-5' in model.lower() or 'o1' in model.lower() or 'o3' in model.lower():
                api_params["max_completion_tokens"] = MAX_TOKENS
                # GPT-5 only supports temperature=1 (default), so we don't set it
            else:
                api_params["max_tokens"] = MAX_TOKENS
                api_params["temperature"] = TEMPERATURE
            
            response = await openai.ChatCompletion.acreate(**api_params)
            
            # Extract response
            answer = response['choices'][0]['message']['content'].strip() if response['choices'][0]['message']['content'] else ""
            tokens_used = response.get('usage', {}).get('total_tokens', 0)
            actual_model = response.get('model', model)  # Get actual model used by API
            
            print(f"[OPENAI] Actual model used: '{actual_model}' | Tokens: {tokens_used}")
            
            # Track cost
            add_cost(tokens_used)
            
            return {
                "model": model,
                "answer": answer,
                "tokens_used": tokens_used,
                "cost": (tokens_used / 1000) * _budget_tracker["cost_per_1k_tokens"]
            }
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

# Global client instance
_client = None

def get_client() -> OpenAIClient:
    """Get or create the global OpenAI client"""
    global _client
    if _client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise Exception("OPENAI_API_KEY not found in environment variables")
        _client = OpenAIClient(api_key)
    return _client

def list_available_models() -> Dict[str, Any]:
    """
    List all OpenAI models available to the current API key.
    Detects GPT-5 variants and provides diagnostic information.
    
    Returns:
        Dict with model list, counts, and GPT-5 detection info
    """
    try:
        # Use the OpenAI API to list models
        response = openai.Model.list()
        
        # Extract model IDs
        model_names = [model['id'] for model in response['data']]
        model_names.sort()  # Sort alphabetically for readability
        
        # Detect GPT-5 variants
        gpt5_models = [m for m in model_names if 'gpt-5' in m.lower()]
        
        # Detect GPT-4 variants for comparison
        gpt4_models = [m for m in model_names if 'gpt-4' in m.lower()]
        
        # Check if vision models are available
        vision_models = [m for m in model_names if 'vision' in m.lower() or 'gpt-4o' in m.lower() or 'gpt-5' in m.lower()]
        
        return {
            "total_models": len(model_names),
            "models": model_names,
            "gpt_5_detected": bool(gpt5_models),
            "gpt_5_variants": gpt5_models,
            "gpt_4_variants": gpt4_models,
            "vision_models": vision_models,
            "current_aliases": MODEL_ALIASES.copy()
        }
    except Exception as e:
        raise Exception(f"Failed to list models: {str(e)}")


# --- Dynamic Model Selection Helper ---

MODEL_ALIASES = {
    # Phase 3C: Optimized model selection (GPT-5 Search as default)
    "fast": "gpt-5-chat-latest",          # GPT-5 Chat Latest with VISION
    "balanced": "gpt-5-search-api-2025-10-14",  # GPT-5 Search (default, hybrid mode)
    "advanced": "gpt-4o",                 # GPT-4o (reliable vision fallback)
    # Alternative models
    "gpt5-mini": "gpt-5-mini",            # GPT-5 Mini (has conversation history issues)
    "gpt4o": "gpt-4o",                    # GPT-4o (vision capable)
    "gpt4o-mini": "gpt-4o-mini"           # GPT-4o-mini (budget option)
}

def resolve_model(requested_model: Optional[str]) -> str:
    """
    Resolves model alias or explicit model name.
    Falls back to DEFAULT_MODEL if invalid or missing.
    
    Args:
        requested_model: Model name or alias (e.g., "fast", "balanced", "gpt-4o-mini")
        
    Returns:
        Resolved model name (e.g., "gpt-4o-mini", "gpt-4o")
        
    Examples:
        resolve_model("fast") -> "gpt-4o-mini"
        resolve_model("gpt-4o") -> "gpt-4o"
        resolve_model(None) -> DEFAULT_MODEL
    """
    if not requested_model:
        return DEFAULT_MODEL
    
    requested_model = requested_model.strip().lower()
    
    # Check if it's an alias
    if requested_model in MODEL_ALIASES:
        return MODEL_ALIASES[requested_model]
    
    # Check if it's a valid OpenAI model name
    if requested_model.startswith("gpt-"):
        return requested_model
    
    # Fall back to default
    return DEFAULT_MODEL

def sync_model_aliases() -> Dict[str, str]:
    """
    Automatically sync MODEL_ALIASES with available models.
    Phase 3B.2: GPT-5 models are now primary user-facing options.
    
    Returns:
        Updated MODEL_ALIASES dictionary
    """
    try:
        model_info = list_available_models()
        
        if model_info['gpt_5_detected']:
            gpt5_variants = model_info['gpt_5_variants']
            working_gpt5_models = [
                'gpt-5-chat-latest',
                'gpt-5-mini',
                'gpt-5-mini-2025-08-07',
                'gpt-5-search-api',
                'gpt-5-search-api-2025-10-14'
            ]
            
            # Update primary aliases with best available GPT-5 models
            if 'gpt-5-chat-latest' in gpt5_variants:
                MODEL_ALIASES['fast'] = 'gpt-5-chat-latest'
            if 'gpt-5-search-api-2025-10-14' in gpt5_variants:
                MODEL_ALIASES['balanced'] = 'gpt-5-search-api-2025-10-14'
            
            available_working = [m for m in working_gpt5_models if m in gpt5_variants]
            print(f"[Phase 3C] GPT-5 Models Active: {len(available_working)} variants available")
            print(f"  Fast: {MODEL_ALIASES['fast']} (native vision)")
            print(f"  Balanced: {MODEL_ALIASES['balanced']} (hybrid mode - RECOMMENDED)")
            print(f"  Advanced: {MODEL_ALIASES['advanced']} (GPT-4o vision)")
        
        return MODEL_ALIASES.copy()
    except Exception as e:
        print(f"Warning: Could not sync model aliases: {str(e)}")
        return MODEL_ALIASES.copy()
