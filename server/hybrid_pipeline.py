"""
Hybrid Vision → Reasoning Pipeline
Phase 3C: Enable GPT-5 Mini/Search to "see" charts via GPT-4o summaries

Flow:
1. GPT-4o analyzes chart → structured JSON summary (cached)
2. GPT-5 Mini/Search reasons about summary + user question
3. Follow-up questions reuse cached summary (zero extra cost)
"""

import io
import base64
import hashlib
from PIL import Image
from fastapi import UploadFile
from typing import Dict, Any

from cache import get_cache
from openai_client import get_client, resolve_model


async def hybrid_reasoning(
    image: UploadFile,
    question: str,
    reasoning_model: str,
    session_id: str,
    conversation_history: list = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Hybrid pipeline: GPT-4o vision → GPT-5 reasoning
    
    Args:
        image: Trading chart image
        question: User's question
        reasoning_model: Model for reasoning (e.g., gpt-5-mini)
        session_id: Session identifier for caching
        conversation_history: Previous messages for context
        force_refresh: Force new vision analysis (ignore cache)
        
    Returns:
        Dict with response, model info, and cache status
    """
    cache = get_cache()
    client = get_client()
    
    # Read and hash the image first (for smart cache invalidation)
    image_data = await image.read()
    image_hash = hashlib.md5(image_data).hexdigest()
    
    # Step 1: Get or generate vision summary with smart cache
    cache_key = "vision_summary"
    cached_image_hash = cache.get(session_id, "image_hash")
    cached_summary = None
    
    # Only use cache if image hasn't changed and not forcing refresh
    if not force_refresh and cached_image_hash == image_hash:
        cached_summary = cache.get(session_id, cache_key)
        print(f"[HYBRID] Image hash matches ({image_hash[:8]}...) - using cached summary")
    elif cached_image_hash and cached_image_hash != image_hash:
        print(f"[HYBRID] Image changed ({cached_image_hash[:8]}... -> {image_hash[:8]}...) - refreshing vision analysis")
        cache.clear(session_id)  # Clear all cache for this session
    else:
        print(f"[HYBRID] New image detected ({image_hash[:8]}...)")
    
    if cached_summary:
        vision_summary = cached_summary
        cache_hit = True
    else:
        print(f"[HYBRID] Generating new vision summary with GPT-4o")
        
        # Process image (we already read it for hashing)
        image_obj = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image_obj.mode != 'RGB':
            image_obj = image_obj.convert('RGB')
        
        # Resize if too large
        max_size = 2048
        if image_obj.width > max_size or image_obj.height > max_size:
            image_obj.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffer = io.BytesIO()
        image_obj.save(buffer, format='JPEG', quality=85)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # GPT-4o vision analysis (structured output)
        vision_prompt = """Analyze this trading chart and provide a concise JSON summary with these keys:
- symbol: Trading symbol/pair shown
- timeframe: Detected timeframe (e.g., "5m", "1h")
- current_price: Current price level visible
- bias: Market bias (bullish/bearish/neutral)
- key_levels: Array of significant price levels
- poi_zones: Points of interest (support/resistance zones)
- structure: Market structure description (CHOCH, BOS, trend, range)
- liquidity: Liquidity sweep notes or resting liquidity
- volume_profile: Volume characteristics if visible
- indicators: Any visible indicators (MACD, RSI, etc.)
- notes: Brief observations about chart patterns

Keep the response under 300 tokens. Be precise and factual."""
        
        vision_response = await client.create_response(
            question=vision_prompt,
            image_base64=image_base64,
            model="gpt-4o",  # Use GPT-4o for vision
            conversation_history=None
        )
        
        vision_summary = vision_response["answer"]
        
        # Cache the summary AND image hash
        cache.set(session_id, cache_key, vision_summary)
        cache.set(session_id, "image_hash", image_hash)
        cache_hit = False
        
        print(f"[HYBRID] Vision summary generated ({len(vision_summary)} chars)")
    
    # Step 2: GPT-5 reasoning with the summary
    # Resolve model alias to actual model name
    resolved_model = resolve_model(reasoning_model)
    print(f"[HYBRID] Reasoning with {reasoning_model} -> {resolved_model}")
    
    # Build reasoning prompt with chart data
    reasoning_prompt = f"""You are a professional trading analyst using Smart Money Concepts (SMC).

**Chart Analysis Data:**
{vision_summary}

**Trading Context:**
- You have access to structured chart data extracted from the image
- Use this data to provide precise, actionable trading advice
- Focus on SMC principles: market structure, POIs, liquidity, and order flow

**User Question:**
{question}

Provide a clear, concise answer based on the chart data above."""
    
    # Add conversation history if provided
    history_for_reasoning = []
    if conversation_history:
        # Include recent context (last 10 messages)
        history_for_reasoning = conversation_history[-10:]
    
    print(f"[HYBRID] Reasoning prompt length: {len(reasoning_prompt)} chars")
    print(f"[HYBRID] Conversation history: {len(history_for_reasoning)} messages")
    
    # Generate reasoning response (use resolved model name)
    print(f"[HYBRID] Calling create_response with model={resolved_model}, history_len={len(history_for_reasoning)}")
    
    reasoning_response = await client.create_response(
        question=reasoning_prompt,
        image_base64=None,  # No image needed for reasoning step
        model=resolved_model,  # Use resolved model name, not alias
        conversation_history=history_for_reasoning
    )
    
    # Debug: Check if response is empty
    answer_length = len(reasoning_response.get("answer", ""))
    print(f"[HYBRID] Response received: {answer_length} chars, model={reasoning_response.get('model')}")
    
    if answer_length == 0:
        print(f"[HYBRID WARNING] Empty response from {resolved_model}!")
        print(f"[HYBRID WARNING] Prompt length: {len(reasoning_prompt)} chars")
        print(f"[HYBRID WARNING] History length: {len(history_for_reasoning)} messages")
        print(f"[HYBRID WARNING] This model may not support the current parameters")
    
    return {
        "model": reasoning_response["model"],
        "answer": reasoning_response["answer"],
        "hybrid_mode": True,
        "vision_model": "gpt-4o",
        "reasoning_model": reasoning_model,
        "cache_hit": cache_hit,
        "vision_summary": vision_summary if not cache_hit else "(cached)",
        "tokens_used": reasoning_response.get("tokens_used", 0)
    }


async def clear_session_cache(session_id: str) -> Dict[str, Any]:
    """
    Clear cached vision summaries for a session.
    Call this when user uploads a new chart or changes symbol.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Status message
    """
    cache = get_cache()
    cache.clear(session_id)
    
    return {
        "status": "cleared",
        "session_id": session_id,
        "message": "Vision cache cleared for session"
    }

