# What Are "Prompt Examples"?

## Simple Explanation

**"Prompt examples"** = The actual annotations you made that get shown to the AI in the prompt.

### Current (Wrong):
When AI analyzes a chart, the prompt says:
```
Similar trades from history:
- Trade 1: 6EZ5, long, win
- Trade 2: MCL, short, loss
```

The AI only sees **metadata** (symbol, direction, outcome) but **NOT your actual annotations**.

### Fixed (Correct):
When AI analyzes a chart, the prompt will say:
```
Here are examples of how I annotated similar trades:

Example 1 - 6EZ5 long win:
- POI: Price level 1.1650 (after liquidity sweep)
- BOS: Line from 1.1640 to 1.1660 (bullish break)
- My notes: "Early long entry after liquidity sweep below local lows, confirmed by bullish BOS"

Example 2 - MCL short loss:
- POI: Price level 1.0850 (resistance zone)
- BOS: Line from 1.0860 to 1.0840 (bearish break)
- My notes: "Short entry at resistance, but trend was still bullish"
```

Now the AI sees **your actual annotations** and can learn from them!

## The Question Was: How Detailed?

I asked: "How detailed should the prompt examples be?"

**Option 1: Price levels only**
```
- POI: 1.1650
- BOS: 1.1640 to 1.1660
```
**Pros**: Simple, clear
**Cons**: Missing context about why

**Option 2: Price levels + Notes**
```
- POI: 1.1650 (after liquidity sweep)
- BOS: 1.1640 to 1.1660 (bullish break)
- Notes: "Early long entry after liquidity sweep below local lows, confirmed by bullish BOS"
```
**Pros**: AI understands the reasoning
**Cons**: Longer prompt

**Option 3: Full coordinates**
```
- POI: left=500, top=300, width=100, height=50, price=1.1650
- BOS: x1=400, y1=350, x2=600, y2=250, price=1.1650
```
**Pros**: Complete information
**Cons**: Too much detail, coordinates are less useful than price levels

## Recommendation: Option 2 (Price Levels + Notes)

This gives AI:
- **What** you annotated (price levels)
- **Why** you annotated it (your notes)
- **Context** (similar trade info)

This is what we'll implement!

