"""
Chart Reconstruction Orchestrator
Main CLI tool to render all imported trades as candlestick charts
"""

import json
import time
import argparse
from pathlib import Path
from data_utils import fetch_price_data
from renderer import render_trade_chart, create_summary_chart


def render_all(limit=None, delay=8, skip_existing=True):
    """
    Render charts for all imported trades
    
    Args:
        limit: Maximum number of trades to render (None = all)
        delay: Delay between requests in seconds (default: 8)
        skip_existing: Skip trades that already have charts (default: True)
        
    Returns:
        dict with statistics about rendering process
    """
    # Paths
    base_dir = Path(__file__).parent.parent
    data_path = base_dir / "data" / "imported_trades.json"
    output_dir = base_dir / "data" / "charts"
    meta_path = base_dir / "data" / "chart_metadata.json"
    retry_path = base_dir / "data" / "retry_queue.json"
    
    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load trades
    if not data_path.exists():
        print(f"[ERROR] No trades found at {data_path}")
        print("[INFO] Please import trades first using POST /trades/import")
        return {"status": "error", "message": "No trades to render"}
    
    try:
        trades = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to load trades: {e}")
        return {"status": "error", "message": str(e)}
    
    if not trades:
        print("[WARN] No trades found in imported_trades.json")
        return {"status": "warning", "message": "No trades to render"}
    
    # Load existing metadata if skip_existing is True
    existing_ids = set()
    if skip_existing and meta_path.exists():
        try:
            existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            existing_ids = {m["trade_id"] for m in existing_meta}
            print(f"[INFO] Found {len(existing_ids)} existing charts, will skip")
        except Exception as e:
            print(f"[WARN] Could not load existing metadata: {e}")
    
    # Apply limit
    trades_to_render = trades[:limit] if limit else trades
    total = len(trades_to_render)
    
    print("\n" + "=" * 60)
    print(f"CHART RECONSTRUCTION - Phase 4D.1")
    print("=" * 60)
    print(f"Total trades to process: {total}")
    print(f"Output directory: {output_dir}")
    print(f"Delay between requests: {delay}s")
    print("=" * 60 + "\n")
    
    # Tracking
    rendered = []
    failed = []
    skipped = []
    
    # Process each trade
    for i, trade in enumerate(trades_to_render, 1):
        trade_id = trade.get("id")
        symbol = trade.get("symbol", "Unknown")
        entry_time = trade.get("entry_time", "")
        
        print(f"\n[{i}/{total}] Processing {symbol} (ID: {trade_id})")
        print(f"         Entry: {entry_time}")
        
        # Skip if already rendered
        if skip_existing and trade_id in existing_ids:
            print(f"[SKIP] Chart already exists for trade {trade_id}")
            skipped.append(trade_id)
            continue
        
        # Fetch price data
        df = fetch_price_data(symbol, entry_time)
        
        # Render chart
        if not df.empty:
            img_path = render_trade_chart(trade, df, output_dir)
            
            if img_path:
                rendered.append({
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "chart_path": img_path,
                    "rendered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "candles": len(df)
                })
                print(f"[SUCCESS] Chart saved: {Path(img_path).name}")
            else:
                failed.append({
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "reason": "Render failed"
                })
                print(f"[FAILED] Could not render chart")
        else:
            failed.append({
                "trade_id": trade_id,
                "symbol": symbol,
                "reason": "No price data available"
            })
            print(f"[FAILED] No price data available")
        
        # Progress bar (simple ASCII for Windows compatibility)
        pct = (i / total) * 100
        progress_bar = "#" * int(pct // 2) + "-" * (50 - int(pct // 2))
        print(f"[PROGRESS] {progress_bar} {pct:.1f}% ({i}/{total})")
        
        # Rate limiting delay (skip on last iteration)
        if i < total:
            print(f"[WAIT] Sleeping {delay}s to respect rate limits...")
            time.sleep(delay)
    
    # Create summary chart
    print("\n" + "=" * 60)
    print("Creating summary performance chart...")
    summary_path = create_summary_chart(trades, output_dir)
    
    # Save metadata and retry queue
    if rendered:
        meta_path.write_text(json.dumps(rendered, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[SAVED] Metadata: {meta_path}")
    
    if failed:
        retry_path.write_text(json.dumps(failed, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[SAVED] Retry queue: {retry_path}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("RENDERING COMPLETE")
    print("=" * 60)
    print(f"[SUCCESS] Rendered: {len(rendered)} charts")
    if skipped:
        print(f"[SKIPPED] Already exist: {len(skipped)} charts")
    if failed:
        print(f"[FAILED] {len(failed)} charts")
        print(f"         Check retry_queue.json for details")
    if summary_path:
        print(f"[SUMMARY] Performance chart: {summary_path}")
    print(f"[OUTPUT] Charts location: {output_dir}")
    print("=" * 60 + "\n")
    
    return {
        "status": "completed",
        "rendered": len(rendered),
        "skipped": len(skipped),
        "failed": len(failed),
        "total": total,
        "output_dir": str(output_dir)
    }


def retry_failed(delay=10):
    """
    Retry rendering charts that previously failed
    
    Args:
        delay: Delay between retry attempts in seconds
        
    Returns:
        dict with retry statistics
    """
    base_dir = Path(__file__).parent.parent
    retry_path = base_dir / "data" / "retry_queue.json"
    data_path = base_dir / "data" / "imported_trades.json"
    
    if not retry_path.exists():
        print("[INFO] No retry queue found")
        return {"status": "nothing_to_retry"}
    
    # Load retry queue
    failed_trades = json.loads(retry_path.read_text(encoding="utf-8"))
    failed_ids = {t["trade_id"] for t in failed_trades}
    
    # Load all trades
    all_trades = json.loads(data_path.read_text(encoding="utf-8"))
    trades_to_retry = [t for t in all_trades if t["id"] in failed_ids]
    
    print(f"\n[RETRY] Found {len(trades_to_retry)} failed trades to retry")
    
    if not trades_to_retry:
        return {"status": "nothing_to_retry"}
    
    # Re-render with longer delay
    return render_all(limit=None, delay=delay, skip_existing=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render candlestick charts for imported trades"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of trades to render (default: all)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=8,
        help="Delay between requests in seconds (default: 8)"
    )
    parser.add_argument(
        "--retry",
        action="store_true",
        help="Retry only failed charts from previous run"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-render existing charts"
    )
    
    args = parser.parse_args()
    
    if args.retry:
        result = retry_failed(delay=args.delay)
    else:
        result = render_all(
            limit=args.limit,
            delay=args.delay,
            skip_existing=not args.force
        )
    
    # Exit with appropriate code
    exit(0 if result["status"] in ["completed", "nothing_to_retry"] else 1)

