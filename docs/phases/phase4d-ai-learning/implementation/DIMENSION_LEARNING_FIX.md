# Dimension Learning Fix

## Issue
When users corrected AI annotations by resizing them (e.g., extending a BOS line, making a POI box larger), the AI would ignore these dimension changes and revert to its original size on the next analysis.

**Root cause:** The AI prompt only included position coordinates but didn't highlight dimension differences or explain why scale matters.

## Solution
Enhanced the AI prompt in `server/ai/routes.py` to:

1. **Calculate dimension differences** between original and corrected annotations
2. **Show dimension changes explicitly** (e.g., "I extended your line by 450px (120%)")
3. **Explain the meaning of dimension changes** (e.g., "Extended BOS = structure break spans a longer time period")
4. **Update learning instructions** to emphasize that dimensions are as important as positions

## Changes Made

### `server/ai/routes.py`

#### BOS Line Corrections (lines 301-337)
- Added `corrected_length` and `original_length` calculations
- Show length in pixels and percentage of chart width
- Display dimension changes if >10% difference
- Explain what the change means (e.g., "line should span more of the time period")

#### POI Corrections (lines 338-375)
- Added width/height dimension tracking
- Show POI size as "width × height" with percentages
- Display dimension changes for width and/or height if >10% difference
- Explain what the change means (e.g., "POI zone should cover more area")

#### Circle Corrections (lines 376-398)
- Added radius dimension tracking
- Show circle radius in pixels
- Display radius changes if >10% difference
- Explain what the change means (e.g., "fractal marker should be larger to emphasize the pattern")

#### Learning Instructions (lines 405-421)
- Updated to emphasize "LOGIC, PATTERNS, AND DIMENSIONS"
- Added section explaining why dimensions matter
- Included examples of what dimension changes mean:
  - Extended BOS = longer time period
  - Wider POI = covers more levels or longer accumulation
  - Larger circle = more significant turning point

## Example Output

Before:
```
BOS 1 (price 1.169): I placed it at x1=930 (20.9% from left), x2=1380 (31.1% from left)
```

After:
```
BOS 1 (price 1.169): I placed it at x1=930 (20.9% from left), x2=1380 (31.1% from left)
  → Length: 450px (10.1% of chart width)
  → I extended your line by 250px (125%) - this shows the BOS should span more of the time period
  → This marks the BOS at price level 1.169 - look for this price level on the chart and identify where the structure break occurred
```

## Testing
1. Navigate to Teach AI page for a trade with past lessons
2. Resize a BOS line (make it longer/shorter)
3. Resize a POI box (make it wider/taller)
4. Resize a circle (make it larger/smaller)
5. Save corrections with a note explaining WHY you changed the size
6. Re-analyze the chart
7. The AI should now respect the dimensions you set and explain its reasoning

## Expected Behavior
- AI should place annotations at approximately the same scale as your corrections
- AI's reasoning should reference the dimension guidance you provided
- Significant dimension changes (>10%) should be highlighted in the prompt
- The AI should understand that dimensions convey meaning (time span, zone coverage, emphasis)

## Related Files
- `server/ai/routes.py`: Enhanced prompt with dimension information
- `server/web/teach.js`: Already calculates correct dimensions when saving corrections
- `server/web/annotate.js`: Already calculates correct dimensions when saving annotations

