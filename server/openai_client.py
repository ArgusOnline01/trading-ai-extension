#!/usr/bin/env python3
"""
OpenAI Client Wrapper for Visual Trade Copilot
Handles API calls with budget enforcement and error handling
"""
import os
from openai import OpenAI
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
        self.client = OpenAI(api_key=api_key)
    
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
        import time
        import re
        t0 = time.perf_counter()
        
        # OPTIMIZATION: Shortcut for "what did I learn from my last loss" queries
        question_lower = question.lower().strip()
        
        # Broader regex pattern for reflection queries
        reflection_pattern = r"(what.*learn|learn.*loss|lesson|reflect|from my last loss)"
        if re.search(reflection_pattern, question_lower):
            # Check if we have summary stats available
            if session_context:
                all_trades = session_context.get("all_trades") or session_context.get("recent_trades", [])
                if all_trades:
                    losses = [t for t in all_trades if t.get('outcome') == 'loss' or (isinstance(t.get('pnl'), (int, float)) and t.get('pnl', 0) < 0)]
                    if losses:
                        # Quick insight response (skip long AI reasoning)
                        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                        print(f"[OPENAI_CLIENT] Quick reflection shortcut triggered (duration: {elapsed_ms} ms)")
                        return {
                            "model": model,
                            "answer": "✅ Quick insight: your loss likely came from early entries or weak POIs. Want a detailed breakdown?",
                            "intent": "stats_command",
                            "phase": "5f",
                            "duration_ms": elapsed_ms,
                            "status": 200
                        }
        
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

                # Phase 4D.3: Include ALL trades if provided by the extension background
                recent = session_context.get("recent_trades")
                all_trades = session_context.get("all_trades")  # Full list if available
                trades_to_use = all_trades if (all_trades and isinstance(all_trades, list)) else (recent if isinstance(recent, list) else [])
                
                if isinstance(trades_to_use, list) and trades_to_use:
                    total_trades = len(trades_to_use)
                    
                    # Build a compact summary of ALL trades showing PnL in DOLLARS
                    # Group by outcome for quick reference
                    wins = [t for t in trades_to_use if (t.get('outcome') == 'win' or (t.get('pnl', 0) > 0 and t.get('outcome') != 'loss'))]
                    losses = [t for t in trades_to_use if (t.get('outcome') == 'loss' or (t.get('pnl', 0) < 0 and t.get('outcome') != 'win'))]
                    breakevens = [t for t in trades_to_use if t.get('outcome') == 'breakeven' or (isinstance(t.get('pnl'), (int, float)) and t.get('pnl', 0) == 0)]
                    
                    context_str += f"\n[USER TRADE HISTORY - COMPLETE DATASET]\n"
                    context_str += f"TOTAL TRADES: {total_trades}\n"
                    context_str += f"Wins: {len(wins)}, Losses: {len(losses)}, Breakevens: {len(breakevens)}\n\n"
                    
                    # Show ALL winning trades with PnL in DOLLARS (sorted newest first)
                    if wins:
                        context_str += "WINNING TRADES (PnL in dollars, newest first):\n"
                        for t in wins[:20]:  # Limit to 20 to save tokens, but user can ask for more
                            sym = t.get('symbol', 'UNK')
                            pnl_dollars = t.get('pnl')
                            pnl_str = f"${pnl_dollars:+.2f}" if isinstance(pnl_dollars, (int, float)) else "N/A"
                            rr = t.get('r_multiple') or t.get('rr')
                            rr_str = f" ({rr}R)" if rr is not None else ""
                            date = t.get('timestamp') or t.get('entry_time') or t.get('trade_day')
                            date_str = date[:10] if date and len(date) >= 10 else (date if date else "?")
                            trade_id = t.get('id') or t.get('trade_id')
                            chart_path = t.get('chart_path')
                            chart_marker = " 📊" if chart_path else ""
                            context_str += f"  - {sym} | {pnl_str}{rr_str} | {date_str} | ID:{trade_id}{chart_marker}\n"
                        if len(wins) > 20:
                            context_str += f"  ... and {len(wins) - 20} more wins\n"
                    
                    # Show recent trades summary (last 15 for context) WITH EXACT PRICES
                    context_str += f"\nRECENT TRADES (last 15, newest first) WITH EXACT PRICES:\n"
                    for t in trades_to_use[:15]:
                        sym = t.get('symbol', 'UNK')
                        outcome = t.get('outcome') or t.get('label')
                        if outcome is None and isinstance(t.get('pnl'), (int, float)):
                            outcome = 'win' if t['pnl'] > 0 else ('loss' if t['pnl'] < 0 else 'breakeven')
                        
                        pnl_dollars = t.get('pnl')
                        pnl_str = f"${pnl_dollars:+.2f}" if isinstance(pnl_dollars, (int, float)) else "N/A"
                        
                        rr = t.get('r_multiple') or t.get('rr')
                        rr_str = f" ({rr}R)" if rr is not None else ""
                        
                        # Include exact entry/exit/stop/target prices
                        entry = t.get('entry_price')
                        stop = t.get('stop_loss')
                        target = t.get('take_profit')
                        exit_price = t.get('exit_price')  # May not exist, calculate if needed
                        
                        price_parts = []
                        if entry: price_parts.append(f"Entry:${entry}")
                        if stop: price_parts.append(f"Stop:${stop}")
                        if target: price_parts.append(f"Target:${target}")
                        if exit_price: price_parts.append(f"Exit:${exit_price}")
                        price_str = f" | {' '.join(price_parts)}" if price_parts else ""
                        
                        date = t.get('timestamp') or t.get('entry_time') or t.get('trade_day')
                        date_str = date[:10] if date and len(date) >= 10 else (date[:20] if date else "?")
                        
                        trade_id = t.get('id') or t.get('trade_id')
                        chart_path = t.get('chart_path')
                        chart_marker = " 📊" if chart_path else ""
                        
                        context_str += f"  {sym} | {outcome or 'pending'} | {pnl_str}{rr_str}{price_str} | {date_str} | ID:{trade_id}{chart_marker}\n"
                    
                    context_str += f"\nIMPORTANT:\n"
                    context_str += f"- You have access to ALL {total_trades} trades in the complete dataset.\n"
                    context_str += f"- ALL PnL values shown above are in DOLLARS (e.g., $762.50, $-160.00).\n"
                    context_str += f"- When users ask about specific trades, reference the dollar amounts directly from this data.\n"
                    context_str += f"- When listing wins/losses, show PnL in dollars (${pnl_dollars:+.2f} format), NOT just R-multiples.\n"
                    context_str += f"- If a user asks about a trade by date/symbol, search ALL {total_trades} trades, not just the recent 15 shown.\n"
                    context_str += f"- **CHART IMAGES: Trades marked with 📊 HAVE chart images available!**\n"
                    context_str += "- **CRITICAL: When a trade is mentioned and a chart image is attached to this message, you ARE seeing it!**\n"
                    context_str += "- **ALWAYS confirm with FULL details:** \"✅ I can see the [SYMBOL] trade chart! Entry: $[price], Exit: $[price], Stop: $[price], Target: $[price], P&L: $[amount] ([R]R).\"\n"
                    context_str += "- **AUTOMATICALLY include entry/exit prices from trade logs** - you have access to exact prices, ALWAYS include them!\n"
                    context_str += "- **NEVER say:** \"You can view it in Teach Copilot\" or \"You can see it here\" - if you see the image, you already have it!\n"
                    context_str += "- Each trade's chart image filename follows pattern: `SYMBOL_5m_TRADE_ID.png` (e.g., `6EZ5_5m_1540306142.png`)\n"

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
            
            # Phase 4A cleanup: Pure AI chat (no command extraction)
            # Extension is now pure conversational AI for trading analysis
            try:
                from memory.utils import get_memory_status
                
                status = get_memory_status()
                
                awareness_context = """

[AI SYSTEM AWARENESS - Phase 4A: Pure Conversational AI]
You are the Visual Trade Copilot, a conversational AI trading assistant.
You analyze charts using Smart Money Concepts (SMC) and provide trading insights.

Your capabilities:
- Access to {} trades with full trade history
- {} active trading sessions
- {} conversation messages for context
- Current win rate: {:.1f}%, Avg R: {:+.2f}

You provide:
- Chart analysis (market structure, POI, BOS, setups)
- Trade review and feedback
- Strategy insights based on user's trade history
- Entry/exit analysis and suggestions

When users ask about their trades, stats, or performance:
- You have access to ALL trades in the complete dataset (not just last 10)
- ALL PnL values are in DOLLARS (e.g., $762.50, $-160.00) - ALWAYS show dollar amounts when listing trades
- When listing winning trades, show PnL in dollars (format: $+XXX.XX or $-XXX.XX), NOT just R-multiples
- If a user asks about a specific trade by date/symbol, search through ALL trades in the dataset
- The context shows: (1) ALL winning trades list, (2) Recent 15 trades summary - but you have access to the FULL dataset
- Chart images are stored at `/charts/{filename}` and are accessible when needed

Respond conversationally, focus on trading analysis and insights.
Be concise but thorough. Use your SMC expertise to help the trader improve.
""".format(
                    status.get('total_trades', 0),
                    status.get('active_sessions', 0),
                    status.get('conversation_messages', 0),
                    status.get('win_rate', 0) * 100,
                    status.get('avg_rr', 0)
                )
                
                system_prompt += awareness_context
                print("[SYSTEM] ✅ Injected pure AI chat awareness context")
                
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
                
                # print(f"[DEBUG] Adding {len(conversation_history)} messages to context")
                for i, msg in enumerate(conversation_history):
                    # Only include text content from history (no images from past messages)
                    if msg.get("role") in ["user", "assistant"]:
                        # Safe logging without emojis for Windows console
                        # content_preview = msg['content'][:50] if isinstance(msg['content'], str) else str(type(msg['content']))
                        # safe_preview = content_preview.encode('ascii', 'ignore').decode('ascii')
                        # print(f"[DEBUG] Message {i}: role={msg['role']}, content preview={safe_preview}")
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                    # else:
                        # print(f"[DEBUG] Skipping message {i} with role: {msg.get('role')}")
            
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
            
            # Build params for Chat Completions (text-only path for Phase 4A)
            chat_params = {
                "model": model,
                "messages": messages,
            }
            # Token and sampling controls where supported
            if not (('gpt-5' in model.lower()) or ('o1' in model.lower()) or ('o3' in model.lower())):
                chat_params["max_tokens"] = MAX_TOKENS
                chat_params["temperature"] = TEMPERATURE

            # Run sync SDK in a thread to preserve async signature
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(**chat_params)
            )

            # Extract response
            choice = response.choices[0]
            answer = (choice.message.content or "").strip()
            tokens_used = (response.usage.total_tokens if getattr(response, "usage", None) else 0)
            actual_model = getattr(response, "model", model)
            
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
        # Use the OpenAI v1 client to list models
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.models.list()
        # Extract model IDs
        model_names = [m.id for m in response.data]
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
