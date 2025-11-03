# Phase 5F.1 Structural Audit - Visual Trade Copilot

**Date:** 2025-01-XX  
**Phase:** 5E → 5F.1 (Intent Analyzer + Unified Chart System)  
**Purpose:** Document current backend/frontend wiring and identify gaps

---

## Executive Summary

The system uses a **hybrid architecture**:
- **Phase 5E (Intent Analyzer)**: LLM-based command detection via `gpt-4o-mini`
- **Phase 5F.1 (Unified Chart Service)**: Centralized chart resolution via `chart_service.py`
- **Direct HTTP calls**: No queue/websocket; synchronous request/response pattern
- **Frontend Actions**: Command results trigger UI updates via Chrome message passing

---

## Feature Availability Matrix

| Feature | Status | Primary Files | Return Format | Latency Notes |
|---------|--------|---------------|---------------|---------------|
| **1. List All Trades** | ✅ Implemented | `system_commands.py:1231`, `app.py:496` | `{success, command, message, data: {trades[], count}}` | Fast (direct file read, ~50-200ms) |
| **2. Open Trade N** | ✅ Implemented | `system_commands.py:1446`, `command_router.py:158` | `{success, command, message, data: {trade, chart_url}}` | Medium (HTTP + fallback, ~200-500ms) |
| **3. Open Current Session Chart** | ⚙️ Partial | `system_commands.py:790`, `chart_service.py:157` | `{success, frontend_action: "show_chart_popup", chart_url}` | Medium (chart resolution, ~100-300ms) |
| **4. Create New Session/Chart** | ✅ Implemented | `system_commands.py:533`, `app.py:688`, `idb.js:101` | `{success, frontend_action: "create_session_prompt"}` | Fast (IndexedDB, ~50-100ms) |
| **5. Switch Between Trades** | ✅ Implemented | `system_commands.py:1286,1313`, `teach_router.py:62` | `{success, message, data: {trade_index, trade_id, chart_url}}` | Medium (file I/O, ~100-200ms) |
| **6. Bias/Direction Tracking** | ✅ Implemented | `performance/models.py:14`, `performance/routes.py:21` | Stored in `TradeRecord.bias` field | N/A (part of trade data) |
| **7. Chart-Triggered "Log This Trade"** | ✅ Implemented | `content.js:1094`, `app.py:313` | Manual form submission → `POST /performance/trades` | Fast (direct POST, ~100-200ms) |
| **8. Intent-Router (NL Commands)** | ✅ Implemented | `intent_analyzer.py:68`, `command_router.py:158` | `{is_command, confidence, commands_detected[]}` | Medium (LLM call, ~500-1500ms) |

**Legend:**
- ✅ **Implemented**: Fully functional with Intent Analyzer integration
- ⚙️ **Partial**: Works but missing some edge cases or optimizations
- 🚧 **Missing**: Not implemented or broken

---

## 1. List All Trades

### Status: ✅ Implemented

**Files:**
- **Controller**: `server/app.py:496` → Routes to `execute_list_trades_command()`
- **Handler**: `server/memory/system_commands.py:1231` (`execute_list_trades_command`)
- **Data Source**: `server/performance/utils.py` (`read_logs()` → reads `performance_logs.json`)
- **Chart Service**: `server/utils/chart_service.py:58` (`get_chart_url_fast`)

**Data Flow:**
```
User: "list my trades"
  ↓
/ask endpoint (app.py:457)
  ↓
Intent Analyzer (intent_analyzer.py:68) → detects "list_trades"
  ↓
Command Router (command_router.py:158) → routes to execute_list_trades_command()
  ↓
system_commands.py:1231 → read_logs() → attach chart_url via get_chart_url_fast()
  ↓
Return: {success: true, message: "...", data: {trades: [...], count: N}}
  ↓
Frontend: Renders trade rows with "🖼 Show Chart" buttons
```

**Return Format:**
```json
{
  "success": true,
  "command": "list_trades",
  "message": "📋 Found N trades.\n\nUse the 🖼 Show Chart button...",
  "data": {
    "trades": [
      {
        "id": 123456,
        "trade_id": 123456,
        "symbol": "MNQZ5",
        "outcome": "win",
        "pnl": 762.50,
        "r_multiple": 2.5,
        "timestamp": "2025-01-10T10:38:57Z",
        "chart_url": "/charts/MNQZ5_5m_123456.png"  // Optional, fast-resolved
      }
    ],
    "count": 25
  }
}
```

**Latency:** ~50-200ms (direct file read, no HTTP calls)

**Notes:**
- Uses `get_chart_url_fast()` (only checks `chart_path` field) for performance
- If `chart_url` missing, frontend resolves on-demand when user clicks "Show Chart"
- Sorted chronologically (oldest first)

---

## 2. Open Trade N

### Status: ✅ Implemented

**Files:**
- **Controller**: `server/app.py:496` → Routes via Intent Analyzer
- **Handler**: `server/memory/system_commands.py:1446` (`execute_view_trade_command`)
- **Chart Service**: `server/utils/chart_service.py:157` (`get_chart_url`)
- **Fallback**: `server/utils/trade_detector.py:32` (if Intent Analyzer fails)

**Data Flow:**
```
User: "show me my third trade" / "view trade #13" / "what was my latest trade"
  ↓
/ask endpoint (app.py:457)
  ↓
Intent Analyzer (intent_analyzer.py:68) → extracts:
  {
    "command": "view_trade",
    "arguments": {"trade_id": "13"} OR {"trade_reference": "third"/"last"}
  }
  ↓
Command Router (command_router.py:158) → routes to execute_view_trade_command()
  ↓
system_commands.py:1446 → Resolves trade_id:
  - Priority 1: arguments.trade_id (numeric)
  - Priority 2: arguments.trade_reference ("first", "last", "third", etc.)
  - Priority 3: Regex fallback on command_text
  - Priority 4: detected_trade from context
  ↓
Fetches trade: GET /performance/trades/{trade_id} (timeout: 30s)
  OR fallback: read_logs() → find by ID
  ↓
Attach chart_url via get_chart_url() (4-priority resolution)
  ↓
Return: {success: true, message: "Trade #N Details...", data: {trade, chart_url}}
```

**Return Format:**
```json
{
  "success": true,
  "command": "view_trade",
  "message": "📊 Trade 1454625013 Details\n\nSymbol: SILZ5\nOutcome: loss\nP&L: $-160.00\nR-Multiple: 0.00R\nTimestamp: 10/10/2025, 10:38:57 AM",
  "data": {
    "trade": {
      "id": 1454625013,
      "symbol": "SILZ5",
      "outcome": "loss",
      "pnl": -160.00,
      "r_multiple": 0.0,
      "timestamp": "2025-01-10T10:38:57Z",
      "chart_path": "charts/SILZ5_5m_1454625013.png"
    },
    "chart_url": "/charts/SILZ5_5m_1454625013.png"
  }
}
```

**Latency:** ~200-500ms (HTTP call + chart resolution, with fallback to file read)

**Notes:**
- Handles ordinal numbers ("first", "second", "third") via timestamp sorting
- Normalizes "latest" → "last"
- Falls back to regex if Intent Analyzer arguments missing
- Chart URL attached for frontend display

---

## 3. Open Current Session Chart

### Status: ⚙️ Partial

**Files:**
- **Handler**: `server/memory/system_commands.py:790` (`execute_show_chart_command`)
- **Chart Service**: `server/utils/chart_service.py:157` (`get_chart_url`)
- **Trade Detector**: `server/utils/trade_detector.py:32` (context resolution)
- **Frontend**: `visual-trade-extension/content/content.js:4052` (`executeFrontendAction` → `show_chart_popup`)

**Data Flow:**
```
User: "show chart" / "pull up its chart" / "display the chart"
  ↓
/ask endpoint (app.py:457)
  ↓
Intent Analyzer → detects "show_chart"
  ↓
Command Router → routes to execute_show_chart_command()
  ↓
system_commands.py:790 → Resolves trade:
  Priority 1: detected_trade from context (from /ask endpoint)
  Priority 2: detect_trade_reference() from conversation history
  Priority 3: Most recent trade as fallback
  ↓
chart_service.py:157 → get_chart_url() (4-priority resolution)
  ↓
Return: {success: true, frontend_action: "show_chart_popup", chart_url: "/charts/..."}
  ↓
Frontend (background.js:186) → Extracts frontend_action
  ↓
chrome.tabs.sendMessage({action: "executeFrontendAction", frontend_action: "show_chart_popup"})
  ↓
Frontend (content.js:4146) → window.openChartPopup(chart_url)
```

**Return Format:**
```json
{
  "success": true,
  "command": "show_chart",
  "message": "📊 Opening chart for MNQZ5 trade 123456...",
  "frontend_action": "show_chart_popup",
  "chart_url": "/charts/MNQZ5_5m_123456.png",
  "data": {
    "trade_id": 123456,
    "chart_url": "/charts/MNQZ5_5m_123456.png",
    "symbol": "MNQZ5"
  }
}
```

**Latency:** ~100-300ms (chart resolution + frontend action)

**Gaps:**
- ❌ No direct "current session chart" endpoint (relies on trade detection)
- ❌ Session context not always passed to chart resolution
- ✅ Chart popup works via frontend action

**Notes:**
- Chart resolution uses 4-priority system:
  1. `trade['chart_path']` field
  2. Metadata API (`/charts/chart/{trade_id}`)
  3. Pattern matching (`{symbol}_5m_{trade_id}.png`)
  4. Glob fallback

---

## 4. Create New Session / Chart

### Status: ✅ Implemented

**Files:**
- **Handler**: `server/memory/system_commands.py:533` (`execute_create_session_command`)
- **Backend API**: `server/app.py:688` (`POST /sessions`)
- **Frontend**: `visual-trade-extension/content/idb.js:101` (`createSession`)
- **Frontend Action**: `content.js:4069` (`create_session_prompt`)

**Data Flow:**
```
User: "create session MNQ" / "new session called 6E"
  ↓
/ask endpoint (app.py:457)
  ↓
Intent Analyzer → extracts:
  {
    "command": "create_session",
    "arguments": {"symbol": "MNQ"}
  }
  ↓
Command Router → routes to execute_create_session_command()
  ↓
system_commands.py:533 → Extracts symbol from arguments
  ↓
Return: {success: true, frontend_action: "create_session_prompt", data: {symbol: "MNQ"}}
  ↓
Frontend (content.js:4069) → Opens session manager modal OR directly creates via IDB
  ↓
IDB (idb.js:101) → createSession(symbol) → Stores in IndexedDB
  ↓
Session created with structure:
  {
    "sessionId": "MNQ-1736789123456",
    "symbol": "MNQ",
    "title": "MNQ Session",
    "created_at": 1736789123456,
    "context": {
      "bias": null,
      "latest_price": null,
      "last_poi": null,
      "timeframe": null,
      "notes": []
    }
  }
```

**Return Format:**
```json
{
  "success": true,
  "command": "create_session",
  "message": "➕ Creating MNQ Session\n\nOpening Session Manager...",
  "frontend_action": "create_session_prompt",
  "data": {
    "symbol": "MNQ"
  }
}
```

**Latency:** ~50-100ms (IndexedDB write)

**Notes:**
- Symbol extraction normalizes filler words ("CALLED", "THE", "A")
- Frontend handles actual creation (backend just triggers UI)
- Session context includes `bias`, `latest_price`, `last_poi` fields for future use

---

## 5. Switch Between Trades

### Status: ✅ Implemented

**Files:**
- **Handlers**: `server/memory/system_commands.py:1286,1313` (`execute_next_trade_teaching_command`, `execute_previous_trade_teaching_command`)
- **Backend API**: `server/routers/teach_router.py:62` (`POST /teach/next`)
- **State Storage**: `server/data/session_contexts.json` (`current_trade_index`)
- **Frontend**: `visual-trade-extension/content/content.js:2238` (`loadTeachCopilotTrades`)

**Data Flow:**
```
User: "next trade" / "previous trade"
  ↓
/ask endpoint (app.py:457)
  ↓
Intent Analyzer → detects "next_trade_teaching" / "previous_trade_teaching"
  ↓
Command Router → routes to execute_next_trade_teaching_command()
  ↓
system_commands.py:1286 → POST /teach/next
  ↓
teach_router.py:62 → Updates session_contexts.json:
  current_trade_index = current_trade_index + 1
  ↓
Returns: {status: "ready", trade_index: N}
  ↓
system_commands.py:1293 → Fetches trade at index N:
  GET /performance/all → trades[N]
  ↓
Attach chart_url via get_chart_url()
  ↓
Return: {success: true, message: "➡️ Moved to trade index N", data: {trade_index, trade_id, chart_url}}
```

**Return Format:**
```json
{
  "success": true,
  "command": "next_trade_teaching",
  "message": "➡️ Moved to trade index 5",
  "data": {
    "trade_index": 5,
    "trade_id": 1454625013,
    "chart_url": "/charts/SILZ5_5m_1454625013.png"
  }
}
```

**Latency:** ~100-200ms (file I/O for state update + trade fetch)

**Notes:**
- State persists in `session_contexts.json`
- `previous_trade_teaching` decrements index (with bounds check)
- Chart URL attached for frontend display
- Used primarily in Teach Copilot mode

---

## 6. Bias / Direction Tracking

### Status: ✅ Implemented

**Files:**
- **Model**: `server/performance/models.py:14` (`TradeRecord.bias`)
- **Storage**: `server/data/performance_logs.json` (each trade has `bias` field)
- **Session Context**: `server/app.py:710` (session.context.bias)
- **Chart Extraction**: `visual-trade-extension/content/content.js:1118` (Log Trade form)

**Data Flow:**
```
User uploads chart → Clicks "Log Trade" button
  ↓
content.js:1094 → Extracts bias from chart via Vision API:
  {
    "symbol": "MNQZ5",
    "entry_price": 12345.67,
    "stop_loss": 12300.00,
    "take_profit": 12450.00,
    "bias": "bullish",  // ← Extracted from chart analysis
    "setup_type": "Supply/Demand",
    "timeframe": "5m"
  }
  ↓
POST /performance/trades (performance/routes.py:21)
  ↓
TradeRecord model validates → Stores in performance_logs.json:
  {
    "id": 123456,
    "symbol": "MNQZ5",
    "bias": "bullish",  // ← Stored here
    "setup_type": "Supply/Demand",
    "entry_price": 12345.67,
    ...
  }
```

**Storage Format:**
- **Trade Records**: `performance_logs.json` → Each trade has `bias: "bullish" | "bearish" | "neutral"`
- **Session Context**: `session_contexts.json` → `context.bias` (for active session)
- **Model**: `TradeRecord.bias: str` (optional, defaults to `None`)

**Notes:**
- Bias extracted from chart analysis (Vision API)
- Stored in trade records for historical tracking
- Session context maintains current bias for active session
- Used for filtering/analysis queries

---

## 7. Chart-Triggered "Log This Trade"

### Status: ✅ Implemented

**Files:**
- **Frontend Form**: `visual-trade-extension/content/content.js:1094` (Log Trade button)
- **Backend API**: `server/performance/routes.py:21` (`POST /performance/trades`)
- **Model**: `server/performance/models.py:6` (`TradeRecord`)
- **Storage**: `server/data/performance_logs.json`

**Data Flow:**
```
User uploads chart image → Clicks "🖼 Log Trade" button
  ↓
content.js:1094 → Extracts trade details via Vision API:
  {
    "symbol": "MNQZ5",
    "entry_price": 12345.67,
    "stop_loss": 12300.00,
    "take_profit": 12450.00,
    "bias": "bullish",
    "setup_type": "Supply/Demand",
    "timeframe": "5m"
  }
  ↓
Form submission → POST /performance/trades
  ↓
performance/routes.py:21 → Validates TradeRecord model
  ↓
save_trade() → Writes to performance_logs.json:
  {
    "session_id": "trade-1736789123456-abc123",
    "timestamp": "2025-01-10T10:38:57Z",
    "symbol": "MNQZ5",
    "timeframe": "5m",
    "bias": "bullish",
    "setup_type": "Supply/Demand",
    "entry_price": 12345.67,
    "stop_loss": 12300.00,
    "take_profit": 12450.00,
    "expected_r": 2.5,
    "outcome": null,  // To be updated later
    "r_multiple": null
  }
  ↓
Returns: {status: "saved", trade_id: 123456}
```

**Return Format:**
```json
{
  "status": "saved",
  "trade_id": 123456,
  "message": "Trade logged successfully"
}
```

**Latency:** ~100-200ms (Vision API extraction + file write)

**Notes:**
- Chart image sent to Vision API for price extraction
- Bias, setup_type, timeframe extracted from chart analysis
- Trade stored as "pending" until outcome updated
- Chart path stored separately (not linked in initial log)

---

## 8. Intent-Router (Natural Language Command Handling)

### Status: ✅ Implemented

**Files:**
- **Intent Analyzer**: `server/ai/intent_analyzer.py:68` (`analyze_intent`)
- **Prompt**: `server/config/intent_prompt.txt` (system prompt with examples)
- **Command Router**: `server/utils/command_router.py:158` (`route_command`)
- **Command Handlers**: `server/memory/system_commands.py` (execute_*_command functions)
- **Frontend Integration**: `visual-trade-extension/background.js:186` (frontend action execution)

**Data Flow:**
```
User: "list my trades" / "show me my third trade" / "create session MNQ"
  ↓
Frontend → POST /ask (app.py:313)
  ↓
app.py:457 → analyze_intent(user_text, conversation_history)
  ↓
intent_analyzer.py:68 → Calls OpenAI API (gpt-4o-mini, temperature=0.1, max_tokens=500):
  {
    "is_command": true,
    "confidence": 0.92,
    "commands_detected": [
      {
        "command": "list_trades",
        "type": "trade",
        "action": "list"
      }
    ]
  }
  ↓
app.py:496 → If is_command && confidence >= 0.5:
  For each command in commands_detected:
    command_router.py:158 → route_command(raw_cmd, context)
      ↓
    Step 1: Validate schema (validate_command_schema)
    Step 2: Normalize command (normalize_command)
    Step 3: Fill missing fields (fill_missing_fields)
    Step 4: Find handler (execute_{command_name}_command)
    Step 5: Execute handler with context
      ↓
    Returns: {success, command, message, frontend_action?, data?}
  ↓
app.py:551 → Return AskResponse:
  {
    "model": "intent-analyzer",
    "answer": "Command executed successfully.",
    "commands_executed": [
      {
        "command": "list_trades",
        "result": {...}
      }
    ],
    "summary": "✅ list_trades: 📋 Found 25 trades..."
  }
  ↓
Frontend (background.js:186) → Extracts frontend_action from commands_executed
  ↓
chrome.tabs.sendMessage({action: "executeFrontendAction", frontend_action: "show_chart_popup"})
  ↓
Frontend (content.js:4146) → Executes UI action
```

**Intent Analyzer Connection:**
- **Type**: Direct HTTP call (no queue/websocket)
- **Endpoint**: `/ask` (app.py:313)
- **Model**: `gpt-4o-mini` (fast, cost-effective)
- **Response Format**: JSON (`response_format={"type": "json_object"}`)
- **Latency**: ~500-1500ms (LLM inference time)
- **Confidence Threshold**: 0.5 (configurable via `INTENT_CONFIDENCE_THRESHOLD` env var)

**Command Schema:**
```json
{
  "command": "string",        // e.g., "list_trades", "view_trade"
  "type": "session|trade|chart|ui|lesson|teaching|performance",
  "action": "string",          // e.g., "list", "view", "create", "delete"
  "arguments": {               // Optional, extracted from user text
    "trade_id": "13",
    "trade_reference": "third",
    "symbol": "MNQ",
    "session_id": "..."
  }
}
```

**Frontend Action Types:**
- `show_chart_popup` - Display chart overlay
- `create_session_prompt` - Open session manager
- `show_session_manager` - Open session manager modal
- `open_teach_copilot` - Open teaching mode UI
- `close_teach_copilot` - Close teaching mode UI
- `minimize_chat` - Collapse chat UI
- `close_chat` - Hide chat UI

**Notes:**
- Intent Analyzer uses last 3 conversation messages for context (optimized for speed)
- Commands are deduplicated via `merge_multi_commands()`
- Frontend actions executed asynchronously via Chrome message passing
- Fallback to regex/keyword matching if Intent Analyzer fails (legacy code)

---

## Intent Analyzer → Backend Endpoint Mapping

### Connection Pattern: Direct HTTP Calls (No Queue/Websocket)

**Flow:**
```
Intent Analyzer (intent_analyzer.py:68)
  ↓
Command Router (command_router.py:158)
  ↓
Command Handlers (system_commands.py:execute_*_command)
  ↓
Backend Endpoints (app.py, routers/*.py)
```

**Endpoint Mapping:**

| Command | Handler Function | Backend Endpoint | HTTP Method |
|---------|------------------|------------------|-------------|
| `list_trades` | `execute_list_trades_command()` | Direct file read (`read_logs()`) | N/A |
| `view_trade` | `execute_view_trade_command()` | `GET /performance/trades/{trade_id}` | GET |
| `show_chart` | `execute_show_chart_command()` | Chart service (no HTTP endpoint) | N/A |
| `create_session` | `execute_create_session_command()` | Frontend action only | N/A |
| `delete_session` | `execute_delete_session_command()` | Frontend action only | N/A |
| `next_trade_teaching` | `execute_next_trade_teaching_command()` | `POST /teach/next` | POST |
| `previous_trade_teaching` | `execute_previous_trade_teaching_command()` | Direct file write | N/A |

**Key Observations:**
- **No queue system**: Commands execute synchronously in request/response cycle
- **No websocket**: All communication via HTTP POST/GET
- **Direct calls**: Handlers call endpoints directly (e.g., `requests.get()`)
- **Frontend actions**: Some commands bypass backend endpoints (e.g., `create_session` triggers frontend UI)

---

## Chart Data Storage & Linking

### Chart File Storage

**Location:** `server/data/charts/` (directory)

**Naming Patterns:** (from `config/chart_patterns.json`)
- `{symbol}_5m_{trade_id}.png`
- `{symbol}_15m_{trade_id}.png`
- `chart_{trade_id}.png`

**Resolution Priority:** (from `chart_service.py:72`)
1. `trade['chart_path']` field (normalized to filename)
2. Metadata API (`GET /charts/chart/{trade_id}`)
3. Pattern matching (deterministic)
4. Glob fallback (allows postfix variations)

### Chart Data Linking

**Trade Object Structure:**
```json
{
  "id": 123456,
  "trade_id": 123456,
  "symbol": "MNQZ5",
  "chart_path": "charts/MNQZ5_5m_123456.png",  // ← Stored here
  "timestamp": "2025-01-10T10:38:57Z",
  ...
}
```

**Chart Metadata:** (if available via `/charts/chart/{trade_id}`)
```json
{
  "trade_id": 123456,
  "chart_path": "/full/path/to/charts/MNQZ5_5m_123456.png",
  "symbol": "MNQZ5",
  "timeframe": "5m"
}
```

**Chart Data (POIs, FVGs, Bias):**
- **POIs/FVGs**: Not stored in chart files (images only)
- **Bias**: Stored in trade object (`trade.bias`), not in chart metadata
- **Session Context**: Stored separately in `session_contexts.json` → `context.bias`

**Gaps:**
- ❌ No chart metadata API for POIs/FVGs (charts are PNG images only)
- ❌ Chart annotations not stored separately
- ✅ Bias stored in trade object (not linked to chart file)

---

## Observed Gaps & Missing Integrations

### 1. Chart Data (POIs, FVGs, Bias) Storage
- **Status**: 🚧 Missing
- **Issue**: Charts stored as PNG images only; no metadata for POIs/FVGs
- **Impact**: Cannot retrieve chart annotations separately from trade data
- **Recommendation**: Add chart metadata API or store annotations in trade object

### 2. Session Chart Endpoint
- **Status**: ⚙️ Partial
- **Issue**: No direct "get current session chart" endpoint
- **Impact**: Must rely on trade detection to find session chart
- **Recommendation**: Add `GET /sessions/{session_id}/chart` endpoint

### 3. Async Command Execution
- **Status**: 🚧 Missing
- **Issue**: Commands execute synchronously (blocks request)
- **Impact**: Long-running commands (e.g., chart generation) block UI
- **Recommendation**: Add command queue with async execution

### 4. Frontend Action Error Handling
- **Status**: ⚙️ Partial
- **Issue**: Frontend actions fail silently if handler missing
- **Impact**: User sees no feedback if action fails
- **Recommendation**: Add error handling and user feedback

### 5. Chart URL Resolution Latency
- **Status**: ⚙️ Partial
- **Issue**: Metadata API calls add ~100-300ms latency
- **Impact**: Chart popup delays when chart_path missing
- **Recommendation**: Cache chart metadata or pre-resolve URLs

### 6. Trade Detection Consistency
- **Status**: ⚙️ Partial
- **Issue**: Multiple detection paths (Intent Analyzer, regex, trade_detector)
- **Impact**: Inconsistent trade resolution across commands
- **Recommendation**: Unify detection via Intent Analyzer only

### 7. Session Context Passing
- **Status**: ⚙️ Partial
- **Issue**: Session context not always passed to chart resolution
- **Impact**: Chart resolution may fail for session-scoped queries
- **Recommendation**: Always include session context in command context

### 8. Command Deduplication
- **Status**: ✅ Implemented
- **Note**: `merge_multi_commands()` handles duplicates correctly

### 9. Chart-Trade Linkage
- **Status**: ✅ Implemented
- **Note**: Chart paths stored in trade objects; resolution works correctly

### 10. Intent Analyzer Fallback
- **Status**: ⚙️ Partial
- **Issue**: Legacy regex/keyword matching still active
- **Impact**: Commands may bypass Intent Analyzer in edge cases
- **Recommendation**: Remove legacy fallback after full Intent Analyzer migration

---

## Summary

**Strengths:**
- ✅ Intent Analyzer provides reliable command detection
- ✅ Unified chart service centralizes chart resolution
- ✅ Frontend actions enable UI updates from commands
- ✅ Trade switching works correctly in Teach Copilot mode
- ✅ Bias tracking stored in trade records

**Weaknesses:**
- ⚠️ No chart metadata API for POIs/FVGs
- ⚠️ Session chart resolution relies on trade detection
- ⚠️ Synchronous command execution blocks requests
- ⚠️ Multiple detection paths create inconsistency

**Recommendations:**
1. Add chart metadata API for annotations
2. Create direct session chart endpoint
3. Implement async command queue for long-running operations
4. Unify trade detection via Intent Analyzer only
5. Add error handling for frontend actions

---

**End of Audit**

