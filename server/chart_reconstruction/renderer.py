"""
Chart Renderer - Generate Annotated Candlestick Charts
Uses mplfinance to create beautiful trading charts with entry/exit markers
"""

from pathlib import Path
import pandas as pd

# Try to import required libraries
try:
    import mplfinance as mpf
    MPLFINANCE_AVAILABLE = True
except ImportError:
    MPLFINANCE_AVAILABLE = False
    print("[WARN] mplfinance not installed. Run: pip install mplfinance")

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[WARN] matplotlib not installed. Run: pip install matplotlib")


def render_trade_chart(trade, data, output_dir):
    """
    Render annotated 5-minute candlestick chart for a trade
    With TradingView style, zoom, vertical/time markers, and entry/exit dots/labels.
    """
    if not MPLFINANCE_AVAILABLE or not MATPLOTLIB_AVAILABLE:
        print("[ERROR] Required libraries not installed")
        return None
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = f"{trade['symbol']}_5m_{trade['id']}.png"
    chart_path = output_path / filename
    if data.empty:
        print(f"[SKIP] No data for trade {trade['id']} ({trade['symbol']})")
        return None
    try:
        entry_price = trade.get("entry_price")
        exit_price = trade.get("exit_price")
        entry_time = pd.to_datetime(trade.get("entry_time"))
        exit_time = pd.to_datetime(trade.get("exit_time")) if trade.get("exit_time") else None
        
        # Fix timezone issues - ensure both entry_time and data.index are timezone-aware or naive
        if entry_time.tz is not None:
            entry_time = entry_time.tz_localize(None) if entry_time.tz is not None else entry_time
        if exit_time is not None and exit_time.tz is not None:
            exit_time = exit_time.tz_localize(None)
        
        # Ensure data index is timezone-naive for comparison
        if data.index.tz is not None:
            data = data.copy()
            data.index = data.index.tz_localize(None)
        
        addplots = []
        # DO NOT draw horizontal price lines
        # Mark entry/exit candles with triangle markers below
        direction = trade.get("direction", "").upper()
        pnl = trade.get("pnl", 0)
        pnl_str = f"${pnl:+.2f}" if pnl else "$0.00"
        title = f"{trade['symbol']} | {direction} | {trade.get('entry_time', '')} (5m) | P&L: {pnl_str}"
        mc = mpf.make_marketcolors(
            up='#26a69a',
            down='#ef5350',
            edge='inherit',
            wick='inherit',
            volume='in',
            alpha=0.9
        )
        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridcolor='#2B2B43',
            gridstyle=':',
            y_on_right=False,
            facecolor='#131722',
            figcolor='#131722',
            edgecolor='#2B2B43',
            rc={
                'axes.labelcolor': '#D1D4DC',
                'axes.edgecolor': '#2B2B43',
                'xtick.color': '#787B86',
                'ytick.color': '#787B86',
                'text.color': '#D1D4DC',
                'font.size': 10,
                'lines.antialiased': True,
                'patch.antialiased': True,
            }
        )
        # Original zoom logic: Use data as-is, let mplfinance handle the display
        # Clean data: remove duplicates and sort
        data = data[~data.index.duplicated(keep='first')].sort_index()
        
        # Use all available data (original behavior)
        focused_data = data.copy()
        
        # Print debug info
        hours_span = (focused_data.index[-1] - focused_data.index[0]).total_seconds() / 3600
        print(f"[CHART] Rendering {len(focused_data)} candles ({hours_span:.1f} hours span)")
        
        # Render without volume panel to avoid jagged appearance
        fig, axlist = mpf.plot(
            focused_data,
            type="candle",
            style=s,
            title=title,
            volume=False,  # Remove volume to fix jagged rendering
            returnfig=True,
            figsize=(16, 9),
            warn_too_much_data=2500,  # Set threshold higher than our max (2000 candles)
            tight_layout=True
        )
        
        ax = axlist[0] if isinstance(axlist, list) else axlist
        # Triangle marker for entry/exit
        for tval, color in [
            (entry_time, '#2962FF'),
            (exit_time, '#F23645')
        ]:
            if tval is None:
                continue
            # Ensure timezone-naive for comparison
            if hasattr(tval, 'tz') and tval.tz is not None:
                tval = tval.tz_localize(None)
            idx = data.index.get_indexer([pd.to_datetime(tval)], method='nearest')[0]
            bar = data.iloc[idx]
            x = idx
            y = bar['Low'] - (bar['High']-bar['Low'])*0.11
            ax.scatter(x, y, marker='^', color=color, s=55, zorder=25, edgecolors='#fff', linewidths=1.4)
        # Save with high DPI and anti-aliasing for crisp rendering
        fig.savefig(
            str(chart_path), 
            dpi=300,  # High DPI for crisp rendering (was 150)
            bbox_inches='tight', 
            facecolor='#131722',
            edgecolor='none',
            pad_inches=0.1,
            transparent=False,
            format='png'
        )
        import matplotlib.pyplot as plt
        plt.close(fig)
        print(f"[RENDERED] {chart_path}")
        return str(chart_path)
    except Exception as e:
        print(f"[ERROR] Failed to render chart for trade {trade['id']}: {e}")
        return None


def create_summary_chart(trades, output_dir):
    """
    Create a summary visualization of all trades
    
    Args:
        trades: List of trade dicts
        output_dir: Output directory path
        
    Returns:
        str: Path to summary chart, or None if failed
    """
    if not MATPLOTLIB_AVAILABLE:
        print("[ERROR] matplotlib not installed")
        return None
    
    try:
        import matplotlib.pyplot as plt
        from collections import defaultdict
        
        # Calculate statistics
        pnl_per_symbol = defaultdict(list)
        for trade in trades:
            symbol = trade.get("symbol", "Unknown")
            pnl = trade.get("pnl", 0)
            if pnl:
                pnl_per_symbol[symbol].append(pnl)
        
        # Calculate averages
        avg_pnl = {
            sym: sum(pnls) / len(pnls)
            for sym, pnls in pnl_per_symbol.items()
        }
        
        # Sort by performance
        sorted_symbols = sorted(avg_pnl.items(), key=lambda x: x[1], reverse=True)
        symbols = [s[0] for s in sorted_symbols]
        pnls = [s[1] for s in sorted_symbols]
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#0f0f1e')
        
        colors = ['#00ff88' if p > 0 else '#ff4444' for p in pnls]
        bars = ax.bar(symbols, pnls, color=colors, edgecolor='#ffd700', linewidth=1.5)
        
        ax.axhline(y=0, color='#ffd700', linestyle='-', linewidth=0.5, alpha=0.5)
        ax.set_xlabel('Symbol', color='#ffd700', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average P&L ($)', color='#ffd700', fontsize=12, fontweight='bold')
        ax.set_title('Performance by Symbol', color='#ffd700', fontsize=16, fontweight='bold', pad=20)
        ax.tick_params(colors='#ffd700')
        ax.spines['bottom'].set_color('#ffd700')
        ax.spines['left'].set_color('#ffd700')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, alpha=0.1, color='#ffd700')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            label_y = height + (5 if height > 0 else -15)
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                label_y,
                f'${height:.2f}',
                ha='center',
                va='bottom' if height > 0 else 'top',
                color='#ffd700',
                fontsize=10,
                fontweight='bold'
            )
        
        # Save
        output_path = Path(output_dir) / "summary_performance.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, facecolor='#1a1a2e', edgecolor='none')
        plt.close()
        
        print(f"[SUMMARY] Created summary chart: {output_path}")
        return str(output_path)
    
    except Exception as e:
        print(f"[ERROR] Failed to create summary chart: {e}")
        return None

