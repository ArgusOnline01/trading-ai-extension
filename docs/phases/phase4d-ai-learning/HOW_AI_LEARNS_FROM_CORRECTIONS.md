# How the AI Learns From Corrections

## Overview
When you correct the AI's annotations and save a lesson, the system stores that correction and uses it to improve future analyses. This document explains exactly what the AI can see and how it learns.

## What the AI Sees When You Save a Correction

### 1. **Corrected Annotation Coordinates**
When you save a correction, the AI stores:
- **BOS lines**: Exact coordinates (x1, y1, x2, y2) where you moved the lines to
- **POI boxes**: Exact coordinates (left, top, width, height) where you placed them
- **Circles**: Exact coordinates (x, y, radius) where you placed them

### 2. **Your Reasoning Corrections**
- The text you write in "Correct AI's Reasoning" field
- This explains WHY you made the corrections
- Example: "fractals are the points that determine where BOS's occur"

### 3. **Past Corrections for the Same Trade**
When analyzing a trade you've corrected before, the AI sees:
- Up to 3 most recent corrections for that SAME trade
- All corrected coordinates from those past attempts
- All reasoning corrections from those past attempts
- Instructions to use those coordinates as reference

## How It Works

### When You Analyze a Chart (First Time)
1. AI sees the chart image
2. AI sees your notes (if any)
3. AI sees similar trades from RAG (other trades you've annotated)
4. AI generates annotations based on this

### When You Analyze a Chart (After Corrections)
1. AI sees the chart image (same as before)
2. AI sees your notes (if any)
3. AI sees **PAST CORRECTIONS** for this same trade:
   - "I corrected your BOS lines: x1=1044, y1=137, x2=1284, y2=134"
   - "I corrected your circles: x=1200, y=450, radius=25"
   - "I corrected your reasoning: 'fractals determine where BOS occur'"
4. AI sees similar trades from RAG
5. AI generates annotations, using past corrections as PRIMARY reference

## Why Improvement Might Be Slow

### 1. **Vision Model Limitations**
- GPT-5 vision is good but not perfect at reading exact pixel coordinates
- It might understand the concept but struggle with precise placement
- This is why we provide coordinates as reference

### 2. **Coordinate System Complexity**
- Charts have margins, axes, labels
- Converting price levels to pixel coordinates requires understanding the chart structure
- The AI might get the price level right but the pixel position wrong

### 3. **Learning Curve**
- First correction: AI learns "this is wrong"
- Second correction: AI learns "this is still wrong, try harder"
- Third correction: AI should start getting closer
- It may take 5-10 corrections before significant improvement

## Testing If It's Learning

### Check Backend Logs
When you analyze a chart, check the backend terminal. You should see:
```
[AI Routes] ===== SENDING PAST CORRECTIONS TO AI =====
[AI Routes] Number of past corrections: 3
[AI Routes] Past corrections text preview: ...
```

If you see this, the AI IS receiving the past corrections.

### Compare Coordinates
1. Look at your past corrections (on Progress page)
2. Look at AI's new coordinates (in backend logs)
3. Compare: Are they getting closer?

Example:
- **Correction 1**: BOS at x1=1044, y1=137
- **AI Attempt 2**: BOS at x1=420, y1=185 (wrong)
- **Correction 2**: BOS at x1=1044, y1=137 (same)
- **AI Attempt 3**: BOS at x1=1044, y1=137 (correct!)

## Potential Improvements

### Option 1: Include Corrected Chart Image
Instead of just coordinates, we could:
- Render your corrected annotations on the chart
- Send that image to the AI as a reference
- AI could visually see where you placed things

**Pros**: More visual, might be easier for AI to understand
**Cons**: Requires rendering, more tokens, more complex

### Option 2: More Explicit Instructions
We've already made the prompt very explicit, but we could:
- Add even more emphasis on using past corrections
- Show side-by-side comparison of AI's wrong vs. your correct coordinates
- Add examples of "this is what I corrected, this is what you should do"

### Option 3: Fine-tuning
Instead of just prompt engineering, we could:
- Fine-tune a model on your corrections
- This would require more data (50-100+ corrections)
- More complex but potentially more effective

## Current Status

The system IS sending past corrections to the AI. You can verify this by:
1. Checking backend logs when you analyze
2. Looking at the Progress page to see what was saved
3. Comparing AI's coordinates with your corrections

If improvement is slow, it might be:
- Vision model limitations (can't read exact pixels perfectly)
- Need more corrections (5-10+ for same trade)
- Need different approach (include corrected chart image)

## Next Steps

1. **Continue teaching**: More corrections = more learning
2. **Test on different trades**: See if it generalizes
3. **Monitor progress**: Use Progress page to track improvement
4. **Consider alternatives**: If improvement stalls, we can try including corrected chart images

