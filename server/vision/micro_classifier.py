"""
Phase 4 Micro-Shift Classifier Scaffold
---------------------------------------
Classifies micro_shift (true/false) on 1m snapshots.
Currently uses filename hint; replace with real vision/prompt model.
"""
from pathlib import Path
from typing import Optional
import re
from .extract import vision_complete


def classify_micro(image_path: Path) -> Optional[bool]:
    """
    Micro_shift classifier.
    - First tries filename convention: trade-XX-1m-true/false.png
    - If not present, uses OpenAI Vision to classify per our rule.
    """
    m = re.search(r"-1m-(true|false)", image_path.name.lower())
    if m:
        return m.group(1) == "true"
    # Vision-based fallback
    prompt = (
        "Decide if this 1m chart shows a valid micro structure shift per our rule: a CHOCH/BOS on 1m confirming a real "
        "directional change (not just any trivial swing break). Only say true if the micro BOS/CHOCH meets the rule. "
        "Respond with JSON: {\"micro_shift\": true/false, \"direction\": \"long|short|unknown\"}."
    )
    txt = vision_complete(prompt, image_path)
    if not txt:
        return None
    import json
    try:
        data = json.loads(txt)
        return bool(data.get("micro_shift")) if isinstance(data, dict) else None
    except Exception:
        return None


if __name__ == "__main__":
    p = Path("server/data/Vision_image_dataset/trade-01-1m-false.png")
    print(p, classify_micro(p))
