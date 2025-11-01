"""
GPT Client for Teaching Engine
Extracts BOS/POI from lesson text using GPT models
"""

import json
import os
import re
from typing import Dict, Any, Optional
import openai


def extract_bos_poi(text: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Extract BOS (Break of Structure) and POI (Price of Interest) from lesson text.
    
    Uses GPT to parse structured data from natural language lesson text.
    Falls back to regex pattern matching if GPT fails.
    
    Args:
        text: User's lesson text describing the trade setup
        model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
    
    Returns:
        Dict with:
            - bos: {"start": price, "end": price} or None
            - poi: [{"low": price, "high": price, "reason": str}] or []
            - confidence: float (0.0-1.0)
    """
    if not text or not text.strip():
        return {
            "bos": None,
            "poi": [],
            "confidence": 0.0
        }
    
    # Try GPT extraction first (using old OpenAI SDK v0.28 style)
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        # Use old-style OpenAI API (compatible with openai==0.28.1)
        openai.api_key = api_key
        
        system_prompt = """You are a trading analysis assistant. Extract BOS (Break of Structure) and POI (Price of Interest) from the user's lesson text.

Return ONLY a valid JSON object with this exact structure:
{
  "bos": {"start": <price>, "end": <price>} or null,
  "poi": [{"low": <price>, "high": <price>, "reason": "<description>"}] or [],
  "confidence": <0.0-1.0>
}

If information is missing, use null/empty array. Confidence should reflect how certain you are about the extraction."""

        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            
            # Validate structure
            result = {
                "bos": parsed.get("bos"),
                "poi": parsed.get("poi", []),
                "confidence": float(parsed.get("confidence", 0.7))
            }
            
            # Validate BOS structure
            if result["bos"] and not isinstance(result["bos"], dict):
                result["bos"] = None
            
            # Validate POI structure
            if not isinstance(result["poi"], list):
                result["poi"] = []
            else:
                # Ensure each POI has required fields
                validated_poi = []
                for poi in result["poi"]:
                    if isinstance(poi, dict) and "low" in poi and "high" in poi:
                        validated_poi.append({
                            "low": float(poi.get("low", 0)),
                            "high": float(poi.get("high", 0)),
                            "reason": str(poi.get("reason", ""))
                        })
                result["poi"] = validated_poi
            
            return result
    
    except Exception as e:
        print(f"[GPT] Extraction failed: {e}, falling back to regex")
    
    # Fallback: Simple regex pattern matching
    return _regex_extract_bos_poi(text)


def _regex_extract_bos_poi(text: str) -> Dict[str, Any]:
    """
    Fallback regex extraction for BOS/POI.
    Looks for common patterns in lesson text.
    """
    text_lower = text.lower()
    
    # Try to find BOS patterns: "BOS at 1.1700" or "break of structure 1.1650 to 1.1700"
    bos_patterns = [
        r'bos\s+(?:at|from|between)\s+(\d+\.?\d*)\s*(?:to|-|and)?\s*(\d+\.?\d*)',
        r'break\s+of\s+structure\s+(\d+\.?\d*)\s*(?:to|-|and)?\s*(\d+\.?\d*)',
        r'structure\s+break\s+(\d+\.?\d*)\s*(?:to|-|and)?\s*(\d+\.?\d*)'
    ]
    
    bos_match = None
    for pattern in bos_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            bos_match = match
            break
    
    bos_result = None
    if bos_match:
        groups = bos_match.groups()
        if len(groups) >= 2:
            try:
                bos_result = {
                    "start": float(groups[0]),
                    "end": float(groups[1])
                }
            except ValueError:
                pass
    
    # Try to find POI patterns: "POI at 1.1700-1.1750" or "price of interest 1.1650 to 1.1700"
    poi_patterns = [
        r'poi\s+(?:at|from|between)\s+(\d+\.?\d*)\s*(?:to|-|and)?\s*(\d+\.?\d*)',
        r'price\s+of\s+interest\s+(\d+\.?\d*)\s*(?:to|-|and)?\s*(\d+\.?\d*)',
        r'support\s+(?:zone|area)\s+(\d+\.?\d*)\s*(?:to|-|and)?\s*(\d+\.?\d*)',
        r'resistance\s+(?:zone|area)\s+(\d+\.?\d*)\s*(?:to|-|and)?\s*(\d+\.?\d*)'
    ]
    
    poi_result = []
    for pattern in poi_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            groups = match.groups()
            if len(groups) >= 2:
                try:
                    poi_result.append({
                        "low": float(groups[0]),
                        "high": float(groups[1]),
                        "reason": "extracted from lesson"
                    })
                except ValueError:
                    pass
    
    # Remove duplicates
    seen = set()
    unique_poi = []
    for poi in poi_result:
        key = (poi["low"], poi["high"])
        if key not in seen:
            seen.add(key)
            unique_poi.append(poi)
    
    return {
        "bos": bos_result,
        "poi": unique_poi,
        "confidence": 0.5 if (bos_result or unique_poi) else 0.3
    }

