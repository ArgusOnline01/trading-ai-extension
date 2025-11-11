"""
Batch import script for Combine 2 - imports all pages at once.
"""

import sys
from pathlib import Path

# Add parent directory to path to import db module
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.import_from_screenshots import import_from_json_file

def main():
    """Import all Combine 2 pages."""
    data_dir = Path(__file__).parent
    combine_name = "Combine 2"
    
    # List of pages to import (all 19 pages)
    pages = list(range(1, 20))  # Pages 1-19
    
    total_imported = 0
    total_updated = 0
    total_skipped = 0
    errors = []
    
    print(f"Importing Combine 2 trades...")
    print(f"Pages to import: {pages}\n")
    
    for page_num in pages:
        json_file = data_dir / f"combine2_page{page_num}.json"
        
        if not json_file.exists():
            print(f"[SKIP] Page {page_num}: File not found: {json_file.name}")
            continue
        
        print(f"Importing page {page_num}...")
        result = import_from_json_file(json_file, combine_name)
        
        if result["success"]:
            total_imported += result["imported"]
            total_updated += result["updated"]
            total_skipped += result["skipped"]
            print(f"  [OK] Imported: {result['imported']}, Updated: {result['updated']}, Skipped: {result['skipped']}")
            if result.get("errors"):
                errors.extend(result["errors"])
        else:
            print(f"  [ERROR] Error: {result.get('error', 'Unknown error')}")
            errors.append(f"Page {page_num}: {result.get('error', 'Unknown error')}")
    
    print(f"\n{'='*50}")
    print(f"[SUMMARY] Combine 2 Import Complete")
    print(f"  Total Imported: {total_imported} trades")
    print(f"  Total Updated: {total_updated} trades")
    print(f"  Total Skipped: {total_skipped} trades")
    if errors:
        print(f"\n[WARNING] Errors ({len(errors)}):")
        for error in errors[:10]:  # Show first 10 errors
            print(f"    - {error}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()

