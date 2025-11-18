import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "amn_training_examples"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def create_baseline_teaching_stub(trade):
    record = {
        "trade_id": trade["id"],
        "symbol": trade["symbol"],
        "direction": trade["direction"],
        "pnl": trade["pnl"],
        "label": trade["label"],
        "chart_path": trade.get("chart_path"),
        "poi_range": None,
        "bos_range": None,
        "outcome": trade["label"],
        "explanation": "",
        "created_at": datetime.now().isoformat()
    }
    (DATA_DIR / f"{trade['id']}.json").write_text(json.dumps(record, indent=2))

def update_teaching_example(payload):
    tid = payload.get("trade_id")
    file = DATA_DIR / f"{tid}.json"
    rec = json.loads(file.read_text()) if file.exists() else {}
    rec.update(payload)
    file.write_text(json.dumps(rec, indent=2))
    from .dataset_compiler import compile_master_dataset
    compile_master_dataset()
    return {"success": True, "message": f"Updated teaching example {tid}"}
