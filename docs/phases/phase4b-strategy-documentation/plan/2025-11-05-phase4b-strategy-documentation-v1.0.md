# Feature Plan: Phase 4B - Strategy Documentation

**Date:** 2025-11-05  
**Phase:** Phase 4B  
**Status:** Planning

---

## Feature Overview

### What It Does
Creates a web-based interface for documenting trading setups, marking POI/BOS on charts, and defining entry methods. This is the foundation for teaching the AI your strategy (Phase 4D) and getting entry confirmation advice (Phase 4E).

**Key Components:**
1. **Setup Definition Interface** - Document what makes a valid setup (bullish/bearish, market structure, etc.)
2. **Chart Annotation Tools** - Mark POI (Point of Interest) and BOS (Break of Structure) on charts visually
3. **Entry Method Documentation** - Define and document entry methods (IFVG, POI + 50%, etc.)
4. **Trade-to-Setup Linking** - Link existing trades to their setups and entry methods

### Why It's Needed
- **Foundation for AI Learning:** Before the AI can learn your strategy (Phase 4D), we need structured data about your setups
- **Entry Confirmation System:** To provide entry advice (Phase 4E), the AI needs to understand what setups you trade and which entry methods work
- **Pattern Analysis:** Linking trades to setups enables analysis like "POI + 50% entries failed 70% of the time"
- **Separation of Concerns:** Teaching/documentation happens in the web app, not the chat (as we learned from Phase 4A)

### User Story
As a trader, I want to document my trading setups and mark POI/BOS on charts so that:
- The AI can learn my strategy from structured examples
- I can analyze which entry methods work best for each setup type
- The AI can later provide entry confirmation advice based on my documented experience

---

## Technical Requirements

### Backend Changes
- [ ] **Setup Model (Database)**
  - [ ] Create `Setup` table (already exists in schema, verify fields)
  - [ ] Fields: `id`, `name`, `type` (bullish/bearish), `description`, `market_structure`, `created_at`
  - [ ] Create `Annotation` table (already exists, verify fields)
  - [ ] Fields: `id`, `trade_id`, `setup_id`, `poi_price`, `bos_price`, `annotations_json`, `created_at`
  - [ ] Create `EntryMethod` table (new)
  - [ ] Fields: `id`, `name`, `description`, `setup_id` (optional), `created_at`

- [ ] **Chart Quality Fixes (Priority)**
  - [ ] Identify bad charts (e.g., CLZ5_5m_1486940457.png, MCLZ5_5m_1499163878.png)
  - [ ] Investigate chart recreation issues (missing data, rendering errors)
  - [ ] Fix chart recreation logic in `chart_reconstruction/renderer.py`
  - [ ] Re-render bad charts with corrected logic
  - [ ] Verify all charts render correctly before Phase 4B annotation work
  
- [ ] **API Endpoints**
  - [ ] `POST /setups` - Create a new setup definition
  - [ ] `GET /setups` - List all setups
  - [ ] `GET /setups/{id}` - Get setup details
  - [ ] `PUT /setups/{id}` - Update setup
  - [ ] `DELETE /setups/{id}` - Delete setup
  - [ ] `POST /annotations` - Create annotation (mark POI/BOS on chart)
  - [ ] `GET /annotations/{trade_id}` - Get annotations for a trade
  - [ ] `PUT /annotations/{id}` - Update annotation
  - [ ] `POST /entry-methods` - Create entry method
  - [ ] `GET /entry-methods` - List entry methods
  - [ ] `POST /trades/{id}/link-setup` - Link trade to setup and entry method

- [ ] **Chart Annotation Service**
  - [ ] Store annotation coordinates (POI, BOS points) as JSON
  - [ ] Support multiple annotations per trade (multiple POIs, BOS levels)
  - [ ] Return annotation data with chart images

### Frontend Changes (Web App)
- [ ] **Setup Definition Page** (`/app/setups`)
  - [ ] List existing setups
  - [ ] Create new setup form (name, type, description, market structure)
  - [ ] Edit/delete setups
  - [ ] Visual setup cards with stats (how many trades use this setup)

- [ ] **Chart Annotation Page** (`/app/annotate/{trade_id}`)
  - [ ] Display chart image (from `/charts/by-trade/{trade_id}`)
  - [ ] Interactive chart canvas (using Fabric.js or Konva.js)
  - [ ] Tools: Mark POI, Mark BOS, Draw lines, Add notes
  - [ ] Save annotations to database
  - [ ] Link trade to setup and entry method from this page

- [ ] **Entry Methods Page** (`/app/entry-methods`)
  - [ ] List existing entry methods
  - [ ] Create new entry method (name, description, optional setup link)
  - [ ] Edit/delete entry methods
  - [ ] Show statistics (win rate, avg R for each method)

- [ ] **Trade Linking Interface**
  - [ ] From trade detail page, add "Link Setup" button
  - [ ] Modal/form to select setup, entry method, and optionally annotate chart
  - [ ] Show linked setup/entry method on trade detail page

### Database Changes
- [ ] **New Tables:**
  - [ ] `entry_methods` table (if not exists)
  - [ ] Verify `setups` and `annotations` tables match requirements
  
- [ ] **Table Modifications:**
  - [ ] Add `setup_id` and `entry_method_id` to `trades` table (if not exists)
  - [ ] Add indexes on `trades.setup_id`, `trades.entry_method_id`

- [ ] **Migrations:**
  - [ ] Create migration script for new tables/columns
  - [ ] Backfill existing trades (optional: link to default setup if possible)

### API Endpoints
| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| POST | `/setups` | Create setup definition | Planned |
| GET | `/setups` | List all setups | Planned |
| GET | `/setups/{id}` | Get setup details | Planned |
| PUT | `/setups/{id}` | Update setup | Planned |
| DELETE | `/setups/{id}` | Delete setup | Planned |
| POST | `/annotations` | Create chart annotation | Planned |
| GET | `/annotations/{trade_id}` | Get annotations for trade | Planned |
| PUT | `/annotations/{id}` | Update annotation | Planned |
| POST | `/entry-methods` | Create entry method | Planned |
| GET | `/entry-methods` | List entry methods | Planned |
| POST | `/trades/{id}/link-setup` | Link trade to setup/entry method | Planned |

---

## Implementation Details

### Architecture Approach
**Web App Only (Not Extension):**
- All setup documentation and chart annotation happens in the web app (`/app`)
- Extension remains pure AI chat (no teaching/documentation UI)
- Web app uses existing chart images from `/charts/by-trade/{trade_id}`
- Annotations stored as JSON coordinates (POI price, BOS price, optional drawing data)

**Chart Annotation Library:**
- Use **Fabric.js** or **Konva.js** for interactive chart drawing
- Store annotation data as JSON (not image overlays - keep original chart clean)
- Support: Mark POI (point), Mark BOS (line/level), Draw trend lines, Add text notes

**Data Flow:**
1. User opens trade in web app → Chart loads from `/charts/by-trade/{trade_id}`
2. User marks POI/BOS on chart → Coordinates saved to `annotations` table
3. User links trade to setup → `trades.setup_id` and `trades.entry_method_id` updated
4. Phase 4D (AI Learning) will use this structured data to learn patterns

### File Structure
```
server/
├── db/
│   └── models.py              # Add EntryMethod model, verify Setup/Annotation
├── setups/
│   ├── __init__.py
│   └── routes.py              # Setup CRUD endpoints
├── annotations/
│   ├── __init__.py
│   └── routes.py              # Annotation endpoints
├── entry_methods/
│   ├── __init__.py
│   └── routes.py              # Entry method endpoints
└── migrations/
    └── 006_add_entry_methods.sql  # Migration script

web/
├── setups/
│   └── page.html              # Setup definition page
├── annotate/
│   └── [trade_id]/
│       └── page.html          # Chart annotation page
├── entry-methods/
│   └── page.html              # Entry methods page
└── components/
    ├── chart-annotator.js     # Fabric.js/Konva.js chart drawing component
    └── setup-form.js          # Setup creation/edit form
```

### Component Breakdown

**Backend:**
- `SetupsRouter` - CRUD for setup definitions
- `AnnotationsRouter` - Store/retrieve chart annotations
- `EntryMethodsRouter` - CRUD for entry methods
- `TradeLinkingService` - Link trades to setups/entry methods

**Frontend:**
- `SetupListPage` - List and manage setups
- `SetupForm` - Create/edit setup definition
- `ChartAnnotator` - Interactive chart drawing (Fabric.js/Konva.js)
- `AnnotationToolbar` - Tools for marking POI, BOS, drawing lines
- `EntryMethodListPage` - List and manage entry methods
- `TradeLinkingModal` - Link trade to setup/entry method

### Data Flow

**Setup Documentation Flow:**
1. User navigates to `/app/setups`
2. Clicks "Create Setup"
3. Fills form: Name (e.g., "Bullish POI + BOS"), Type (bullish/bearish), Description
4. Saves → `POST /setups` → Stored in `setups` table

**Chart Annotation Flow:**
1. User opens trade detail page → Sees chart image
2. Clicks "Annotate Chart" → Opens annotation page
3. Chart loads with Fabric.js/Konva.js canvas overlay
4. User marks POI (clicks point) → Coordinates saved
5. User marks BOS (draws line) → Price level saved
6. User optionally links trade to setup/entry method
7. Saves → `POST /annotations` + `POST /trades/{id}/link-setup`

**Trade Linking Flow:**
1. User views trade → Sees "Link Setup" button
2. Clicks button → Modal opens
3. Selects setup from dropdown, entry method from dropdown
4. Optionally opens annotation page to mark POI/BOS
5. Saves → `POST /trades/{id}/link-setup` → Updates `trades.setup_id` and `trades.entry_method_id`

---

## Teaching System Design (For Phase 4D)

### How Teaching Will Work (Not in Chat)

**Location:** Web App Only (`/app/teach`)

**Goal:** Teach AI to draw setups from random charts (POI, BOS, setup type). Once AI can do this, it can suggest entry methods and precise entries.

**Two Teaching Approaches:**

#### Approach 1: Review Your Trades (Primary Method)
**Process:**
1. **User Draws Setup:**
   - User opens trade from their history
   - User marks POI and BOS on chart (using annotation tools)
   - User links trade to setup type and entry method
   - User adds notes: "This POI is correct because..."

2. **AI Learns from Examples:**
   - Each annotated trade becomes a teaching example
   - Stored in vector database (Chroma) with chart + annotations + setup + outcome
   - AI learns: "This setup looks like trade #15, which was a win with POI + 50% entry"

**When to Use:**
- Start with your existing 31 trades (and 2 other combines later)
- Go through trades one by one
- Draw setups yourself, explain why they're correct
- Build foundation of examples for AI to learn from

#### Approach 2: Test on Random Charts (Validation Method)
**Process:**
1. **AI Attempts Detection:**
   - User uploads random chart (not from your trades)
   - AI analyzes chart using GPT-5 Vision
   - AI attempts to draw POI and BOS on chart (using chart rendering tools)
   - AI suggests setup type and entry method

2. **User Corrects AI:**
   - User sees AI's attempt on annotation page
   - User adjusts POI/BOS points (drag markers)
   - User corrects setup type or entry method
   - User adds notes: "This POI is wrong because..."

3. **AI Learns from Corrections:**
   - Corrected example stored in vector database
   - AI learns: "I was wrong about this POI, correct one is here because..."
   - AI improves gradually with each correction

**When to Use:**
- After you've annotated 10-20 of your trades (foundation built)
- Test AI's understanding on new charts
- Correct AI's mistakes to improve accuracy
- Validate that AI is learning correctly

**Combined Approach (Recommended):**
1. **Phase 1 (Foundation):** Review your trades (Approach 1)
   - Annotate 20-30 trades from your history
   - Draw setups yourself, explain why
   - Build solid foundation of examples

2. **Phase 2 (Validation):** Test on random charts (Approach 2)
   - Upload random charts
   - Let AI try to draw setups
   - Correct AI's mistakes
   - Validate learning progress

3. **Phase 3 (Iteration):** Repeat until AI can draw setups accurately
   - Continue testing on random charts
   - AI accuracy improves with each correction
   - Goal: AI can draw setups from random charts with 90%+ accuracy

### AI Drawing Capability (Critical Feature)

**AI Must Be Able to Draw:**
- AI should use chart rendering tools to DRAW POI and BOS on charts
- AI's drawings should be visible on the annotation page
- User can see what AI learned and correct it visually

**How It Works:**
1. **AI Detection:**
   - AI analyzes chart image using GPT-5 Vision
   - AI identifies POI price levels and BOS break points
   - AI generates annotation coordinates (POI price, BOS price)

2. **AI Drawing:**
   - AI uses chart rendering tools (same as chart recreation)
   - AI draws POI markers (points) and BOS lines on chart
   - AI's drawing appears on annotation page as overlay

3. **User Correction:**
   - User sees AI's drawing
   - User can drag POI/BOS markers to correct positions
   - User can delete incorrect markers
   - User can add missing POI/BOS points

4. **Learning Feedback:**
   - Corrected annotations stored in database
   - AI learns from corrections
   - Next time AI sees similar chart, it draws more accurately

**Progress Visualization:**
- After each lesson, show what AI learned:
  - "AI correctly identified POI in 8/10 trades"
  - "AI correctly identified BOS in 6/10 trades"
  - "AI accuracy: 70% (improving)"
- Visual progress dashboard showing learning curve
- Compare AI's drawings to your corrections

**Why Not in Chat:**
- Chart annotation requires visual UI (drawing tools, canvas)
- Setup documentation needs structured forms
- Teaching flow is multi-step (detect → review → correct → learn)
- AI drawing requires chart rendering tools (not suitable for chat)
- Chat is for quick questions, not complex workflows

### Model Selection: RAG (Recommended)

**Why RAG (Not Fine-Tuning):**
- ✅ You have 60-70 trades (not enough for fine-tuning, which needs 200+)
- ✅ RAG works with limited data and improves as you add more
- ✅ Easy to add new examples (just annotate more trades)
- ✅ No expensive training costs
- ✅ Can update knowledge without retraining

**How RAG Works:**
1. **Store Examples:** Each annotated trade becomes a "teaching example"
   - Chart image + setup type + POI/BOS + entry method + outcome
   - Stored as vector embeddings in Chroma database

2. **Retrieve Similar:** When AI sees new chart
   - Converts chart to vector embedding
   - Searches Chroma for similar charts
   - Retrieves top 3-5 most similar examples

3. **Learn from Examples:** AI uses retrieved examples to understand
   - "This chart looks like trade #15 (POI setup, win)"
   - "Trade #15 used POI + 50% entry, but it failed"
   - "Based on similar examples, this setup has 60% win rate"

**Vector Database: Chroma (Recommended)**
- Free, local, easy to use
- Perfect for 60-70 trades (scales to thousands)
- No cloud costs
- Runs in Docker container alongside backend

**Alternative: Fine-Tuning (Future)**
- If you accumulate 200+ annotated trades later
- Can fine-tune GPT-5 on your specific strategy
- More expensive but more accurate
- Consider this in Phase 4E or later

---

## Testing Requirements

### Test Scenarios

#### Happy Path
1. **Scenario:** Create a new setup definition
   - **Steps:** Navigate to `/app/setups`, click "Create Setup", fill form, save
   - **Expected Frontend:** Setup appears in list, can edit/delete
   - **Expected Backend:** `POST /setups` returns 201, setup stored in database
   - **Success Criteria:** Setup visible in list, can be selected when linking trades

2. **Scenario:** Annotate a chart (mark POI and BOS)
   - **Steps:** Open trade detail, click "Annotate", mark POI point, mark BOS line, save
   - **Expected Frontend:** POI and BOS markers visible on chart, saved successfully
   - **Expected Backend:** `POST /annotations` returns 201, annotation stored with coordinates
   - **Success Criteria:** Annotation persists, can be viewed later, coordinates accurate

3. **Scenario:** Link trade to setup and entry method
   - **Steps:** Open trade detail, click "Link Setup", select setup and entry method, save
   - **Expected Frontend:** Trade shows linked setup/entry method, can be filtered by setup
   - **Expected Backend:** `POST /trades/{id}/link-setup` updates `trades` table
   - **Success Criteria:** Trade linked correctly, appears in setup statistics

#### Edge Cases
1. **Scenario:** Annotate chart without linking to setup
   - **Steps:** Mark POI/BOS, save annotation, don't link to setup
   - **Expected:** Annotation saved, trade remains unlinked (can link later)

2. **Scenario:** Delete setup that has linked trades
   - **Steps:** Create setup, link trades to it, delete setup
   - **Expected:** Option to unlink trades or prevent deletion with warning

3. **Scenario:** Multiple annotations per trade
   - **Steps:** Mark multiple POIs, multiple BOS levels on same chart
   - **Expected:** All annotations saved, can view/edit individually

#### Error Handling
1. **Scenario:** Invalid annotation coordinates
   - **Steps:** Try to save annotation with coordinates outside chart bounds
   - **Expected:** Validation error, annotation not saved

2. **Scenario:** Network error during save
   - **Steps:** Disconnect network, try to save annotation
   - **Expected:** Error message, option to retry, data not lost

### Integration Testing
- [ ] Setup creation → Annotation → Trade linking flow works end-to-end
- [ ] Chart annotation coordinates match visual markers
- [ ] Trade filtering by setup works correctly
- [ ] Statistics (win rate per setup/entry method) calculate correctly

### Regression Testing
- [ ] Existing trade viewing still works
- [ ] Chart images still load correctly
- [ ] Extension chat still works (no changes to extension)

---

## Deliverables

### Final Output
- Web app pages for setup definition, chart annotation, and entry method management
- API endpoints for setups, annotations, and entry methods
- Database schema with `setups`, `annotations`, and `entry_methods` tables
- Interactive chart annotation tool (Fabric.js or Konva.js)
- Trade linking interface (link trades to setups/entry methods)

### Acceptance Criteria
- [ ] Can create, edit, and delete setup definitions
- [ ] Can mark POI and BOS on charts visually
- [ ] Annotations persist and can be viewed later
- [ ] Can link trades to setups and entry methods
- [ ] Can filter trades by setup type
- [ ] Statistics show win rate per setup/entry method
- [ ] Chart annotation tool is intuitive and responsive
- [ ] All data stored in database (not JSON files)

### What "Done" Looks Like
A fully functional web app interface where you can:
1. Document your trading setups (bullish/bearish, market structure)
2. Mark POI and BOS on any trade's chart
3. Link trades to their setups and entry methods
4. View statistics about which setups/entry methods work best
5. Have structured data ready for Phase 4D (AI Learning System)

---

## Dependencies

### Prerequisites
- [ ] Phase 4A complete (database, web app foundation, chart viewing)
- [ ] Chart images accessible via `/charts/by-trade/{trade_id}`
- [ ] Web app foundation working (`/app` loads)

### Blockers
- [ ] None identified

### External Libraries
- [ ] **Fabric.js** or **Konva.js** (for chart annotation canvas)
  - Recommendation: **Fabric.js** (easier to use, better documentation)
  - Alternative: **Konva.js** (more performant, but steeper learning curve)

---

## Notes

### Design Decisions

**1. Web App Only (Not Extension):**
- Chart annotation requires visual UI (canvas, drawing tools)
- Setup documentation needs structured forms
- Teaching flow is multi-step (not suitable for chat)
- Extension remains pure AI chat (as per Phase 4A)

**2. Annotation Storage:**
- Store as JSON coordinates (not image overlays)
- Keep original chart images clean
- Can regenerate annotation overlays from JSON data
- More flexible for future features

**3. Model Selection: RAG (Not Fine-Tuning):**
- 60-70 trades is not enough for fine-tuning (needs 200+)
- RAG works with limited data and improves gradually
- No expensive training costs
- Can add examples incrementally

**4. Vector Database: Chroma:**
- Free, local, easy to use
- Perfect for current data size
- Can scale to thousands of trades
- Runs in Docker (no cloud costs)

### Adding More Trades (From Other Combines)

**Current State:**
- 31 trades from funded/eval account (already in database)
- 2 other combines with trades (not yet added)
- Trading journal images available (not CSV)

**When to Add:**
- **After Phase 4B Setup Complete:** Add trades after annotation system is ready
- **Why:** Need annotation tools to properly document setups for new trades
- **How:** Use trading journal images to extract trade data (similar to CSV import)

**Process:**
1. **Phase 4B Complete:** Annotation system working, can mark POI/BOS
2. **Extract Trade Data:** From trading journal images (manual entry or OCR)
3. **Import Trades:** Add to database (similar to CSV import process)
4. **Annotate Trades:** Use Phase 4B annotation tools to mark setups
5. **Link Setups:** Link new trades to setups/entry methods

**Recommendation:**
- Wait until Phase 4B annotation system is complete
- Then add trades from other combines
- Annotate all trades (old + new) together
- Build complete teaching dataset for Phase 4D

### Chart Quality Issues

**Problem:**
- Some charts rendered badly (e.g., CLZ5_5m_1486940457.png, MCLZ5_5m_1499163878.png)
- Need to identify and fix bad charts before annotation work

**Solution:**
1. **Identify Bad Charts:**
   - Review all chart images in `server/data/charts/`
   - Flag charts with rendering issues (missing data, incorrect markers, etc.)

2. **Fix Chart Recreation:**
   - Investigate `chart_reconstruction/renderer.py` for issues
   - Fix rendering logic (data handling, marker placement, etc.)
   - Test with known bad charts

3. **Re-render Bad Charts:**
   - Re-run chart recreation for bad charts
   - Verify all charts render correctly
   - Ensure all charts are ready for annotation

**Priority:**
- Fix before Phase 4B annotation work begins
- Bad charts will cause issues when annotating POI/BOS
- Need clean charts for teaching system

### Remove Old Command Logic from Chat

**Current State:**
- `/ask` endpoint is pure AI chat (no command execution)
- But `openai_client.py` still has command extraction logic in prompt (old code)
- Backend doesn't execute commands, just returns AI response

**Should We Remove It?**
- **Option 1: Remove Now (Recommended)**
  - Clean up codebase before Phase 4B
  - Remove command extraction logic from `openai_client.py` prompt
  - Simplify chat to pure natural language only
  - **Pros:** Clean code, no confusion, aligns with Phase 4A goals
  - **Cons:** Small refactor needed

- **Option 2: Remove Later**
  - Keep old code for now, focus on Phase 4B
  - Remove in Phase 4D or later cleanup
  - **Pros:** No interruption to Phase 4B work
  - **Cons:** Technical debt, confusing code

**Recommendation:**
- **Remove Now (Before Phase 4B)**
  - Quick cleanup (remove command extraction from prompt)
  - Aligns with Phase 4A "pure AI chat" goal
  - Clean codebase for Phase 4B work
  - Estimated time: 30 minutes

### Open Questions (For Discussion)

1. **Chart Annotation Library:**
   - Fabric.js vs Konva.js?
   - Recommendation: Fabric.js (easier, better docs)

2. **Annotation Granularity:**
   - One annotation per trade, or multiple?
   - Recommendation: Multiple (can mark multiple POIs, BOS levels)

3. **Setup Types:**
   - Predefined list or free-form?
   - Recommendation: Start with free-form, add common types later

4. **Entry Method Creation:**
   - User creates all methods, or AI suggests based on trade data?
   - Recommendation: User creates initially, AI suggests in Phase 4D

5. **Trade Linking:**
   - Required or optional?
   - Recommendation: Optional (can annotate without linking, link later)

---

## Implementation Status

### Completed
- [ ] (TBD)

### In Progress
- [x] Plan document

### Pending
- [ ] Database schema verification and migrations
- [ ] Backend API endpoints (setups, annotations, entry methods)
- [ ] Frontend pages (setup definition, chart annotation, entry methods)
- [ ] Chart annotation tool (Fabric.js/Konva.js integration)
- [ ] Trade linking interface
- [ ] Statistics and filtering

---

## Testing Status

### Passed
- [ ] (TBD)

### Failed
- [ ] (TBD)

### Pending
- [ ] Setup CRUD tests
- [ ] Chart annotation tests
- [ ] Trade linking tests
- [ ] Statistics calculation tests

---

## Changes from Original Plan

- N/A (initial plan)

---

## Next Steps After Phase 4B

**Phase 4C: Trade Analysis & Linking** (Optional - may merge with 4B)
- Pattern analysis dashboard
- "What worked, what didn't" analysis
- Entry method performance comparison

**Phase 4D: AI Learning System**
- RAG system with Chroma vector database
- Automated setup detection from charts
- Feedback loop: AI detects → You correct → AI learns
- Setup verification system

**Phase 4E: Entry Confirmation System**
- Entry confirmation query interface
- Historical pattern analysis
- Multi-factor entry assessment
- Alternative entry suggestions

---

**Remember:** This plan is the contract. Refer back to it during implementation and testing to stay on track!

