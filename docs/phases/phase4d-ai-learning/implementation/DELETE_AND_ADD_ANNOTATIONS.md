# Delete & Add Annotations Feature

## Overview
Users can now **delete incorrect AI annotations** (when AI hallucinates patterns) and **add missing annotations** (when AI misses patterns) on the Teach AI page. This gives complete control over the teaching process and helps the AI learn what NOT to identify and what it MISSED.

## Features

### 1. Delete AI Annotations
- **Right-click or press Delete/Backspace** on any AI-generated annotation to remove it
- **Delete button** appears when an annotation is selected
- **Tracks deletions** to teach the AI: "this pattern should not exist"

### 2. Add New Annotations
- **Drawing tools** on the Teach AI page (same as Annotate page):
  - 📦 **POI**: Draw rectangles for Point of Interest zones
  - 📏 **BOS**: Draw lines for Break of Structure levels
  - ⭕ **Circle**: Draw circles for fractals/markers
  - 👆 **Select**: Switch back to selection mode (default)
- **Green stroke** (#4caf50) for user-added annotations to distinguish them
- **Tracks additions** to teach the AI: "you missed this pattern"

### 3. AI Learning from Deletions & Additions
- **Deletions are stored separately** in `deleted_annotations` field
- **Additions are marked** with `added: true` flag in `corrected_annotations`
- **AI prompt includes:**
  - Count of deleted annotations: "🗑️ DELETIONS: I deleted N annotation(s) you created that SHOULD NOT EXIST"
  - Count of added annotations: "➕ ADDITIONS: I added N annotation(s) that you MISSED"
  - Guidance on what these mean

## UI Changes

### Teach AI Page Controls
```
[Show AI Annotations] [Show My Annotations] | [📦 POI] [📏 BOS] [⭕ Circle] [👆 Select] | [🗑️ Delete Selected] [🔍 Reset Zoom] [✅ Save Corrections]
```

- **Tool buttons**: Click to activate drawing mode
- **Active tool**: Highlighted with accent color and bold font
- **Delete button**: Only visible when an annotation is selected
- **Keyboard shortcut**: Delete/Backspace key to delete selected annotation

### Visual Indicators
- **AI annotations**: Blue dashed lines (existing)
- **User corrections**: Solid lines (existing)
- **User additions**: **Green solid lines** with thicker stroke (#4caf50)

## Technical Implementation

### Frontend (`teach.js`)

**New State:**
```javascript
let currentTool = null; // 'poi', 'bos', 'circle', or null
let isDrawing = false;
let deletedAIAnnotations = []; // Track deleted AI annotations
let addedAnnotations = { poi: [], bos: [], circles: [] }; // Track user-added annotations
```

**Key Functions:**
- `selectTool(tool)`: Activate drawing tool or select mode
- `deleteSelected()`: Remove annotation and track deletion
- `handle Mouse Down/Move/Up()`: Drawing handlers for preview and finalization
- `createAddedPOI/BOS/Circle()`: Create new annotation and track as addition
- `updateDeleteButtonVisibility()`: Show/hide delete button based on selection

**Save Corrections:**
- Converts added annotations to `corrected_annotations` with `added: true` flag
- Sends `deleted_annotations` array to backend

### Backend (`ai/routes.py`)

**Model Update:**
```python
class SaveLessonRequest(BaseModel):
    trade_id: str
    ai_annotations: Dict[str, Any]
    corrected_annotations: Dict[str, Any]
    corrected_reasoning: Optional[str] = None
    deleted_annotations: Optional[List[Dict[str, Any]]] = None  # NEW
```

**Database Migration:**
```sql
ALTER TABLE ai_lessons ADD COLUMN deleted_annotations TEXT;
```

**AI Prompt Enhancement:**
- Counts deletions from `lesson.deleted_annotations`
- Counts additions from `corrected_annotations` where `added: true` and `original is None`
- Displays:
  ```
  🗑️ DELETIONS: I deleted N annotation(s) you created that SHOULD NOT EXIST:
    → These annotations were hallucinations or incorrect identifications
    → DO NOT create similar annotations - they don't represent valid patterns
    
  ➕ ADDITIONS: I added N annotation(s) that you MISSED:
    → These annotations should have been identified but weren't in your initial analysis
    → Learn to identify these patterns/structures that you overlooked
  ```

## Usage Flow

### Deleting an Incorrect AI Annotation
1. Go to Teach AI page for a trade
2. AI generates annotations (some may be incorrect)
3. **Click** on the incorrect annotation to select it
4. **Press Delete key** or **click "🗑️ Delete Selected" button**
5. The annotation is removed and tracked as a deletion
6. **Save Corrections** to teach the AI not to create similar annotations

### Adding a Missing Annotation
1. Go to Teach AI page for a trade
2. AI generates annotations (may miss some patterns)
3. **Click drawing tool button** (e.g., "📦 POI")
4. **Draw the annotation** on the chart (click-drag-release)
5. The annotation is created with green stroke
6. **Add a note** explaining WHY this pattern exists (optional but recommended)
7. **Save Corrections** to teach the AI to identify similar patterns

## Example Scenarios

### Scenario 1: AI Hallucinates a BOS Line
**Problem:** AI marks a BOS line where no structure break occurred.

**Solution:**
1. Select the incorrect BOS line
2. Press Delete
3. Save corrections with note: "No BOS here - price only retested support, didn't break structure"

**AI Learning:** On next analysis, AI will be less likely to mark BOS at retest levels.

### Scenario 2: AI Misses a Fractal
**Problem:** AI doesn't circle an important swing high fractal.

**Solution:**
1. Click "⭕ Circle" tool
2. Draw circle around the fractal
3. Save corrections with note: "Fractal at swing high - key reversal point"

**AI Learning:** On next analysis, AI will look for similar swing high patterns and mark them.

### Scenario 3: AI Marks Too Many POI Zones
**Problem:** AI creates 5 POI boxes when only 2 are valid.

**Solution:**
1. Delete the 3 invalid POI boxes
2. Adjust the 2 valid ones (resize/reposition)
3. Save corrections with note: "Only mark POI zones at actual imbalances, not every pullback"

**AI Learning:** AI will be more selective about POI identification.

## Files Changed

### Frontend
- `server/web/teach.html`: Added tool buttons and delete button
- `server/web/teach.js`: Added drawing, deletion, and tracking logic

### Backend
- `server/ai/routes.py`: Updated `SaveLessonRequest`, added deletion/addition prompt logic
- `server/db/models.py`: Added `deleted_annotations` column to `AILesson`
- `server/migrations/011_add_deleted_annotations.sql`: Migration script
- `server/migrations/apply_011.py`: Migration application script

## Benefits

1. **Complete Teaching Control**: Users can fully correct AI's mistakes (not just reposition)
2. **Negative Learning**: AI learns what NOT to do (prevent false positives)
3. **Positive Learning**: AI learns what it MISSED (prevent false negatives)
4. **Faster Iteration**: No need to wait for AI to get it right - just delete/add and move on
5. **Better Accuracy**: Over time, AI learns to avoid hallucinations and catch all patterns

## Future Enhancements

- **Undo/Redo**: Add undo/redo for deletions and additions
- **Bulk Operations**: Select multiple annotations and delete them at once
- **Copy/Paste**: Copy an annotation and paste it elsewhere
- **Templates**: Save common annotation patterns as templates
- **Detailed Deletion Reasons**: Add dropdown to categorize why an annotation was deleted (hallucination, wrong pattern, wrong timeframe, etc.)

