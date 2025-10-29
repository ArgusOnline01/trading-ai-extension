# Changelog

All notable changes to Visual Trade Copilot will be documented in this file.

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

