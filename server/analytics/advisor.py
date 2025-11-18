"""
Phase 3 Advisor helper.
- Scores a setup (A+/A/B/C) using advisor_scoring.
- Computes risk using risk_utils (with a 10% remaining-drawdown cap by default).
- Selects a rule and attaches its historical stats from entry_lab_rules_summary.json.
- Emits a decision payload: enter/skip plus rationale.
"""

from typing import Dict, Any
from .advisor_scoring import score_trade
from .risk_utils import compute_risk
from .load_rule_stats import load_rule_stats

DEFAULT_RULE = "R4_counterfactual_poi50"
RULE_STATS = load_rule_stats()

def select_rule(row: Dict[str, Any]) -> str:
    em = (row.get("entry_method") or "").lower()
    # IFVG-specific rule
    if "ifvg" in em and "R5_ifvg_fractal" in RULE_STATS:
        return "R5_ifvg_fractal"
    # Micro-specific rule (based on entry_method, not just micro_shift flag)
    if "micro" in em and "R6_micro_shift" in RULE_STATS:
        return "R6_micro_shift"
    return DEFAULT_RULE if DEFAULT_RULE in RULE_STATS else (list(RULE_STATS.keys())[0] if RULE_STATS else DEFAULT_RULE)


def evaluate_setup(
    row: Dict[str, Any],
    remaining_drawdown: float = 500.0,
    risk_cap_pct: float = 0.10,
    require_grade: str = "A+",
    require_micro: bool = False,
) -> Dict[str, Any]:
    """
    Evaluate a setup dict and return decision + rationale.

    Inputs expected in row (use what you have):
      - entry_price, sl, tp (optional; falls back to POI/TP/fractal if missing)
      - poi_low/high, fractal_target
      - contracts (defaults 1.0 if missing)
      - micro_shift (bool/str) for gating
    """
    resp: Dict[str, Any] = {"decision": "wait", "reason": [], "grade": None, "score": None}

    rule = select_rule(row)
    resp["rule"] = rule
    if RULE_STATS:
        stats = RULE_STATS.get(rule, {})
        resp["rule_stats"] = stats.get("clean") or stats.get("all")

    # Grade
    g = score_trade(row)
    grade = g["grade"]
    resp.update(g)

    # Micro gate
    micro_shift = row.get("micro_shift")
    if isinstance(micro_shift, str):
        micro_shift = micro_shift.lower() == "true"

    # Normalize prices
    entry = row.get("entry_price")
    sl = row.get("sl") or row.get("stop_loss") or row.get("poi_low")  # fallback to POI extreme for SL
    tp = row.get("tp") or row.get("fractal_target")
    # If no explicit entry, default to POI mid when available
    if entry is None and row.get("poi_low") is not None and row.get("poi_high") is not None:
        entry = (row["poi_low"] + row["poi_high"]) / 2.0

    contracts = row.get("contracts") or 1.0
    symbol = row.get("symbol") or row.get("ContractName") or ""

    # Risk calc
    risk_info = compute_risk(entry, sl, tp, symbol, contracts=contracts)
    resp["risk"] = risk_info

    # Risk cap check
    risk_cap = remaining_drawdown * risk_cap_pct if remaining_drawdown is not None else None
    over_risk = risk_cap is not None and risk_info.get("risk_usd") is not None and risk_info["risk_usd"] > risk_cap
    if over_risk:
        resp["reason"].append(f"Risk {risk_info['risk_usd']:.2f} exceeds cap {risk_cap:.2f}")

    # Grade gate
    grade_order = ["C", "B", "A", "A+"]
    required_idx = grade_order.index(require_grade) if require_grade in grade_order else len(grade_order) - 1
    grade_idx = grade_order.index(grade)
    if grade_idx < required_idx:
        resp["reason"].append(f"Grade {grade} below required {require_grade}")

    if require_micro and not micro_shift:
        resp["reason"].append("Micro shift missing; gating to wait/skip")

    # Decision
    if over_risk or grade_idx < required_idx or (require_micro and not micro_shift):
        resp["decision"] = "skip"
    else:
        resp["decision"] = "enter"

    return resp
