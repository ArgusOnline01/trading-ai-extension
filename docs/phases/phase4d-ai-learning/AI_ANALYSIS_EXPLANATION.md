# How AI Chart Analysis Works - Phase 4D.1

## Overview

This document explains how the AI analyzes trading charts, what it sees, how the prompt works, and why you might see different results each time.

## What Does the AI See?

### 1. **The Chart Image (PNG File)**
- The AI receives the **raw chart image** (PNG file) that was rendered from your trade data
- This is the same image you see when you view the chart
- The image includes:
  - Candlesticks (price action)
  - Entry/exit markers (blue ▲ for entry, red ▼ for exit)
  - Chart title with trade info
  - Price axis and time axis labels
  - **BUT NOT your manual annotations** (POI, BOS, circles you drew)

### 2. **Why You Can't See Your Annotations When AI Analyzes**

The AI analyzes the **static chart image file**, not the interactive canvas with your annotations. Here's why:

```
Your Annotations (on canvas) → NOT sent to AI
     ↓
Chart Image (PNG file) → Sent to AI ✅
```

- Your annotations are stored separately in the database
- The AI only sees the base chart image (the PNG file)
- This is intentional - the AI learns from the raw chart, not from previous annotations
- When you save corrections, those become training data for future analysis

### 3. **What Information Does the AI Get?**

The AI receives:
1. **Chart Image**: Base64-encoded PNG image of the chart
2. **Similar Trades Context**: Information about similar trades from your history (via RAG)
3. **Prompt Instructions**: Detailed instructions on what to look for

The AI does **NOT** receive:
- Your existing annotations for this trade
- Your notes
- Other trades' annotations (except as context in the prompt)

## How the Prompt Works

### Current Prompt Structure

The AI receives this prompt (from `server/ai/routes.py`):

```
You are an expert trader analyzing charts for Smart Money Concepts (SMC) setups.
Your task is to identify:
1. POI (Point of Interest) - Price levels where price may react
2. BOS (Break of Structure) - Lines showing structure breaks
3. Any other relevant annotations

Return your analysis as JSON with this format:
{
  "poi": [{"left": x, "top": y, "width": w, "height": h, "price": price_level}],
  "bos": [{"x1": x1, "y1": y1, "x2": x2, "y2": y2, "price": price_level}],
  "circles": [{"x": x, "y": y, "radius": r}],
  "notes": "Brief explanation of the setup",
  "reasoning": "Why you identified these annotations"
}

Coordinates should be relative to the chart image dimensions.

Similar trades from history:
[Similar trades data from RAG]

Based on these examples, analyze this chart and identify the setup.
```

### Key Points About the Prompt

1. **Coordinates System**: 
   - The AI is asked to provide coordinates "relative to the chart image dimensions"
   - This means coordinates should be in pixels relative to the original image size
   - Example: If the image is 2000x1000 pixels, coordinates should be between 0-2000 (x) and 0-1000 (y)

2. **What the AI is Looking For**:
   - **POI (Point of Interest)**: Price levels where price may react (support/resistance zones)
   - **BOS (Break of Structure)**: Lines showing where market structure broke
   - **Circles**: Areas of interest (liquidity zones, etc.)

3. **Similar Trades Context**:
   - The RAG system finds similar trades from your history
   - These are included in the prompt as examples
   - The AI uses these to understand your trading style and what you typically annotate

## Why Annotations Appear in Wrong Places

### The Coordinate Scaling Problem (FIXED)

**Problem**: The AI gives coordinates for the original image size, but the image is scaled down when displayed on the canvas.

**Example**:
- Original image: 2400x1200 pixels
- Canvas display: 1200x600 pixels (scaled by 0.5)
- AI says: POI at `left: 1000, top: 500`
- Without scaling: Annotation appears at (1000, 500) on 1200x600 canvas → **WRONG!**
- With scaling: Annotation appears at (500, 250) on 1200x600 canvas → **CORRECT!**

**Solution**: The code now scales coordinates from original image size to canvas size:
```javascript
const scale = canvas.chartScale || 1;
const left = (poi.left || 0) * scale;
const top = (poi.top || 0) * scale;
```

### Why Annotations Might Still Be Inaccurate

1. **AI Vision Limitations**: 
   - The AI is interpreting a 2D image, not actual price data
   - It might misidentify price levels or time positions
   - It's learning from examples, not from raw data

2. **Coordinate Estimation**:
   - The AI estimates pixel coordinates by looking at the image
   - Small errors in estimation can lead to misaligned annotations
   - The AI doesn't have access to the actual price/time data

3. **Image Quality/Resolution**:
   - Lower resolution images = less accurate coordinate estimation
   - Chart text/labels might confuse the AI's coordinate system

## Why Re-Analyzing Gives Different Results

### This is Expected Behavior (Not a Bug)

The AI uses **GPT-5** which is a probabilistic model. This means:

1. **Non-Deterministic Responses**: 
   - Same input can produce different outputs
   - This is by design - the model explores different interpretations
   - Each analysis is a "fresh look" at the chart

2. **Context Variations**:
   - RAG might find slightly different similar trades each time
   - The model's internal state varies between calls

3. **Learning Opportunity**:
   - Different analyses help you see multiple perspectives
   - You can compare and choose the best interpretation
   - Corrections you make teach the AI over time

### When This Becomes a Problem

- If annotations are **completely wrong** every time → Prompt needs improvement
- If annotations are **inconsistent but reasonable** → This is normal AI behavior
- If you want **more consistency** → We can adjust temperature/parameters (future enhancement)

## How to Improve AI Analysis

### 1. **Better Prompts** (Future Enhancement)

We can improve the prompt to:
- Include more specific instructions about coordinate systems
- Provide better examples of what POI/BOS look like
- Add instructions about price level accuracy
- Include information about the trade direction and outcome

### 2. **Fine-Tuning** (Future Enhancement)

After collecting enough corrections:
- Train a custom model on your specific annotation style
- This will make the AI more consistent with your preferences
- Requires Phase 4D.2+ (Interactive Teaching)

### 3. **Better Coordinate System** (Future Enhancement)

Instead of pixel coordinates, we could:
- Ask AI to identify price levels and time ranges
- Convert those to coordinates programmatically
- This would be more accurate than pixel estimation

## Current Workflow

```
1. User clicks "Analyze Chart"
   ↓
2. Backend loads chart image (PNG file)
   ↓
3. RAG finds similar trades from history
   ↓
4. Prompt is built with:
   - Chart image (base64)
   - Similar trades context
   - Instructions
   ↓
5. GPT-5 analyzes the image
   ↓
6. AI returns JSON with:
   - POI coordinates
   - BOS coordinates
   - Circles
   - Notes
   - Reasoning
   ↓
7. Frontend scales coordinates to canvas size
   ↓
8. Annotations displayed on chart
   ↓
9. User can:
   - Correct annotations
   - Save corrections
   - Re-analyze (goes back to step 1)
```

## Questions & Answers

### Q: Why doesn't the AI see my existing annotations?
**A**: The AI learns from the raw chart to develop its own understanding. Your corrections become training data for future analyses.

### Q: Can the AI see other trades' annotations?
**A**: Not directly. The RAG system finds similar trades and includes basic info (symbol, direction, outcome) in the prompt, but not the actual annotation coordinates.

### Q: Why are coordinates sometimes wrong?
**A**: The AI estimates pixel positions from the image. This is less accurate than using actual price/time data. We're working on improving this.

### Q: How can I make the AI more accurate?
**A**: 
1. Save corrections when the AI is wrong
2. Over time, the RAG system will learn from your corrections
3. In Phase 4D.2, we'll add more sophisticated learning

### Q: Should I re-analyze multiple times?
**A**: Yes! Different analyses can give you different perspectives. Compare them and save the best one (or combine them).

## Next Steps

1. **Test the coordinate scaling fix** - Annotations should now appear in correct positions
2. **Try re-analyzing** - See how different analyses compare
3. **Save corrections** - Help the AI learn your style
4. **Provide feedback** - Let us know what works and what doesn't

## Technical Details

### Files Involved

- **Backend**: `server/ai/routes.py` - Handles AI analysis endpoint
- **Backend**: `server/ai/rag/retrieval.py` - Finds similar trades
- **Backend**: `server/ai/rag/embeddings.py` - Generates embeddings
- **Frontend**: `server/web/teach.js` - Displays annotations and handles corrections
- **Frontend**: `server/web/teach.html` - UI for teaching page

### Key Variables

- `chartScale`: Scale factor between original image and canvas (e.g., 0.5 if image is 2400px but canvas is 1200px)
- `canvas.chartScale`: Stored on canvas for coordinate conversion
- `canvas.originalImageWidth/Height`: Original image dimensions before scaling

