# Visual Trade Copilot - Software Requirements Specification (SRS)

**Version:** 5.2.0  
**Date:** December 2024  
**Status:** Production Ready - Interactive Teaching Mode Complete

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Features](#3-system-features)
4. [External Interface Requirements](#4-external-interface-requirements)
5. [System Architecture](#5-system-architecture)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Data Requirements](#8-data-requirements)
9. [User Interface Requirements](#9-user-interface-requirements)
10. [Performance Requirements](#10-performance-requirements)
11. [Security Requirements](#11-security-requirements)
12. [API Specifications](#12-api-specifications)
13. [Use Cases](#13-use-cases)
14. [Testing Requirements](#14-testing-requirements)
15. [Future Enhancements](#15-future-enhancements)

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) documents the functional and non-functional requirements for **Visual Trade Copilot**, an AI-powered trading assistant that provides real-time Smart Money Concepts (SMC) analysis using GPT-4o and GPT-5 vision models.

### 1.2 Scope
Visual Trade Copilot consists of:
- **Backend:** FastAPI server with 36+ REST API endpoints
- **Frontend:** Chrome Extension (Manifest v3) with persistent chat interface
- **AI Integration:** OpenAI GPT-4o/GPT-5 vision models for chart analysis
- **Data Management:** JSON-based persistent storage for trades, sessions, and teaching data

### 1.3 Definitions and Acronyms
- **SMC:** Smart Money Concepts (trading methodology)
- **BOS:** Break of Structure
- **POI:** Price of Interest
- **FVG:** Fair Value Gap
- **R-Multiple:** Risk-to-reward ratio
- **PnL:** Profit and Loss
- **IDB:** IndexedDB (browser storage API)

### 1.4 References
- OpenAI API Documentation
- Chrome Extensions Manifest v3
- FastAPI Documentation
- Smart Money Concepts Methodology

### 1.5 Overview
This document is organized into 15 sections covering all aspects of the system from high-level features to detailed API specifications.

---

## 2. Overall Description

### 2.1 Product Perspective
Visual Trade Copilot is a standalone application consisting of:
- **Backend Server:** FastAPI application running on `http://127.0.0.1:8765`
- **Chrome Extension:** Browser-based UI for chart capture and chat interaction
- **Data Storage:** Local JSON files and browser IndexedDB for persistence

### 2.2 Product Functions
The system provides:
1. **Real-time Chart Analysis** using AI vision models
2. **Conversational Trading Assistant** with persistent memory
3. **Performance Tracking** with win rate, R-multiples, and statistics
4. **Trade Import** from CSV files (Topstep Trader format)
5. **Chart Reconstruction** with TradingView-style visualization
6. **Interactive Teaching Mode** for AI dataset preparation
7. **System Command Recognition** via natural language processing

### 2.3 User Classes
- **Primary:** Retail traders using Smart Money Concepts
- **Secondary:** Trading educators preparing training datasets
- **Tertiary:** Developers extending the platform

### 2.4 Operating Environment
- **Server:** Python 3.8+ on Windows/macOS/Linux
- **Client:** Google Chrome or Chromium-based browser (Manifest v3)
- **Network:** Localhost (127.0.0.1:8765) or configurable port
- **Dependencies:** OpenAI API key with GPT-4o/GPT-5 access

### 2.5 Design and Implementation Constraints
- Must use Chrome Extension Manifest v3 (not v2)
- OpenAI API rate limits and cost constraints
- Local-first architecture (no cloud database)
- Browser IndexedDB limitations (~50MB storage)

### 2.6 Assumptions and Dependencies
- Users have OpenAI API key with sufficient credits
- Users are familiar with Smart Money Concepts terminology
- Users have Python 3.8+ installed
- Chrome browser is available and up-to-date

---

## 3. System Features

### 3.1 Core Chart Analysis (Phase 1)

**3.1.1 Real-time Chart Analysis**
- **Description:** Analyze trading charts using GPT-4o/GPT-5 Vision API
- **Input:** Chart image (PNG/JPG format)
- **Output:** Structured SMC analysis (bias, POI, BOS, FVG, displacement)
- **Processing:** AI model analyzes image and returns structured JSON
- **Performance:** 2-8 seconds depending on model selected

**3.1.2 Smart Money Concepts Detection**
- Market bias detection (bullish/bearish/neutral)
- Point of Interest (POI) identification
- Break of Structure (BOS) detection
- Liquidity sweep identification
- Fair Value Gap (FVG) detection
- Displacement analysis
- 50% mitigation level calculation

**3.1.3 Model Selection**
- **Fast Mode:** GPT-4o-mini (2-3s, $0.001/1K tokens)
- **Balanced Mode:** GPT-4o (3-5s, $0.005/1K tokens) - Default
- **Advanced Mode:** GPT-5/GPT-5-mini (5-8s, $0.015/1K tokens)
- Dynamic model switching per request
- Automatic GPT-5 detection at startup

### 3.2 Conversational AI (Phase 3A-3B)

**3.2.1 Persistent Chat Interface**
- Draggable and resizable chat panel
- Persistent conversation history (survives browser restarts)
- IndexedDB storage for local data
- Message timestamps and formatting
- Export functionality (JSON download)

**3.2.2 Multi-Session Management**
- Unlimited sessions per trading symbol
- Session manager UI modal
- Automatic context extraction (prices, bias, POIs)
- 50-message context window per session
- Session export and deletion

**3.2.3 Hybrid Vision → Reasoning Pipeline (Phase 3C)**
- GPT-4o Vision for image analysis
- GPT-5 Reasoning for text responses
- Session-based caching (40% cost savings)
- Automatic routing based on model capabilities
- MD5 hash-based cache invalidation

### 3.3 Performance Tracking (Phase 4A)

**3.3.1 Trade Logging**
- Automatic trade detection from chat messages
- Manual trade logging via UI button
- R-multiple extraction from natural language
- Outcome tracking (win/loss/breakeven)
- Dual persistence (IndexedDB + backend JSON)

**3.3.2 Performance Analytics**
- Real-time win rate calculation
- Average R-multiple tracking
- Profit factor calculation
- Total PnL in dollars
- Color-coded statistics (green/yellow/red)

**3.3.3 Trade Management**
- View all trades with details
- Delete trades with confirmation
- Restore last deleted trade
- Update trade outcomes
- Filter by symbol/date/outcome

### 3.4 Analytics Dashboard (Phase 4B)

**3.4.1 Interactive Charts**
- Rolling win rate over time (Chart.js)
- Average R-multiple by setup type
- Win/Loss/Breakeven distribution pie chart
- Real-time data refresh
- Dark theme with gold accents

**3.4.2 Performance Insights**
- Setup type performance breakdown
- Symbol-specific statistics
- Trend analysis (improving/declining)
- Best/worst performing setups

### 3.5 Adaptive Learning Engine (Phase 4C)

**3.5.1 Learning Profile Generation**
- Auto-update every 5 trades
- Setup type performance analysis
- Bias performance tracking
- Trend strength assessment
- Personalized trading advice

**3.5.2 Context Injection**
- AI prompt enhancement with trading history
- ~250 tokens of context injected
- Performance-aware suggestions
- Pattern recognition from history

### 3.6 CSV Import & Chart Reconstruction (Phase 4D)

**3.6.1 CSV Import System (Phase 4D.0)**
- Topstep Trader CSV format support
- Full trade normalization
- Terminal-based analytics summary
- Import error handling
- UTF-8-sig encoding support

**3.6.2 Chart Reconstruction (Phase 4D.1)**
- TradingView-style candlestick charts
- 5-minute OHLCV data from yfinance
- Entry/exit price markers
- Volume panel integration
- 3-day historical context (935+ candles)
- Dark theme (#131722 background)
- Retry logic with rate limiting

**3.6.3 Interactive Merge System (Phase 4D.2)**
- Single trade merge endpoint
- Batch merge functionality
- Duplicate prevention (merged flag)
- Auto-labeling based on P&L
- Chart linking to reconstructed charts
- Teaching stub creation

### 3.7 Interactive Teaching Mode (Phase 5A-5C)

**3.7.1 Teach Copilot UI (Phase 5A)**
- Full-page overlay modal
- Trade selection dropdown
- Chart preview with automatic loading
- Voice input support (Chrome Web Speech API)
- Lesson text input with local storage
- Trade information display

**3.7.2 Conversational Teaching Engine (Phase 5B)**
- Backend API endpoints (`/teach/*`)
- GPT-powered BOS/POI extraction
- Teaching session management
- Progress tracking (examples_total, avg_confidence)
- Dataset auto-compilation
- Frontend integration

**3.7.3 Interactive Teaching Mode (Phase 5C)**
- **Incremental Parser:** Real-time BOS/POI extraction as user types
- **Live UI Feedback:** Dynamic chips showing extracted fields
- **Visual Overlays:** Preview BOS lines and POI zones on charts
- **Clarifying Questions:** Context-aware prompts for missing information
- **Session State Management:** Partial lessons persist across messages
- **Auto-advance:** Automatically move to next trade after saving
- **Chart Popup:** Resizable and draggable side panel for charts
- **Lessons Viewer:** UI to view all saved lessons and progress stats

### 3.8 System Command Recognition (Phase 4C.1, 5C)

**3.8.1 Natural Language Commands**
- Fuzzy matching for command recognition
- Question phrasing support ("can you...", "how about...")
- 30+ available commands covering all platform features

**3.8.2 Command Categories**
- **UI Controls:** close/open/minimize/resize chat, session manager
- **Performance:** show stats, delete/restore trades
- **Session Management:** create/switch/delete/rename sessions
- **Teaching:** start/end teaching, next/skip trade
- **Lesson Management:** view/delete/edit lessons
- **Chart Commands:** show/close chart popup
- **System:** help, model info, clear memory

### 3.9 Memory & Context Management

**3.9.1 Persistent Backend Memory**
- Survives server restarts
- JSON file storage (`server/data/`)
- Session contexts, conversation logs, performance logs
- User profile with teaching progress

**3.9.2 System Awareness**
- AI prompt injection with current status
- Trade count, win rate, average R-multiple
- Active sessions and message counts
- Real-time performance metrics

---

## 4. External Interface Requirements

### 4.1 User Interfaces

**4.1.1 Chrome Extension Popup**
- Extension icon in browser toolbar
- Quick actions: "Analyze Chart", "Open Chat Panel"
- Model selection dropdown (Fast/Balanced/Advanced)
- Performance stats display
- "Teach Copilot" and "Performance Tab" buttons

**4.1.2 Chat Panel (Content Script)**
- Draggable and resizable panel
- Message input with send button
- Message history with timestamps
- Export and clear buttons
- Minimize and close buttons

**4.1.3 Teach Copilot Modal**
- Full-page overlay
- Trade selection dropdown
- Chart preview area
- Lesson input textarea
- Voice input toggle
- Preview overlay button
- Skip and Save buttons
- Dynamic chips for extracted fields
- Status band for prompts

**4.1.4 Performance Tab Modal**
- Trade list with filtering
- Statistics summary
- Trade details view
- Delete and restore actions

**4.1.5 Lessons Viewer**
- All lessons list
- Progress statistics
- Individual lesson details modal
- Chart image display

**4.1.6 Chart Popup**
- Resizable and draggable side panel
- Chart image display
- Close button
- Initial positioning (right side, avoids chat panel)

### 4.2 Hardware Interfaces
- **Display:** Standard monitor (minimum 1024x768)
- **Input:** Keyboard and mouse
- **Network:** Internet connection for OpenAI API

### 4.3 Software Interfaces

**4.3.1 OpenAI API**
- Endpoint: `https://api.openai.com/v1/chat/completions`
- Models: `gpt-4o`, `gpt-4o-mini`, `gpt-5-mini`, `gpt-5-chat-latest`
- Authentication: Bearer token (API key)
- Rate Limits: Per OpenAI account tier
- Cost Tracking: Real-time budget monitoring

**4.3.2 yfinance API**
- Endpoint: Public Yahoo Finance API
- Purpose: Historical OHLCV data for chart reconstruction
- Data Format: 5-minute candlestick data
- Rate Limiting: 8-second delays between requests

**4.3.3 Browser APIs**
- **Chrome Extensions API:** Manifest v3, service workers
- **IndexedDB API:** Local storage for conversations
- **Chrome Tabs API:** Active tab access
- **Chrome Scripting API:** Content script injection
- **Web Speech API:** Voice recognition

### 4.4 Communication Interfaces
- **HTTP/REST:** FastAPI server (localhost:8765)
- **JSON:** Data exchange format
- **CORS:** Enabled for browser extension access
- **FormData:** Image upload format

---

## 5. System Architecture

### 5.1 Architecture Overview
```
┌─────────────────────────────────────────────────────────┐
│                    Chrome Extension                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Popup UI   │  │ Content Script│  │ Background.js │ │
│  │  (popup.js)  │  │ (content.js)  │  │  (SW worker)  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                   │                   │        │
│         └───────────────────┴───────────────────┘        │
│                          │                                │
└──────────────────────────┼────────────────────────────────┘
                           │ HTTP/REST (JSON)
                           │
┌──────────────────────────▼────────────────────────────────┐
│                  FastAPI Backend                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  app.py (Main Application)                         │  │
│  │  ├── Routers: performance, memory, teach, etc.      │  │
│  │  ├── OpenAI Client (openai_client.py)            │  │
│  │  └── Decision Logic (decision.py)                 │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Data Layer (JSON Files)                           │  │
│  │  ├── performance_logs.json                         │  │
│  │  ├── session_contexts.json                         │  │
│  │  ├── imported_trades.json                          │  │
│  │  ├── user_profile.json                             │  │
│  │  └── amn_training_examples/                        │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────┬────────────────────────────────┘
                           │
                           │ HTTPS
                           │
┌──────────────────────────▼────────────────────────────────┐
│                  External Services                        │
│  ┌──────────────┐          ┌──────────────┐             │
│  │ OpenAI API   │          │ yfinance API │             │
│  │ (GPT-4/5)    │          │ (OHLCV Data) │             │
│  └──────────────┘          └──────────────┘             │
└──────────────────────────────────────────────────────────┘
```

### 5.2 Component Descriptions

**5.2.1 Frontend Components**
- **Popup UI:** Extension popup with quick actions
- **Content Script:** Injected chat panel and UI controls
- **Background Service Worker:** Message routing and API calls
- **IDB Wrapper:** IndexedDB abstraction layer

**5.2.2 Backend Components**
- **FastAPI App:** Main application server
- **Router Modules:** Feature-specific endpoints
  - `performance/` - Trade tracking and analytics
  - `memory/` - Persistent memory and system commands
  - `routers/teach_router.py` - Teaching mode endpoints
  - `trades_import/` - CSV import system
  - `chart_reconstruction/` - Chart rendering
  - `trades_merge/` - Trade merging logic
  - `copilot_bridge/` - Copilot data sync
- **Utilities:**
  - `openai_client.py` - OpenAI API wrapper
  - `trade_detector.py` - Trade reference detection
  - `teach_parser.py` - Incremental lesson parsing
  - `overlay_drawer.py` - Visual overlay rendering

**5.2.3 Data Storage**
- **Backend JSON Files:**
  - `performance_logs.json` - All trade records
  - `session_contexts.json` - Teaching session state
  - `imported_trades.json` - CSV-imported trades
  - `user_profile.json` - User preferences and progress
  - `training_dataset.json` - Master training dataset
  - `conversation_log.json` - Backend conversation log
- **Browser IndexedDB:**
  - Sessions table (unlimited sessions)
  - Messages table (conversation history)
- **Static Files:**
  - `data/charts/` - Reconstructed chart images
  - `data/amn_training_examples/` - Teaching lesson files
  - `data/amn_training_examples/overlays/` - Visual overlay images

---

## 6. Functional Requirements

### 6.1 Chart Analysis

**FR-1.1: Chart Capture**
- System shall capture visible chart images from the browser
- System shall support PNG and JPG formats
- System shall validate image format before processing

**FR-1.2: AI Analysis**
- System shall analyze charts using GPT-4o or GPT-5 Vision models
- System shall return structured SMC analysis (bias, POI, BOS, FVG)
- System shall process analysis requests in 2-8 seconds
- System shall handle API errors gracefully with user feedback

**FR-1.3: Model Selection**
- System shall allow per-request model selection (fast/balanced/advanced)
- System shall detect GPT-5 availability at startup
- System shall default to balanced mode (GPT-4o) if not specified

### 6.2 Conversational Interface

**FR-2.1: Chat Panel**
- System shall provide draggable and resizable chat panel
- System shall persist conversation history across browser restarts
- System shall display messages with timestamps
- System shall allow message export as JSON

**FR-2.2: Session Management**
- System shall support unlimited trading sessions
- System shall allow session creation, deletion, and renaming
- System shall maintain 50-message context per session
- System shall extract trading context (prices, bias, POIs) automatically

**FR-2.3: Hybrid Pipeline**
- System shall use GPT-4o Vision for image analysis
- System shall use GPT-5 Reasoning for text responses
- System shall cache vision summaries per session (MD5 hash)
- System shall achieve 40% average cost savings for multi-question sessions

### 6.3 Performance Tracking

**FR-3.1: Trade Logging**
- System shall automatically detect trades from chat messages
- System shall extract R-multiples from natural language
- System shall track trade outcomes (win/loss/breakeven)
- System shall store trades in both IndexedDB and backend JSON

**FR-3.2: Trade Management**
- System shall allow viewing all trades with details
- System shall allow deleting trades with confirmation
- System shall allow restoring last deleted trade
- System shall allow updating trade outcomes

**FR-3.3: Statistics Calculation**
- System shall calculate win rate in real-time
- System shall calculate average R-multiple
- System shall calculate profit factor
- System shall display PnL in dollars

### 6.4 CSV Import & Chart Reconstruction

**FR-4.1: CSV Import**
- System shall parse Topstep Trader CSV format
- System shall normalize trade data to standard format
- System shall display import summary in terminal
- System shall handle encoding errors (UTF-8-sig)

**FR-4.2: Chart Reconstruction**
- System shall fetch 5-minute OHLCV data from yfinance
- System shall render TradingView-style candlestick charts
- System shall display entry/exit price markers
- System shall include 3-day historical context (935+ candles)
- System shall implement retry logic with rate limiting

### 6.5 Interactive Teaching Mode

**FR-5.1: Teaching Session**
- System shall allow starting and ending teaching sessions
- System shall track current trade index
- System shall navigate to next trade automatically
- System shall allow skipping trades

**FR-5.2: Incremental Parsing**
- System shall extract BOS/POI from user messages incrementally
- System shall update partial lesson as user types
- System shall display extracted fields as dynamic chips
- System shall ask clarifying questions for missing information

**FR-5.3: Visual Overlays**
- System shall generate preview overlays with BOS lines
- System shall display POI zones with colors
- System shall serve overlay images via `/overlays/` endpoint
- System shall update chart preview with overlay

**FR-5.4: Lesson Management**
- System shall save lessons to training dataset
- System shall extract BOS/POI via GPT-4o-mini
- System shall calculate confidence scores
- System shall auto-compile master training dataset
- System shall allow viewing, editing, and deleting lessons

### 6.6 System Commands

**FR-6.1: Command Recognition**
- System shall recognize 30+ commands via fuzzy matching
- System shall handle question phrasings ("can you...", "how about...")
- System shall normalize user input before matching

**FR-6.2: Command Execution**
- System shall execute UI control commands (close/open chat, etc.)
- System shall execute performance commands (show stats, delete trade)
- System shall execute session management commands
- System shall execute teaching commands (start/end teaching)
- System shall execute chart commands (show/close chart)

### 6.7 Memory & Context

**FR-7.1: Persistent Memory**
- System shall persist backend memory in JSON files
- System shall survive server restarts
- System shall initialize default files on startup

**FR-7.2: System Awareness**
- System shall inject current status into AI prompts
- System shall include trade count, win rate, average R-multiple
- System shall include session and message counts

---

## 7. Non-Functional Requirements

### 7.1 Performance

**NFR-1.1: Response Time**
- Chart analysis shall complete within 2-8 seconds depending on model
- API endpoints shall respond within 500ms for non-AI operations
- UI interactions shall feel responsive (<100ms)

**NFR-1.2: Throughput**
- System shall handle 10+ concurrent chat sessions
- System shall process CSV imports with 100+ trades in <5 minutes
- System shall render charts at rate of 1 per 8 seconds (yfinance limit)

**NFR-1.3: Scalability**
- System shall handle 10,000+ trades in performance logs
- System shall support unlimited chat sessions
- System shall handle 50+ concurrent API requests

### 7.2 Reliability

**NFR-2.1: Availability**
- System shall handle OpenAI API outages gracefully
- System shall display clear error messages to users
- System shall retry failed requests with exponential backoff

**NFR-2.2: Data Integrity**
- System shall prevent data loss on server restart
- System shall validate JSON data before saving
- System shall maintain data consistency between IndexedDB and backend

**NFR-2.3: Error Handling**
- System shall catch and log all exceptions
- System shall provide user-friendly error messages
- System shall not crash on invalid user input

### 7.3 Usability

**NFR-3.1: User Interface**
- System shall provide intuitive drag-and-drop for chat panel
- System shall display clear status messages for all actions
- System shall support keyboard shortcuts (Ctrl+Enter to send)

**NFR-3.2: Accessibility**
- System shall be usable with keyboard navigation
- System shall provide visual feedback for all actions
- System shall display error messages clearly

**NFR-3.3: Learning Curve**
- System shall be usable with minimal documentation
- System shall provide helpful error messages
- System shall support natural language commands

### 7.4 Maintainability

**NFR-4.1: Code Quality**
- System shall follow Python PEP 8 style guide
- System shall include inline documentation for complex functions
- System shall use type hints where appropriate

**NFR-4.2: Modularity**
- System shall be organized into logical modules
- System shall use dependency injection where possible
- System shall minimize coupling between components

### 7.5 Portability

**NFR-5.1: Operating Systems**
- System shall run on Windows, macOS, and Linux
- System shall use cross-platform file paths (Pathlib)
- System shall handle OS-specific encoding issues

**NFR-5.2: Browsers**
- System shall work in Chrome and Chromium-based browsers
- System shall require Manifest v3 support
- System shall not depend on browser-specific features (except Chrome APIs)

### 7.6 Security

**NFR-6.1: API Key Management**
- System shall store API keys in environment variables
- System shall never expose API keys in client code
- System shall validate API keys before use

**NFR-6.2: Data Privacy**
- System shall store all data locally (IndexedDB, JSON files)
- System shall not send data to external servers (except OpenAI)
- System shall allow data export for user control

**NFR-6.3: Input Validation**
- System shall validate all user input
- System shall sanitize file uploads
- System shall prevent injection attacks

### 7.7 Cost Constraints

**NFR-7.1: Budget Management**
- System shall track OpenAI API spending in real-time
- System shall enforce budget limits if configured
- System shall optimize costs with hybrid pipeline (40% savings)

---

## 8. Data Requirements

### 8.1 Trade Data Structure

```json
{
  "id": 1234567890,
  "symbol": "MNQZ5",
  "direction": "long",
  "entry_price": 1.1450,
  "exit_price": 1.1480,
  "entry_time": "2024-10-14T10:30:00Z",
  "exit_time": "2024-10-14T11:15:00Z",
  "outcome": "win",
  "pnl": 762.50,
  "r_multiple": 2.5,
  "setup_type": "BOS",
  "chart_path": "/charts/MNQZ5_5m_1234567890.png"
}
```

### 8.2 Session Data Structure

```json
{
  "session_id": "session_abc123",
  "symbol": "6EZ5",
  "created_at": "2024-10-14T09:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What's the bias?",
      "timestamp": "2024-10-14T09:01:00Z"
    }
  ],
  "context": {
    "bias": "bullish",
    "price": 1.1450,
    "poi": [1.1440, 1.1452]
  }
}
```

### 8.3 Teaching Example Data Structure

```json
{
  "id": "example_1234567890",
  "trade_id": 1234567890,
  "symbol": "MNQZ5",
  "direction": "long",
  "outcome": "win",
  "pnl": 762.50,
  "timestamp": "2024-10-14T10:30:00Z",
  "lesson_text": "BOS from 1.1450 to 1.1480, bullish POI at 1.1440-1.1452",
  "bos": {
    "start": 1.1450,
    "end": 1.1480
  },
  "poi": [
    {
      "low": 1.1440,
      "high": 1.1452,
      "reason": "imbalance"
    }
  ],
  "bias": "bullish",
  "feedback_confidence": 0.9,
  "understood": true,
  "chart_path": "/charts/MNQZ5_5m_1234567890.png"
}
```

### 8.4 Data Storage Locations

- **Backend JSON:** `server/data/`
- **IndexedDB:** Browser local storage
- **Static Files:** `server/data/charts/`, `server/data/amn_training_examples/`
- **Logs:** Console output (stdout/stderr)

### 8.5 Data Retention

- **Trades:** Persisted indefinitely (user can delete)
- **Sessions:** Persisted indefinitely (user can delete)
- **Teaching Examples:** Persisted indefinitely (user can delete)
- **Chart Images:** Persisted indefinitely (can be regenerated)

---

## 9. User Interface Requirements

### 9.1 Chat Panel

**UI-1.1: Layout**
- Position: Draggable, default right side of screen
- Size: Resizable (300px - 800px width, 400px - 90vh height)
- Style: Dark theme (#1c1c1c background, #ffd700 accents)

**UI-1.2: Features**
- Message history area with scroll
- Input field with send button
- Timestamp display for each message
- Export button (💾 icon)
- Clear button (🗑️ icon)
- Minimize button (➖ icon)
- Close button (✖️ icon)

### 9.2 Teach Copilot Modal

**UI-2.1: Layout**
- Position: Full-page overlay (z-index: 2147483646)
- Background: Semi-transparent dark overlay
- Content: Centered modal with max-width 1200px

**UI-2.2: Components**
- Trade selection dropdown (sorted by date, newest first)
- Trade details panel (symbol, outcome, PnL, R-multiple, dates)
- Chart preview area (auto-loads chart image)
- Lesson input textarea (with local storage)
- Voice input toggle (🎙️ button)
- Preview overlay button (👁️ icon)
- Skip button (⏭️ icon)
- Save lesson button (💾 icon)
- Dynamic chips area (BOS, POI, Bias, Conf)
- Status band (waiting/prompts/ready to save)
- Close button (✖️ icon)

### 9.3 Performance Tab Modal

**UI-3.1: Layout**
- Position: Full-page overlay
- Content: Scrollable trade list with statistics

**UI-3.2: Components**
- Statistics summary (win rate, avg R, total PnL)
- Trade list with filters (symbol, outcome, date)
- Trade detail view (expandable)
- Delete and restore actions

### 9.4 Chart Popup

**UI-4.1: Layout**
- Position: Resizable and draggable side panel
- Initial Position: Right side, avoids chat panel (~620px from right)
- Size: 500px width, 600px height (min: 300x400, max: 90vw x 90vh)

**UI-4.2: Features**
- Chart image display (scaled to fit)
- Drag handle (header bar)
- Resize handles (corners and edges)
- Close button (✖️ icon)
- Gold border (#ffd700) with dark gradient background

### 9.5 Lessons Viewer

**UI-5.1: Layout**
- Position: Side panel (similar to chart popup)
- Content: Scrollable list with statistics

**UI-5.2: Components**
- Progress statistics (total lessons, understood count, win/loss breakdown)
- Lessons list (sorted by date, newest first)
- Lesson detail modal (expandable)
- Chart image preview (clickable)
- Delete and edit actions

### 9.6 Visual Design

**UI-6.1: Color Scheme**
- Background: Dark (#1c1c1c, #2a2a2a gradients)
- Accent: Gold (#ffd700)
- Text: Light gray (#ffffff, #cccccc)
- Success: Green (#26a69a)
- Error: Red (#ef5350)
- Warning: Yellow (#ffa726)

**UI-6.2: Typography**
- Font: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif
- Headers: Bold, larger size
- Body: Regular, readable size (14-16px)
- Code: Monospace for technical data

**UI-6.3: Animations**
- Panel drag: Smooth movement
- Modal open/close: Fade and scale transitions
- Button hover: Color transitions
- Status updates: Fade-in notifications

---

## 10. Performance Requirements

### 10.1 Response Times

| Operation | Target | Maximum |
|-----------|--------|---------|
| Chart analysis (Fast) | 2-3s | 5s |
| Chart analysis (Balanced) | 3-5s | 8s |
| Chart analysis (Advanced) | 5-8s | 12s |
| API endpoint (non-AI) | 100ms | 500ms |
| UI interaction | 50ms | 100ms |
| CSV import (100 trades) | 2min | 5min |
| Chart rendering (per chart) | 8s | 15s |

### 10.2 Throughput

- **Concurrent Users:** Support 10+ simultaneous sessions
- **API Requests:** Handle 50+ concurrent requests
- **Chart Rendering:** Process 1 chart per 8 seconds (yfinance rate limit)
- **Trade Import:** Process 100+ trades in <5 minutes

### 10.3 Resource Usage

- **Memory:** <500MB for backend server
- **Disk:** Variable (charts, logs, teaching examples)
- **Network:** ~1-5MB per chart analysis (image upload)
- **CPU:** Moderate (AI processing, chart rendering)

---

## 11. Security Requirements

### 11.1 API Key Protection

**SEC-1.1: Storage**
- API keys shall be stored in environment variables (`.env` file)
- API keys shall never be exposed in client-side code
- API keys shall not be committed to version control

**SEC-1.2: Validation**
- System shall validate API keys before use
- System shall handle invalid/expired API keys gracefully
- System shall log API key errors without exposing keys

### 11.2 Data Privacy

**SEC-2.1: Local Storage**
- All user data shall be stored locally (IndexedDB, JSON files)
- No data shall be sent to external servers (except OpenAI)
- Users shall have full control over their data

**SEC-2.2: Export/Delete**
- Users shall be able to export all their data
- Users shall be able to delete all their data
- System shall provide clear data management options

### 11.3 Input Validation

**SEC-3.1: Sanitization**
- All user input shall be validated
- File uploads shall be checked for format/size
- System shall prevent injection attacks (SQL, XSS)

**SEC-3.2: Error Handling**
- System shall not expose sensitive information in error messages
- System shall log errors securely (no API keys, passwords)
- System shall handle malformed input gracefully

### 11.4 CORS Configuration

**SEC-4.1: Origins**
- Production: Restrict to specific origins
- Development: Allow localhost (127.0.0.1:8765)
- System shall validate origin headers

---

## 12. API Specifications

### 12.1 Core Analysis Endpoints

#### `POST /analyze`
- **Purpose:** Structured SMC chart analysis
- **Input:** `image` (file), `model` (optional, string)
- **Output:** JSON with bias, POI, BOS, FVG, displacement, verdict
- **Example:**
```bash
curl -X POST http://127.0.0.1:8765/analyze \
  -F "image=@chart.png" \
  -F "model=balanced"
```

#### `POST /ask`
- **Purpose:** Conversational chart Q&A
- **Input:** `image` (file), `question` (string), `model` (optional)
- **Output:** JSON with natural-language answer
- **Example:**
```bash
curl -X POST http://127.0.0.1:8765/ask \
  -F "image=@chart.png" \
  -F "question=What's the risk/reward?" \
  -F "model=fast"
```

### 12.2 Performance Tracking Endpoints

#### `POST /performance/log`
- **Purpose:** Log a new trade
- **Input:** JSON with trade details
- **Output:** JSON with trade ID and status

#### `GET /performance/all`
- **Purpose:** Get all trades
- **Output:** JSON array of all trades

#### `DELETE /performance/{trade_id}`
- **Purpose:** Delete a trade
- **Output:** JSON with status

#### `POST /performance/restore-last`
- **Purpose:** Restore last deleted trade
- **Output:** JSON with restored trade

### 12.3 Teaching Endpoints

#### `POST /teach/start`
- **Purpose:** Start teaching session
- **Output:** JSON with session status

#### `POST /teach/stream`
- **Purpose:** Incremental lesson parsing
- **Input:** `message` (string)
- **Output:** JSON with partial_lesson, missing_fields, next_question

#### `POST /teach/preview`
- **Purpose:** Generate overlay preview
- **Input:** Optional example data
- **Output:** JSON with overlay_path and overlay_url

#### `POST /teach/record`
- **Purpose:** Save lesson with GPT extraction
- **Input:** `trade_id` (int), `lesson_text` (string)
- **Output:** JSON with example_id and confidence

#### `POST /teach/skip`
- **Purpose:** Skip current trade
- **Output:** JSON with next_trade_index

#### `POST /teach/end`
- **Purpose:** End teaching session
- **Output:** JSON with session summary

#### `GET /teach/status`
- **Purpose:** Get session status
- **Output:** JSON with teaching_active, current_trade_index, partial_lesson

#### `GET /teach/lessons`
- **Purpose:** List all saved lessons
- **Output:** JSON with lessons array

#### `GET /teach/lessons/{example_id}`
- **Purpose:** Get lesson details
- **Output:** JSON with full lesson data

#### `DELETE /teach/lessons/{example_id}`
- **Purpose:** Delete a lesson
- **Output:** JSON with status

#### `PUT /teach/lessons/{example_id}`
- **Purpose:** Update/edit a lesson
- **Input:** JSON with lesson data
- **Output:** JSON with updated lesson

#### `GET /teach/progress`
- **Purpose:** Get teaching progress statistics
- **Output:** JSON with totals, averages, breakdowns

### 12.4 Memory & Commands Endpoints

#### `POST /memory/system/command`
- **Purpose:** Execute system command
- **Input:** `command` (string), `context` (object)
- **Output:** JSON with command result

#### `GET /memory/status`
- **Purpose:** Get memory status
- **Output:** JSON with trade count, win rate, sessions, messages

### 12.5 CSV Import Endpoints

#### `POST /trades/import`
- **Purpose:** Import CSV file
- **Input:** `file` (CSV file)
- **Output:** JSON with import summary

#### `GET /trades/stats`
- **Purpose:** Get import statistics
- **Output:** JSON with total, merged, pending counts

### 12.6 Chart Reconstruction Endpoints

#### `POST /charts/render`
- **Purpose:** Render chart for trade
- **Input:** `trade_id` (int)
- **Output:** JSON with chart_path

#### `GET /charts/metadata`
- **Purpose:** Get chart metadata
- **Output:** JSON array with chart info

### 12.7 System Endpoints

#### `GET /`
- **Purpose:** Health check
- **Output:** JSON with status

#### `GET /models`
- **Purpose:** List available OpenAI models
- **Output:** JSON with models list and GPT-5 detection

#### `GET /budget`
- **Purpose:** Get API spending status
- **Output:** JSON with budget info

---

## 13. Use Cases

### 13.1 UC-1: Analyze Trading Chart

**Actor:** Trader  
**Precondition:** Chart visible in browser, extension installed, server running

**Main Flow:**
1. Trader navigates to TradingView chart
2. Trader clicks extension icon
3. Trader clicks "Analyze Chart"
4. System captures chart image
5. System sends image to backend
6. Backend analyzes chart with GPT-4o
7. Backend returns SMC analysis
8. System displays analysis in chat panel

**Postcondition:** Analysis visible in chat panel, conversation history saved

**Alternative Flow:**
- 4a. Image capture fails → Display error message
- 6a. API error → Display error message with retry option

### 13.2 UC-2: Log Trade Performance

**Actor:** Trader  
**Precondition:** Trade executed, extension active

**Main Flow:**
1. Trader mentions trade in chat (e.g., "entered long at 1.1450")
2. System detects trade from message
3. System extracts entry price, symbol, direction
4. System prompts for exit details
5. Trader provides exit information
6. System calculates PnL and R-multiple
7. System saves trade to performance logs
8. System updates statistics

**Postcondition:** Trade logged, statistics updated

### 13.3 UC-3: Start Teaching Session

**Actor:** Trader  
**Precondition:** Extension active, trades available

**Main Flow:**
1. Trader says "open teach copilot" or clicks button
2. System opens Teach Copilot modal
3. System loads all trades from `/performance/all`
4. Trader selects a trade from dropdown
5. System loads chart image automatically
6. System displays trade details
7. Trader enters lesson explanation
8. System extracts BOS/POI incrementally
9. System displays extracted fields as chips
10. Trader clicks "Save Lesson"
11. System finalizes lesson with GPT extraction
12. System saves to training dataset
13. System auto-advances to next trade

**Postcondition:** Lesson saved, next trade loaded

### 13.4 UC-4: Import CSV Trades

**Actor:** Trader  
**Precondition:** CSV file from Topstep Trader, server running

**Main Flow:**
1. Trader prepares CSV file
2. Trader calls `POST /trades/import` with file
3. System parses CSV format
4. System normalizes trade data
5. System saves to `imported_trades.json`
6. System displays import summary
7. System triggers chart reconstruction (optional)

**Postcondition:** Trades imported, charts available (if reconstructed)

### 13.5 UC-5: View Performance Dashboard

**Actor:** Trader  
**Precondition:** Trades logged, extension active

**Main Flow:**
1. Trader clicks "Performance Tab" button
2. System opens Performance Tab modal
3. System loads all trades from `/performance/all`
4. System calculates statistics (win rate, avg R, PnL)
5. System displays interactive charts (Chart.js)
6. System shows trade list with filters
7. Trader can filter by symbol/outcome/date
8. Trader can view individual trade details

**Postcondition:** Performance dashboard visible

### 13.6 UC-6: Execute System Command

**Actor:** Trader  
**Precondition:** Extension active, command recognition enabled

**Main Flow:**
1. Trader types command in chat (e.g., "show my stats")
2. System normalizes input (removes question words)
3. System matches command via fuzzy matching
4. System executes command handler
5. System performs action (e.g., displays stats)
6. System returns result to chat

**Postcondition:** Command executed, result displayed

---

## 14. Testing Requirements

### 14.1 Unit Testing

**TEST-1.1: Chart Analysis**
- Test image format validation
- Test API error handling
- Test model selection logic
- Test response parsing

**TEST-1.2: Trade Detection**
- Test trade extraction from messages
- Test R-multiple calculation
- Test outcome detection

**TEST-1.3: Command Recognition**
- Test fuzzy matching accuracy
- Test question phrasing normalization
- Test command execution

### 14.2 Integration Testing

**TEST-2.1: Frontend-Backend Integration**
- Test chat panel communication
- Test trade logging flow
- Test teaching mode workflow

**TEST-2.2: API Integration**
- Test OpenAI API calls
- Test yfinance API calls
- Test error handling

### 14.3 System Testing

**TEST-3.1: End-to-End Workflows**
- Test complete chart analysis flow
- Test trade import and reconstruction
- Test teaching session workflow

**TEST-3.2: Performance Testing**
- Test response times under load
- Test concurrent user handling
- Test memory usage

### 14.4 Acceptance Testing

**TEST-4.1: User Acceptance**
- Test with real trading scenarios
- Test with various chart types
- Test with different trade formats

**TEST-4.2: Documentation Verification**
- Verify all features documented
- Verify API examples work
- Verify installation instructions

---

## 15. Future Enhancements

### 15.1 Short-term (v5.3 - v5.5)

**ENH-1.1: Enhanced Voice Commands**
- Voice dictation for teaching mode
- Voice commands for UI controls
- Voice feedback for actions

**ENH-1.2: Batch Annotation**
- Batch teaching workflow
- Multi-trade selection
- Bulk lesson creation

**ENH-1.3: Advanced Chart Annotations**
- Manual BOS/POI drawing on charts
- Custom annotation tools
- Annotation export

### 15.2 Medium-term (v6.0)

**ENH-2.1: Real-time Trade Alerts**
- Price level alerts
- Setup detection alerts
- Custom alert rules

**ENH-2.2: Backtesting Integration**
- Historical strategy backtesting
- Performance comparison
- Strategy optimization

**ENH-2.3: Multi-timeframe Analysis**
- Multiple timeframe comparison
- Higher timeframe context
- Timeframe switching

### 15.3 Long-term (v7.0+)

**ENH-3.1: RAG Integration**
- Retrieval Augmented Generation
- Trading knowledge base
- Context-aware responses

**ENH-3.2: Broker Integration**
- Live trade execution
- Order management
- Account integration

**ENH-3.3: Mobile App**
- React Native mobile app
- Push notifications
- Mobile-optimized UI

**ENH-3.4: Social Trading**
- Share strategies
- Community features
- Leaderboards

---

## Appendix A: Glossary

- **BOS:** Break of Structure - Price movement breaking through a key level
- **POI:** Price of Interest - Important price zones for trading decisions
- **FVG:** Fair Value Gap - Price gaps that may be filled
- **R-Multiple:** Risk-to-reward ratio (e.g., 2R = 2x risk)
- **SMC:** Smart Money Concepts - Trading methodology focusing on institutional behavior
- **PnL:** Profit and Loss - Financial outcome of a trade
- **OHLCV:** Open, High, Low, Close, Volume - Candlestick data
- **IndexedDB:** Browser-based NoSQL database for client-side storage

## Appendix B: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Initial | Backend foundation |
| 2.0.0 | - | Chrome Extension |
| 3.0.0 | - | Conversational memory |
| 3.1.0 | - | Multi-session management |
| 3.2.0 | - | Hybrid pipeline |
| 4.3.1 | - | Performance tracking |
| 4.4.0 | - | Analytics dashboard |
| 4.5.0 | - | Adaptive learning |
| 4.6.0 | - | System awareness |
| 4.7.0 | - | CSV import |
| 4.8.0 | - | Chart reconstruction |
| 4.9.0 | - | Interactive merge |
| 5.0.0 | - | Performance context sync |
| 5.1.0 | Nov 2024 | Teach Copilot UI + Voice |
| 5.2.0 | Dec 2024 | Interactive Teaching Mode + Comprehensive Commands |

---

**Document Status:** Complete  
**Last Updated:** December 2024  
**Next Review:** March 2025
