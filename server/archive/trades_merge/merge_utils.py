import json
from pathlib import Path
from datetime import datetime
from amn_teaching.teach_utils import create_baseline_teaching_stub
from amn_teaching.dataset_compiler import compile_master_dataset
from .vision_linker import find_chart_for_trade

# FIX: Resolve data dir relative to this file
DATA = Path(__file__).parent.parent / "data"
IMPORT_FILE = DATA / "imported_trades.json"
PERF_FILE = DATA / "performance_logs.json"

def load_json(path):
    if Path(path).exists():
        return json.loads(Path(path).read_text())
    return []

def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2))

def merge_trade_by_id(trade_id, label=None):
    try:
        print(f"[MERGE] Requested merge for trade_id={trade_id} (type: {type(trade_id)})")
        imported = load_json(IMPORT_FILE)
        perf     = load_json(PERF_FILE)
        ids = [int(t["id"]) for t in imported]
        print(f"[MERGE] Candidate imported trade IDs: {ids}")
        match = next((t for t in imported if int(t["id"]) == int(trade_id)), None)
        if not match:
            print(f"[MERGE] Trade {trade_id} not found in imported IDs: {ids}")
            return {"success": False, "message": f"Trade {trade_id} not found", "ids": ids}
        
        # Check if already merged
        if match.get("merged"):
            return {"success": False, "message": f"Trade {trade_id} already merged"}
        
        # Mark as merged and add metadata
        match["label"] = label or ("win" if match["pnl"] > 0 else "loss")
        match["merged"] = True
        match["chart_path"] = find_chart_for_trade(match["symbol"], match["id"])
        
        # Save updated imported_trades.json with merged flag
        save_json(IMPORT_FILE, imported)
        
        # Add to performance logs
        perf.append(match)
        save_json(PERF_FILE, perf)
        
        # Create teaching stub and recompile dataset
        create_baseline_teaching_stub(match)
        compile_master_dataset()
        
        print_summary([match])
        return {"success": True, "message": f"Merged trade {trade_id}"}
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[MERGE][ERROR] Exception during merging: {tb}")
        return {"success": False, "error": str(e), "traceback": tb}

def auto_merge_all():
    imported = load_json(IMPORT_FILE)
    pending = [t for t in imported if not t.get("merged")]
    if not pending:
        return {"success": False, "message": "No pending trades"}
    results = []
    for trade in pending:
        results.append(merge_trade_by_id(trade["id"]))
    print_summary(pending)
    return {"success": True, "count": len(pending)}

def get_merge_preview(trade_id):
    """
    Preview what will happen when merging a trade (Phase 4D.2 requirement)
    Shows trade details, calculated label, chart path if available, etc.
    """
    try:
        imported = load_json(IMPORT_FILE)
        match = next((t for t in imported if int(t["id"]) == int(trade_id)), None)
        if not match:
            return {"success": False, "message": f"Trade {trade_id} not found in imported trades"}
        
        # Check if already merged
        if match.get("merged"):
            return {"success": False, "message": f"Trade {trade_id} already merged"}
        
        # Calculate what label will be assigned
        auto_label = "win" if match["pnl"] > 0 else ("loss" if match["pnl"] < 0 else "breakeven")
        
        # Check for chart availability
        chart_path = find_chart_for_trade(match["symbol"], match["id"])
        
        preview = {
            "success": True,
            "trade_id": match["id"],
            "symbol": match["symbol"],
            "direction": match["direction"],
            "entry_price": match["entry_price"],
            "exit_price": match["exit_price"],
            "pnl": match["pnl"],
            "auto_label": auto_label,
            "chart_available": chart_path is not None,
            "chart_path": chart_path,
            "will_create_teaching_stub": True,
            "will_add_to_performance_logs": True,
            "will_update_training_dataset": True
        }
        
        return preview
    except Exception as e:
        return {"success": False, "error": str(e)}

def print_summary(trades):
    total = len(trades)
    wins  = len([t for t in trades if t["pnl"] > 0])
    losses= len([t for t in trades if t["pnl"] < 0])
    breakeven = total - wins - losses
    avg_pnl = sum(t["pnl"] for t in trades)/total if total else 0
    print("\n============================================================")
    print(f"[MERGE SUMMARY]  {datetime.now().strftime('%H:%M:%S')}")
    print(f" Trades merged: {total}")
    print(f" Wins: {wins} | Losses: {losses} | Breakeven: {breakeven}")
    print(f" Avg PnL: ${avg_pnl:,.2f}")
    print(f" Teaching examples created: {total}")
    print(" Dataset auto-compiled -> training_dataset.json")
    print("============================================================\n")
