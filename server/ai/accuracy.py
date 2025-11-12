"""
Phase 4D.3: AI Accuracy Calculation Module

Calculates how well AI's annotations match user's corrections.
"""

from typing import Dict, Any, List, Tuple
import math


def calculate_annotation_accuracy(
    ai_annotations: Dict[str, Any],
    corrected_annotations: Dict[str, Any],
    deleted_annotations: List[Dict[str, Any]] = None,
    image_width: int = 4440,
    image_height: int = 2651
) -> Dict[str, float]:
    """
    Calculate accuracy of AI annotations compared to user corrections.

    Accuracy is based on:
    1. Position accuracy (how close AI's annotations are to corrected positions)
    2. Detection accuracy (did AI identify the right number of patterns)
    3. Deletion penalty (AI created annotations that shouldn't exist)
    4. Addition penalty (AI missed patterns that should exist)

    Args:
        ai_annotations: AI's original annotations {poi: [], bos: [], circles: []}
        corrected_annotations: User's corrections {poi: [], bos: [], circles: []}
        deleted_annotations: Annotations user deleted (hallucinations)
        image_width: Chart image width in pixels
        image_height: Chart image height in pixels

    Returns:
        {
            "poi_accuracy": 0.85,
            "bos_accuracy": 0.90,
            "circles_accuracy": 0.80,
            "overall_accuracy": 0.85,
            "detection_rate": 0.90,  # How many patterns AI found
            "precision": 0.85,  # How many AI annotations were correct
            "deletion_penalty": 0.10,  # Penalty for hallucinations
            "addition_penalty": 0.15  # Penalty for missed patterns
        }
    """

    # Initialize scores
    poi_accuracy = 0.0
    bos_accuracy = 0.0
    circles_accuracy = 0.0

    # Count annotations
    ai_poi_count = len(ai_annotations.get("poi", []))
    ai_bos_count = len(ai_annotations.get("bos", []))
    ai_circles_count = len(ai_annotations.get("circles", []))
    ai_total = ai_poi_count + ai_bos_count + ai_circles_count

    # Count corrections (only actual corrections, not additions)
    corrected_poi = [p for p in corrected_annotations.get("poi", []) if isinstance(p, dict)]
    corrected_bos = [b for b in corrected_annotations.get("bos", []) if isinstance(b, dict)]
    corrected_circles = [c for c in corrected_annotations.get("circles", []) if isinstance(c, dict)]

    # Count corrections that are NOT additions (have original)
    corrections_count = sum([
        1 for p in corrected_poi if p.get("original") is not None and not p.get("added", False)
    ]) + sum([
        1 for b in corrected_bos if b.get("original") is not None and not b.get("added", False)
    ]) + sum([
        1 for c in corrected_circles if c.get("original") is not None and not c.get("added", False)
    ])

    # Count additions (user added patterns AI missed)
    additions_count = sum([
        1 for p in corrected_poi if not p.get("original") and p.get("added", False)
    ]) + sum([
        1 for b in corrected_bos if not b.get("original") and b.get("added", False)
    ]) + sum([
        1 for c in corrected_circles if not c.get("original") and c.get("added", False)
    ])

    # Count deletions (user deleted AI's annotations - hallucinations)
    deletions_count = len(deleted_annotations) if deleted_annotations else 0

    # Calculate total expected annotations (what should exist)
    # This is: AI's annotations - deletions + additions
    expected_total = ai_total - deletions_count + additions_count

    # Calculate POI accuracy
    if ai_poi_count > 0 or len(corrected_poi) > 0:
        poi_accuracy = _calculate_category_accuracy(
            ai_annotations.get("poi", []),
            corrected_poi,
            deleted_annotations,
            image_width,
            image_height,
            "poi"
        )

    # Calculate BOS accuracy
    if ai_bos_count > 0 or len(corrected_bos) > 0:
        bos_accuracy = _calculate_category_accuracy(
            ai_annotations.get("bos", []),
            corrected_bos,
            deleted_annotations,
            image_width,
            image_height,
            "bos"
        )

    # Calculate circles accuracy
    if ai_circles_count > 0 or len(corrected_circles) > 0:
        circles_accuracy = _calculate_category_accuracy(
            ai_annotations.get("circles", []),
            corrected_circles,
            deleted_annotations,
            image_width,
            image_height,
            "circles"
        )

    # Calculate overall accuracy (weighted average)
    categories_with_data = 0
    total_accuracy = 0.0

    if ai_poi_count > 0 or len(corrected_poi) > 0:
        total_accuracy += poi_accuracy
        categories_with_data += 1

    if ai_bos_count > 0 or len(corrected_bos) > 0:
        total_accuracy += bos_accuracy
        categories_with_data += 1

    if ai_circles_count > 0 or len(corrected_circles) > 0:
        total_accuracy += circles_accuracy
        categories_with_data += 1

    overall_accuracy = total_accuracy / categories_with_data if categories_with_data > 0 else 0.0

    # Calculate detection rate (how many patterns AI found out of expected)
    detection_rate = (ai_total - deletions_count) / expected_total if expected_total > 0 else 0.0
    detection_rate = max(0.0, min(1.0, detection_rate))  # Clamp to [0, 1]

    # Calculate precision (how many AI annotations were correct)
    precision = (ai_total - deletions_count) / ai_total if ai_total > 0 else 0.0
    precision = max(0.0, min(1.0, precision))

    # Calculate penalties
    deletion_penalty = deletions_count / ai_total if ai_total > 0 else 0.0
    addition_penalty = additions_count / expected_total if expected_total > 0 else 0.0

    return {
        "poi_accuracy": round(poi_accuracy, 4),
        "bos_accuracy": round(bos_accuracy, 4),
        "circles_accuracy": round(circles_accuracy, 4),
        "overall_accuracy": round(overall_accuracy, 4),
        "detection_rate": round(detection_rate, 4),
        "precision": round(precision, 4),
        "deletion_penalty": round(deletion_penalty, 4),
        "addition_penalty": round(addition_penalty, 4),
        "details": {
            "ai_total": ai_total,
            "corrections_count": corrections_count,
            "deletions_count": deletions_count,
            "additions_count": additions_count,
            "expected_total": expected_total
        }
    }


def _calculate_category_accuracy(
    ai_annotations: List[Dict[str, Any]],
    corrected_annotations: List[Dict[str, Any]],
    deleted_annotations: List[Dict[str, Any]],
    image_width: int,
    image_height: int,
    category: str
) -> float:
    """
    Calculate accuracy for a specific category (POI, BOS, or circles).

    Accuracy is based on:
    1. How close AI's positions are to corrected positions
    2. Whether AI was deleted (penalty)
    3. Whether user added new ones (penalty for missing)

    Returns accuracy score 0.0-1.0
    """

    if not ai_annotations and not corrected_annotations:
        return 1.0  # No annotations needed, perfect

    # Filter corrected annotations for this category
    corrections = [c for c in corrected_annotations if c.get("corrected")]

    # Count deletions for this category
    deleted_count = 0
    if deleted_annotations:
        for d in deleted_annotations:
            # Check if this deletion belongs to this category
            if category == "poi" and ("left" in d or "width" in d):
                deleted_count += 1
            elif category == "bos" and ("x1" in d and "x2" in d):
                deleted_count += 1
            elif category == "circles" and ("radius" in d):
                deleted_count += 1

    # Count additions for this category
    additions = [c for c in corrected_annotations if c.get("added", False) and not c.get("original")]

    if not corrections:
        # No corrections means AI was either perfect or completely wrong
        if deleted_count > 0:
            # AI created hallucinations - bad
            return 0.0
        elif len(additions) > 0:
            # AI missed patterns - bad
            return 0.0
        else:
            # No corrections, no deletions, no additions - perfect!
            return 1.0

    # Calculate position accuracy for each correction
    total_position_accuracy = 0.0

    for correction in corrections:
        original = correction.get("original", {})
        corrected = correction.get("corrected", {})

        if not original or not corrected:
            continue

        # Calculate distance between original and corrected
        if category == "poi":
            distance = _calculate_poi_distance(original, corrected, image_width, image_height)
        elif category == "bos":
            distance = _calculate_bos_distance(original, corrected, image_width, image_height)
        elif category == "circles":
            distance = _calculate_circle_distance(original, corrected, image_width, image_height)
        else:
            distance = 0.0

        # Convert distance to accuracy score (closer = higher score)
        # Use exponential decay: accuracy = e^(-distance/threshold)
        threshold = 200.0  # pixels - if correction is > 200px away, accuracy drops significantly
        position_accuracy = math.exp(-distance / threshold)
        total_position_accuracy += position_accuracy

    # Average position accuracy
    avg_position_accuracy = total_position_accuracy / len(corrections) if corrections else 0.0

    # Apply penalties
    deletion_penalty = deleted_count / (len(ai_annotations) + deleted_count) if (len(ai_annotations) + deleted_count) > 0 else 0.0
    addition_penalty = len(additions) / (len(corrections) + len(additions)) if (len(corrections) + len(additions)) > 0 else 0.0

    # Final accuracy: position accuracy - penalties
    final_accuracy = avg_position_accuracy * (1.0 - deletion_penalty * 0.5) * (1.0 - addition_penalty * 0.3)

    return max(0.0, min(1.0, final_accuracy))


def _calculate_poi_distance(original: Dict, corrected: Dict, img_w: int, img_h: int) -> float:
    """Calculate distance between original and corrected POI positions."""
    # POI is a rectangle - calculate center distance
    orig_center_x = original.get("left", 0) + original.get("width", 0) / 2
    orig_center_y = original.get("top", 0) + original.get("height", 0) / 2

    corr_center_x = corrected.get("left", 0) + corrected.get("width", 0) / 2
    corr_center_y = corrected.get("top", 0) + corrected.get("height", 0) / 2

    # Euclidean distance
    distance = math.sqrt((orig_center_x - corr_center_x)**2 + (orig_center_y - corr_center_y)**2)

    return distance


def _calculate_bos_distance(original: Dict, corrected: Dict, img_w: int, img_h: int) -> float:
    """Calculate distance between original and corrected BOS lines."""
    # BOS is a line - calculate midpoint distance
    orig_mid_x = (original.get("x1", 0) + original.get("x2", 0)) / 2
    orig_mid_y = (original.get("y1", 0) + original.get("y2", 0)) / 2

    corr_mid_x = (corrected.get("x1", 0) + corrected.get("x2", 0)) / 2
    corr_mid_y = (corrected.get("y1", 0) + corrected.get("y2", 0)) / 2

    # Euclidean distance
    distance = math.sqrt((orig_mid_x - corr_mid_x)**2 + (orig_mid_y - corr_mid_y)**2)

    return distance


def _calculate_circle_distance(original: Dict, corrected: Dict, img_w: int, img_h: int) -> float:
    """Calculate distance between original and corrected circle centers."""
    orig_x = original.get("x", 0)
    orig_y = original.get("y", 0)

    corr_x = corrected.get("x", 0)
    corr_y = corrected.get("y", 0)

    # Euclidean distance
    distance = math.sqrt((orig_x - corr_x)**2 + (orig_y - corr_y)**2)

    return distance
