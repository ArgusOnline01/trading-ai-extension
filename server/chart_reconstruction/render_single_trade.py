"""
Quick script to re-render a single trade for testing
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.session import SessionLocal
from db.models import Trade
from chart_reconstruction.data_utils import fetch_price_data
from chart_reconstruction.renderer import render_trade_chart


def render_single_trade(trade_id: str):
    """Render a single trade by trade_id"""
    db = SessionLocal()
    
    try:
        # Find the trade
        trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
        
        if not trade:
            print(f"[ERROR] Trade {trade_id} not found in database")
            return
        
        print(f"\n{'='*60}")
        print(f"RENDERING SINGLE TRADE")
        print(f"{'='*60}")
        print(f"Trade ID: {trade.trade_id}")
        print(f"Symbol: {trade.symbol}")
        print(f"Entry Time: {trade.entry_time}")
        print(f"Exit Time: {trade.exit_time}")
        print(f"Direction: {trade.direction}")
        print(f"Entry Price: {trade.entry_price}")
        print(f"Exit Price: {trade.exit_price}")
        print(f"P&L: {trade.pnl}")
        print(f"{'='*60}\n")
        
        if not trade.entry_time or not trade.symbol:
            print("[ERROR] Trade missing entry_time or symbol")
            return
        
        # Fetch price data
        print(f"[FETCH] Fetching price data for {trade.symbol}...")
        df = fetch_price_data(trade.symbol, trade.entry_time)
        
        if df.empty:
            print("[ERROR] No price data available")
            return
        
        print(f"[SUCCESS] Fetched {len(df)} candles")
        print(f"[INFO] Data range: {df.index[0]} to {df.index[-1]}")
        
        # Convert trade to dict format expected by renderer
        charts_dir = Path(__file__).parent.parent / "data" / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        trade_dict = {
            "id": trade.trade_id,
            "symbol": trade.symbol,
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "entry_price": trade.entry_price,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "exit_price": trade.exit_price,
            "direction": trade.direction,
            "pnl": trade.pnl
        }
        
        # Render chart
        print(f"\n[RENDER] Rendering chart...")
        img_path = render_trade_chart(trade_dict, df, charts_dir)
        
        if img_path:
            # Update chart_url in database
            chart_filename = f"{trade.symbol}_5m_{trade.trade_id}.png"
            chart_url = f"/charts/{chart_filename}"
            trade.chart_url = chart_url
            db.add(trade)
            db.commit()
            
            print(f"\n[SUCCESS] Chart rendered: {img_path}")
            print(f"[SUCCESS] Chart URL: {chart_url}")
        else:
            print("[ERROR] Failed to render chart")
    
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python render_single_trade.py <trade_id>")
        print("Example: python render_single_trade.py 1540212786")
        sys.exit(1)
    
    trade_id = sys.argv[1]
    render_single_trade(trade_id)

