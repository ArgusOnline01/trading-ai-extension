"""
Phase 4C: Adaptive Learning Engine
Makes the AI Copilot learn from user's trading performance and adapt advice automatically.
"""

from fastapi import APIRouter
from datetime import datetime
import json
import os
from pathlib import Path
import statistics
from typing import Dict, Any, List

# Phase 4D.3: Unify paths to server/data and reuse normalized logs from performance.utils
DATA_DIR = Path(__file__).parent.parent / "data"
LOG_PATH = str(DATA_DIR / "performance_logs.json")
PROFILE_PATH = str(DATA_DIR / "user_profile.json")

learning_router = APIRouter(prefix="/learning", tags=["Learning"])


def _load_json(path: str) -> List[Dict[str, Any]]:
    """Load JSON file with error handling"""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_json(path: str, data: Dict[str, Any]):
    """Save JSON file with proper formatting"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_learning_profile() -> Dict[str, Any]:
    """
    Analyze performance logs and generate an adaptive learning profile.
    This profile is injected into the AI's system prompt to personalize advice.
    """
    # Use the normalized reader from performance.utils to ensure outcomes/R are present
    try:
        from .utils import read_logs
        logs = read_logs()
    except Exception:
        logs = _load_json(LOG_PATH)
    total = len(logs)
    
    # Initialize empty profile
    if total == 0:
        profile = {
            "total_trades": 0,
            "win_rate": 0.0,
            "best_setup": "None yet",
            "worst_setup": "None yet",
            "avg_rr": 0.0,
            "setup_performance": {},
            "bias_performance": {"Bullish": 0.0, "Bearish": 0.0},
            "common_mistakes": [],
            "recent_trend": {"win_rate_change": 0.0, "rr_change": 0.0},
            "last_updated": datetime.utcnow().isoformat()
        }
        _save_json(PROFILE_PATH, profile)
        return profile
    
    # Calculate win rate
    wins = [t for t in logs if t.get("outcome") == "win"]
    losses = [t for t in logs if t.get("outcome") == "loss"]
    completed = len(wins) + len(losses)
    win_rate = (len(wins) / completed) if completed > 0 else 0.0
    
    # Calculate average R:R (approximate if missing using median absolute loss baseline)
    neg = [abs(t.get("pnl", 0)) for t in logs if isinstance(t.get("pnl"), (int, float)) and t.get("pnl", 0) < 0]
    base = statistics.median(neg) if neg else None
    def derive_r(t):
        r = t.get("r_multiple")
        if r is None and base and isinstance(t.get("pnl"), (int, float)):
            r = round(t["pnl"] / base, 2)
        return r
    r_values = [derive_r(t) for t in logs if derive_r(t) is not None]
    avg_rr = statistics.mean(r_values) if r_values else 0.0
    
    # Group by setup type
    setups = {}
    for t in logs:
        setup = t.get("setup_type", "Unknown")
        if setup not in setups:
            setups[setup] = []
        r = derive_r(t)
        if r is not None:
            setups[setup].append(r)
    
    # Calculate average R per setup
    setup_perf = {}
    for setup, values in setups.items():
        if values:
            setup_perf[setup] = round(statistics.mean(values), 2)
    
    # Group by bias (Bullish/Bearish)
    bias = {"Bullish": [], "Bearish": []}
    for t in logs:
        b = t.get("bias", "Bullish")
        if b not in bias:
            bias[b] = []
        r = derive_r(t)
        if r is not None:
            bias[b].append(r)
    
    bias_perf = {}
    for b, values in bias.items():
        if values:
            bias_perf[b] = round(statistics.mean(values), 2)
    
    # Identify best and worst setups
    best_setup = max(setup_perf, key=setup_perf.get) if setup_perf else "None yet"
    worst_setup = min(setup_perf, key=setup_perf.get) if setup_perf else "None yet"
    
    # Calculate recent trend (last 10 vs previous 10 trades)
    recent = logs[-10:] if len(logs) >= 10 else logs
    prev = logs[-20:-10] if len(logs) >= 20 else []
    
    def _win_rate(lst):
        if not lst:
            return 0.0
        wins = len([t for t in lst if t.get("outcome") == "win"])
        completed = len([t for t in lst if t.get("outcome") in ["win", "loss"]])
        return (wins / completed) if completed > 0 else 0.0
    
    def _avg_rr(lst):
        vals = [t.get("r_multiple", 0) for t in lst if t.get("r_multiple") is not None]
        return statistics.mean(vals) if vals else 0.0
    
    trend = {
        "win_rate_change": round((_win_rate(recent) - _win_rate(prev)) * 100, 1),
        "rr_change": round(_avg_rr(recent) - _avg_rr(prev), 2)
    }
    
    # Identify common mistakes (setups with negative R)
    common_mistakes = [
        f"{setup} ({r}R avg)" 
        for setup, r in setup_perf.items() 
        if r < 0
    ]
    
    # Build profile
    profile = {
        "total_trades": total,
        "completed_trades": completed,
        "win_rate": round(win_rate, 3),
        "best_setup": best_setup,
        "worst_setup": worst_setup,
        "avg_rr": round(avg_rr, 2),
        "setup_performance": setup_perf,
        "bias_performance": bias_perf,
        "common_mistakes": common_mistakes,
        "recent_trend": trend,
        "last_updated": datetime.utcnow().isoformat()
    }
    
    _save_json(PROFILE_PATH, profile)
    print(f"[LEARNING] Profile updated: {total} trades, {win_rate*100:.1f}% win rate, best: {best_setup}")
    
    return profile


@learning_router.get("/profile")
async def get_profile():
    """
    Get current learning profile
    Returns the AI's learned knowledge about user's trading performance
    """
    profile = _load_json(PROFILE_PATH)
    if not profile:
        profile = generate_learning_profile()
    return profile


@learning_router.post("/update")
async def update_profile():
    """
    Manually trigger profile regeneration
    Useful after logging multiple trades
    """
    profile = generate_learning_profile()
    return {
        "status": "updated",
        "profile": profile
    }


@learning_router.post("/reset")
async def reset_profile():
    """
    Reset learning profile to defaults
    Useful for starting fresh or testing
    """
    default_profile = {
        "total_trades": 0,
        "completed_trades": 0,
        "win_rate": 0.0,
        "best_setup": "None yet",
        "worst_setup": "None yet",
        "avg_rr": 0.0,
        "setup_performance": {},
        "bias_performance": {"Bullish": 0.0, "Bearish": 0.0},
        "common_mistakes": [],
        "recent_trend": {"win_rate_change": 0.0, "rr_change": 0.0},
        "last_updated": None
    }
    
    _save_json(PROFILE_PATH, default_profile)
    print("[LEARNING] Profile reset to defaults")
    
    return {
        "status": "reset",
        "profile": default_profile
    }


def get_learning_context() -> str:
    """
    Generate a concise learning context string to inject into AI prompts.
    Kept under 300 tokens to minimize API cost.
    """
    profile = _load_json(PROFILE_PATH)
    
    if not profile or profile.get("total_trades", 0) == 0:
        return ""
    
    # Build adaptive context
    total = profile.get("total_trades", 0)
    completed = profile.get("completed_trades", 0)
    win_rate = profile.get("win_rate", 0) * 100
    best = profile.get("best_setup", "Unknown")
    worst = profile.get("worst_setup", "Unknown")
    avg_r = profile.get("avg_rr", 0)
    trend = profile.get("recent_trend", {})
    
    # Determine performance level
    if win_rate >= 60:
        level = "strong"
    elif win_rate >= 50:
        level = "solid"
    elif win_rate >= 40:
        level = "developing"
    else:
        level = "needs improvement"
    
    # Build context string
    context = f"\n🎯 USER PERFORMANCE PROFILE:\n"
    context += f"- Track record: {completed}/{total} trades completed ({win_rate:.1f}% win rate - {level})\n"
    context += f"- Average R:R: {avg_r:.2f}\n"
    context += f"- Strongest setup: {best}"
    
    if best in profile.get("setup_performance", {}):
        context += f" (+{profile['setup_performance'][best]:.2f}R avg)\n"
    else:
        context += "\n"
    
    if worst != "None yet" and worst in profile.get("setup_performance", {}):
        worst_r = profile['setup_performance'][worst]
        if worst_r < 0:
            context += f"- Struggling with: {worst} ({worst_r:.2f}R avg)\n"
    
    # Add trend analysis
    rr_change = trend.get("rr_change", 0)
    if abs(rr_change) > 0.5:
        direction = "improving" if rr_change > 0 else "declining"
        context += f"- Recent trend: {direction} ({rr_change:+.2f}R change)\n"
    
    context += "\n💡 ADAPT YOUR ADVICE BASED ON THIS DATA.\n"
    
    return context

