#!/usr/bin/env python3
"""
View import summary statistics
"""
import requests
import json

# Get stats
stats = requests.get("http://127.0.0.1:8765/trades/stats").json()

print("\n" + "=" * 60)
print("IMPORTED TRADES SUMMARY")
print("=" * 60)
print(f"Total Trades: {stats['total']}")
print(f"Merged: {stats['merged']}")
print(f"Pending: {stats['pending']}")
print(f"Symbols: {', '.join(stats['symbols'])}")
print("=" * 60)

# Get first 10 trades
trades = requests.get("http://127.0.0.1:8765/trades/imported?limit=31").json()

wins = sum(1 for t in trades['trades'] if (t['pnl'] or 0) > 0)
losses = sum(1 for t in trades['trades'] if (t['pnl'] or 0) < 0)
breakevens = stats['total'] - (wins + losses)

total_pnl = sum((t['pnl'] or 0) for t in trades['trades'])
avg_pnl = total_pnl / stats['total'] if stats['total'] > 0 else 0
win_rate = (wins / stats['total'] * 100) if stats['total'] > 0 else 0

print(f"\nWins: {wins}")
print(f"Losses: {losses}")
print(f"Breakevens: {breakevens}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Total PnL: ${total_pnl:,.2f}")
print(f"Avg PnL: ${avg_pnl:,.2f}")

# Per-symbol performance
from collections import defaultdict

pnl_per_symbol = defaultdict(list)
for t in trades['trades']:
    pnl_per_symbol[t['symbol']].append(t['pnl'] or 0)

avg_per_symbol = {
    sym: sum(vals) / len(vals)
    for sym, vals in pnl_per_symbol.items() if vals
}

print("\n" + "-" * 60)
print("Per-Contract Performance:")
print("-" * 60)

for sym, val in sorted(avg_per_symbol.items(), key=lambda x: -x[1]):
    status = "PROFIT" if val > 0 else "LOSS"
    print(f"{sym:10s} ${val:+8.2f}  ({status})")

print("=" * 60)
print("\nImport successful! Data ready for Phase 4D.2 merge.")
print("=" * 60 + "\n")

