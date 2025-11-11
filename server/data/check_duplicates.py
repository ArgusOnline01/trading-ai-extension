"""Check for duplicate trade IDs across Combine 2 pages."""

import json
from pathlib import Path

data_dir = Path(__file__).parent
all_ids = {}

# Collect all trade IDs
for page_num in range(1, 11):
    json_file = data_dir / f"combine2_page{page_num}.json"
    if json_file.exists():
        with open(json_file, 'r') as f:
            trades = json.load(f)
            for trade in trades:
                trade_id = trade['trade_id']
                if trade_id in all_ids:
                    print(f"DUPLICATE: Trade ID {trade_id} found in both page {all_ids[trade_id]} and page {page_num}")
                else:
                    all_ids[trade_id] = page_num

print(f"\nTotal unique trade IDs: {len(all_ids)}")
print("No duplicates found!" if len(all_ids) == sum(len(json.load(open(data_dir / f"combine2_page{i}.json"))) for i in range(1, 11) if (data_dir / f"combine2_page{i}.json").exists()) else "Some duplicates may exist")

