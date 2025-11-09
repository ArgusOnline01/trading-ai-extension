"""
Fix Bad Charts - Re-render specific charts that came out bad
Usage: python fix_bad_charts.py --trade-ids 1486940457 1499163878
"""

import json
import time
import argparse
from pathlib import Path
import sys

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from chart_reconstruction.data_utils import fetch_price_data
from chart_reconstruction.renderer import render_trade_chart
from db.session import SessionLocal
from db.models import Trade


def fix_charts(trade_ids, delay=8):
    """
    Re-render charts for specific trade IDs
    
    Args:
        trade_ids: List of trade IDs to re-render
        delay: Delay between requests in seconds
    """
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "data" / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 60)
        print("FIXING BAD CHARTS")
        print("=" * 60)
        print(f"Trade IDs to fix: {trade_ids}")
        print(f"Output directory: {output_dir}")
        print("=" * 60 + "\n")
        
        fixed = []
        failed = []
        
        for i, trade_id in enumerate(trade_ids, 1):
            print(f"\n[{i}/{len(trade_ids)}] Processing trade {trade_id}")
            
            # Get trade from database
            trade = db.query(Trade).filter(Trade.trade_id == str(trade_id)).first()
            if not trade:
                print(f"[ERROR] Trade {trade_id} not found in database")
                failed.append({
                    "trade_id": trade_id,
                    "reason": "Trade not found in database"
                })
                continue
            
            # Convert trade to dict format expected by renderer
            trade_dict = {
                "id": trade.trade_id,
                "symbol": trade.symbol,
                "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
                "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                "entry_price": float(trade.entry_price) if trade.entry_price else None,
                "exit_price": float(trade.exit_price) if trade.exit_price else None,
                "direction": trade.direction,
                "pnl": float(trade.pnl) if trade.pnl else 0
            }
            
            if not trade_dict["entry_time"]:
                print(f"[ERROR] Trade {trade_id} has no entry_time")
                failed.append({
                    "trade_id": trade_id,
                    "reason": "No entry_time"
                })
                continue
            
            print(f"         Symbol: {trade_dict['symbol']}")
            print(f"         Entry: {trade_dict['entry_time']}")
            
            # Fetch price data
            df = fetch_price_data(trade_dict["symbol"], trade_dict["entry_time"])
            
            if df.empty:
                print(f"[FAILED] No price data available")
                failed.append({
                    "trade_id": trade_id,
                    "symbol": trade_dict["symbol"],
                    "reason": "No price data available"
                })
                continue
            
            # Delete old chart if exists
            old_chart = output_dir / f"{trade_dict['symbol']}_5m_{trade_id}.png"
            if old_chart.exists():
                old_chart.unlink()
                print(f"[DELETED] Old chart: {old_chart.name}")
            
            # Render new chart
            img_path = render_trade_chart(trade_dict, df, output_dir)
            
            if img_path:
                fixed.append({
                    "trade_id": trade_id,
                    "symbol": trade_dict["symbol"],
                    "chart_path": img_path,
                    "rendered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "candles": len(df)
                })
                print(f"[SUCCESS] Chart saved: {Path(img_path).name}")
            else:
                failed.append({
                    "trade_id": trade_id,
                    "symbol": trade_dict["symbol"],
                    "reason": "Render failed"
                })
                print(f"[FAILED] Could not render chart")
            
            # Rate limiting delay (skip on last iteration)
            if i < len(trade_ids):
                print(f"[WAIT] Sleeping {delay}s to respect rate limits...")
                time.sleep(delay)
        
        # Final summary
        print("\n" + "=" * 60)
        print("FIXING COMPLETE")
        print("=" * 60)
        print(f"[SUCCESS] Fixed: {len(fixed)} charts")
        if failed:
            print(f"[FAILED] {len(failed)} charts")
            for f in failed:
                print(f"         Trade {f['trade_id']}: {f['reason']}")
        print("=" * 60 + "\n")
        
        return {
            "status": "completed",
            "fixed": len(fixed),
            "failed": len(failed),
            "fixed_charts": fixed,
            "failed_charts": failed
        }
        
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Re-render specific bad charts"
    )
    parser.add_argument(
        "--trade-ids",
        nargs="+",
        required=True,
        help="Trade IDs to re-render (e.g., --trade-ids 1486940457 1499163878)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=8,
        help="Delay between requests in seconds (default: 8)"
    )
    
    args = parser.parse_args()
    
    result = fix_charts(args.trade_ids, delay=args.delay)
    
    exit(0 if result["status"] == "completed" and result["failed"] == 0 else 1)



