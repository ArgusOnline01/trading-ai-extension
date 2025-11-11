"""
Script to backfill missing outcome values and estimate exit times for existing trades.
- Calculates outcome from PnL: win (PnL > 0), loss (PnL < 0), breakeven (PnL == 0)
- Estimates exit time for trades with PnL but no exit_time
"""

from datetime import timedelta
from sqlalchemy import func
from db.session import SessionLocal
from db.models import Trade


def backfill_trades(db):
    """Backfill missing outcomes and estimate exit times for existing trades."""
    updated_outcome = 0
    updated_exit_time = 0
    
    # First, calculate average trade duration for exit time estimation
    trades_with_duration = db.query(Trade).filter(
        Trade.entry_time.isnot(None),
        Trade.exit_time.isnot(None),
        Trade.pnl.isnot(None)
    ).all()
    
    durations = []
    for t in trades_with_duration:
        if t.entry_time and t.exit_time:
            duration = t.exit_time - t.entry_time
            if duration.total_seconds() > 0:
                durations.append(duration.total_seconds())
    
    if durations:
        avg_seconds = sum(durations) / len(durations)
        estimated_duration = min(avg_seconds, 24 * 3600)  # Cap at 24 hours
    else:
        estimated_duration = 2 * 3600  # Default: 2 hours
    
    # Process all trades
    for t in db.query(Trade).all():
        changed = False
        
        # Recalculate outcome from PnL (always recalculate to fix inconsistencies)
        if t.pnl is not None:
            if t.pnl > 0:
                new_outcome = "win"
            elif t.pnl < 0:
                new_outcome = "loss"
            else:
                new_outcome = "breakeven"
            
            # Always update outcome from PnL to ensure consistency
            if t.outcome != new_outcome:
                t.outcome = new_outcome
                updated_outcome += 1
                changed = True
        elif t.outcome is not None:
            # If PnL is None but outcome is set, clear the outcome
            t.outcome = None
            updated_outcome += 1
            changed = True
        
        # Estimate exit time for trades with PnL but no exit_time
        if t.pnl is not None and t.exit_time is None and t.entry_time:
            estimated_exit = t.entry_time + timedelta(seconds=estimated_duration)
            t.exit_time = estimated_exit
            updated_exit_time += 1
            changed = True
        
        if changed:
            db.add(t)
    
    db.commit()
    return {"outcome": updated_outcome, "exit_time": updated_exit_time}


def main():
    """Backfill missing outcomes and exit times for all trades."""
    print("Backfilling missing outcomes and exit times for existing trades...")
    
    with SessionLocal() as db:
        result = backfill_trades(db)
        
        print(f"\n[SUCCESS] Backfill complete!")
        print(f"  Updated outcomes: {result['outcome']} trades")
        print(f"  Estimated exit times: {result['exit_time']} trades")


if __name__ == "__main__":
    main()

