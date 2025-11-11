"""Check for duplicate trade IDs across all Combine 2 pages."""

import json
from pathlib import Path
from collections import defaultdict

data_dir = Path(__file__).parent
all_ids = defaultdict(list)

# Collect all trade IDs
for page_num in range(1, 20):
    json_file = data_dir / f"combine2_page{page_num}.json"
    if json_file.exists():
        with open(json_file, 'r') as f:
            trades = json.load(f)
            for trade in trades:
                trade_id = trade['trade_id']
                all_ids[trade_id].append(page_num)

# Find duplicates
duplicates = {tid: pages for tid, pages in all_ids.items() if len(pages) > 1}

if duplicates:
    print("DUPLICATES FOUND:")
    for trade_id, pages in duplicates.items():
        print(f"  Trade ID {trade_id} found in pages: {pages}")
else:
    print("No duplicates found!")

# Count trades per page
print(f"\nTrades per page:")
for page_num in range(1, 20):
    json_file = data_dir / f"combine2_page{page_num}.json"
    if json_file.exists():
        with open(json_file, 'r') as f:
            trades = json.load(f)
            print(f"  Page {page_num}: {len(trades)} trades")

print(f"\nTotal unique trade IDs: {len(all_ids)}")
total_trades = sum(len(json.load(open(data_dir / f"combine2_page{i}.json"))) for i in range(1, 20) if (data_dir / f"combine2_page{i}.json").exists())
print(f"Total trades (including duplicates): {total_trades}")

