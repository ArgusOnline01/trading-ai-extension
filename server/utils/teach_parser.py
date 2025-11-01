"""
Phase 5C: Incremental Teaching Parser
Extracts BOS/POI fields from user messages incrementally during teaching sessions
"""

import re
import random
from typing import Dict, Any, List, Optional


def normalize_number(text: str) -> str:
    """
    Crude verbal → numeric normalizer.
    Converts spoken numbers like "one fourteen fifty" to "1.1450"
    """
    # Common verbal patterns for trading prices
    replacements = {
        "one fourteen fifty": "1.1450",
        "one fifteen": "1.1500",
        "one sixteen": "1.1600",
        "one seventeen": "1.1700",
        "one eighteen": "1.1800",
        "one nineteen": "1.1900",
        "one twenty": "1.2000",
        "fourteen fifty": "1450",
        "fifteen hundred": "1500",
        "sixteen hundred": "1600",
    }
    
    text_lower = text.lower()
    for verbal, numeric in replacements.items():
        text_lower = text_lower.replace(verbal, numeric)
    
    return text_lower


def extract_reason(text: str) -> str:
    """
    Heuristic reason detection for POI zones.
    """
    text_lower = text.lower()
    
    if "imbalance" in text_lower or "fvg" in text_lower or "fair value gap" in text_lower:
        return "fair value gap / imbalance"
    if "break" in text_lower or "structure" in text_lower or "bos" in text_lower:
        return "break of structure"
    if "liquidity" in text_lower or "sweep" in text_lower:
        return "liquidity sweep"
    if "order block" in text_lower or "ob" in text_lower:
        return "order block"
    if "supply" in text_lower or "demand" in text_lower:
        return "supply/demand zone"
    if "resistance" in text_lower or "support" in text_lower:
        return "support/resistance"
    
    return "unspecified"


def update_partial_lesson(message: str, partial: Dict[str, Any]) -> Dict[str, Any]:
    """
    Incrementally extract BOS/POI from user messages.
    
    Args:
        message: User's current message
        partial: Existing partial lesson dict to update
        
    Returns:
        Updated partial lesson dict
    """
    if not message or not message.strip():
        return partial
    
    # Ensure partial is a dict
    if not isinstance(partial, dict):
        partial = {}
    
    text = normalize_number(message.lower())
    
    # Extract BOS (Break of Structure)
    # Patterns: "BOS from 1.1450 to 1.1480", "BOS 1.1450-1.1480", "break from 1.1450 to 1.1480"
    bos_patterns = [
        r"bos.*?(?:from|between|at)\s*(\d+\.?\d*)\s*(?:to|and|-)\s*(\d+\.?\d*)",
        r"bos\s*(\d+\.?\d*)\s*(?:to|-)\s*(\d+\.?\d*)",
        r"break.*?(?:from|between|at)\s*(\d+\.?\d*)\s*(?:to|and|-)\s*(\d+\.?\d*)",
        r"structure.*?(?:from|between|at)\s*(\d+\.?\d*)\s*(?:to|and|-)\s*(\d+\.?\d*)",
    ]
    
    for pattern in bos_patterns:
        bos_match = re.search(pattern, text, re.IGNORECASE)
        if bos_match:
            try:
                start_val = float(bos_match.group(1))
                end_val = float(bos_match.group(2))
                # Ensure start < end
                if start_val > end_val:
                    start_val, end_val = end_val, start_val
                partial["bos"] = {"start": start_val, "end": end_val}
                break
            except (ValueError, IndexError):
                continue
    
    # Extract POI (Price of Interest)
    # Patterns: "POI at 1.1440-1.1452", "POI 1.1440 to 1.1452", "zone 1.1440-1.1452"
    poi_patterns = [
        r"poi.*?(?:at|between|from)\s*(\d+\.?\d*)\s*(?:to|and|-)\s*(\d+\.?\d*)",
        r"poi\s*(\d+\.?\d*)\s*(?:to|-)\s*(\d+\.?\d*)",
        r"(?:zone|area|level).*?(?:at|between|from)\s*(\d+\.?\d*)\s*(?:to|and|-)\s*(\d+\.?\d*)",
        r"price.*?(?:of|at|between)\s*(?:interest)?.*?(\d+\.?\d*)\s*(?:to|and|-)\s*(\d+\.?\d*)",
    ]
    
    for pattern in poi_patterns:
        poi_match = re.search(pattern, text, re.IGNORECASE)
        if poi_match:
            try:
                low_val = float(poi_match.group(1))
                high_val = float(poi_match.group(2))
                # Ensure low < high
                if low_val > high_val:
                    low_val, high_val = high_val, low_val
                
                # Check if this POI already exists (avoid duplicates)
                existing_pois = partial.get("poi", [])
                is_duplicate = False
                for existing in existing_pois:
                    if abs(existing.get("low", 0) - low_val) < 0.0001 and abs(existing.get("high", 0) - high_val) < 0.0001:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    poi_entry = {
                        "low": low_val,
                        "high": high_val,
                        "reason": extract_reason(text)
                    }
                    if "poi" not in partial:
                        partial["poi"] = []
                    partial["poi"].append(poi_entry)
                break
            except (ValueError, IndexError):
                continue
    
    # Extract bias (bullish/bearish)
    if any(x in text for x in ["bullish", "bull", "long", "up", "buy"]):
        partial["bias"] = "bullish"
    elif any(x in text for x in ["bearish", "bear", "short", "down", "sell"]):
        partial["bias"] = "bearish"
    
    # Update confidence hint based on fields present
    confidence = partial.get("confidence_hint", 0.5)
    if partial.get("bos"):
        confidence += 0.2
    if partial.get("poi") and len(partial.get("poi", [])) > 0:
        confidence += 0.2
    if partial.get("bias"):
        confidence += 0.1
    
    # Cap at 0.9 (final validation comes from Phase 5D Vision check)
    partial["confidence_hint"] = min(0.9, confidence)
    
    # Store raw lesson text (accumulate)
    if "lesson_text" not in partial:
        partial["lesson_text"] = ""
    partial["lesson_text"] += " " + message
    partial["lesson_text"] = partial["lesson_text"].strip()
    
    return partial


def build_clarifying_question(missing_fields: List[str]) -> Optional[str]:
    """
    Build a clarifying question based on missing fields.
    
    Args:
        missing_fields: List of field names that are missing
        
    Returns:
        Question string, or None if nothing is missing
    """
    if not missing_fields:
        return random.choice([
            "Anything else to add before saving?",
            "Would you like to preview this setup?",
            "Ready to save this lesson?",
            "All set! Ready to save?"
        ])
    
    qmap = {
        "bos": "Can you specify which candles or price range formed your BOS (Break of Structure)?",
        "poi": "Where is your POI (Price of Interest) range? Please give me a price zone.",
        "bias": "Is this setup bullish or bearish?",
        "reason": "What's the reason for this POI? (e.g., imbalance, order block, liquidity sweep)"
    }
    
    # Prioritize most important missing fields
    priority_order = ["bos", "poi", "bias", "reason"]
    for field in priority_order:
        if field in missing_fields:
            return qmap.get(field, f"Could you clarify the {field}?")
    
    # Fallback for any other missing field
    return qmap.get(missing_fields[0], "Could you clarify that part?")


def get_missing_fields(partial_lesson: Dict[str, Any]) -> List[str]:
    """
    Determine which fields are missing from a partial lesson.
    
    Args:
        partial_lesson: Partial lesson dict
        
    Returns:
        List of missing field names
    """
    missing = []
    
    # BOS is important
    if not partial_lesson.get("bos"):
        missing.append("bos")
    
    # POI is important
    if not partial_lesson.get("poi") or len(partial_lesson.get("poi", [])) == 0:
        missing.append("poi")
    else:
        # Check if any POI is missing a reason
        for poi in partial_lesson.get("poi", []):
            if not poi.get("reason") or poi.get("reason") == "unspecified":
                if "reason" not in missing:
                    missing.append("reason")
    
    # Bias is helpful but not critical
    if not partial_lesson.get("bias"):
        missing.append("bias")
    
    return missing


