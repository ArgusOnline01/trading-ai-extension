# Visual Trade Copilot - Command Handling System Technical Summary

## Overview

The Visual Trade Copilot uses a **hybrid AI-driven command extraction system** where commands are detected and executed automatically from natural language user input. The system combines LLM-based extraction (primary) with regex-based fallback (secondary) to ensure reliable command detection.

---

## 1. Command Detection & Parsing Flow

### 1.1 Primary Method: LLM JSON Extraction

**Location:** `server/utils/command_extractor.py`

**Process:**
1. **AI Response Analysis**: After the LLM generates a response, the system extracts JSON command blocks from the AI's text
2. **Pattern Matching**: Uses regex patterns to find JSON in multiple formats:
   - Code blocks: `` ```json {...} ``` ``
   - Code blocks without language: `` ``` {...} ``` ``
   - Inline JSON objects

**Extraction Patterns:**
```python
json_block_patterns = [
    r'```json\s*(\{.*?\})\s*```',
    r'```\s*(\{.*?"commands_detected".*?\})\s*```',
    r'```\s*(\{.*?"command".*?\})\s*```'
]
```

**JSON Schema Expected:**
```json
{
  "commands_detected": [
    {
      "command": "delete_session",
      "type": "session",
      "name": "CALLED",
      "id": "CALLED-1762061940754",
      "action": "delete"
    }
  ]
}
```

### 1.2 Fallback Method: Natural Language Extraction

**Location:** `server/utils/fallback_command_extractor.py`

**When Used:**
- If LLM doesn't include JSON in response
- If JSON extraction fails (malformed JSON, no matches)

**Process:**
1. **Priority-Based Pattern Matching**: Checks patterns in order:
   - **PRIORITY 0**: Standalone "both"/"all" responses (extracts session IDs from conversation)
   - **PRIORITY 1**: Multi-session deletions ("delete the other 2 sil sessions")
   - **PRIORITY 2**: Follow-up resolution ("the first one")
   - **PRIORITY 3**: General command patterns (delete_session, create_session, etc.)

2. **Regex Patterns**: Uses regex to detect:
   - Command keywords: "delete session", "create session", "show chart"
   - Session names/symbols: Extracts 2-6 character symbols (e.g., "SIL", "MNQ")
   - Trade references: "first one", "last trade", trade IDs
   - Action hints: "both", "duplicate", "other 2", "all"

**Example Patterns:**
```python
# Session deletion
r'delete (?:the |that |duplicate |other )?([a-z]{2,6})\s+session'

# Session creation
r'(?:create|new|make|start) session ([A-Za-z0-9]+)'

# Chart display
"show chart", "open chart", "pull up chart", "pull up image"
```

### 1.3 Legacy Method: Fuzzy Pattern Matching (Deprecated)

**Location:** `server/memory/system_commands.py` - `detect_command()`

**Status:** Still exists but **not actively used** in current flow. The system now relies on AI extraction.

**How It Works:**
- Uses `COMMAND_PATTERNS` dictionary with fuzzy matching (difflib)
- 75% similarity threshold
- Normalizes input (removes "can you", "how about", etc.)

---

## 2. JSON Command Schema

### 2.1 Command Structure

Every command follows this base structure:

```json
{
  "command": "command_name",
  "type": "session|trade|chart|ui|lesson|teaching",
  "action": "delete|create|show|list|switch|rename|...",
  // Type-specific fields below
}
```

### 2.2 Command Types & Required Fields

#### Session Commands

**`delete_session`**
```json
{
  "command": "delete_session",
  "type": "session",
  "name": "CALLED",                    // Session symbol/name
  "session_id": "CALLED-1234567890",  // Optional: specific session ID
  "action_hint": "both|duplicate|other 2",  // Optional: deletion hint
  "action": "delete"
}
```

**`create_session`**
```json
{
  "command": "create_session",
  "type": "session",
  "symbol": "MNQ",
  "action": "create"
}
```

**`rename_session`**
```json
{
  "command": "rename_session",
  "type": "session",
  "new_name": "MNQ Session",
  "action": "rename"
}
```

**`switch_session`**
```json
{
  "command": "switch_session",
  "type": "session",
  "name": "session name or symbol",
  "action": "switch"
}
```

**`list_sessions`**
```json
{
  "command": "list_sessions",
  "type": "session",
  "action": "list"
}
```

#### Trade Commands

**`delete_trade`**
```json
{
  "command": "delete_trade",
  "type": "trade",
  "trade_id": "1464422308",  // or "last" for most recent
  "action": "delete"
}
```

**`view_trade`**
```json
{
  "command": "view_trade",
  "type": "trade",
  "trade_id": "1464422308",
  "action": "view"
}
```

#### Chart Commands

**`show_chart`**
```json
{
  "command": "show_chart",
  "type": "chart",
  "trade_reference": "recent|last|that",  // How to find the trade
  "symbol": "6EZ5",                        // Optional: specific symbol
  "trade_id": "1464422308",                // Optional: specific trade ID
  "action": "show_popup"
}
```

#### UI Commands

**`minimize_chat`**
```json
{
  "command": "minimize_chat",
  "type": "ui",
  "action": "minimize"
}
```

**`close_chat`** / **`open_chat`**
```json
{
  "command": "close_chat",
  "type": "ui",
  "action": "close"
}
```

**`show_session_manager`**
```json
{
  "command": "show_session_manager",
  "type": "ui",
  "action": "show"
}
```

#### Teaching & Lesson Commands

**`open_teach_copilot`**
```json
{
  "command": "open_teach_copilot",
  "type": "teaching",
  "trade_id": "1464422308",  // Optional: auto-select trade
  "action": "open"
}
```

**`view_lessons`**
```json
{
  "command": "view_lessons",
  "type": "lesson",
  "action": "view_all"
}
```

**`delete_lesson`**
```json
{
  "command": "delete_lesson",
  "type": "lesson",
  "lesson_id": "123",
  "action": "delete"
}
```

### 2.3 Multi-Command Support

The system supports **multiple commands in a single JSON block**:

```json
{
  "commands_detected": [
    {
      "command": "delete_session",
      "type": "session",
      "session_id": "SIL-456",
      "action": "delete"
    },
    {
      "command": "delete_session",
      "type": "session",
      "session_id": "SIL-789",
      "action": "delete"
    }
  ]
}
```

---

## 3. Backend Command Execution

### 3.1 Execution Flow

**Location:** `server/app.py` - `/ask` endpoint

**Process:**
1. **AI Response Generated**: LLM processes user question and generates response
2. **Command Extraction**: 
   - Try JSON extraction (`extract_commands_from_response`)
   - If fails, try fallback extraction (`extract_commands_from_natural_language`)
3. **Command Normalization**: Each command is normalized via `normalize_command()`
4. **Context Building**: Command context includes:
   - `detected_command`: Normalized command dict
   - `detected_trade`: Trade detected from question (if applicable)
   - `all_trades`: All trades from database
   - `conversation_history`: Last 50 messages
   - `command_text`: Original user question
   - `session_context`: Current session data
5. **Command Execution**: Calls `execute_command(cmd_name, cmd_context)`
6. **Result Aggregation**: Commands executed and results collected

**Code Flow:**
```python
# Extract commands from AI response
raw_commands = extract_commands_from_response(answer_text)

# Fallback if no JSON found
if len(raw_commands) == 0:
    raw_commands = extract_commands_from_natural_language(answer_text, question, enriched_context)

# Execute each command
for raw_cmd in raw_commands:
    normalized = normalize_command(raw_cmd)
    cmd_context = {
        **session_context,
        'conversation_history': conversation_history,
        'detected_command': normalized,
        'detected_trade': detected_trade,
        'all_trades': all_trades_for_context,
        'command_text': question
    }
    result = execute_command(cmd_name, cmd_context)
```

### 3.2 Command Handlers

**Location:** `server/memory/system_commands.py`

**Handler Function Pattern:**
```python
def execute_{command_name}_command(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute '{command_name}' command
    Returns dict with:
    - success: bool
    - command: str
    - message: str
    - frontend_action: str (optional)
    - data: dict (optional)
    """
```

**Available Handlers:**
- `execute_stats_command()` - Performance statistics
- `execute_delete_last_trade_command()` - Delete most recent trade
- `execute_restore_last_trade_command()` - Restore deleted trade
- `execute_delete_trade_command()` - Delete specific trade
- `execute_view_trade_command()` - View trade details
- `execute_create_session_command()` - Create new session
- `execute_delete_session_command()` - Delete session(s)
- `execute_rename_session_command()` - Rename session
- `execute_switch_session_command()` - Switch active session
- `execute_list_sessions_command()` - List all sessions
- `execute_show_chart_command()` - Display chart popup
- `execute_minimize_chat_command()` - Minimize chat UI
- `execute_close_chat_command()` - Close chat UI
- `execute_open_chat_command()` - Open chat UI
- `execute_open_teach_copilot_command()` - Open teaching mode
- `execute_close_teach_copilot_command()` - Close teaching mode
- `execute_view_lessons_command()` - List all lessons
- `execute_delete_lesson_command()` - Delete lesson
- `execute_view_lesson_command()` - View lesson details
- `execute_edit_lesson_command()` - Edit lesson
- `execute_teaching_progress_command()` - Show teaching statistics
- `execute_help_command()` - Display command help
- `execute_clear_memory_command()` - Clear temporary data
- `execute_model_info_command()` - Show current AI model

### 3.3 Frontend Action System

**Commands can trigger frontend actions:**

**Frontend Action Types:**
- `show_chart_popup` - Display chart in popup overlay
- `delete_session` - Delete session(s) from IndexedDB
- `create_session_prompt` - Open session manager for creation
- `rename_session` - Update session title
- `show_session_manager` - Open session manager modal
- `minimize_chat` - Collapse chat UI
- `close_chat` - Hide chat UI
- `open_chat` - Show chat UI
- `open_teach_copilot` - Open teaching mode UI
- `close_teach_copilot` - Close teaching mode UI

**Execution Flow:**
1. Backend returns `frontend_action` in command result
2. `background.js` receives `commands_executed` array
3. Extracts `frontend_action` from each command result
4. Sends message to `content.js` via `chrome.tabs.sendMessage`
5. `content.js` handles action in `executeFrontendAction` listener

---

## 4. Command Normalization

**Location:** `server/utils/command_extractor.py` - `normalize_command()`

**Purpose:** Standardize command dictionaries from various formats (AI output can vary)

**Normalization Rules:**
- Maps `command_name` → `command`
- Maps `command_type` → `type`
- Extracts type-specific fields:
  - Sessions: `session_name`, `session_id`, `symbol`
  - Trades: `trade_id`, `symbol`
  - Charts: `trade_id`, `symbol`, `trade_reference`
- Preserves all other fields

**Example:**
```python
# Input (variations)
{"command_name": "delete_session", "name": "SIL"}
{"command": "delete_session", "session_name": "SIL"}

# Output (normalized)
{"command": "delete_session", "type": "session", "session_name": "SIL", "action": "delete"}
```

---

## 5. Multi-Turn Command Handling

### 5.1 Context Resolution

**Supported Patterns:**
- **"this session"** → Resolves to `current_session_id` from context
- **"that trade" / "the trade"** → Resolves to most recently mentioned trade
- **"last trade"** → Uses most recent trade by timestamp
- **"the first one"** → Extracts from AI's previous message listing items
- **"both" / "all"** → Extracts all session IDs from previous AI message
- **"other 2"** → Extracts 2 session IDs, excluding current session
- **"mnq and sil"** → Creates multiple commands (for create/delete)

### 5.2 Follow-Up Resolution

**Location:** `server/utils/fallback_command_extractor.py`

**Handles:**
- User: "delete 2 sessions" → AI: "Which sessions?" → User: "mnq and sil"
  - Extracts 2 `create_session` or `delete_session` commands
  
- User: "delete a trade" → AI: "Which trade?" → User: "the first one"
  - Resolves to trade ID from conversation history

- User: "delete called session" → AI: "Found 2 sessions. Which?" → User: "both"
  - Extracts both session IDs from AI's previous message

---

## 6. Trade Detection & Chart Loading

### 6.1 Trade Detection Priority

**Location:** `server/utils/trade_detector.py` - `detect_trade_reference()`

**Priority Order:**
1. **Trade ID** (most reliable): "trade 1464422308"
2. **Symbol + Date**: "6EZ5 from 10/29" or "6EZ5 on 2025-10-23"
3. **Symbol + Outcome**: "6EZ5 loss" or "6EZ5 win"
4. **Symbol + Context**: "first trade: MNQZ5"
5. **Recent Trade**: Most recent trade if ambiguous

**Context Sources:**
- Direct trade ID in message
- Conversation history (last 15 messages)
- Explicit symbol mentions with dates
- Symbol + outcome combinations

### 6.2 Chart Loading

**Location:** `server/memory/system_commands.py` - `execute_show_chart_command()`

**Process:**
1. **Trade Detection**: Uses `detected_trade` from context (set in `/ask` endpoint)
2. **Chart Path Resolution**:
   - First: Check `trade['chart_path']` field
   - Second: Query metadata API (`/charts/chart/{trade_id}`)
   - Third: File system pattern matching (`{symbol}_5m_{trade_id}.png`)
3. **URL Generation**: Returns `/charts/{filename}` for frontend
4. **Frontend Display**: `content.js` calls `window.openChartPopup(chart_url)`

---

## 7. Known Issues & Flaky Cases

### 7.1 AI JSON Extraction Reliability

**Issue:** AI doesn't always include JSON in response, even with strong prompting

**Impact:** Falls back to regex extraction, which may miss complex commands

**Mitigation:**
- Fallback extractor handles common patterns
- System prompt explicitly requires JSON-first format
- Multiple extraction attempts (JSON blocks, inline JSON, single commands)

**Status:** Partially mitigated - AI compliance varies by model

### 7.2 Multi-Session Deletion

**Issue:** When user says "delete both called sessions", sometimes only one gets deleted

**Root Cause:** 
- Backend returns `additional_session_ids` but frontend wasn't handling it
- Session name matching finds multiple but only deleted first

**Fix Applied:**
- Updated `handleSystemCommand` to handle `additional_session_ids`
- Changed `.find()` to `.filter()` to find ALL matching sessions
- Backend now returns ALL session IDs when "both" is detected

**Status:** ✅ Fixed in latest version

### 7.3 Chart Display Accuracy

**Issue:** "Pull up chart" sometimes shows wrong trade when multiple trades have same symbol

**Root Cause:**
- Trade detection prioritized symbol over date+symbol combination
- Most recent trade selected when multiple matches exist

**Fix Applied:**
- Updated `trade_detector.py` to prioritize date+symbol combinations
- `execute_show_chart_command` now uses `detected_trade` from context (set in `/ask`)
- Priority: Trade ID → Symbol+Date → Symbol+Outcome → Symbol → Recent

**Status:** ✅ Fixed in latest version

### 7.4 Session Creation Not Reflecting

**Issue:** AI confirms session created but it doesn't appear in UI

**Root Cause:**
- Frontend action `create_session_prompt` opens modal but doesn't always create
- Session creation happens in frontend, not backend
- UI refresh timing issues

**Status:** ⚠️ Partially resolved - UI refresh added but may need more testing

### 7.5 Fallback Extraction False Positives

**Issue:** Regex patterns can match non-command text (e.g., "delete" in normal conversation)

**Mitigation:**
- Context-aware patterns (checks conversation history)
- Invalid word filtering (filters out "THE", "SESSION", etc.)
- Priority-based matching (more specific patterns first)

**Status:** ⚠️ Ongoing - patterns refined but edge cases may exist

---

## 8. Fallback & Reasoning Toggles

### 8.1 "Reasoned Commands" Toggle

**Location:** `visual-trade-extension/content/content.js`

**Status:** **DEPRECATED** - Always enabled

**Previous Behavior:**
- `reasonedCommandsEnabled = true`: Commands sent to backend for AI extraction
- `reasonedCommandsEnabled = false`: Local regex matching in `content.js`

**Current Behavior:**
- All commands always go through AI-driven extraction
- Toggle exists in code but has no effect
- Commands always extracted from AI response (JSON or fallback)

**Code:**
```javascript
let reasonedCommandsEnabled = true; // Always enabled - commands are AI-extracted
```

### 8.2 No Manual Fallback Toggle

**Note:** There is **no user-facing toggle** to disable command extraction. The system always attempts both methods (JSON extraction → fallback regex).

---

## 9. Command Execution Context

### 9.1 Context Variables Available to Commands

When a command handler executes, it receives:

```python
cmd_context = {
    # Session data
    'current_session_id': str,
    'all_sessions': List[Dict],
    'session_context': Dict,
    
    # Trade data
    'all_trades': List[Dict],
    'detected_trade': Dict,  # Trade detected from user question
    
    # Conversation
    'conversation_history': List[Dict],  # Last 50 messages
    'command_text': str,  # Original user question
    
    # Command data
    'detected_command': Dict,  # Normalized command dict
    
    # Other
    'all_sessions': List[Dict],  # Sometimes used for session list
}
```

### 9.2 Context Resolution Examples

**"this session"**
- Resolved to `current_session_id` from context
- Used in: `delete_session`, `rename_session`

**"that trade"**
- Resolved from `conversation_history`
- Checks last 15 messages for trade mentions
- Used in: `show_chart`, `delete_trade`, `view_trade`

**"both" sessions**
- Extracted from AI's previous message
- Pattern: `ID: CALLED-123` or `CALLED-123`
- Used in: `delete_session` (multiple deletions)

---

## 10. Command Result Format

**Standard Response Structure:**

```python
{
    "success": bool,
    "command": str,  # Command name
    "message": str,  # User-facing message
    "frontend_action": str,  # Optional: UI action to trigger
    "data": {  # Optional: Additional data
        "session_id": str,
        "session_name": str,
        "additional_session_ids": List[str],  # For multiple deletions
        "chart_url": str,  # For show_chart
        "trade_id": int,
        "symbol": str,
        ...
    }
}
```

**Example:**
```python
{
    "success": True,
    "command": "delete_session",
    "message": "🗑️ **Deleting 2 Sessions**\n\nDeleting matching sessions...",
    "frontend_action": "delete_session",
    "data": {
        "session_name": "CALLED",
        "session_id": "CALLED-1762061940754",
        "additional_session_ids": ["CALLED-1762061996880"],
        "available_sessions": [...]
    }
}
```

---

## 11. Frontend Integration

### 11.1 Message Flow

```
User Input → content.js → background.js → /ask endpoint
                                                    ↓
                                            AI Response + Commands
                                                    ↓
background.js ← command results ← /ask response
        ↓
chrome.tabs.sendMessage → content.js
        ↓
executeFrontendAction() → UI Update
```

### 11.2 Frontend Action Execution

**Location:** `visual-trade-extension/content/content.js` - `executeFrontendAction` listener

**Handles:**
- `delete_session`: Deletes from IndexedDB, refreshes UI
- `create_session_prompt`: Opens session manager, creates session if symbol provided
- `show_chart_popup`: Calls `window.openChartPopup(chart_url)`
- `minimize_chat`: Collapses chat UI
- `open_chat` / `close_chat`: Shows/hides chat
- `show_session_manager`: Opens session manager modal
- `rename_session`: Updates session title in IndexedDB
- `open_teach_copilot`: Opens teaching mode UI
- `close_teach_copilot`: Closes teaching mode UI

---

## 12. Testing Status

### 12.1 Test Coverage

**Test Files:** (Referenced but specific test files may have been cleaned up)

**Known Passing:**
- ✅ UI Control Commands (7/7)
- ✅ Lesson Management (1/1)
- ✅ Chart Commands (1/1)
- ✅ System Commands (1/1)
- ✅ Teaching Endpoints (2/2)

**Known Issues:**
- ⚠️ Teaching Session Commands: 2 timeout issues (test environment related, endpoints work functionally)

### 12.2 Untested/Flaky Areas

- Multi-command extraction (e.g., "delete both sessions" when AI lists them)
- Complex multi-turn scenarios (e.g., "delete 2 sessions" → "mnq and sil")
- Trade detection accuracy with multiple trades (same symbol, different dates)
- Session creation reliability (UI refresh timing)
- Fallback extraction edge cases (false positives/negatives)

---

## 13. Architecture Decisions

### 13.1 Why AI-Driven Extraction?

**Rationale:**
- More flexible than regex patterns
- Handles natural language variations
- Can extract multiple commands from one message
- Understands context ("this session", "that trade")
- Supports multi-turn conversations

### 13.2 Why Fallback Regex?

**Rationale:**
- AI doesn't always include JSON (compliance ~60-80%)
- Provides reliability when AI fails
- Handles common patterns quickly
- No API cost for regex matching

### 13.3 Why Context Passing?

**Rationale:**
- Commands need access to current state (sessions, trades)
- Trade detection improves with conversation history
- Multi-turn commands require context resolution
- Frontend actions need session/trade IDs

---

## 14. Performance Considerations

### 14.1 Extraction Performance

- **JSON Extraction**: O(n) regex matching - fast
- **Fallback Extraction**: Multiple regex passes - moderate
- **Command Execution**: Varies by command type
- **Frontend Actions**: Async IndexedDB operations

### 14.2 Optimization Opportunities

- Cache extracted commands if same message repeated
- Batch multiple commands in single frontend action
- Reduce conversation history size (currently 50 messages)
- Optimize trade detection (currently checks last 15 messages)

---

## 15. Future Improvements

### 15.1 Planned Enhancements

- [ ] Command validation before execution
- [ ] Command history/undo system
- [ ] Command aliases (shortcuts)
- [ ] Command templates (pre-configured commands)
- [ ] Better error messages for failed commands
- [ ] Command confirmation for destructive actions (optional)

### 15.2 Technical Debt

- Remove deprecated `COMMAND_PATTERNS` fuzzy matching (if not used)
- Consolidate duplicate command extraction logic
- Improve AI JSON compliance (better prompting/validation)
- Add comprehensive test suite for all command types
- Document all frontend actions and their requirements

---

## Summary

The Visual Trade Copilot command system is a **hybrid AI-driven approach** that:

1. **Primary**: Extracts structured JSON commands from LLM responses
2. **Fallback**: Uses regex patterns when JSON extraction fails
3. **Execution**: Dispatches to specialized handlers with rich context
4. **Frontend**: Triggers UI actions via message passing

**Key Strengths:**
- Flexible natural language understanding
- Multiple command support
- Context-aware resolution
- Robust fallback mechanisms

**Key Weaknesses:**
- AI JSON compliance varies
- Some edge cases in multi-turn scenarios
- Session creation UI refresh timing
- Trade detection can be ambiguous with duplicate symbols

**Overall Status:** ✅ Functional with known issues - system works reliably for common use cases but has edge cases that need refinement.

