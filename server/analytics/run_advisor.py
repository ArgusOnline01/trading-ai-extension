#!/usr/bin/env python
"""
Phase 3 advisor CLI helper.

Usage:
  source venv/bin/activate && python server/analytics/run_advisor.py --row-json path/to/row.json --remaining-drawdown 500

The JSON should be a single object with the annotation fields (see ANNOTATION_CSV_GUIDE).
Minimum helpful fields: trade_id, symbol, direction, entry_time, poi_low, poi_high, fractal_target, micro_shift (true/false),
entry_method, contracts. If entry/sl/tp are missing, the advisor will fall back to POI mid for entry and POI low for SL.
"""
import argparse
import json
from pathlib import Path

import importlib.util

# Lightweight imports to avoid loading server.analytics __init__ (which depends on db/routes)
BASE_PATH = Path(__file__).resolve().parent

def _load_module(name: str, rel: str):
    mod_path = BASE_PATH / rel
    spec = importlib.util.spec_from_file_location(name, mod_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore
    return module

_risk = _load_module("risk_utils_mod", "risk_utils.py")
_score = _load_module("advisor_scoring_mod", "advisor_scoring.py")
compute_risk = _risk.compute_risk  # type: ignore
score_trade = _score.score_trade  # type: ignore


def main():
    parser = argparse.ArgumentParser(description="Run Entry Lab advisor on a single row JSON.")
    parser.add_argument("--row-json", type=str, required=True, help="Path to a JSON file with one setup row.")
    parser.add_argument("--remaining-drawdown", type=float, default=500.0, help="Remaining drawdown buffer (for risk cap calc).")
    parser.add_argument("--risk-cap-pct", type=float, default=0.10, help="Risk cap as fraction of remaining drawdown.")
    parser.add_argument("--require-grade", type=str, default="A+", help="Minimum grade to allow enter (A+/A/B/C).")
    parser.add_argument("--require-micro", action="store_true", help="Require micro_shift to be true to allow enter.")
    args = parser.parse_args()

    row_path = Path(args.row_json)
    if not row_path.exists():
        raise SystemExit(f"Row JSON not found: {row_path}")
    with row_path.open("r", encoding="utf-8") as f:
        row = json.load(f)

    def evaluate_local(row, remaining_drawdown=500.0, risk_cap_pct=0.10, require_grade="A+", require_micro=False):
        """Local copy of evaluate_setup to avoid heavy imports."""
        resp = {"decision": "wait", "reason": [], "grade": None, "score": None}
        g = score_trade(row)
        grade = g["grade"]
        resp.update(g)

        micro_shift = row.get("micro_shift")
        if isinstance(micro_shift, str):
            micro_shift = micro_shift.lower() == "true"

        entry = row.get("entry_price")
        sl = row.get("sl") or row.get("stop_loss") or row.get("poi_low")
        tp = row.get("tp") or row.get("fractal_target")
        if entry is None and row.get("poi_low") is not None and row.get("poi_high") is not None:
            entry = (row["poi_low"] + row["poi_high"]) / 2.0

        contracts = row.get("contracts") or 1.0
        symbol = row.get("symbol") or row.get("ContractName") or ""

        risk_info = compute_risk(entry, sl, tp, symbol, contracts=contracts)
        resp["risk"] = risk_info

        risk_cap = remaining_drawdown * risk_cap_pct if remaining_drawdown is not None else None
        over_risk = risk_cap is not None and risk_info.get("risk_usd") is not None and risk_info["risk_usd"] > risk_cap
        if over_risk:
            resp["reason"].append(f"Risk {risk_info['risk_usd']:.2f} exceeds cap {risk_cap:.2f}")

        grade_order = ["C", "B", "A", "A+"]
        required_idx = grade_order.index(require_grade) if require_grade in grade_order else len(grade_order) - 1
        grade_idx = grade_order.index(grade) if grade in grade_order else -1
        if grade_idx < required_idx:
            resp["reason"].append(f"Grade {grade} below required {require_grade}")

        if require_micro and not micro_shift:
            resp["reason"].append("Micro shift missing; gating to wait/skip")

        if over_risk or grade_idx < required_idx or (require_micro and not micro_shift):
            resp["decision"] = "skip"
        else:
            resp["decision"] = "enter"

        return resp


    resp = evaluate_local(
        row,
        remaining_drawdown=args.remaining_drawdown,
        risk_cap_pct=args.risk_cap_pct,
        require_grade=args.require_grade,
        require_micro=args.require_micro,
    )
    print(json.dumps(resp, indent=2))


if __name__ == "__main__":
    main()
