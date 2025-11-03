# Visual Trade Copilot – Chart Loading and Display System Analysis

## Executive Summary

The chart loading system uses **multiple fallback mechanisms** across backend and frontend:
- **Static file serving** via FastAPI mount (`/charts/{filename}`)
- **Metadata API** (`/charts/chart/{trade_id}`) for chart path lookup
- **Pattern matching** fallbacks when `chart_path` is missing
- **Auto-detection** in `/ask` endpoint before Intent Analyzer runs
- **Base64 encoding** for OpenAI Vision API integration

**Current State**: Chart loading works but has **4 different resolution paths** with potential inconsistencies.

---

## 1️⃣ Backend Endpoints for Chart Images

### 1.1 Static File Serving (Primary)

**File**: `server/app.py` (lines 85-89)
- **Endpoint**: `/charts/{filename}` (e.g., `/charts/MNQZ5_5m_1540306142.png`)
- **Type**: Static file mount (FastAPI `StaticFiles`)
- **Path**: `server/data/charts/`
- **Mount Code**:
  ```python
  charts_dir = Path(__file__).parent / "data" / "charts"
  if charts_dir.exists():
      app.mount("/charts", StaticFiles(directory=str(charts_dir)), name="charts")
  ```
- **Status**: ✅ **Primary method** - All chart URLs resolve to this endpoint

### 1.2 Chart Metadata API

**File**: `server/chart_reconstruction/routes.py` (lines 129-157)
- **Endpoint**: `GET /charts/chart/{trade_id}`
- **Returns**: `{"trade_id": int, "symbol": str, "chart_path": str, ...}`
- **Logic**: Searches `chart_metadata.json` for matching trade_id
- **Usage**: Fallback when `chart_path` not in trade object

**Example Response**:
```json
{
  "trade_id": 1540306142,
  "symbol": "MNQZ5",
  "chart_path": "C:\\Users\\alfre\\.cursor-tutor\\trading-ai-extension\\server\\data\\charts\\MNQZ5_5m_1540306142.png"
}
```

### 1.3 Other Chart Endpoints

**File**: `server/chart_reconstruction/routes.py`
- `GET /charts/metadata` - List all chart metadata
- `GET /charts/stats` - Chart statistics
- `GET /charts/retry-queue` - Failed chart renders

**Status**: ⚠️ **Not used for chart display** - Only for metadata/admin

### 1.4 Performance Endpoints (Indirect)

**File**: `server/performance/routes.py`
- `GET /performance/all` - Returns all trades with `chart_path` field
- `GET /performance/trades/{id}` - Returns single trade with `chart_path` field

**Status**: ✅ **Source of chart_path** - Trade objects include `chart_path` field

---

## 2️⃣ Trade Object Chart Path Linking

### 2.1 Data Source: `performance_logs.json`

**File**: `server/data/performance_logs.json`
- **Format**: Array of trade objects
- **Chart Path Field**: `chart_path` (can be absolute or relative)
- **Example**:
  ```json
  {
    "id": 1540306142,
    "symbol": "MNQZ5",
    "chart_path": "C:\\Users\\alfre\\.cursor-tutor\\trading-ai-extension\\server\\data\\charts\\MNQZ5_5m_1540306142.png"
  }
  ```

### 2.2 Chart Path Resolution Priority

**Location**: `server/utils/trade_detector.py` → `load_chart_image_for_trade()` (lines 301-400)

**Priority Order**:
1. **Direct `chart_path` field** (if exists and file exists)
2. **Filename extraction** from `chart_path` → search in `charts_dir`
3. **Pattern matching** (`{symbol}_5m_{trade_id}.png`)
4. **Glob fallback** (`{symbol}_5m_{trade_id}*.png`)

**Code Flow**:
```python
# Priority 1: chart_path field
chart_path = trade.get('chart_path')
if chart_path and Path(chart_path).exists():
    image_file_path = Path(chart_path)

# Priority 2: Extract filename
if not image_file_path:
    filename = Path(chart_path).name
    candidate = charts_dir / filename
    if candidate.exists():
        image_file_path = candidate

# Priority 3: Pattern matching
if not image_file_path:
    patterns = [
        f"{symbol}_5m_{trade_id}.png",
        f"{symbol}_15m_{trade_id}.png",
        f"chart_{trade_id}.png"
    ]
    # Try each pattern...

# Priority 4: Glob fallback
if not image_file_path:
    matches = list(charts_dir.glob(f"{symbol}_5m_{trade_id}*.png"))
```

### 2.3 Chart Path Format

**Supported Formats**:
- **Absolute**: `C:\Users\alfre\.cursor-tutor\trading-ai-extension\server\data\charts\MNQZ5_5m_1540306142.png`
- **Relative**: `MNQZ5_5m_1540306142.png` (resolved against `charts_dir`)
- **Filename only**: Extracted from absolute path

**Pattern**: `{SYMBOL}_{TIMEFRAME}_{TRADE_ID}.png`
- Example: `MNQZ5_5m_1540306142.png`
- Timeframe: Usually `5m` or `15m`

---

## 3️⃣ Frontend Chart Display Logic

### 3.1 Chart Popup Function

**File**: `visual-trade-extension/content/content.js` (lines 512-738)
- **Function**: `window.openChartPopup(src)`
- **Purpose**: Creates full-size side panel with chart image
- **Logic**:
  1. Creates `<div id="vtc-chart-side-panel">` element
  2. Adds `<img>` element with `src` URL
  3. Appends to `document.body`
  4. Handles close button and ESC key
  5. Logs load/error events

**Usage**:
```javascript
window.openChartPopup("http://127.0.0.1:8765/charts/MNQZ5_5m_1540306142.png")
```

### 3.2 Frontend Action Handler

**File**: `visual-trade-extension/content/content.js` (lines 3374-3410, 4052-4065)

**Handler 1**: Direct response handling (`handleSystemCommand`)
```javascript
if (res.frontend_action === "show_chart_popup") {
  const chartUrl = res.chart_url || res.data?.chart_url || res.chartUrl;
  const fullUrl = chartUrl.startsWith('http') 
    ? chartUrl 
    : `http://127.0.0.1:8765${chartUrl}`;
  window.openChartPopup(fullUrl);
}
```

**Handler 2**: Chrome message passing (`chrome.runtime.onMessage`)
```javascript
if (frontendAction === "show_chart_popup") {
  const chartUrl = actionData?.chart_url || actionData?.chartUrl;
  const fullUrl = chartUrl.startsWith('http') ? chartUrl : `http://127.0.0.1:8765${chartUrl}`;
  window.openChartPopup(fullUrl);
}
```

**Status**: ✅ **Both paths work** - Handles both direct calls and message passing

### 3.3 Teach Copilot Chart Loading

**File**: `visual-trade-extension/content/content.js` (lines 2246-2306)

**Function**: `loadTeachChart(trade)`
- **Priority 1**: Use `trade.chart_path` → Extract filename → Load from `/charts/{filename}`
- **Priority 2**: Call `/charts/chart/{trade_id}` metadata API
- **Priority 3**: Pattern matching fallback (`tryPatternMatchChart`)

**Auto-Popup**: In teaching mode, automatically opens full-size popup after image loads (line 2269)

**Code Flow**:
```javascript
// Priority 1: chart_path field
if (trade.chart_path) {
  const fileName = trade.chart_path.split(/[/\\]/).pop();
  chartImg.src = `http://127.0.0.1:8765/charts/${fileName}`;
  chartImg.onerror = () => tryPatternMatchChart(...);
}

// Priority 2: Metadata API
if (!chartImg.src) {
  const metaResponse = await fetch(`http://127.0.0.1:8765/charts/chart/${tradeId}`);
  const meta = await metaResponse.json();
  if (meta.chart_path) {
    const fileName = meta.chart_path.split(/[/\\]/).pop();
    chartImg.src = `http://127.0.0.1:8765/charts/${fileName}`;
  }
}

// Priority 3: Pattern matching
if (!chartImg.src) {
  tryPatternMatchChart(symbol, tradeId, chartImg, chartContainer);
}
```

### 3.4 Pattern Matching Fallback

**File**: `visual-trade-extension/content/content.js` (lines 2308-2347)

**Function**: `tryPatternMatchChart(symbol, tradeId, chartImg, chartContainer)`
- **Patterns**:
  ```javascript
  const patterns = [
    `${symbol}_5m_${tradeId}.png`,
    `${symbol}_15m_${tradeId}.png`,
    `chart_${tradeId}.png`
  ];
  ```
- **Logic**: Tries each pattern, constructs URL, tests image load
- **Status**: ⚠️ **Fallback only** - Used when `chart_path` missing

---

## 4️⃣ Auto-Loading Behavior

### 4.1 Auto-Detection in `/ask` Endpoint

**File**: `server/app.py` (lines 370-426)

**Trigger**: When user sends question WITHOUT image upload

**Flow**:
1. **Explicit trade_id** (if provided): Load chart directly
2. **Auto-detection**: Check AI's recent responses for trade mentions
3. **User question**: Detect trade reference in question text
4. **Load chart**: Call `load_chart_image_for_trade()` → Convert to base64

**Code**:
```python
# Step 1: Check AI's recent response
for msg in reversed(parsed_messages[-5:]):
    if msg.get('role') == 'assistant':
        ai_trade = detect_trade_reference(str(msg.get('content', '')), all_trades, [])
        if ai_trade:
            image_base64 = load_chart_image_for_trade(ai_trade)  # Auto-load for next turn

# Step 2: Check user question
if not detected_trade:
    detected_trade = detect_trade_reference(question, all_trades, conversation_history)
if detected_trade:
    image_base64 = load_chart_image_for_trade(detected_trade)  # Auto-load for this turn
```

**Status**: ✅ **Works correctly** - Charts auto-load when trade is mentioned

### 4.2 Auto-Loading When Trade Listed

**Scenario**: User asks "list my trades" → AI lists trade → User says "show chart"

**Flow**:
1. AI response contains trade mention (e.g., "Trade #13: MNQZ5")
2. User says "show chart" or "pull up its chart"
3. `detect_trade_reference()` searches conversation history
4. Finds trade #13 from AI's previous message
5. `execute_show_chart_command()` uses detected trade
6. Chart popup opens

**Status**: ✅ **Works correctly** - Conversation history enables context-aware detection

### 4.3 Teach Copilot Auto-Popup

**File**: `visual-trade-extension/content/content.js` (lines 2264-2273)

**Behavior**: When trade selected in Teach Copilot, automatically opens full-size popup

**Code**:
```javascript
chartImg.onload = () => {
  if (!chartImg.dataset.popupShown) {
    chartImg.dataset.popupShown = "true";
    setTimeout(() => {
      if (window.openChartPopup) {
        window.openChartPopup(chartImg.src);
      }
    }, 500);
  }
};
```

**Status**: ✅ **Works correctly** - Auto-opens popup on trade selection

---

## 5️⃣ Inconsistencies and Fallbacks

### 5.1 Multiple Chart Path Resolution Paths

**Issue**: Chart path resolution happens in **4 different places** with slightly different logic:

1. **Backend**: `execute_show_chart_command()` (system_commands.py:769-951)
   - Priority: `chart_path` → Metadata API → Pattern matching → File system glob
   
2. **Backend**: `load_chart_image_for_trade()` (trade_detector.py:301-400)
   - Priority: `chart_path` → Filename extraction → Pattern matching → Glob
   
3. **Frontend**: `loadTeachChart()` (content.js:2246-2306)
   - Priority: `chart_path` → Metadata API → Pattern matching
   
4. **Frontend**: `tryPatternMatchChart()` (content.js:2308-2347)
   - Priority: Pattern matching only

**Problem**: Each path has different fallback logic, leading to inconsistent behavior

### 5.2 Chart Path Format Inconsistency

**Issue**: `chart_path` can be:
- Absolute path: `C:\Users\...\charts\MNQZ5_5m_1540306142.png`
- Relative path: `MNQZ5_5m_1540306142.png`
- Missing: `null` or not present

**Handling**:
- Backend: Handles both absolute and relative
- Frontend: Extracts filename with `split(/[/\\]/).pop()` (works for both)

**Status**: ✅ **Handled correctly** but inconsistent format is confusing

### 5.3 Metadata API Timeout

**File**: `server/memory/system_commands.py` (line 886)

**Issue**: Metadata API call has `timeout=2` seconds (very short)

**Code**:
```python
meta_response = requests.get(f"http://127.0.0.1:8765/charts/chart/{trade_id}", timeout=2)
```

**Problem**: May timeout on slow systems, causing unnecessary fallback

**Status**: ⚠️ **Too short** - Should be increased to 5-10 seconds

### 5.4 Base64 vs URL Mismatch

**Issue**: Charts are loaded in **two different formats**:

1. **Base64** (for OpenAI Vision API):
   - Location: `load_chart_image_for_trade()` returns base64 string
   - Used in: `/ask` endpoint auto-detection
   - Purpose: Embed in AI request

2. **URL** (for frontend display):
   - Location: `execute_show_chart_command()` returns `/charts/{filename}`
   - Used in: Frontend popup display
   - Purpose: Browser image loading

**Problem**: Two different code paths for same trade

**Status**: ✅ **Works correctly** but duplicates logic

### 5.5 Pattern Matching Conflicts

**Issue**: Pattern matching uses different patterns in different places:

**Backend** (`system_commands.py:902-906`):
```python
patterns = [
    f"{symbol}_5m_{trade_id}.png",
    f"{symbol}_5m_{trade_id}*.png",  # Glob
    f"{symbol}_*_{trade_id}.png"     # Wildcard
]
```

**Backend** (`trade_detector.py:350-354`):
```python
patterns = [
    f"{symbol}_5m_{trade_id}.png",
    f"{symbol}_15m_{trade_id}.png",
    f"chart_{trade_id}.png"
]
```

**Frontend** (`content.js:2309-2313`):
```javascript
const patterns = [
  `${symbol}_5m_${tradeId}.png`,
  `${symbol}_15m_${tradeId}.png`,
  `chart_${tradeId}.png`
];
```

**Problem**: Patterns differ slightly (backend has glob, frontend doesn't)

**Status**: ⚠️ **Inconsistent** - Should use same patterns everywhere

---

## 6️⃣ Data Flow Diagrams

### 6.1 Current Flow: "Show Chart" Command

```
User: "show chart"
  ↓
/ask endpoint → analyze_intent()
  ↓
Intent Analyzer: {"is_command": true, "commands_detected": [{"command": "show_chart"}]}
  ↓
command_router.route_command()
  ↓
execute_show_chart_command(context)
  ↓
[CHART PATH RESOLUTION]
  ├─ Priority 1: context.get('detected_trade').get('chart_path')
  ├─ Priority 2: GET /charts/chart/{trade_id} (metadata API)
  ├─ Priority 3: Pattern matching (file system glob)
  └─ Priority 4: Most recent trade fallback
  ↓
Chart found: Extract filename → Build URL: /charts/{filename}
  ↓
Return: {
  "success": true,
  "frontend_action": "show_chart_popup",
  "chart_url": "/charts/MNQZ5_5m_1540306142.png"
}
  ↓
Frontend: handleSystemCommand() receives response
  ↓
Extract chart_url → Build full URL: http://127.0.0.1:8765/charts/...
  ↓
window.openChartPopup(fullUrl)
  ↓
Create side panel → Load image → Display popup
```

### 6.2 Current Flow: Auto-Load Chart in `/ask`

```
User: "what about trade #13?"
  ↓
/ask endpoint → detect_trade_reference("trade #13", all_trades)
  ↓
Trade detected: {id: 13, symbol: "MNQZ5", chart_path: "..."}
  ↓
load_chart_image_for_trade(trade)
  ↓
[CHART LOADING]
  ├─ Priority 1: trade.get('chart_path') → Check if exists
  ├─ Priority 2: Extract filename → Search charts_dir
  ├─ Priority 3: Pattern matching ({symbol}_5m_{trade_id}.png)
  └─ Priority 4: Glob fallback ({symbol}_5m_{trade_id}*.png)
  ↓
Chart found: Load file → Convert to RGB → Resize → Encode base64
  ↓
image_base64 = "data:image/jpeg;base64,/9j/4AAQ..."
  ↓
Pass to OpenAI Vision API (embedded in request)
  ↓
AI analyzes chart image + user question
  ↓
Return response with chart context
```

### 6.3 Current Flow: Teach Copilot Chart Display

```
User selects trade in Teach Copilot dropdown
  ↓
loadTeachChart(trade)
  ↓
[CHART PATH RESOLUTION - FRONTEND]
  ├─ Priority 1: trade.chart_path → Extract filename → /charts/{filename}
  ├─ Priority 2: GET /charts/chart/{trade_id} (metadata API)
  └─ Priority 3: tryPatternMatchChart() (pattern matching)
  ↓
Chart URL: http://127.0.0.1:8765/charts/MNQZ5_5m_1540306142.png
  ↓
Load image in <img> element
  ↓
onload event → Auto-open popup (if not already shown)
  ↓
window.openChartPopup(chartImg.src)
  ↓
Full-size popup displays chart
```

### 6.4 Multiple Paths Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHART LOADING PATHS                          │
└─────────────────────────────────────────────────────────────────┘

PATH A: Intent Analyzer → Command Router → Backend Resolution
  User: "show chart"
    → Intent Analyzer detects command
    → execute_show_chart_command()
    → Backend: chart_path → metadata API → pattern → glob
    → Return URL: /charts/{filename}
    → Frontend: openChartPopup()

PATH B: Auto-Detection → Base64 Encoding
  User: "what about trade #13?"
    → detect_trade_reference() in /ask
    → load_chart_image_for_trade()
    → Backend: chart_path → pattern → glob
    → Return base64 string
    → Embedded in AI request

PATH C: Frontend Direct Resolution
  Teach Copilot: User selects trade
    → loadTeachChart()
    → Frontend: chart_path → metadata API → pattern
    → Load image directly
    → Auto-open popup

PATH D: Frontend Bypass (Legacy)
  handleCopilotIntent(): "what was trade 13"
    → Direct API call to /copilot/teach/example/13
    → Returns formatted text (no chart loading)
    → ⚠️ BYPASSES Intent Analyzer
```

---

## 7️⃣ File Reference Map

### Backend Files

| File | Function | Purpose |
|------|----------|---------|
| `server/app.py` | `/ask` endpoint (line 314) | Auto-detection before Intent Analyzer |
| `server/app.py` | `app.mount("/charts")` (line 89) | Static file serving |
| `server/memory/system_commands.py` | `execute_show_chart_command()` (line 769) | Chart command handler |
| `server/utils/trade_detector.py` | `load_chart_image_for_trade()` (line 301) | Base64 chart loading |
| `server/utils/trade_detector.py` | `detect_trade_reference()` (line 32) | Trade detection from text |
| `server/chart_reconstruction/routes.py` | `/charts/chart/{trade_id}` (line 129) | Metadata API |
| `server/performance/utils.py` | `read_logs()` (line 25) | Read `performance_logs.json` |
| `server/utils/overlay_drawer.py` | `find_chart_image()` (line 25) | Chart file finder |

### Frontend Files

| File | Function | Purpose |
|------|----------|---------|
| `visual-trade-extension/content/content.js` | `window.openChartPopup()` (line 512) | Chart popup display |
| `visual-trade-extension/content/content.js` | `loadTeachChart()` (line 2246) | Teach Copilot chart loader |
| `visual-trade-extension/content/content.js` | `tryPatternMatchChart()` (line 2308) | Pattern matching fallback |
| `visual-trade-extension/content/content.js` | `handleSystemCommand()` (line 3374) | Frontend action handler |
| `visual-trade-extension/background.js` | Message passing (line 196) | Chart URL forwarding |

### Data Files

| File | Purpose |
|------|---------|
| `server/data/performance_logs.json` | Trade objects with `chart_path` field |
| `server/data/charts/` | Directory containing PNG chart images |
| `server/data/chart_metadata.json` | Chart metadata (optional) |

---

## 8️⃣ Summary: Chart Loading Architecture

### Current Architecture Strengths

✅ **Multiple fallback paths** ensure charts load even if `chart_path` missing
✅ **Auto-detection** works well for context-aware chart loading
✅ **Static file serving** is efficient and simple
✅ **Base64 encoding** enables OpenAI Vision API integration
✅ **Frontend popup** provides good UX for chart viewing

### Current Architecture Weaknesses

⚠️ **Inconsistent resolution logic** across 4 different code paths
⚠️ **Pattern matching differs** between backend and frontend
⚠️ **Metadata API timeout** too short (2 seconds)
⚠️ **Chart path format** inconsistent (absolute vs relative)
⚠️ **No unified chart service** - logic scattered across files

### Recommended Unification (Phase 5F.1)

**Goal**: Create unified chart resolution service

**Proposed Changes**:

1. **Create `server/utils/chart_service.py`**:
   ```python
   def resolve_chart_path(trade: Dict[str, Any]) -> Optional[str]:
       """Unified chart path resolution with consistent priority"""
       # Priority 1: chart_path field
       # Priority 2: Metadata API
       # Priority 3: Pattern matching
       # Priority 4: Glob fallback
       # Returns: /charts/{filename} or None
   ```

2. **Unify Pattern Matching**:
   - Create `CHART_PATTERNS` constant
   - Use same patterns in backend and frontend
   - Document pattern format

3. **Increase Metadata API Timeout**:
   - Change from 2s to 10s
   - Add retry logic

4. **Standardize Chart Path Format**:
   - Always store relative path (`MNQZ5_5m_1540306142.png`)
   - Resolve against `charts_dir` at runtime

5. **Integrate with Intent Analyzer**:
   - Pass `chart_path` in command arguments
   - Remove regex fallbacks from `execute_show_chart_command()`

---

## 9️⃣ Data Flow: Unified Phase 5E → Phase 5F.1 Flow

### Target Flow: "Show Chart" Command (Unified)

```
User: "show chart"
  ↓
/ask endpoint → analyze_intent()
  ↓
Intent Analyzer: {
  "is_command": true,
  "commands_detected": [{
    "command": "show_chart",
    "arguments": {
      "trade_reference": "recent"  // or specific trade_id
    }
  }]
}
  ↓
command_router.route_command()
  ↓
execute_show_chart_command(context)
  ↓
[UNIFIED CHART SERVICE]
  chart_service.resolve_chart_path(detected_trade)
    ├─ Priority 1: chart_path field
    ├─ Priority 2: Metadata API (timeout: 10s)
    ├─ Priority 3: Pattern matching (unified patterns)
    └─ Priority 4: Glob fallback
  ↓
Chart found: /charts/MNQZ5_5m_1540306142.png
  ↓
Return: {
  "success": true,
  "frontend_action": "show_chart_popup",
  "chart_url": "/charts/MNQZ5_5m_1540306142.png"
}
  ↓
Frontend: handleSystemCommand() → window.openChartPopup()
  ↓
Chart popup displays
```

### Target Flow: Auto-Load Chart (Unified)

```
User: "what about trade #13?"
  ↓
/ask endpoint → detect_trade_reference()
  ↓
Trade detected: {id: 13, symbol: "MNQZ5"}
  ↓
[UNIFIED CHART SERVICE]
  chart_service.load_chart_base64(trade)
    ├─ Resolve path via chart_service.resolve_chart_path()
    ├─ Load file → Convert to RGB → Resize
    └─ Encode base64
  ↓
image_base64 = "data:image/jpeg;base64,..."
  ↓
Pass to OpenAI Vision API
  ↓
AI analyzes chart + question
  ↓
Return response
```

---

## 🔟 Conclusion

The chart loading system is **functional but fragmented**. Multiple resolution paths work independently, leading to:

- ✅ **Reliability**: Multiple fallbacks ensure charts load
- ⚠️ **Complexity**: 4 different code paths
- ⚠️ **Inconsistency**: Different patterns and priorities

**Next Steps for Phase 5F.1**:
1. Create unified `chart_service.py` module
2. Standardize chart path resolution logic
3. Integrate with Intent Analyzer command arguments
4. Unify pattern matching across backend and frontend
5. Increase metadata API timeout
6. Document chart path format specification

**End of Analysis**

