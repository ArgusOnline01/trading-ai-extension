"""
Diagnostic script to check trade data in the database.
Shows trades with PnL but no outcome, and trades with outcome but no PnL.
"""

from db.session import SessionLocal
from db.models import Trade


def main():
    """Check trade data for inconsistencies."""
    with SessionLocal() as db:
        all_trades = db.query(Trade).all()
        
        trades_with_pnl_no_outcome = []
        trades_with_outcome_no_pnl = []
        trades_with_both = []
        trades_with_neither = []
        
        for t in all_trades:
            has_pnl = t.pnl is not None
            has_outcome = t.outcome is not None
            
            if has_pnl and not has_outcome:
                trades_with_pnl_no_outcome.append(t)
            elif has_outcome and not has_pnl:
                trades_with_outcome_no_pnl.append(t)
            elif has_pnl and has_outcome:
                trades_with_both.append(t)
            else:
                trades_with_neither.append(t)
        
        print(f"Total trades: {len(all_trades)}")
        print(f"\nTrades with PnL but no outcome: {len(trades_with_pnl_no_outcome)}")
        if trades_with_pnl_no_outcome:
            print("  Examples:")
            for t in trades_with_pnl_no_outcome[:5]:
                print(f"    - Trade {t.trade_id}: PnL={t.pnl}, Outcome={t.outcome}")
        
        print(f"\nTrades with outcome but no PnL: {len(trades_with_outcome_no_pnl)}")
        if trades_with_outcome_no_pnl:
            print("  Examples:")
            for t in trades_with_outcome_no_pnl[:5]:
                print(f"    - Trade {t.trade_id}: PnL={t.pnl}, Outcome={t.outcome}")
        
        print(f"\nTrades with both PnL and outcome: {len(trades_with_both)}")
        print(f"Trades with neither: {len(trades_with_neither)}")
        
        # Check for outcome/PnL mismatches
        mismatches = []
        for t in trades_with_both:
            if t.pnl > 0 and t.outcome != "win":
                mismatches.append((t.trade_id, t.pnl, t.outcome, "should be win"))
            elif t.pnl < 0 and t.outcome != "loss":
                mismatches.append((t.trade_id, t.pnl, t.outcome, "should be loss"))
            elif t.pnl == 0 and t.outcome != "breakeven":
                mismatches.append((t.trade_id, t.pnl, t.outcome, "should be breakeven"))
        
        print(f"\nTrades with PnL/outcome mismatches: {len(mismatches)}")
        if mismatches:
            print("  Examples:")
            for trade_id, pnl, outcome, expected in mismatches[:5]:
                print(f"    - Trade {trade_id}: PnL={pnl}, Outcome={outcome} ({expected})")


if __name__ == "__main__":
    main()

