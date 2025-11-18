import json
from pathlib import Path

# Unified data path resolution
DATA_DIR = Path(__file__).parent.parent / "data" / "amn_training_examples"
OUT_FILE = Path(__file__).parent.parent / "data" / "training_dataset.json"

def compile_master_dataset():
    examples = [json.loads(f.read_text()) for f in DATA_DIR.glob("*.json")]
    OUT_FILE.write_text(json.dumps(examples, indent=2))
    print(f"[DATASET] Compiled {len(examples)} examples -> training_dataset.json")
