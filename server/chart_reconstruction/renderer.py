"""
Chart Renderer - Generate Annotated Candlestick Charts
Uses mplfinance to create beautiful trading charts with entry/exit markers
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.dates as mdates
import pytz

CHICAGO_TZ = pytz.timezone("America/Chicago")

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
        entry_original = pd.to_datetime(trade.get("entry_time"))
        exit_original = pd.to_datetime(trade.get("exit_time")) if trade.get("exit_time") else None

        if entry_original.tzinfo is None:
            entry_local = CHICAGO_TZ.localize(entry_original)
        else:
            entry_local = entry_original.tz_convert(CHICAGO_TZ)
        entry_time = entry_local.tz_localize(None)

        if exit_original is not None:
            if exit_original.tzinfo is None:
                exit_local = CHICAGO_TZ.localize(exit_original)
            else:
                exit_local = exit_original.tz_convert(CHICAGO_TZ)
            exit_time = exit_local.tz_localize(None)
        else:
            exit_local = None
            exit_time = None

        # Ensure data index is localized to Chicago
        if getattr(data.index, 'tz', None) is not None:
            data = data.copy()
            data.index = data.index.tz_convert(CHICAGO_TZ).tz_localize(None)
        else:
            data.index = pd.to_datetime(data.index)

        addplots = []
        # DO NOT draw horizontal price lines
        # Mark entry/exit candles with triangle markers below
        direction = trade.get("direction", "").upper()
        pnl = trade.get("pnl", 0)
        pnl_str = f"${pnl:+.2f}" if pnl else "$0.00"
        
        # Title formatting uses original local time
        local_display = entry_original
        if local_display.tzinfo is None:
            local_display = local_display.tz_localize("America/New_York")
        local_display_str = local_display.strftime("%m/%d/%Y %H:%M:%S %z")

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
            title=f"{trade['symbol']} | {direction} | {local_display_str} (5m) | P&L: {pnl_str}",
            volume=False,  # Remove volume to fix jagged rendering
            returnfig=True,
            figsize=(16, 9),
            warn_too_much_data=2500,  # Set threshold higher than our max (2000 candles)
            tight_layout=True
        )
        
        ax = axlist[0] if isinstance(axlist, list) else axlist
        # Triangle markers for entry/exit
        is_short = direction.upper() == "SHORT"

        index_np = data.index.to_numpy(dtype='datetime64[ns]')

        def compute_x(dt):
            if dt is None:
                return None
            t = pd.to_datetime(dt)
            t_np = t.to_datetime64()
            idx = np.searchsorted(index_np, t_np) - 1
            if idx < 0:
                idx = 0
            if idx >= len(data):
                idx = len(data) - 1
            base_time = data.index[idx]
            if idx + 1 < len(data):
                next_time = data.index[idx + 1]
            else:
                next_time = base_time + (base_time - data.index[idx - 1]) if idx > 0 else base_time
            if next_time > base_time:
                frac = (t - base_time) / (next_time - base_time)
                frac = max(0, min(1, frac))
            else:
                frac = 0
            return idx + float(frac)

        def plot_marker(dt, price, color, marker, offset_pixels=0):
            if dt is None or price is None:
                return
            x = compute_x(dt)
            if x is None:
                return
            x_disp, y_disp = ax.transData.transform((x, price))
            y_disp -= offset_pixels
            x_new, y_new = ax.transData.inverted().transform((x_disp, y_disp))
            ax.scatter(
                [x_new],
                [y_new],
                marker=marker,
                s=90,
                c=color,
                edgecolors='#FFFFFF',
                linewidths=1.2,
                zorder=30,
                clip_on=False,
            )

        long_offset = 18  # pixels downward
        short_offset = -18  # pixels upward

        # Entry marker (blue)
        if entry_time is not None:
            try:
                entry_dt = pd.to_datetime(entry_time)
                x_pos = compute_x(entry_dt)
                idx = min(int(np.floor(x_pos)), len(data) - 1)
                bar = data.iloc[idx]
                print(f"[DEBUG] Selected entry candle at index {idx}, time: {data.index[idx]}")
                if is_short:
                    price = bar['High'] + (bar['High'] - bar['Low']) * 0.05
                    plot_marker(entry_dt, price, '#2962FF', 'v', offset_pixels=short_offset)
                else:
                    price = bar['Low'] - (bar['High'] - bar['Low']) * 0.05
                    plot_marker(entry_dt, price, '#2962FF', '^', offset_pixels=long_offset)
            except Exception as e:
                print(f"[WARN] Could not place entry marker: {e}")
                import traceback
                traceback.print_exc()

        # Exit marker (red)
        if exit_time is not None:
            try:
                exit_dt = pd.to_datetime(exit_time)
                x_pos = compute_x(exit_dt)
                idx = min(int(np.floor(x_pos)), len(data) - 1)
                bar = data.iloc[idx]
                print(f"[DEBUG] Selected exit candle at index {idx}, time: {data.index[idx]}")
                distance = bar['High'] - bar['Low']
                offset = -distance * 0.25
                price = bar['Low'] - distance * 0.1
                exit_marker = 'v' if is_short else '^'
                if is_short:
                    price = bar['Low'] - (bar['High'] - bar['Low']) * 0.05
                    plot_marker(exit_dt, price, '#F23645', 'v', offset_pixels=long_offset)
                else:
                    price = bar['Low'] - (bar['High'] - bar['Low']) * 0.05
                    plot_marker(exit_dt, price, '#F23645', '^', offset_pixels=long_offset)
            except Exception as e:
                print(f"[WARN] Could not place exit marker: {e}")
                import traceback
                traceback.print_exc()
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

