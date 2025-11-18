import json
from pathlib import Path
from typing import Dict, Any

SUMMARY_JSON = Path(__file__).resolve().parent.parent / "data" / "entry_lab_rules_summary.json"

def load_rule_stats(path: Path = SUMMARY_JSON) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}
