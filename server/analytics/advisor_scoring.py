"""
Advisor scoring/gating helpers for Phase 3.

We assign a simple score/grade to each setup so the advisor can filter to A+ only by default.
You can extend the weights/criteria as you add more tags.
"""

from typing import Dict, Any


def score_trade(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a simple score/grade for a trade annotation row.
    Current criteria (weights are additive):
      - POI present: +2
      - Fractal target present: +1
      - Micro structure shift (micro_shift == True): +3
      - IFVG present: +1
      - Session in {London, Asia}: +1
    Grades:
      A+ (7-8), A (5-6), B (3-4), C (<3)
    """
    score = 0

    # POI present
    if row.get("poi_low") is not None and row.get("poi_high") is not None:
        score += 2

    # Fractal target present
    if row.get("fractal_target") is not None:
        score += 1

    # Micro structure shift flag
    micro_shift = row.get("micro_shift")
    if isinstance(micro_shift, str):
        micro_shift = micro_shift.lower() == "true"
    if micro_shift:
        score += 3

    # IFVG present
    if row.get("ifvg_present"):
        score += 1

    # Session bonus
    if row.get("session") in {"London", "Asia"}:
        score += 1

    if score >= 7:
        grade = "A+"
    elif score >= 5:
        grade = "A"
    elif score >= 3:
        grade = "B"
    else:
        grade = "C"

    return {"score": score, "grade": grade}
