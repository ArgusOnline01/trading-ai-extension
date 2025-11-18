"""
Risk utilities for Entry Lab advisor.
Computes dollar risk/R multiple using per-symbol tick specs.
Extend this table if you add more products.
"""

from typing import Optional

# Tick specs: tick_size and dollars per tick per contract.
TICK_SPECS = {
    "MNQ": {"tick_size": 0.25, "tick_value": 0.5},
    "NQ": {"tick_size": 0.25, "tick_value": 5.0},
    "GC": {"tick_size": 0.1, "tick_value": 10.0},
    "MGC": {"tick_size": 0.1, "tick_value": 1.0},
    "SIL": {"tick_size": 0.005, "tick_value": 5.0},
    "SI": {"tick_size": 0.005, "tick_value": 25.0},
    "MCL": {"tick_size": 0.01, "tick_value": 4.0},
    "CL": {"tick_size": 0.01, "tick_value": 10.0},
    "6E": {"tick_size": 0.00005, "tick_value": 6.25},  # per tick; two ticks = 0.0001 = $12.50
    "M6E": {"tick_size": 0.00005, "tick_value": 4.375},
}


def normalize_symbol(symbol: str) -> str:
    """Strip month/year codes and map to base symbol key."""
    if not symbol:
        return ""
    sym = symbol.upper()
    # remove last 2 chars if last char is digit (e.g., MNQZ5 -> MNQ)
    if len(sym) > 2 and sym[-1].isdigit():
        sym = sym[:-2]
    return sym


def get_tick_specs(symbol: str) -> Optional[dict]:
    return TICK_SPECS.get(normalize_symbol(symbol))


def compute_risk(entry: float, sl: float, tp: Optional[float], symbol: str, contracts: float = 1.0):
    """
    Compute dollar risk, R multiple, and tick specs given entry/sl/tp.
    entry, sl, tp are prices. contracts can be fractional if desired.
    Returns dict with risk_usd, tick_value, tick_size, r_multiple (if tp given), move (abs entry-sl), ticks (abs move/tick_size).
    """
    specs = get_tick_specs(symbol)
    if specs is None or entry is None or sl is None:
        return {"risk_usd": None, "tick_value": None, "tick_size": None, "r_multiple": None, "move": None, "ticks": None}
    tick_size = specs["tick_size"]
    tick_value = specs["tick_value"]
    move = abs(entry - sl)
    ticks = move / tick_size if tick_size else None
    risk_usd = (ticks * tick_value * contracts) if ticks is not None else None
    r_mult = None
    if tp is not None and risk_usd:
        reward_ticks = abs(tp - entry) / tick_size
        reward_usd = reward_ticks * tick_value * contracts
        if risk_usd != 0:
            r_mult = reward_usd / risk_usd
    return {
        "risk_usd": risk_usd,
        "tick_value": tick_value,
        "tick_size": tick_size,
        "ticks": ticks,
        "r_multiple": r_mult,
        "move": move,
    }
