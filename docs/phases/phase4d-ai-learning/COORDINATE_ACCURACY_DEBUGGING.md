# Coordinate Accuracy Debugging Guide

## Problem
The AI's annotations (POI, BOS, circles) may appear in approximately the right location but not exactly where they should be. This could be due to:
1. **AI providing approximate coordinates** instead of exact pixel positions
2. **Coordinate conversion/scaling errors** in our rendering code
3. **AI not being able to accurately read pixel positions** from the chart image

## How to Diagnose

### Step 1: Check Backend Logs
When you click "Analyze Chart", check the backend server console (where FastAPI is running). You should see logs like:
```
[AI Routes] AI returned annotations:
  POI count: 0
  BOS count: 2
    BOS 0: x1=1234, y1=567, x2=2345, y2=567, price=1.169
    BOS 1: x1=1234, y1=890, x2=2345, y2=890, price=1.166
  Circles count: 2
    Circle 0: x=1500, y=567, radius=30
    Circle 1: x=1500, y=890, radius=30
```

**What to look for:**
- Are the coordinates reasonable? (e.g., if image is 2000px wide, x1=1234 is reasonable, but x1=999999 is not)
- Do the coordinates match the price levels mentioned? (e.g., if price=1.169, is y1 at the right vertical position?)
- Are coordinates too close to 0 or too large? (might indicate the AI is guessing)

### Step 2: Check Browser Console
Open the browser console (F12) and look for logs like:
```
[TEACH] Displaying AI annotations: {scale: 0.75, origWidth: 2000, origHeight: 1200, ...}
[TEACH] BOS 0: {original: {x1: 1234, y1: 567, ...}, scaled: {x1: 925.5, y1: 425.25, ...}}
```

**What to look for:**
- Is the `scale` factor correct? (should be < 1 if image was scaled down)
- Are the `scaled` coordinates reasonable for the canvas size?
- Do the scaled coordinates match where the annotations appear on screen?

### Step 3: Compare with User Annotations
1. Enable "Show My Annotations" checkbox
2. Compare where your annotations are vs where AI's annotations are
3. If they're close but not exact, it's likely an AI coordinate accuracy issue
4. If they're way off, it might be a coordinate conversion bug

## Common Issues

### Issue 1: AI Provides Approximate Coordinates
**Symptom:** AI says "around 1.169" in reasoning, but coordinates are slightly off
**Cause:** AI is not calculating exact pixel positions from the chart image
**Solution:** The improved prompt now emphasizes exact pixel coordinate calculation

### Issue 2: Coordinates Are Off by a Fixed Amount
**Symptom:** All annotations are shifted by the same amount (e.g., all 50px to the right)
**Cause:** Possible offset issue in coordinate conversion or chart rendering
**Solution:** Check if there's a padding/margin offset in the chart image

### Issue 3: Y-Coordinates Are Inverted
**Symptom:** Annotations appear on the opposite side of the chart (top vs bottom)
**Cause:** Y-axis might be inverted (0 at top vs 0 at bottom)
**Solution:** Check if we need to flip Y coordinates: `y = image_height - y`

### Issue 4: Coordinates Scale Incorrectly
**Symptom:** Annotations are too small or too large
**Cause:** Scale factor calculation might be wrong
**Solution:** Verify `canvas.chartScale` is calculated correctly in `loadChart()`

## Testing Coordinate Accuracy

1. **Manual Test:**
   - Create a test annotation manually (draw a POI at a known price level)
   - Note the exact coordinates
   - Ask AI to analyze the same chart
   - Compare AI's coordinates with your manual coordinates

2. **Price Level Test:**
   - If AI says price=1.169, manually calculate where 1.169 should be on the Y-axis
   - Compare with where AI actually placed the annotation
   - Formula: `y = (price - min_price) / (max_price - min_price) * image_height`

3. **Time Position Test:**
   - If AI places a BOS line, check if the X coordinates match the time positions on the chart
   - X-axis represents time, so x1 should be at the start time, x2 at the end time

## Next Steps

If coordinates are consistently inaccurate:
1. Check backend logs to see what coordinates AI is providing
2. Check browser console to see how coordinates are being scaled
3. Compare with your manual annotations
4. Report findings so we can improve the prompt or coordinate conversion logic

