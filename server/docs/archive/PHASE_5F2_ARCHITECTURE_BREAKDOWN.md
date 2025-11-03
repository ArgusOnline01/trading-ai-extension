# Phase 5F.2 System Architecture Breakdown - Visual Trade Copilot

**Purpose:** Detailed architectural documentation of subsystems for Phase 5F.2 fixes  
**Date:** 2025-01-XX  
**Phase:** 5E → 5F.1 → 5F.2

---

## 1️⃣ Intent Analysis & Command Routing

### 1.1 Intent Analyzer: Command Detection & Confidence

**File:** `server/ai/intent_analyzer.py`  
**Function:** `analyze_intent(user_text, conversation, model="gpt-4o-mini")` (lines 68-217)

**How it works:**

1. **Input Processing:**
   - Receives `user_text` (raw user message)
   - Optional `conversation` history (last 3 messages only for speed)
   - Model defaults to `gpt-4o-mini` (fast, cost-effective)

2. **LLM Call:**
   ```python
   # Build messages with system prompt + conversation context
   messages = [
       {"role": "system", "content": load_intent_prompt()},  # From config/intent_prompt.txt
       ...conversation[-3:],  # Last 3 messages for context
       {"role": "user", "content": user_text}
   ]
   
   # Call OpenAI API with JSON mode
   response = client.chat.completions.create(
       model="gpt-4o-mini",
       messages=messages,
       response_format={"type": "json_object"},
       temperature=0.1,  # Low temperature for consistency
       max_tokens=500   # Limit for speed
   )
   ```

3. **Response Parsing:**
   ```python
   data = json.loads(result_text)
   # Returns:
   {
       "is_command": bool,
       "confidence": float (0.0-1.0),
       "commands_detected": [
           {
               "command": "view_trade",
               "type": "trade",
               "action": "view",
               "arguments": {
                   "trade_id": "13",
                   "trade_reference": "third"  # OR "first", "last", "recent"
               }
           }
       ]
   }
   ```

4. **Schema Validation:**
   - Each command in `commands_detected` validated via `validate_command_schema()`
   - Invalid commands removed; if all invalid, `is_command=False`

5. **Confidence Threshold:**
   - Default: `0.5` (configurable via `INTENT_CONFIDENCE_THRESHOLD` env var)
   - Applied in `app.py:467`: `is_command = intent_analysis.get("is_command") and confidence >= CONFIDENCE_THRESHOLD`

**Latency:** ~500-1500ms (LLM inference time)

**Context Resolution:**
- **Conversation History:** Last 3 messages only (optimized for speed)
- **Arguments Extraction:** LLM extracts `trade_reference` ("recent", "largest_loss", "previous") from user text
- **No Context Memory:** Intent Analyzer does NOT track "current trade" state; it's stateless

---

### 1.2 Command Router: Validation & Execution

**File:** `server/utils/command_router.py`  
**Function:** `route_command(raw_cmd, context)` (lines 158-253)

**Data Flow:**

```
Intent Analyzer Output → route_command(raw_cmd, context)
  ↓
Step 1: Validate Schema (validate_command_schema)
  ↓
Step 2: Normalize Command (normalize_command)
  ↓
Step 3: Fill Missing Fields (fill_missing_fields)
  - Fills session_id from context.current_session_id
  - Fills trade_id from context.detected_trade
  - Fills symbol from context.session_context.symbol
  ↓
Step 4: Find Handler (execute_{command_name}_command)
  - Maps "view_trade" → execute_view_trade_command()
  - Maps "show_chart" → execute_show_chart_command()
  ↓
Step 5: Execute Handler (handler(enhanced_context))
  - enhanced_context = {**context, "detected_command": cmd}
  - Returns: {success, command, message, frontend_action?, data?}
```

**Context Repair Logic (`fill_missing_fields`):**

```python
# File: command_router.py:74-111

# Fill session_id if missing
if cmd.get("type") == "session" and not cmd.get("session_id"):
    cmd["session_id"] = context.get("current_session_id")

# Fill trade_id if missing
if cmd.get("type") in ["trade", "chart"] and not cmd.get("trade_id"):
    detected_trade = context.get("detected_trade")
    if detected_trade:
        cmd["trade_id"] = detected_trade.get("id") or detected_trade.get("trade_id")

# Fill symbol from session context
if cmd.get("symbol") is None:
    session_context = context.get("session_context", {})
    if session_context and session_context.get("symbol"):
        cmd["symbol"] = session_context.get("symbol")
```

**Context Memory:**

- **No Central Context Manager:** Context is passed per-request via `cmd_context` dict in `app.py:487-493`
- **Current Trade State:** Stored in `server/data/session_contexts.json` → `current_trade_index` (for Teach Copilot only)
- **Session State:** Stored in IndexedDB (frontend) + `server/data/session_contexts.json` (backend)

**Context Dict Structure:**

```python
cmd_context = {
    **session_context,  # From /ask endpoint Form('context')
    'conversation_history': conversation_history,  # Last 50 messages
    'detected_trade': detected_trade,  # From trade_detector (if auto-detected)
    'all_trades': all_trades_for_context,  # From read_logs() or session_context
    'command_text': question  # Original user message
}
```

---

### 1.3 Trade Reference Resolution

**File:** `server/memory/system_commands.py`  
**Function:** `execute_view_trade_command(context)` (lines 1446-1717)

**Resolution Priority:**

1. **Intent Analyzer Arguments:**
   ```python
   arguments = detected_command.get('arguments', {})
   trade_id = arguments.get('trade_id')  # Numeric ID
   trade_reference = arguments.get('trade_reference', '').lower()  # "first", "last", "third", etc.
   ```

2. **Ordinal Numbers:**
   ```python
   ordinal_map = {
       'first': 1, 'second': 2, 'third': 3, ..., 'tenth': 10
   }
   if trade_reference in ordinal_map:
       ordinal_index = ordinal_map[trade_reference]
       sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time'), reverse=False)
       trade_id = sorted_trades[ordinal_index - 1].get('id')  # 1-based → 0-based index
   ```

3. **"First"/"Last"/"Recent":**
   ```python
   if trade_reference in ['first', 'last', 'recent']:
       sorted_trades = sorted(all_trades, key=get_timestamp_sort_key, reverse=(trade_reference == 'last'))
       trade_id = sorted_trades[0].get('id')
   ```

4. **Regex Fallback:**
   ```python
   # If Intent Analyzer arguments missing, fallback to regex
   id_match = re.search(r'(?:trade|#)\s*[#:]?\s*(\d+)', command_text, re.IGNORECASE)
   if id_match:
       extracted_id = int(id_match.group(1))
       # Try to find by ID first, then interpret as index if not found
   ```

5. **Detected Trade from Context:**
   ```python
   detected_trade = context.get('detected_trade')
   if detected_trade:
       trade_id = detected_trade.get('id') or detected_trade.get('trade_id')
   ```

**Issues:**
- ❌ "largest_loss" / "largest_win" not supported (no sorting by P&L)
- ❌ "previous" not normalized (should map to `current_trade_index - 1`)
- ⚠️ Multiple resolution paths create inconsistency

---

## 2️⃣ Trade Retrieval & Context Navigation

### 2.1 Trade ID/Index Mapping

**Files:**
- **Handler:** `server/memory/system_commands.py:1446` (`execute_view_trade_command`)
- **Trade Fetch:** `server/performance/routes.py:145` (`GET /performance/trades/{trade_id}`)
- **Data Source:** `server/performance/utils.py:25` (`read_logs()` → reads `performance_logs.json`)

**Trade Fetch Flow:**

```
execute_view_trade_command(context)
  ↓
trade_id resolved (from Intent Analyzer or fallback)
  ↓
Attempt 1: GET /performance/trades/{trade_id} (timeout: 30s)
  ↓
If 404: GET /performance/all (timeout: 30s) → find by ID
  ↓
If timeout: read_logs() → find by ID directly
  ↓
Trade object retrieved
```

**Trade Object Structure:**

```json
{
  "id": 1454625013,
  "trade_id": 1454625013,
  "session_id": "trade-1736789123456-abc123",
  "symbol": "SILZ5",
  "timestamp": "2025-01-10T10:38:57Z",
  "entry_time": "10/10/2025 10:38:57 -05:00",
  "outcome": "loss",
  "pnl": -160.00,
  "r_multiple": 0.0,
  "chart_path": "charts/SILZ5_5m_1454625013.png",
  "bias": "bearish",
  "setup_type": "Supply/Demand",
  "timeframe": "5m",
  "entry_price": 12345.67,
  "stop_loss": 12300.00,
  "take_profit": 12450.00
}
```

---

### 2.2 Chronological Order & Trade Index

**File:** `server/memory/system_commands.py:1446` (`execute_view_trade_command`)

**Sorting Logic:**

```python
# For ordinal numbers ("first", "second", "third"):
sorted_trades = sorted(all_trades, key=lambda t: t.get('timestamp') or t.get('entry_time') or '', reverse=False)
# Result: Oldest first (index 0 = first trade)

# For "last"/"recent":
sorted_trades = sorted(all_trades, key=get_timestamp_sort_key, reverse=True)
# Result: Newest first (index 0 = last trade)

# Timestamp parsing (get_timestamp_sort_key):
def get_timestamp_sort_key(trade):
    ts = trade.get('timestamp') or trade.get('entry_time') or ''
    if isinstance(ts, (int, float)):
        return ts
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.timestamp()
        except:
            try:
                return float(ts)
            except:
                return 0
    return 0
```

**Trade Index State:**

- **File:** `server/data/session_contexts.json`
- **Field:** `current_trade_index` (integer, 0-based)
- **Updated By:** `POST /teach/next` (increments), `execute_previous_trade_teaching_command()` (decrements)
- **Used For:** Teach Copilot navigation only

**Index Consistency Issues:**

- ❌ Trade index not synchronized with `list_trades` order
- ❌ Index-based lookup uses different sorting than ordinal lookup
- ❌ No validation that `current_trade_index` matches actual trade order

---

### 2.3 Trade Metadata Injection

**File:** `server/memory/system_commands.py:1644-1717` (`execute_view_trade_command`)

**Response Formatting:**

```python
if trade:
    symbol = trade.get('symbol', 'Unknown')
    outcome = trade.get('outcome', 'unknown')
    pnl = trade.get('pnl', 0)
    r_multiple = trade.get('r_multiple', 0)
    timestamp = trade.get('timestamp') or trade.get('entry_time')
    
    # Format message
    message = f"📊 Trade {trade_id} Details\n\n"
    message += f"Symbol: {symbol}\n"
    message += f"Outcome: {outcome}\n"
    message += f"P&L: ${pnl:.2f}\n"
    message += f"R-Multiple: {r_multiple:.2f}R\n"
    if timestamp:
        message += f"Timestamp: {format_timestamp(timestamp)}\n"
    
    # Attach chart URL
    chart_url = get_chart_url(trade)
    
    return {
        "success": True,
        "command": "view_trade",
        "message": message,
        "data": {
            "trade": trade,
            "chart_url": chart_url
        }
    }
```

**Chat Response Injection:**

- **Backend:** Returns `AskResponse` with `answer` field (formatted message)
- **Frontend:** Renders message in chat UI, extracts `chart_url` for "Show Chart" button
- **No Template System:** Messages formatted as plain text strings

---

### 2.4 Current Trade State Storage

**Storage Locations:**

1. **Teach Copilot Index:**
   - **File:** `server/data/session_contexts.json`
   - **Field:** `current_trade_index` (integer)
   - **Access:** `load_json()` / `save_json()` in `teach_router.py:68-77`
   - **Scope:** Teaching mode only

2. **Session Context:**
   - **File:** `server/data/session_contexts.json`
   - **Fields:** `teaching_active`, `partial_lesson`, `session_start`, `session_end`
   - **Scope:** Teaching session state

3. **Frontend Session State:**
   - **Storage:** IndexedDB (`window.IDB`)
   - **File:** `visual-trade-extension/content/idb.js`
   - **Scope:** UI session management (active session, messages)

**No Global Current Trade:**
- ❌ No centralized "current trade" state for non-teaching commands
- ❌ Each command resolves trade independently
- ❌ No persistence of "last viewed trade" across requests

---

## 3️⃣ Chart Service & Performance Flow

### 3.1 Chart File Serving

**Static File Serving:**

**File:** `server/app.py` (lines 85-89)  
**Endpoint:** `GET /charts/{filename}`  
**Type:** FastAPI `StaticFiles` mount

```python
from fastapi.staticfiles import StaticFiles

charts_dir = Path(__file__).parent / "data" / "charts"
if charts_dir.exists():
    app.mount("/charts", StaticFiles(directory=str(charts_dir)), name="charts")
```

**Request Flow:**

```
Frontend: window.openChartPopup("/charts/MNQZ5_5m_1540306142.png")
  ↓
GET /charts/MNQZ5_5m_1540306142.png
  ↓
FastAPI StaticFiles → server/data/charts/MNQZ5_5m_1540306142.png
  ↓
Returns PNG file (Content-Type: image/png)
```

**Caching:**
- ❌ No explicit cache headers
- ❌ No browser cache control
- ✅ FastAPI StaticFiles handles HTTP caching automatically

**Prefetching:**
- ❌ No prefetching for chart URLs
- ❌ Charts loaded on-demand when user clicks "Show Chart"

---

### 3.2 Chart Resolution (4-Priority System)

**File:** `server/utils/chart_service.py`  
**Function:** `resolve_chart_filename(trade)` (lines 72-154)

**Priority Order:**

1. **Direct `chart_path` Field:**
   ```python
   chart_path = trade.get('chart_path')  # e.g., "charts/MNQZ5_5m_1540306142.png"
   filename = Path(chart_path).name  # "MNQZ5_5m_1540306142.png"
   if (CHARTS_DIR / filename).exists():
       return filename
   ```

2. **Metadata API:**
   ```python
   response = requests.get(f"http://127.0.0.1:8765/charts/chart/{trade_id}", timeout=10.0)
   if response.ok:
       meta = response.json()
       chart_path = meta.get("chart_path")
       filename = Path(chart_path).name
       if (CHARTS_DIR / filename).exists():
           return filename
   ```
   - **Endpoint:** `GET /charts/chart/{trade_id}` (from `chart_reconstruction/routes.py:129`)
   - **Timeout:** 10 seconds (configurable via `CHART_METADATA_TIMEOUT_SEC`)
   - **Latency:** ~100-300ms per API call

3. **Pattern Matching:**
   ```python
   patterns = [
       "{symbol}_5m_{trade_id}.png",
       "{symbol}_15m_{trade_id}.png",
       "chart_{trade_id}.png"
   ]
   for pat in patterns:
       fname = pat.format(symbol=symbol, trade_id=trade_id)
       if (CHARTS_DIR / fname).exists():
           return fname
   ```
   - **Patterns:** Loaded from `config/chart_patterns.json`

4. **Glob Fallback:**
   ```python
   glob_pattern = f"{symbol}_*_{trade_id}*.png"
   matches = list(CHARTS_DIR.glob(glob_pattern))
   if matches:
       return sorted(matches)[0].name
   ```

**Latency Breakdown:**

- Priority 1 (direct): ~1-5ms (file existence check)
- Priority 2 (metadata API): ~100-300ms (HTTP call + timeout)
- Priority 3 (pattern matching): ~5-20ms (file system checks)
- Priority 4 (glob): ~10-50ms (directory scan)

**Performance Optimizations:**

- ✅ `get_chart_url_fast()` bypasses Priority 2-4 for bulk operations
- ❌ No caching of resolved chart URLs
- ❌ Metadata API calls not batched

---

### 3.3 Chart Request Flow (Frontend → Backend)

**Frontend Initiation:**

**File:** `visual-trade-extension/content/content.js`  
**Function:** `window.openChartPopup(chart_url)` (lines ~3374)

```javascript
window.openChartPopup = function(src) {
  // src = "/charts/MNQZ5_5m_1540306142.png"
  
  // Create side panel
  const sidePanel = document.createElement('div');
  sidePanel.id = 'vtc-chart-side-panel';
  
  // Load image
  const img = document.createElement('img');
  img.src = src;  // Triggers GET /charts/{filename}
  img.onload = () => { /* hide loading indicator */ };
  img.onerror = () => { /* show error */ };
  
  sidePanel.appendChild(img);
  document.body.appendChild(sidePanel);
}
```

**Backend Request Handling:**

- **Type:** Static file request (no Python handler)
- **Handler:** FastAPI `StaticFiles` middleware
- **Response Time:** ~10-50ms (file read + HTTP response)

**Chart Popup from Command:**

```
User: "show chart"
  ↓
Intent Analyzer → detects "show_chart"
  ↓
Command Router → execute_show_chart_command()
  ↓
Chart Service → get_chart_url(trade) → "/charts/MNQZ5_5m_1540306142.png"
  ↓
Return: {frontend_action: "show_chart_popup", chart_url: "/charts/..."}
  ↓
Frontend (background.js:186) → chrome.tabs.sendMessage({action: "executeFrontendAction"})
  ↓
Frontend (content.js:4146) → window.openChartPopup(chart_url)
```

---

### 3.4 Request Duration & Retry Logic

**Request Duration:**

- **Intent Analyzer:** ~500-1500ms (LLM call)
- **Trade Fetch:** ~100-500ms (HTTP or file read)
- **Chart Resolution:** ~1-300ms (depending on priority)
- **Total Command Execution:** ~600-2300ms

**Retry Logic:**

- ❌ No retry logic for Intent Analyzer failures
- ❌ No retry logic for chart resolution failures
- ⚠️ Timeout handling: Metadata API has 10s timeout, falls back to next priority
- ✅ Fallback chains: HTTP → file read → pattern matching → glob

**Model Switching:**

- ❌ No automatic model switching (mini → chat-latest)
- ✅ Model selection in `/ask` endpoint via `resolve_model()` function
- ✅ Intent Analyzer always uses `gpt-4o-mini` (fast, cost-effective)

---

## 4️⃣ Latency & Prefetching Mechanism

### 4.1 Latency Sources (20-30s Delay Analysis)

**Primary Latency Contributors:**

1. **Intent Analyzer LLM Call:**
   - **Time:** ~500-1500ms
   - **Location:** `intent_analyzer.py:123-154`
   - **Bottleneck:** OpenAI API response time

2. **Trade Fetch (HTTP):**
   - **Time:** ~200-500ms (if using HTTP endpoint)
   - **Location:** `system_commands.py:1623` (`GET /performance/trades/{trade_id}`)
   - **Timeout:** 30 seconds
   - **Fallback:** Direct file read (~50-200ms)

3. **Chart Metadata API:**
   - **Time:** ~100-300ms (if Priority 2 used)
   - **Location:** `chart_service.py:110-123`
   - **Timeout:** 10 seconds
   - **Impact:** Only used if `chart_path` missing

4. **File I/O Operations:**
   - **Time:** ~50-200ms (reading `performance_logs.json`)
   - **Location:** `performance/utils.py:25` (`read_logs()`)
   - **Bottleneck:** Large JSON file parsing

5. **Frontend Rendering:**
   - **Time:** ~100-500ms (DOM updates, chart image loading)
   - **Location:** `content.js` (UI rendering)

**Total Expected Latency:** ~950-3000ms (NOT 20-30s)

**Why 20-30s Delays Occur:**

- ⚠️ **HTTP Timeouts:** `/performance/trades/{trade_id}` has 30s timeout
- ⚠️ **Metadata API Timeout:** `/charts/chart/{trade_id}` has 10s timeout
- ⚠️ **No Caching:** Repeated requests fetch same data
- ⚠️ **Sequential Operations:** Each step waits for previous to complete

---

### 4.2 Prefetch & Caching

**Current State:**

**Trade Data:**
- ❌ No prefetching of `/performance/all`
- ❌ No caching of trade list
- ✅ `read_logs()` reads from file (fast, but no in-memory cache)

**Chart URLs:**
- ❌ No prefetching of chart URLs
- ❌ No caching of resolved chart paths
- ✅ `get_chart_url_fast()` optimizes bulk operations (bypasses API)

**Session Context:**
- ❌ No caching of `session_contexts.json`
- ✅ File read per request (`load_json()` in `teach_router.py:68`)

**Cache Components:**

- **Frontend:** No explicit cache (relies on browser cache for static files)
- **Backend:** No in-memory cache (file reads per request)
- **Service Worker:** Not used for caching

**Recommendations:**

- ✅ Add in-memory cache for `read_logs()` (TTL: 5-10 seconds)
- ✅ Prefetch chart URLs when listing trades
- ✅ Cache resolved chart paths (trade_id → filename mapping)

---

### 4.3 Cache Logic Components

**Frontend:**

- **File:** `visual-trade-extension/content/content.js`
- **Cache Type:** None (no explicit caching)
- **Browser Cache:** Automatic for static files (`/charts/*.png`)

**FastAPI Backend:**

- **File:** `server/app.py`, `server/performance/utils.py`
- **Cache Type:** None (file reads per request)
- **HTTP Cache:** No cache headers set

**Service Worker:**

- **File:** `visual-trade-extension/background.js`
- **Cache Type:** None (no service worker caching)

---

## 5️⃣ Trade Logging

### 5.1 Log Trade Feature Flow

**File:** `visual-trade-extension/content/content.js`  
**Function:** `logTradeBtn.onclick` (lines 1094-1202)

**Flow:**

```
User uploads chart image → Clicks "🖼 Log Trade" button
  ↓
content.js:1094 → Check if image uploaded (uploadedImageData)
  ↓
Extraction prompt sent to Vision API:
  {
    "symbol": "ticker symbol",
    "entry_price": 12345.67,
    "stop_loss": 12300.00,
    "take_profit": 12450.00,
    "bias": "bullish",
    "setup_type": "Supply/Demand",
    "timeframe": "5m"
  }
  ↓
chrome.runtime.sendMessage({action: "captureAndAnalyze", uploadedImage: uploadedImageData})
  ↓
background.js → POST /ask endpoint with image + extraction prompt
  ↓
OpenAI Vision API → Extracts trade details from chart
  ↓
Response parsed (JSON extraction from AI response)
  ↓
openTradeLogModal(extractedData) → Pre-fills form
  ↓
User submits form → POST /performance/trades
  ↓
TradeRecord model validates → Saved to performance_logs.json
```

**Why PNG Required:**

- **Vision API:** OpenAI Vision API accepts PNG, JPEG, GIF, WebP
- **Current Implementation:** No explicit format validation (accepts any image)
- **Reason:** Chart images are typically PNG (screenshots from trading platforms)

**Schema Validation:**

**File:** `server/performance/models.py`  
**Model:** `TradeRecord` (Pydantic BaseModel)

```python
class TradeRecord(BaseModel):
    session_id: str
    timestamp: str  # ISO format datetime string
    symbol: str
    timeframe: str
    bias: str
    setup_type: str
    ai_verdict: str
    user_action: str
    outcome: Optional[str] = None
    r_multiple: Optional[float] = None
    comments: Optional[str] = ""
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    expected_r: Optional[float] = None
```

**Validation Location:**

- **Endpoint:** `server/performance/routes.py:20` (`POST /performance/trades`)
- **Validation:** Pydantic model validation (automatic)
- **Error Handling:** FastAPI returns 422 if validation fails

**Trade Storage:**

**File:** `server/performance/utils.py:100` (`save_trade()`)

```python
def save_trade(trade: TradeRecord) -> Dict[str, Any]:
    logs = read_logs()
    trade_dict = trade.dict()
    
    # Add metadata
    trade_dict['id'] = len(logs) + 1
    trade_dict['created_at'] = datetime.utcnow().isoformat()
    
    logs.append(trade_dict)
    write_logs(logs)  # Writes to performance_logs.json
    
    return trade_dict
```

**File Location:** `server/data/performance_logs.json`

---

## Summary: Key Architectural Points

### Intent Analysis & Routing:
- ✅ LLM-based detection via `gpt-4o-mini` (~500-1500ms)
- ✅ Command validation & normalization via `command_router.py`
- ❌ No context memory manager (stateless per request)
- ⚠️ Multiple resolution paths create inconsistency

### Trade Retrieval:
- ✅ Trade fetch via HTTP endpoint (with file read fallback)
- ✅ Chronological sorting via timestamp parsing
- ❌ Index consistency issues (different sorting for ordinals vs. indices)
- ❌ No global "current trade" state

### Chart Service:
- ✅ 4-priority resolution system (direct → API → pattern → glob)
- ✅ Static file serving via FastAPI `StaticFiles`
- ❌ No caching of resolved chart URLs
- ⚠️ Metadata API adds ~100-300ms latency

### Latency & Caching:
- ❌ No prefetching for trades or charts
- ❌ No in-memory caching (file reads per request)
- ⚠️ HTTP timeouts (30s for trades, 10s for metadata) cause delays
- ✅ Fast bulk operations via `get_chart_url_fast()`

### Trade Logging:
- ✅ Vision API extraction for chart analysis
- ✅ Pydantic model validation
- ✅ File-based storage (`performance_logs.json`)
- ❌ No text-only logging (requires image upload)

---

**End of Architecture Breakdown**

