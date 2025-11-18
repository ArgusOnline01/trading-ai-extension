"""
CSV Parser for Topstep Trader Exports
Normalizes trade data into standard JSON format
"""

import csv
import json
import os
from datetime import datetime
from collections import Counter, defaultdict

# Try to import optional dependencies
try:
    from dateutil import tz
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False
    print("[IMPORT] Warning: python-dateutil not installed. Using basic datetime parsing.")

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False
    print("[IMPORT] Note: Install 'tabulate' for pretty table output (pip install tabulate)")


# Data paths
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "imported_trades.json")


def safe_float(value):
    """Safely convert value to float, return None if invalid"""
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None


def parse_time(time_string):
    """Parse time string with timezone awareness (if dateutil available)"""
    if not time_string:
        return ""
    
    try:
        if DATEUTIL_AVAILABLE:
            # Try to parse with timezone
            tz_cst = tz.gettz("America/Chicago")
            dt = datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=tz_cst)
            return dt.isoformat()
        else:
            # Basic parsing without timezone
            dt = datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")
            return dt.isoformat()
    except Exception as e:
        # If parsing fails, return as-is
        return time_string


def normalize_trade(row):
    """
    Normalize a single trade row from Topstep CSV format
    
    Expected CSV columns:
    - Id, ContractName, EnteredAt, ExitedAt, EntryPrice, ExitPrice
    - Type (Buy/Sell), PnL, Size, Fees, Commissions, TradeDay, TradeDuration
    """
    # Calculate total fees
    fees = (safe_float(row.get("Fees")) or 0) + (safe_float(row.get("Commissions")) or 0)
    
    # Determine direction
    trade_type = row.get("Type", "").lower()
    direction = "long" if trade_type == "buy" else "short"
    
    # Clean symbol (remove slashes)
    symbol = row.get("ContractName", "").replace("/", "").strip()
    
    return {
        "id": int(row.get("Id", 0)) if row.get("Id") else 0,
        "symbol": symbol,
        "entry_time": parse_time(row.get("EnteredAt", "")),
        "exit_time": parse_time(row.get("ExitedAt", "")),
        "entry_price": safe_float(row.get("EntryPrice")),
        "exit_price": safe_float(row.get("ExitPrice")),
        "direction": direction,
        "pnl": safe_float(row.get("PnL")),
        "contracts": safe_float(row.get("Size")),
        "fees": fees,
        "trade_day": row.get("TradeDay", ""),
        "duration": row.get("TradeDuration", ""),
        "source": "topstep",
        "merged": False
    }


def print_summary(trades):
    """Print comprehensive import summary to terminal"""
    total = len(trades)
    
    if total == 0:
        print("\n[IMPORT] No trades found in CSV")
        return
    
    # Basic statistics
    wins = sum(1 for t in trades if (t["pnl"] or 0) > 0)
    losses = sum(1 for t in trades if (t["pnl"] or 0) < 0)
    breakevens = total - (wins + losses)
    avg_pnl = sum((t["pnl"] or 0) for t in trades) / total if total > 0 else 0
    total_pnl = sum((t["pnl"] or 0) for t in trades)
    
    # Contract statistics
    setup_counts = Counter(t["symbol"] for t in trades)
    common = setup_counts.most_common(5)
    
    # Per-contract performance
    pnl_per_symbol = defaultdict(list)
    for t in trades:
        pnl_per_symbol[t["symbol"]].append(t["pnl"] or 0)
    
    avg_per_symbol = {
        sym: round(sum(vals) / len(vals), 2)
        for sym, vals in pnl_per_symbol.items() if vals
    }
    
    # Print summary
    print("\n" + "=" * 60)
    print("[IMPORT SUMMARY]")
    print(f" Total Trades: {total}")
    print(f" Wins: {wins} | Losses: {losses} | Breakeven: {breakevens}")
    print(f" Win Rate: {(wins/total*100):.1f}%")
    print(f" Total PnL: ${total_pnl:,.2f}")
    print(f" Avg PnL: ${avg_pnl:,.2f}")
    print(f" Most common contracts: {', '.join([f'{s} ({n})' for s, n in common])}")
    print("-" * 60)
    print(" Avg PnL per Contract:")
    
    for sym, val in sorted(avg_per_symbol.items(), key=lambda x: -x[1])[:10]:
        # Color-coded output (green for positive, red for negative)
        color = "\033[92m" if val > 0 else "\033[91m"
        reset = "\033[0m"
        print(f"  {color}{sym}: ${val:+.2f}{reset}")
    
    print("=" * 60 + "\n")
    
    # Optional: Pretty table of first 10 trades
    if TABULATE_AVAILABLE and total > 0:
        rows = [
            [
                t["symbol"],
                t["direction"],
                f"${t['entry_price']:.2f}" if t["entry_price"] else "N/A",
                f"${t['exit_price']:.2f}" if t["exit_price"] else "N/A",
                f"${t['pnl']:.2f}" if t["pnl"] else "N/A",
                t["trade_day"]
            ]
            for t in trades[:10]
        ]
        print(tabulate(
            rows,
            headers=["Symbol", "Dir", "Entry", "Exit", "PnL", "Day"],
            tablefmt="fancy_grid"
        ))
        
        if total > 10:
            print(f"\n... {total - 10} more trades not shown ...\n")


def import_csv(file_path):
    """
    Import and normalize Topstep CSV file
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of normalized trade dicts
    """
    trades = []
    
    print(f"\n[IMPORT] Reading CSV from: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    normalized = normalize_trade(row)
                    trades.append(normalized)
                except Exception as e:
                    print(f"[IMPORT] Warning: Skipped malformed row: {e}")
                    continue
        
        print(f"[IMPORT] Successfully parsed {len(trades)} trades")
        
        # Save to JSON
        save_imported_trades(trades)
        
        # Print summary
        print_summary(trades)
        
        return trades
    
    except Exception as e:
        print(f"[IMPORT] Error reading CSV: {e}")
        raise


def save_imported_trades(trades):
    """Save normalized trades to JSON file"""
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2)
    
    print(f"[IMPORT] Saved {len(trades)} trades to: {DATA_PATH}")


def load_imported_trades():
    """Load imported trades from JSON file"""
    if not os.path.exists(DATA_PATH):
        return []
    
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[IMPORT] Error loading trades: {e}")
        return []


def get_import_stats():
    """Get statistics about imported trades"""
    trades = load_imported_trades()
    
    if not trades:
        return {
            "total": 0,
            "merged": 0,
            "pending": 0,
            "symbols": []
        }
    
    merged_count = sum(1 for t in trades if t.get("merged", False))
    symbols = list(set(t["symbol"] for t in trades))
    
    return {
        "total": len(trades),
        "merged": merged_count,
        "pending": len(trades) - merged_count,
        "symbols": sorted(symbols)
    }

