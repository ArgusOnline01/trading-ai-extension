from fastapi import APIRouter
import json, os, statistics
from datetime import datetime
from .utils import read_logs

router = APIRouter(prefix="/performance")

@router.get("/dashboard-data")
async def dashboard_data():
    """
    Aggregate performance data for dashboard visualization
    Returns time-series win rate, setup performance, and outcome distribution
    """
    logs = read_logs()
    
    if not logs:
        return {
            "dates": [],
            "win_rates": [],
            "setups": [],
            "avg_r": [],
            "outcomes": {"win": 0, "loss": 0, "breakeven": 0}
        }
    
    # Sort by timestamp
    logs_sorted = sorted(logs, key=lambda x: x.get("timestamp", ""))
    
    # Initialize counters
    dates, win_rates = [], []
    wins, losses, breakeven = 0, 0, 0
    setup_perf = {}  # {setup_type: [r_multiples]}
    
    # Calculate rolling win rate and aggregate setup performance
    for i, trade in enumerate(logs_sorted, start=1):
        outcome = trade.get("outcome")
        
        # Count outcomes
        if outcome == "win":
            wins += 1
        elif outcome == "loss":
            losses += 1
        elif outcome == "breakeven":
            breakeven += 1
        
        # Calculate rolling win rate (only for completed trades)
        completed = wins + losses + breakeven
        if completed > 0:
            win_rate = round((wins / completed) * 100, 1)
        else:
            win_rate = 0
        
        win_rates.append(win_rate)
        
        # Extract date from timestamp (YYYY-MM-DD)
        timestamp = trade.get("timestamp", "")
        date = timestamp[:10] if timestamp else f"Trade {i}"
        dates.append(date)
        
        # Aggregate setup performance
        setup = trade.get("setup_type", "Unknown")
        if setup not in setup_perf:
            setup_perf[setup] = []
        
        # Only include completed trades with R multiple
        if trade.get("r_multiple") is not None:
            setup_perf[setup].append(trade["r_multiple"])
    
    # Calculate average R per setup
    avg_r_by_setup = {}
    for setup, r_values in setup_perf.items():
        if r_values:
            avg_r_by_setup[setup] = round(statistics.mean(r_values), 2)
    
    outcomes = {
        "win": wins,
        "loss": losses,
        "breakeven": breakeven
    }
    
    print(f"[DASHBOARD] Loaded {len(logs)} trades | Wins: {wins}, Losses: {losses}, BE: {breakeven}")
    
    return {
        "dates": dates,
        "win_rates": win_rates,
        "setups": list(avg_r_by_setup.keys()),
        "avg_r": list(avg_r_by_setup.values()),
        "outcomes": outcomes
    }

