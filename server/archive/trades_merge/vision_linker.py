from pathlib import Path

def find_chart_for_trade(symbol, trade_id):
    """Find chart image for a given trade using unified path resolution"""
    charts_dir = Path(__file__).parent.parent / "data" / "charts"
    if not charts_dir.exists():
        return None
    for f in charts_dir.glob(f"{symbol}_5m_{trade_id}*.png"):
        return str(f)
    return None
