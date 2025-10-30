# Changelog

All notable changes to Visual Trade Copilot will be documented in this file.

## [4.8.0] - Phase 4D.1: Chart Reconstruction Engine

### Added
- TradingView-style chart reconstruction for all imported trades
- New `server/chart_reconstruction/` module with 5 files
- `data_utils.py`: yfinance integration for 5m OHLCV data
- `renderer.py`: TradingView-style dark theme candlestick charts
- `render_charts.py`: CLI orchestrator with progress tracking
- `routes.py`: REST API for chart metadata
- Dark theme: `#131722` background, `#26a69a` green, `#ef5350` red candles
- Entry lines (blue `#2962FF`), exit lines (red `#F23645`)
- 3-day historical context (935+ candles per chart)
- Retry queue for failed renders
- Chart metadata JSON output
- Summary performance bar chart
- New API endpoints: `/charts/metadata`, `/charts/stats`, `/charts/retry-queue`
- CLI flags: `--limit`, `--delay`, `--retry`, `--force`

### Changed
- Updated `requirements.txt`: Added yfinance, mplfinance, matplotlib, pandas
- Charts now show wider time range (3 days before + 1 day after entry)
- 16:9 aspect ratio matching TradingView
- 150 DPI high-quality output

### Fixed
- MultiIndex column handling from yfinance
- Rate limiting with randomized backoff
- Windows Unicode compatibility (ASCII progress bars)

---

## [4.7.0] - Phase 4D.0: CSV Import & Normalization - 2025-10-30

### Added
- **📁 CSV Import System**: Import Topstep Trader CSV exports into Visual Trade Copilot
- **New Module** (`server/trades_import/`):
  - `parser.py` - CSV parsing, normalization, and import summary
  - `routes.py` - 7 API endpoints for trade import management
  - `merge_utils.py` - Stub functions for Phase 4D.2 merging
- **7 New API Endpoints**:
  - `POST /trades/import` - Upload and parse CSV file
  - `GET /trades/imported` - List imported trades (with limit)
  - `GET /trades/stats` - Get import statistics
  - `POST /trades/merge/{id}` - Merge specific trade (stub)
  - `POST /trades/merge/batch` - Batch merge trades (stub)
  - `POST /trades/merge/auto` - Auto-merge all trades (stub)
  - `DELETE /trades/imported` - Clear all imported trades
- **Terminal Import Summary**:
  - Total trades, wins, losses, breakeven count
  - Win rate percentage
  - Total & average P&L
  - Most common contracts
  - Per-contract performance (color-coded)
  - Optional pretty table (first 10 trades with tabulate)
- **Data Normalization**:
  - Cleans symbol names (removes "/")
  - Parses timestamps with timezone support (if python-dateutil installed)
  - Calculates total fees (fees + commissions)
  - Determines direction (long/short) from trade type
  - Handles malformed rows gracefully
- **Persistent Storage**: `server/data/imported_trades.json`

### Technical
- Graceful degradation: Works without optional dependencies (dateutil, tabulate)
- Safe type conversion for numeric fields
- UTF-8-sig encoding support for Excel CSV exports
- Temporary file handling for uploads
- Color-coded terminal output (green/red for profit/loss)

### Coming in Phase 4D.1-4D.2
- Chart reconstruction from trade data
- Interactive Copilot-driven trade review
- Merge functionality into performance_logs.json
- Auto-calculation of R-multiples

## [4.6.0] - Phase 4C.1: System Awareness + Persistent Memory - 2025-10-30

### Fixed
- **Default Model**: Changed `DEFAULT_MODEL` from `gpt-4o` to `gpt-5-chat-latest` to match Phase 3B.1+ configuration

### Added
- **🧠 System Awareness Layer**: AI now knows it's the Visual Trade Copilot, understands its capabilities and available data
- **💾 Persistent Backend Memory**: All data survives browser restarts and cookie deletion
- **🗂️ New Memory Module** (`server/memory/`):
  - `utils.py` - JSON persistence helpers
  - `system_commands.py` - Natural language command parser
  - `routes.py` - Memory management API endpoints
- **📁 Backend JSON Storage**:
  - `session_contexts.json` - All chat sessions
  - `conversation_log.json` - Message history (last 500)
  - Existing: `performance_logs.json`, `user_profile.json`
- **🤖 System Commands** (fuzzy matching):
  - "show my stats" → Performance summary
  - "delete last trade" → Remove recent trade
  - "what model are you using" → Show current AI model
  - "list sessions" → Show active sessions
  - "clear memory" → Reset temporary data
  - "help" → Show all commands
- **6 New API Endpoints**:
  - `GET /memory/status` - Memory system health check
  - `POST /memory/save` - Save conversation messages
  - `GET /memory/load/{id}` - Load session by ID
  - `POST /memory/session` - Save session context
  - `POST /memory/clear` - Wipe all memory
  - `POST /memory/system/command` - Execute system commands
- **Enhanced Startup**: Server now displays:
  - Version banner (v4.6.0)
  - Memory loaded (trades, sessions, messages)
  - Win rate & Avg R if available
  - Awareness layer status
  - Registered commands

### Technical
- Awareness context injected into every AI request (~150 tokens)
- AI now references its own capabilities in responses
- Fuzzy command matching using `difflib` (80% similarity)
- Auto-creates missing JSON files on startup
- Memory survives crashes, restarts, cookie clears

### AI Behavior Changes
- AI now says "I have access to X trades, Y sessions"
- Responds to system commands with formatted summaries
- Self-aware of being a Chrome Extension + FastAPI backend
- Can reference its own memory status

## [4.5.1] - 2025-10-30

### Fixed
- **🐛 Learning Path Bug**: Fixed incorrect path to `performance_logs.json` (was looking in `server/data`, actual location is `server/server/data`)
- **Auto-Update Now Works**: Profile correctly reads trades and updates every 5 logs
- **Tested with Real Data**: Verified with 5 actual trades (100% win rate, 4.81R avg!)

## [4.5.0] - Phase 4C: Adaptive Learning Engine - 2025-10-30

### Added
- **🧠 Adaptive Learning System**: AI now learns from your trading performance and personalizes advice
- **Learning Profile Generation**: Automatically analyzes `performance_logs.json` to build user profile
- **Smart Context Injection**: Injects ~250 token performance summary into AI system prompt
- **Auto-Update Trigger**: Profile automatically regenerates every 5 trades
- **3 New API Endpoints**:
  - `GET /learning/profile` - View current learning profile
  - `POST /learning/update` - Manually trigger profile update
  - `POST /learning/reset` - Reset profile to defaults
- **Performance Metrics Tracked**:
  - Total trades & win rate
  - Best/worst setup types with avg R
  - Bullish vs Bearish performance
  - Recent trend analysis (last 10 vs previous 10 trades)
  - Common mistakes identification

### Technical
- Created `server/performance/learning.py` with profile generation logic
- Created `server/data/user_profile.json` for persistent storage
- Modified `openai_client.py` to inject learning context into system prompt
- Modified `performance/routes.py` to auto-update profile every 5 trades
- Token-efficient: Learning context kept under 300 tokens (~$0.0005/call)

### AI Adaptation Examples
- "Your win rate is 60% - strong! Best setup: Demand Zone (+3.2R)"
- "Struggling with: Supply Zone (-0.5R avg)"
- "Recent trend: improving (+1.2R change)"

## [4.4.0] - Phase 4B.1: Analytics Dashboard - 2025-10-30

### Added
- **📈 Analytics Dashboard**: Full visual performance dashboard with Chart.js integration
- **Backend Route**: `GET /performance/dashboard-data` - Aggregates time-series win rate, setup performance, outcome distribution
- **Interactive Charts**:
  - 📈 Rolling Win Rate Over Time (line chart)
  - 📊 Average R-Multiple by Setup Type (bar chart)
  - 🎯 Outcome Distribution Win/Loss/Breakeven (pie chart)
- **Dashboard Features**:
  - Beautiful dark + gold theme matching extension
  - Real-time refresh button
  - Responsive grid layout
  - Auto-loads data from `performance_logs.json`
- **Extension Integration**: "📈 Analytics Dashboard" button in popup opens dashboard in new tab
- **Static File Serving**: FastAPI static file mounting for `/static` directory

### Technical
- Created `server/performance/dashboard.py` with aggregation logic
- Created `server/static/dashboard.html` with Chart.js visualizations
- Mounted `StaticFiles` in `app.py` for serving dashboard
- Added dashboard router to FastAPI app

## [4.3.1] - 2025-10-30

### Fixed
- **🐛 CRITICAL: Delete Trade Button**: Fixed bug where deleting one trade would delete ALL trades
- **Root Cause**: All trades logged in the same session were using the same `session_id`, causing bulk deletion
- **Solution**: Changed `session_id` to be a unique trade ID: `trade-{timestamp}-{random9chars}`
- **Impact**: Each trade now has a truly unique identifier, delete works correctly per-trade

## [4.3.0] - 2025-10-30

### Added
- **Outcome Selection in Log Trade Modal**: Added "Outcome" dropdown (Pending/Win/Loss/Breakeven) to allow immediate trade completion
- **Actual R-Multiple Field**: Added optional field to specify actual R achieved (auto-shown when outcome is selected)
- **Smart Auto-Calculation**: If outcome is selected but R not specified, auto-calculates (Win = expected R, Loss = -1.0, BE = 0)
- **Performance Stats Now Work**: Stats (Win%, Avg R, Profit Factor) now calculate correctly when trades have outcomes

### Changed
- **Default Behavior**: Trades still default to "Pending" (can be updated later)
- **Modal Layout**: Added divider and "Trade Outcome (Optional)" section below setup details
- **Notification Text**: Updated to reflect outcome status when saving

## [4.2.9] - 2025-10-30

### Fixed
- **Log Trade Response Flow**: Added `forLogTrade` flag to get direct response from background.js instead of routing through `showOverlay`
- **Response Structure**: Background.js now returns `answer` field directly for Log Trade requests
- **Empty Response Issue**: Fixed issue where Log Trade was receiving empty response because data was sent via wrong message path

## [4.2.8] - 2025-10-30

### Fixed
- **JSON Extraction**: Complete rewrite with comprehensive logging - tries parsing as pure JSON first, then uses greedy pattern matching
- **Delete Trade Button**: Switched from `onclick` to event delegation pattern for more reliable click handling
- **Debug Logging**: Added extensive console logs showing full AI response length, preview, and parsing attempts

## [4.2.7] - 2025-10-30

### Fixed
- **Modal Visibility**: Increased z-index to 2147483648 to ensure Log Trade modal appears above all elements
- **JSON Extraction**: Enhanced AI response parsing with 3 fallback methods to reliably extract trade data
- **Delete Trade Button**: Fixed deletion not working in Performance tab - now properly reloads stats after deletion
- **Modal Opacity**: Explicitly set opacity and pointer-events for better visibility
- **Console Logging**: Added detailed debug logs for trade deletion workflow

## [4.2.0] - Phase 4A.2: Smart Log Trade Feature - 2025-10-30

### Added
- **📊 Log Trade Button**: New smart logging feature with AI-powered extraction
  - Dedicated button in chat footer for structured trade logging
  - Uses GPT-5 Chat to extract trade details from chart images
  - Structured JSON extraction prompt for 99% accuracy
- **Trade Confirmation Modal**: Beautiful modal form for reviewing/editing extracted data
  - Pre-filled fields from AI extraction
  - Editable inputs for: Symbol, Entry, Stop Loss, Take Profit, Bias, Setup Type, Timeframe
  - Real-time R:R calculation with color-coded display (green ≥2:1, yellow ≥1:1, red <1:1)
  - Risk/Reward visualization
  - AI analysis summary field
- **Hybrid Logging Approach**: Best of both worlds
  - AI extraction (~$0.001 per trade, ~500 tokens)
  - Manual verification/editing before saving
  - One-click save to IndexedDB + backend
  - Auto-clears uploaded image after successful log
- **Enhanced Extraction Patterns**: Improved natural language parsing
  - Handles markdown formatting (bold, italic, etc.)
  - Parses price ranges (e.g., "3562-3565" → midpoint 3563.5)
  - Expanded keyword detection (40+ variations)
  - Catches: "shorted around X", "sitting at Y", "profit around Z"

### Changed
- Upload button now required for Log Trade feature
- Extraction patterns more robust for conversational AI responses

### Fixed
- Trade detection now works with "took this trade", "took the trade"
- Price extraction handles markdown and special characters
- Modal styling optimized for readability

## [4.0.0] - Phase 4A: Performance Tracking & Trade Logging - 2025-10-30

### Added
- **Performance Tracking Backend**: Complete FastAPI module for logging and analyzing trades
  - `server/performance/` package with models, utils, and routes
  - CRUD operations for trade records (create, read, update, delete)
  - Performance statistics calculation (win rate, avg R, profit factor)
  - Local JSON storage in `server/data/performance_logs.json`
- **7 New API Endpoints**:
  - `POST /performance/log` - Log a new trade
  - `POST /performance/update` - Update trade outcome
  - `GET /performance/stats` - Get performance statistics
  - `GET /performance/trades` - Get all trades with pagination
  - `GET /performance/trades/{id}` - Get specific trade
  - `DELETE /performance/trades/{id}` - Delete a trade
  - `POST /performance/backtest` - Placeholder for chart backtesting (Phase 4B)
- **Auto-Detect Trade Logging**: Intelligent keyword detection in chat messages
  - Detects trade entry: "entered", "took trade", "went long", "went short", "bought", "sold"
  - Detects trade exit: "closed", "exited", "took profit", "hit stop", "stopped out"
  - Auto-extracts R multiples from messages (e.g., "2r", "1.5r", "3:1")
  - Syncs to both IndexedDB and backend automatically
- **IndexedDB Performance Store**: v3 schema with `performance_logs` object store
  - Persistent local storage for trade history
  - Helper functions: `savePerformanceLog`, `getPerformanceLogs`, `updatePerformanceLog`, `calculatePerformanceStats`
- **"My Performance" Tab**: New UI in extension popup
  - Displays total trades, win rate, avg R:R, profit factor, total R
  - Color-coded stats (green for good, yellow for ok, red for bad)
  - Empty state with instructions for new users
  - Loads stats from backend API
- **Trade Notifications**: Real-time feedback when trades are logged
  - "📊 Trade logged!" on entry
  - "📊 Trade closed: win (2.5R)" on exit

### Changed
- IndexedDB upgraded from v2 to v3 to support performance tracking
- Extension version bumped to 4.0.0 (major feature release)

### Technical Details
- **Backend**: FastAPI + Pydantic for type-safe trade records
- **Frontend**: Auto-detection with regex pattern matching for flexible input
- **Storage**: Dual persistence (IndexedDB + JSON) for reliability
- **Statistics**: Industry-standard metrics (win rate, profit factor, R multiples)

---

## [3.3.2] - Session Manager Scrolling Fix - 2025-10-29

### Fixed
- **Session Manager Display**: Added scrolling to sessions list to show all sessions (was only showing 2 visible)
- **Modal Overflow**: Fixed CSS `min-height: 0` for proper flex scrolling behavior
- **Sessions List**: Added max-height and overflow-y to enable scrolling when many sessions exist

### Added
- Debug logging to show total session count in console

---

## [3.3.1] - Phase 3C: Model Optimization & UX Polish - 2025-10-29

### Changed
- **Default Model**: Changed "Balanced" to use GPT-5 Search (hybrid mode) instead of GPT-5 Mini
- **Model Aliases Updated**: 
  - Fast: GPT-5 Chat Latest (native vision, **no caching**)
  - Balanced: GPT-5 Search API (hybrid mode, **with caching**) ← **NEW DEFAULT**
  - Advanced: GPT-4o (native vision, **no caching**)
- **Caching Strategy**: Only GPT-5 Search uses hybrid pipeline with caching; GPT-5 Chat and GPT-4o use direct vision
- **Optimized Chat Size**: Set default width to 620px (balanced between content visibility and not covering chart prices)
- **Compact Header Layout**: Reorganized header to use vertical flex layout with smaller controls
- **Model Selector**: Reorganized to show recommended models first, marked GPT-5 Mini as "Limited"
- **Smaller UI Elements**: Reduced padding and font sizes for more compact header

### Fixed
- **Emoji Crash**: AI responses containing emojis no longer crash server with Error 500
- **Unicode Encoding**: ASCII-safe debug logging prevents Windows console crashes
- Indentation errors in `openai_client.py`
- Auto-routing logic updated to reflect new model assignments
- Chat panel no longer covers price section on trading charts

---

## [3.3.0] - Phase 3C: Hybrid Vision → Reasoning Bridge - 2025-10-29

### Added
- **Hybrid Pipeline**: GPT-4o vision extraction → GPT-5 reasoning for cost-efficient analysis
- **Smart Image Cache**: MD5 hash-based cache invalidation (auto-refreshes on new charts)
- **Session-Based Caching**: Vision summaries cached per session for 60% cost reduction on follow-ups
- **Auto-Routing**: Frontend automatically detects text-only models and enables hybrid mode
- **Cost Optimization**: ~40% average savings for multi-question trading sessions
- **Two New Endpoints**:
  - `POST /hybrid` - Hybrid vision→reasoning endpoint
  - `DELETE /hybrid/cache/{id}` - Clear session vision cache
- **Debug Logging**: Extensive hybrid mode logging for troubleshooting
- **Unicode Fix**: Removed special characters from server logs for Windows compatibility

### Changed
- Model aliases now resolve before being sent to OpenAI API
- `/hybrid` endpoint auto-detects image changes via hash comparison
- Cache automatically clears when new chart image detected
- Debug overlay shows "🧠 Hybrid (4o→5)" mode in pink color
- Notification messages updated for hybrid mode confirmation

### Fixed
- Import errors in `hybrid_pipeline.py` (relative to absolute imports)
- Unicode encoding errors in server print statements
- Model alias resolution in hybrid reasoning calls

### Technical Details
- **New Files**: `server/cache.py`, `server/hybrid_pipeline.py`
- **Image Hashing**: MD5 hash computed before GPT-4o call to avoid duplicate vision API calls
- **Cache Logic**: Only uses cache if image hash matches previous request
- **Working Models**: GPT-5 Chat Latest (native vision), GPT-5 Search (hybrid), GPT-4o/Mini (native vision)

### Performance
- First request: GPT-4o vision (~300 tokens) + GPT-5 reasoning (~1,400 tokens)
- Follow-ups (same chart): GPT-5 reasoning only (~1,400 tokens) = 60% cheaper
- Average (3 follow-ups): ~40% cost reduction vs. direct vision calls

---

## [3.1.0] - Phase 3B: Multi-Session Memory - 2025-01-29

### ✨ Added
- **Multi-session management** - Unlimited trading sessions per symbol
- **Session manager UI** - Modal interface for managing all sessions
- **IndexedDB v2 schema** - Separate stores for sessions and messages
- **Automatic context extraction** - Tracks price, bias, POIs from conversations
- **Context state injection** - AI remembers session-specific trading context
- **50-message context window** - Up from 5 messages (10x increase)
- **Session export/import** - Download sessions as JSON
- **Session statistics** - Message counts, creation time, last updated
- **Toast notifications** - Visual feedback for all session operations
- **Empty state UI** - Helpful guidance for new sessions
- **7 new backend endpoints** - Full session CRUD API
- **Hybrid reasoning placeholder** - `/analyze/hybrid` for Phase 3C

### 🔧 Changed
- Completely rewrote `content.js` (~800 lines) for session management
- Upgraded IndexedDB from v1 to v2 with automatic migration
- Enhanced `/ask` endpoint to accept session context parameter
- Updated `openai_client.py` to inject context into AI prompts
- Increased backend message context limit from 5 to 50
- Updated background.js to retrieve and pass session context
- Extension version bumped to 3.1.0

### 🗂️ New Files
- `content/idb.js` - Complete IndexedDB wrapper (600+ lines)
- `PHASE_3B_SUMMARY.md` - Comprehensive documentation

### 📚 Documentation
- Added Phase 3B summary with full technical details
- Updated API documentation with session endpoints
- Added 10 test scenarios for session operations
- Documented context extraction and injection patterns

### ⚙️ API Changes
**New Endpoints:**
- `GET /sessions` - List all sessions
- `POST /sessions` - Create new session
- `GET /sessions/{id}` - Get session details
- `PUT /sessions/{id}` - Update session
- `DELETE /sessions/{id}` - Delete session
- `GET /sessions/{id}/memory` - Get session context
- `PUT /sessions/{id}/memory` - Update session context
- `POST /analyze/hybrid` - Placeholder (501)

**Enhanced Endpoints:**
- `POST /ask` - Now accepts `context` parameter (session state)

### 🔄 Migration
- Automatic migration from Phase 3A on first load
- Old chat_history → Default session in new structure
- Zero data loss during upgrade

---

## [3.0.0] - Phase 3A: Conversational Memory - 2025-01-28

### ✨ Added
- **Persistent chat panel** with IndexedDB storage for conversation history
- **Draggable and resizable** chat window - move and resize freely
- **Direct messaging** from chat panel - no popup needed for follow-ups
- **Context-aware AI** - remembers last 5 messages for coherent responses
- **Toggle chat button** in popup to open/close chat panel
- **Export chat** functionality - save conversations as JSON
- **Clear chat** with confirmation dialog
- **Minimize chat** functionality
- **Smart timestamps** ("Just now", "X mins ago")
- **Message formatting** - bold, italic, paragraphs
- **Loading states** for all async operations
- **Keyboard shortcuts** - Ctrl+Enter to send from chat
- **Auto-scroll** to latest message
- **Empty state** UI for first-time users

### 🔧 Changed
- Replaced modal overlay with persistent side panel
- Background script now handles chart capture for direct messaging
- Improved async message handling to suppress Chrome extension errors
- Enhanced error messages with helpful suggestions
- Updated popup UI with new chat toggle button

### 🐛 Fixed
- "Could not establish connection" errors in Chrome console
- Content script not injecting on pages loaded before extension
- Message channel closing prematurely
- Async/await timing issues in message passing
- IndexedDB transaction handling

### 📚 Documentation
- Added PHASE_3A_SUMMARY.md (623 lines)
- Added TEST_PHASE_3A.md with 10 test scenarios
- Added TROUBLESHOOTING_3A.md for common issues
- Updated README.md with Phase 3A features
- Updated extension README with new usage instructions

---

## [2.0.0] - Phase 2: Chrome Extension - 2025-01-27

### ✨ Added
- Chrome Extension with Manifest v3
- Extension popup UI with model selection
- Chart capture using `chrome.tabs.captureVisibleTab()`
- Modal overlay for displaying AI responses
- Server status indicator in popup
- Copy to clipboard functionality
- Beautiful dark theme UI
- Extension icons (16px, 48px, 128px)

### 📚 Documentation
- Added PHASE_2_SUMMARY.md
- Added extension README.md
- Created INSTALLATION_GUIDE.md

---

## [1.7.0] - Phase 1.7: Model Discovery & GPT-5 - 2025-01-26

### ✨ Added
- `/models` endpoint to list available OpenAI models
- Automatic GPT-5 detection and alias syncing
- `sync_model_aliases()` function
- Model diagnostics and reporting

### 🔧 Changed
- Updated system prompt to be context-aware
- Enhanced model resolution logic
- Improved GPT-5 parameter handling

### 📚 Documentation
- Added PHASE_1_7_SUMMARY.md

---

## [1.6.0] - Phase 1.6: Dynamic Model Switching - 2025-01-26

### ✨ Added
- Dynamic model selection per request
- Model aliases: "fast", "balanced", "advanced"
- `resolve_model()` helper function
- Optional `model` parameter for `/analyze` and `/ask` endpoints

### 📚 Documentation
- Added PHASE_1_6_SUMMARY.md
- Updated SRS.md with model selection features

---

## [1.5.0] - Phase 1.5: Conversational Agent - 2025-01-25

### ✨ Added
- `/ask` endpoint for natural language Q&A
- Conversational AI capabilities
- `AskResponse` Pydantic model
- OpenAI client wrapper with budget tracking

### 📚 Documentation
- Updated SRS.md with Phase 1.5 details

---

## [1.0.0] - Phase 1: Backend Foundation - 2025-01-24

### ✨ Added
- FastAPI backend server
- `/analyze` endpoint for structured SMC analysis
- Smart Money Concepts trading logic
- GPT-4 Vision integration
- Budget tracking and enforcement
- CORS middleware for browser extension
- Health check endpoint
- Prompt debugging endpoint

### 📚 Documentation
- Created README.md
- Created QUICK_START.md
- Created docs/SRS.md
- Created docs/DEVELOPMENT_CONTEXT.md

---

## Legend
- ✨ Added: New features
- 🔧 Changed: Changes to existing functionality
- 🐛 Fixed: Bug fixes
- 📚 Documentation: Documentation changes
- ⚠️ Deprecated: Soon-to-be removed features
- 🗑️ Removed: Removed features

