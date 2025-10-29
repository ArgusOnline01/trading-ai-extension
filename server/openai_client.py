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
DEFAULT_MODEL = "gpt-4o"
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
                            image_base64: str, 
                            model: str = DEFAULT_MODEL,
                            conversation_history: list = None) -> Dict[str, Any]:
        """
        Create a conversational response about a trading chart (Phase 3A: With memory)
        
        Args:
            question: User's question about the chart
            image_base64: Base64 encoded chart image
            model: OpenAI model to use
            conversation_history: Optional list of previous messages for context
            
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
            
            # Build messages array starting with system prompt
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]
            
            # Add conversation history if provided (for context)
            if conversation_history:
                for msg in conversation_history:
                    # Only include text content from history (no images from past messages)
                    if msg.get("role") in ["user", "assistant"]:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
            
            # Add current question with image
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
    "fast": "gpt-4o-mini",    # Fastest, cheapest  
    "balanced": "gpt-4o",     # Default, stable
    "advanced": "gpt-4o"      # Best available (GPT-5 vision support pending)
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
    Updates 'advanced' alias to use GPT-5 if detected, otherwise falls back to GPT-4o.
    
    Returns:
        Updated MODEL_ALIASES dictionary
    """
    try:
        model_info = list_available_models()
        
        if model_info['gpt_5_detected']:
            # Prefer gpt-5-mini for vision support (base gpt-5 doesn't support vision yet)
            gpt5_variants = model_info['gpt_5_variants']
            if 'gpt-5-mini' in gpt5_variants:
                MODEL_ALIASES['advanced'] = 'gpt-5-mini'
            elif 'gpt-5' in gpt5_variants:
                MODEL_ALIASES['advanced'] = 'gpt-5'
            elif gpt5_variants:
                # Use the first available GPT-5 variant
                MODEL_ALIASES['advanced'] = gpt5_variants[0]
            
            print(f"GPT-5 detected! Updated 'advanced' alias to: {MODEL_ALIASES['advanced']}")
        else:
            # Fallback to GPT-4o if GPT-5 not available
            MODEL_ALIASES['advanced'] = 'gpt-4o'
            print("GPT-5 not available. 'advanced' alias set to: gpt-4o")
        
        return MODEL_ALIASES.copy()
    except Exception as e:
        print(f"Warning: Could not sync model aliases: {str(e)}")
        return MODEL_ALIASES.copy()
