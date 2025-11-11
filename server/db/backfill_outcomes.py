"""
Script to backfill missing outcome values for existing trades.
Calculates outcome from PnL: win (PnL > 0), loss (PnL < 0), breakeven (PnL == 0).
"""

from db.session import SessionLocal
from db.maintenance import backfill_trades


def main():
    """Backfill missing outcomes for all trades."""
    print("Backfilling missing outcomes for existing trades...")
    
    with SessionLocal() as db:
        result = backfill_trades(db)
        
        print(f"\n[SUCCESS] Backfill complete!")
        print(f"  Updated outcomes: {result['outcome']} trades")
        print(f"  Updated entry times: {result['entry_time']} trades")


if __name__ == "__main__":
    main()

