"""
Batch Chart Rendering Script
Renders charts for all trades in the database, with batch processing support
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.session import SessionLocal
from db.models import Trade
from chart_reconstruction.data_utils import fetch_price_data
from chart_reconstruction.renderer import render_trade_chart


def get_trades_without_charts(db, limit=None, offset=0):
    """
    Get trades that don't have charts yet
    
    Args:
        db: Database session
        limit: Maximum number of trades to return (None = all)
        offset: Number of trades to skip
        
    Returns:
        List of Trade objects
    """
    # Get all trades, ordered by entry_time
    query = db.query(Trade).filter(
        Trade.entry_time.isnot(None),
        Trade.symbol.isnot(None)
    ).order_by(Trade.entry_time.desc())
    
    # Check if chart file exists
    charts_dir = Path(__file__).parent.parent / "data" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    trades_to_render = []
    for trade in query.offset(offset).limit(limit) if limit else query.offset(offset):
        # Check if chart file exists
        chart_filename = f"{trade.symbol}_5m_{trade.trade_id}.png"
        chart_path = charts_dir / chart_filename
        
        if not chart_path.exists():
            trades_to_render.append(trade)
        elif not trade.chart_url:
            # Chart exists but URL not set in database - update it
            trade.chart_url = f"/charts/{chart_filename}"
            db.add(trade)
    
    db.commit()
    return trades_to_render


def render_trades_batch(db, trades, delay=8, batch_size=50, force=False):
    """
    Render charts for a batch of trades
    
    Args:
        trades: List of Trade objects
        delay: Delay between requests in seconds
        batch_size: Number of trades to process before showing summary
        
    Returns:
        dict with statistics
    """
    charts_dir = Path(__file__).parent.parent / "data" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    rendered = []
    failed = []
    skipped = []
    
    total = len(trades)
    print(f"\n{'='*60}")
    print(f"BATCH CHART RENDERING")
    print(f"{'='*60}")
    print(f"Total trades to process: {total}")
    print(f"Delay between requests: {delay}s")
    print(f"Batch size: {batch_size}")
    print(f"{'='*60}\n")
    
    for i, trade in enumerate(trades, 1):
        trade_id = trade.trade_id
        symbol = trade.symbol
        entry_time = trade.entry_time
        
        print(f"\n[{i}/{total}] Processing {symbol} (ID: {trade_id})")
        print(f"         Entry: {entry_time}")
        
        # Check if chart already exists
        chart_filename = f"{symbol}_5m_{trade_id}.png"
        chart_path = charts_dir / chart_filename
        
        if chart_path.exists() and not force:
            print(f"[SKIP] Chart already exists: {chart_filename}")
            # Update chart_url in database if not set
            if not trade.chart_url:
                trade.chart_url = f"/charts/{chart_filename}"
                db.add(trade)
                db.commit()
            skipped.append(trade_id)
            continue
        elif chart_path.exists() and force:
            print(f"[FORCE] Re-rendering existing chart: {chart_filename}")
            # Delete old chart
            chart_path.unlink()
        
        # Fetch price data
        try:
            df = fetch_price_data(symbol, entry_time)
        except Exception as e:
            print(f"[ERROR] Failed to fetch data: {e}")
            failed.append({
                "trade_id": trade_id,
                "symbol": symbol,
                "reason": f"Data fetch failed: {str(e)}"
            })
            continue
        
        # Render chart
        if not df.empty:
            try:
                # Convert trade to dict format expected by renderer
                trade_dict = {
                    "id": trade_id,
                    "symbol": symbol,
                    "entry_time": entry_time.isoformat() if entry_time else None,
                    "entry_price": trade.entry_price,
                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                    "exit_price": trade.exit_price,
                    "direction": trade.direction
                }
                
                img_path = render_trade_chart(trade_dict, df, charts_dir)
                
                if img_path:
                    # Update chart_url in database
                    chart_url = f"/charts/{chart_filename}"
                    trade.chart_url = chart_url
                    db.add(trade)
                    db.commit()
                    
                    rendered.append({
                        "trade_id": trade_id,
                        "symbol": symbol,
                        "chart_path": img_path,
                        "rendered_at": datetime.now().isoformat(),
                        "candles": len(df)
                    })
                    print(f"[SUCCESS] Chart saved: {chart_filename}")
                else:
                    failed.append({
                        "trade_id": trade_id,
                        "symbol": symbol,
                        "reason": "Render failed"
                    })
                    print(f"[FAILED] Could not render chart")
            except Exception as e:
                print(f"[ERROR] Render exception: {e}")
                failed.append({
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "reason": f"Render exception: {str(e)}"
                })
        else:
            failed.append({
                "trade_id": trade_id,
                "symbol": symbol,
                "reason": "No price data available"
            })
            print(f"[FAILED] No price data available")
        
        # Progress bar
        pct = (i / total) * 100
        progress_bar = "#" * int(pct // 2) + "-" * (50 - int(pct // 2))
        print(f"[PROGRESS] {progress_bar} {pct:.1f}% ({i}/{total})")
        
        # Rate limiting delay (skip on last iteration)
        if i < total:
            print(f"[WAIT] Sleeping {delay}s to respect rate limits...")
            time.sleep(delay)
        
        # Batch summary
        if i % batch_size == 0:
            print(f"\n{'='*60}")
            print(f"BATCH SUMMARY (after {i} trades)")
            print(f"  Rendered: {len(rendered)}")
            print(f"  Failed: {len(failed)}")
            print(f"  Skipped: {len(skipped)}")
            print(f"{'='*60}\n")
    
    # Final summary
    print(f"\n{'='*60}")
    print("RENDERING COMPLETE")
    print(f"{'='*60}")
    print(f"[SUCCESS] Rendered: {len(rendered)} charts")
    if skipped:
        print(f"[SKIPPED] Already exist: {len(skipped)} charts")
    if failed:
        print(f"[FAILED] {len(failed)} charts")
        print("\nFailed trades:")
        for f in failed[:10]:  # Show first 10
            print(f"  - {f['symbol']} (ID: {f['trade_id']}): {f['reason']}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")
    print(f"[OUTPUT] Charts location: {charts_dir}")
    print(f"{'='*60}\n")
    
    return {
        "rendered": len(rendered),
        "skipped": len(skipped),
        "failed": len(failed),
        "total": len(trades)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Render candlestick charts for all trades in the database"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of trades to render (default: all without charts)"
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of trades to skip (for batch processing)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=8,
        help="Delay between requests in seconds (default: 8)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of trades to process before showing summary (default: 50)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-render existing charts"
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        # Get trades to render
        if args.force:
            # Get all trades (will re-render existing ones)
            query = db.query(Trade).filter(
                Trade.entry_time.isnot(None),
                Trade.symbol.isnot(None)
            ).order_by(Trade.entry_time.desc())
            
            trades = query.offset(args.offset).limit(args.limit).all() if args.limit else query.offset(args.offset).all()
        else:
            # Get only trades without charts
            trades = get_trades_without_charts(db, limit=args.limit, offset=args.offset)
        
        if not trades:
            print("[INFO] No trades to render")
            print("[INFO] All trades already have charts, or no trades found")
            return
        
        # Render charts
        result = render_trades_batch(
            db,
            trades,
            delay=args.delay,
            batch_size=args.batch_size,
            force=args.force
        )
        
        print(f"\n[SUMMARY]")
        print(f"  Total processed: {result['total']}")
        print(f"  Rendered: {result['rendered']}")
        print(f"  Skipped: {result['skipped']}")
        print(f"  Failed: {result['failed']}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

