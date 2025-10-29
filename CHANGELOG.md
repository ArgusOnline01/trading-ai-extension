# Changelog

All notable changes to Visual Trade Copilot will be documented in this file.

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

