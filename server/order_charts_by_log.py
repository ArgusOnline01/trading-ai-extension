import json
from pathlib import Path
import shutil

base = Path(__file__).parent / 'data'
trade_log_file = base / 'imported_trades.json'
chart_meta_file = base / 'chart_metadata.json'
ordered_dir = base / 'ordered_charts'

# Ensure output dir exists
ordered_dir.mkdir(exist_ok=True)

# Load logs and metadata
with open(trade_log_file, encoding='utf-8') as f:
    trades = json.load(f)
with open(chart_meta_file, encoding='utf-8') as f:
    charts = {str(c['trade_id']): c['chart_path'] for c in json.load(f)}

copied = 0
for n, trade in enumerate(trades, 1):
    tid = str(trade['id'])
    if tid in charts:
        src = Path(charts[tid])
        if src.exists():
            dest = ordered_dir / f"trade_{n:02d}.png"
            shutil.copy2(src, dest)
            print(f"Copied: {src.name} -> {dest.name}")
            copied += 1
        else:
            print(f"WARNING: Not found for trade id {tid!r}: {src}")
    else:
        print(f"WARNING: No chart for trade id {tid!r}")

print(f"\nDone. {copied} chart images copied to {ordered_dir}\n")
