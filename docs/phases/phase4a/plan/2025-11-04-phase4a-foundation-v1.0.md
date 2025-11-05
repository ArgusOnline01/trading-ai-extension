# Feature Plan: Phase 4A - Foundation (Clean Slate) - Project Restructure

**Date:** 2025-11-04  
**Phase:** Phase 4A  
**Status:** Planning

---

## Feature Overview

### What It Does
Completely restructures the Visual Trade Copilot project to:
1. Separate pure AI chat from trade management features
2. Create clean architecture for future development
3. Set up foundation for strategy teaching system
4. Move from JSON files to SQLite database
5. Prepare for web app integration

### Why It's Needed
- Current project has entangled concerns (chat + commands + trade management)
- Need clean foundation for Phase 4B-4E (strategy teaching, entry confirmation)
- Database migration needed for better data querying
- Architecture separation needed for hybrid extension + web app approach

### User Story
As a trader, I want a clean, organized project structure so that:
- AI chat is separate from trade management
- I can easily add new features without breaking existing ones
- The system is ready for strategy teaching and entry confirmation
- Data is stored in a proper database for better analysis

---

## Technical Requirements

### Backend Changes
- [x] **Docker Setup:**
  - [x] Create Dockerfile for backend
  - [x] Create docker-compose.yml (backend only for Phase 4A)
  - [x] Create .dockerignore
  - [x] Test Docker setup (start/stop server)
  
- [x] **Database Migration:**
  - [x] Install SQLite (in-container file at `server/data/vtc.db`)
  - [x] Create database schema (trades, setups, annotations, teaching_sessions)
  - [x] Migrate existing JSON data to database (from `data/performance_logs.json`)
  - [x] Create database models and ORM setup (SQLAlchemy 2.0)
  
- [x] **API Restructure:**
  - [x] Separate `/ask` endpoint (pure AI chat only)
  - [x] Create `/trades` endpoints (trade management)
  - [x] Create `/charts` endpoints (chart recreation/viewing)
  - [x] Remove command routing from chat endpoint
  
- [x] **Clean Architecture:**
  - [x] Separate AI chat logic from trade management
  - [ ] Create strategy module (for future Phase 4B)
  - [ ] Create teaching module (for future Phase 4D)
  - [ ] Create analysis module (for future Phase 4E)

- [x] **Dependencies:**
  - [x] Docker (for backend containerization)
  - [x] SQLite (initial; PostgreSQL later phase)
  - [x] SQLAlchemy (ORM)
  - [x] FastAPI, OpenAI v1 client

### Frontend Changes
- [x] **Extension (Chrome Extension):**
  - [x] Simplify to quick AI chat only
  - [x] Remove trade management UI from extension
  - [x] Keep overlay chat for natural language queries
  - [ ] (Optional) Add data sync to backend (future)
  
- [x] **Web App (New):**
  - [x] Create minimal web app structure (static)
  - [x] Trade management UI (list, filter; navigation via API)
  - [x] Chart viewer links (by trade)
  - [ ] Prepare for teaching interface (Phase 4D)

- [x] **State Management:**
  - [x] Separate chat (extension) from trade management (web app)
  - [x] Trade state via API parameters
  - [x] Chart viewer via DB-backed endpoint

### Database Changes
- [ ] **New Tables:**
  - [ ] `trades` - Trade data (from performance_logs.json)
  - [ ] `charts` - Chart metadata and URLs
  - [ ] `setups` - Setup definitions (for Phase 4B)
  - [ ] `annotations` - POI/BOS annotations (for Phase 4D)
  - [ ] `teaching_sessions` - Teaching session data (for Phase 4D)
  
- [ ] **Table Schema:**
```sql
-- trades table
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    trade_id TEXT UNIQUE,
    symbol TEXT,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    entry_price REAL,
    exit_price REAL,
    direction TEXT, -- 'long' or 'short'
    outcome TEXT, -- 'win', 'loss', 'breakeven'
    pnl REAL,
    r_multiple REAL,
    chart_url TEXT,
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- charts table
CREATE TABLE charts (
    id INTEGER PRIMARY KEY,
    trade_id TEXT,
    chart_url TEXT,
    chart_path TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- setups table (for Phase 4B)
CREATE TABLE setups (
    id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    setup_type TEXT, -- 'bullish' or 'bearish'
    definition JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- annotations table (for Phase 4D)
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY,
    trade_id TEXT,
    chart_id INTEGER,
    poi_locations JSON, -- [{x, y, price, timestamp}]
    bos_locations JSON, -- [{x, y, price, timestamp}]
    notes TEXT,
    ai_detected BOOLEAN,
    user_corrected BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- teaching_sessions table (for Phase 4D)
CREATE TABLE teaching_sessions (
    id INTEGER PRIMARY KEY,
    session_name TEXT,
    trades_reviewed INTEGER,
    ai_accuracy REAL,
    status TEXT, -- 'in_progress', 'completed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints
| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| POST | `/ask` | Pure AI chat (natural language only) | Done |
| GET | `/trades` | List/filter/sort trades | Done |
| GET | `/trades/{trade_id}` | Get specific trade | Done |
| POST | `/trades` | Create new trade | Done |
| PUT | `/trades/{trade_id}` | Update trade | Done |
| DELETE | `/trades/{trade_id}` | Delete trade | Done |
| GET | `/charts/by-trade/{trade_id}` | Serve chart image for trade | Done |
| GET | `/charts/recreate/{trade_id}` | Recreate chart from trade | Keep |
| GET | `/navigation/next` | Navigate to next trade | Done |
| GET | `/navigation/previous` | Navigate to previous trade | Done |
| GET | `/navigation/current` | Get current trade index | Done |

---

## Implementation Details

### Step 0: Docker Setup (Week 1) ✅ COMPLETED
1. **Create Dockerfile** ✅
   - Base image: Python 3.11-slim
   - Install dependencies from requirements.txt
   - Expose port 8765
   - Set working directory
   - CMD: uvicorn app:app --host 0.0.0.0 --port 8765 --reload
   
2. **Create docker-compose.yml** ✅
   - Backend service only (for Phase 4A)
   - Port mapping: 8765:8765
   - Volume mounts for code and data (hot reload)
   - Environment variables (OPENAI_API_KEY)
   
3. **Create .dockerignore** ✅
   - Exclude __pycache__, venv, .env, etc.
   - Both server/ and root level
   
4. **Create .env.example** ✅
   - Template for environment variables
   - Copy to .env and fill in API key
   
5. **Test Docker Setup** ✅ COMPLETED
   - `docker-compose build` - Build image successfully
   - `docker-compose up -d` - Start server in background
   - `docker-compose logs` - View logs (server starts correctly)
   - API responds at `http://localhost:8765/` with status 200
   - Container running: `vtc-backend` on port 8765

### Step 1: Database Setup (Week 1)
1. **Install SQLite (or PostgreSQL)**
   - Decision: SQLite for simplicity (local, no setup)
   - Or PostgreSQL for production (more powerful)
   
2. **Create Database Schema**
   - Create all tables as defined above
   - Add indexes for performance
   - Add foreign key constraints
   
3. **Create Database Models**
   - Use SQLAlchemy ORM (or similar)
   - Create model classes for each table
   - Add validation and relationships

### Step 2: Data Migration (Week 1)
1. **Migrate Existing Data**
   - Read `performance_logs.json`
   - Migrate trades to `trades` table
   - Migrate chart metadata to `charts` table
   - Verify data integrity
   
2. **Create Migration Script**
   - Script to migrate JSON to database
   - Backup existing JSON files
   - Rollback capability if needed

### Step 3: API Restructure (Week 1-2)
1. **Separate Chat Endpoint**
   - Move `/ask` to pure AI chat only
   - Remove command routing from chat
   - Keep natural language processing
   
2. **Create Trade Management Endpoints**
   - Create `/trades` endpoints
   - Implement CRUD operations
   - Add filtering and pagination
   
3. **Create Navigation Endpoints**
   - Move navigation logic to separate endpoints
   - Use database for state management
   - Return JSON responses

### Step 4: Extension Simplification (Week 2)
1. **Remove Trade Management UI**
   - Remove trade list/navigation from extension
   - Keep only chart capture + chat
   - Simplify overlay UI
   
2. **Update Data Sync**
   - Sync chart captures to backend
   - Sync chat messages to backend
   - Remove trade management sync

### Step 5: Web App Foundation (Week 2-3)
1. **Create Web App Structure**
   - Set up React/Vue/vanilla JS frontend
   - Create basic routing
   - Set up API client
   
2. **Build Trade Management UI**
   - Trade list view
   - Trade detail view
   - Filter and search functionality
   - Navigation controls (next/previous)
   
3. **Build Chart Viewer**
   - Chart recreation viewer
   - Chart display component
   - Navigation between charts

### Step 6: Clean Architecture (Week 3)
1. **Separate Modules**
   - `ai/` - AI chat logic
   - `trades/` - Trade management
   - `charts/` - Chart recreation
   - `strategy/` - Strategy definitions (for Phase 4B)
   - `teaching/` - Teaching system (for Phase 4D)
   - `analysis/` - Analysis tools (for Phase 4E)
   
2. **Update Imports**
   - Fix all import paths
   - Remove circular dependencies
   - Clean up unused code

---

## Testing Requirements

### Test Scenarios

#### Happy Path
1. **Scenario:** Database Migration
   - **Steps:** 
     1. Run migration script
     2. Verify all trades migrated
     3. Check data integrity
   - **Expected Frontend:** No visible changes yet
   - **Expected Backend:** All trades in database, JSON files backed up
   - **Success Criteria:** All trades accessible via API, no data loss

2. **Scenario:** AI Chat Works
   - **Steps:** 
     1. Open extension chat
     2. Ask natural language question
     3. Receive AI response
   - **Expected Frontend:** Chat overlay shows response
   - **Expected Backend:** `/ask` endpoint returns answer, no commands executed
   - **Success Criteria:** Pure natural language chat works, no command routing

3. **Scenario:** Trade Management Works
   - **Steps:** 
     1. Open web app
     2. View trade list
     3. Filter by win/loss
     4. Navigate to next trade
   - **Expected Frontend:** Trade list shows, filters work, navigation works
   - **Expected Backend:** `/trades` endpoints return data, navigation updates state
   - **Success Criteria:** All trade management features work

#### Edge Cases
1. **Scenario:** Empty Database
   - **Steps:** Start with empty database
   - **Expected:** System handles gracefully, shows "No trades" message

2. **Scenario:** Migration with Invalid Data
   - **Steps:** Run migration with corrupted JSON
   - **Expected:** Error handling, logs invalid data, continues with valid data

#### Error Handling
1. **Scenario:** Database Connection Failure
   - **Steps:** Simulate database connection error
   - **Expected:** Error message, system falls back gracefully

2. **Scenario:** API Endpoint Not Found
   - **Steps:** Call non-existent endpoint
   - **Expected:** 404 error with helpful message

### Integration Testing
- [ ] Extension → Backend communication works
- [ ] Web App → Backend communication works
- [ ] Database operations work correctly
- [ ] Chart recreation works from database

### Regression Testing
- [ ] Chart recreation still works (existing feature)
- [ ] Trade data still accessible (existing feature)
- [ ] No breaking changes to extension
- [ ] All existing functionality preserved

---

## Deliverables

### Final Output
- Docker setup complete (backend containerized)
- Complete project restructure with clean architecture
- Database migration complete (JSON → SQLite)
- Pure AI chat (separated from trade management)
- Trade management web app
- Simplified extension (chart capture + chat only)

### Acceptance Criteria
- [x] Docker setup complete (backend containerized, `docker-compose up` works)
- [x] Database migration complete (all data migrated, no data loss)
- [x] AI chat works (pure natural language, no command routing)
- [x] Trade management works (list, filter, navigate)
- [x] Chart viewer works (image serving by trade)
- [x] Extension simplified (chat only)
- [x] Web app foundation ready (for Phase 4B)
- [x] Clean architecture (separated modules)
- [x] No broken features from old system

### What "Done" Looks Like
- Clean, organized project structure with separated concerns
- Database replaces JSON files
- AI chat is pure natural language (no command routing)
- Trade management is in separate web app
- Extension is lightweight (chart capture + chat only)
- All existing features still work
- Foundation ready for Phase 4B (strategy teaching)

---

## Timeline

**Week 1: Docker & Database Setup**
- Docker setup (1 day)
- Database setup (1 day)
- Data migration (2 days)
- Testing (1 day)

**Week 2: API & Extension**
- API restructure (3 days)
- Extension simplification (2 days)

**Week 3: Web App & Cleanup**
- Web app foundation (3 days)
- Clean architecture (2 days)

**Total: 3 weeks**

---

## Risks & Mitigations

### Risk 1: Data Loss During Migration
**Mitigation:**
- Backup all JSON files before migration
- Create rollback script
- Test migration on copy first

### Risk 2: Breaking Existing Features
**Mitigation:**
- Comprehensive testing before deployment
- Keep old code until new code is verified
- Gradual migration (not all at once)

### Risk 3: Database Performance
**Mitigation:**
- Add proper indexes
- Use pagination for large queries
- Monitor query performance

---

## Dependencies

### Prerequisites
- [ ] Docker installed (containerization)
- [ ] SQLite installed (or PostgreSQL decided)
- [ ] SQLAlchemy installed (ORM)
- [ ] FastAPI (already installed)
- [ ] OpenAI (already installed)
- [ ] Frontend framework decided (React/Vue/vanilla JS)

### Blockers
- [ ] None currently identified

---

## Notes

- This is a complete restructure - careful testing required
- Database migration must be done carefully to avoid data loss
- Keep old code until new code is verified working
- Follow Plan → Implement → Test workflow strictly

---

## Implementation Status

### Completed
- [x] Docker setup (Dockerfile, docker-compose.yml, .dockerignore)
- [x] Docker testing
- [x] Database setup
- [x] Data migration
- [x] API restructure
- [x] Extension simplification
- [x] Web app foundation
- [x] Clean architecture (Phase 4A scope)

### In Progress
- [ ] None

### Pending
- [ ] Strategy/Teaching/Analysis modules (future phases)

---

## Testing Status

### Passed
- [x] All Phase 4A smoke tests (see /docs/phases/phase4a/test)

### Failed
- [ ] (To be updated during testing)

### Pending
- [ ] Unit tests
- [ ] Integration tests
- [ ] User tests
- [ ] Regression tests

---

## Changes from Original Plan

### Iteration 1 (Post-Testing Refinement)
- Scope: Fix filters/sorting behavior, add DB backfill for derived fields, add minimal web UI.
- Implemented:
  - Outcome derivation from PnL when missing
  - Null-safe sorting and date filters
  - Minimal web UI at `/app` with dark theme
- Tests: Updated API/Web app test docs under `docs/phases/phase4a/test/`.

### Iteration 2 (In Progress)
- Scope: Correct timestamps from source logs; UI polish (format currency, better buttons, visible dates).
- Plan:
  - Parse CSV→JSON merge pipeline to recover `entry_time`/`exit_time` and `r_multiple`
  - Enrich DB from logs; show human-readable dates and $PnL
  - Add small UI refinements (button styles, header emphasis)

---

**Remember:** This plan is the contract. Refer back to it during implementation and testing to stay on track!

