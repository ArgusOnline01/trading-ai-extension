# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Visual Trading Coach (VTC) is a Chrome extension + FastAPI backend system that provides AI-powered trading analysis using Smart Money Concepts (SMC). The system uses a hybrid GPT-4o Vision → GPT-5 reasoning pipeline for cost-optimized chart analysis with conversational memory.

## Development Commands

### Backend (FastAPI Server)

**Start Server:**
```bash
# Using Docker (recommended)
docker-compose up

# Direct (from server/ directory)
cd server
uvicorn app:app --host 0.0.0.0 --port 8765 --reload
```

**Install Dependencies:**
```bash
cd server
pip install -r requirements.txt
```

**Database:**
- SQLite database at `server/data/vtc.db`
- Managed through SQLAlchemy ORM
- Manual migration scripts in `server/db/`

### Chrome Extension

**Load Extension:**
1. Navigate to `chrome://extensions/`
2. Enable Developer mode
3. Click "Load unpacked"
4. Select `visual-trade-extension/` folder

**No build step required** - Pure JavaScript (Manifest v3)

### Testing

- No automated test suite currently
- Manual testing via browser and API endpoints
- Follow the **MANDATORY** Plan → Implement → Test workflow documented in `docs/New_Files_to_see/DEVELOPMENT_WORKFLOW.md`
- All features require comprehensive testing (frontend + backend, visual validation)
- Test results documented in `docs/phases/*/test/TEST_RESULTS.md`

## Tech Stack

**Backend:**
- FastAPI 0.100.0+ with Uvicorn ASGI server
- OpenAI API: GPT-4o Vision + GPT-5 Chat (hybrid pipeline)
- SQLite + SQLAlchemy 2.0 ORM
- ChromaDB for RAG (AI learning)
- yfinance, mplfinance for chart generation
- Python 3.11+, Docker containerized

**Frontend:**
- Chrome Extension: Vanilla JavaScript (Manifest v3)
- Web App: Static HTML/CSS/JS served by FastAPI
- IndexedDB for local persistence
- No frontend frameworks - direct DOM manipulation

## Architecture

### Three-Tier System

1. **Chrome Extension Layer** (User Interface)
   - `popup/` - Quick actions UI (model selection, stats)
   - `content/` - Injectable chat panel for conversational AI
   - `background.js` - Service worker for screenshots and message routing
   - IndexedDB for local chat history and session storage

2. **FastAPI Backend Layer** (Core Logic)
   - **Router-based modular architecture** - 15+ domain routers in `server/` directory
   - Key routers: `trades/`, `charts/`, `ai/`, `analytics/`, `setups/`, `annotations/`, `strategy/`, `chat/`, `memory/`, `amn_teaching/`
   - Core modules:
     - `openai_client.py` - OpenAI API wrapper with budget tracking
     - `hybrid_pipeline.py` - GPT-4o vision → GPT-5 reasoning pipeline (40% cost savings)
     - `decision.py` - SMC (Smart Money Concepts) analysis logic
     - `cache.py` - Session-based image analysis caching
   - Database: `db/models.py` - SQLAlchemy models (Trade, Chart, Setup, Annotation, etc.)

3. **Web Application Layer** (Trade Management)
   - `index.html` - Trade list with filtering/sorting/pagination
   - `teach.html` - AI teaching interface (correct AI, annotate charts)
   - `annotate.html` - Chart annotation tool (POI/BOS marking)
   - `analytics.html` - Performance dashboard
   - `strategy.html` - Strategy documentation viewer

### Data Flow

```
User → Chrome Extension (popup/content)
     ↓ screenshot + question
Backend /ask → Hybrid Pipeline:
     1. GPT-4o analyzes chart → structured summary (cached)
     2. GPT-5 reasons about summary + question (reuses cache)
     ↓ structured response
IndexedDB (local) + SQLite (server)
     ↓ query/filter
Web App (http://localhost:8765/app/)
```

### Hybrid Vision Pipeline

The system uses a two-stage AI pipeline for cost optimization:

1. **GPT-4o Vision Stage**: Analyzes chart screenshot once → structured summary (cached by session using MD5 hash)
2. **GPT-5 Reasoning Stage**: Answers user questions using cached summary (no re-analysis)
3. **40% cost savings** for multi-question sessions via cache reuse

Cache invalidation: New screenshot or session change triggers fresh GPT-4o analysis.

## Key Architectural Patterns

### Backend Patterns

- **Router modularity**: Each domain in separate `/routes.py` file mounted in `app.py`
- **Dependency injection**: SQLAlchemy session via `get_db()` dependency
- **Pydantic validation**: All request/response models use Pydantic 2.0
- **Session-based caching**: Image analysis cached by session ID + MD5 hash
- **Budget tracking**: In-memory OpenAI API cost tracking per request

### Frontend Patterns

- **No bundler**: Direct JavaScript module loading
- **Chrome messaging**: Extension components communicate via `chrome.runtime.sendMessage`
- **IndexedDB wrapper**: `idb.js` provides abstraction for persistence
- **Async/await**: All API calls use modern async patterns
- **Dark theme**: CSS variables for consistent theming

### Database Design

- **Core entities**: Trade (with relationships to Chart, Annotation, Setup)
- **Annotations**: POI/BOS locations stored as JSON arrays with coordinates
- **Setup/EntryMethod**: Trading strategy docs linked to trades
- **Soft timestamps**: `created_at` fields, no explicit soft delete

### API Conventions

- **RESTful routes**: Standard GET/POST/PUT/DELETE on `/resource` and `/resource/{id}`
- **Query params for filtering**: symbol, outcome, direction, session, date ranges
- **JSON response format**: `{"data": [...], "total": N}` for collections
- **CORS enabled**: Allows extension origin for development
- **Error format**: `{"detail": "message"}` via HTTPException

## Phase System

The project follows a structured phase-based development approach:

- **Phase 1-3**: Foundation, extension basics, conversational memory
- **Phase 4A**: Database migration, architecture cleanup
- **Phase 4B**: Strategy documentation system
- **Phase 4C**: Trade analysis and learning
- **Phase 4D**: AI learning system (RAG + corrections)
- **Phase 4E**: Entry suggestion system

Each phase has documentation in `docs/phases/[phase]/` with `plan/`, `implementation/`, `test/` folders.

## Development Workflow (MANDATORY)

All feature development MUST follow this workflow (documented in `docs/New_Files_to_see/DEVELOPMENT_WORKFLOW.md`):

1. **PLAN** - Discuss requirements, document in `docs/phases/*/plan/`
2. **IMPLEMENT** - Follow plan strictly, document changes in `docs/phases/*/implementation/`
3. **TEST** - Comprehensive testing (frontend + backend, visual validation), document in `docs/phases/*/test/`
4. **ITERATE** - Document issues, fix, re-test

See `docs/PHASE_STRUCTURE_GUIDE.md` for standard documentation structure.

## Critical Files

- `server/app.py` - Main FastAPI app with all router mounts (900+ lines)
- `server/openai_client.py` - OpenAI integration with budget tracking
- `server/hybrid_pipeline.py` - Cost-optimized vision→reasoning pipeline
- `server/db/models.py` - All SQLAlchemy models
- `visual-trade-extension/manifest.json` - Extension configuration
- `visual-trade-extension/content/content.js` - Chat panel logic
- `visual-trade-extension/popup/popup.js` - Extension popup logic
- `docs/New_Files_to_see/DEVELOPMENT_WORKFLOW.md` - Required reading for development

## Important Notes

- Always test both frontend (extension + web app) and backend together
- Visual testing required for UI changes (use browser automation)
- Document all iterations and refinements in TEST_RESULTS.md files
- No feature ships without following Plan → Implement → Test workflow
- Cache invalidation happens automatically on new session or different image
