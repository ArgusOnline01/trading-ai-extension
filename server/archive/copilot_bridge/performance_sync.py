import json, os
from statistics import mean

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def load_json(file_name):
    path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except Exception: return []

def summarize_performance():
    trades = load_json("performance_logs.json")
    total = len(trades)
    if total == 0:
        return {"summary": "No trades logged yet."}
    wins = [t for t in trades if t.get("pnl",0) > 0]
    losses = [t for t in trades if t.get("pnl",0) < 0]
    breakeven = total - len(wins) - len(losses)
    win_rate = round(len(wins)/total*100,1)
    rrlist = [t.get("r_multiple", t.get("rr",0)) for t in trades]
    avg_rr = round(mean(rrlist),2) if rrlist else 0
    best = max(trades, key=lambda x: x.get("r_multiple", x.get("rr",0)))
    return {
        "total": total,
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": breakeven,
        "win_rate": win_rate,
        "avg_rr": avg_rr,
        "best_setup": best.get("setup_type","Unknown"),
    }

def list_teaching_examples(limit=10):
    examples = load_json("training_dataset.json")
    return examples[-limit:] if examples else []

def get_example_by_id(trade_id):
    examples = load_json("training_dataset.json")
    for e in examples:
        if str(e.get("trade_id")) == str(trade_id):
            return e
    return None
