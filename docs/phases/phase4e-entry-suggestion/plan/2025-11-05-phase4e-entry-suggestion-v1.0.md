<!-- 8625daef-3307-4dd2-bcf5-a673704fdbbc 27244c8c-6dc6-4ab3-a44d-1efbb0626ba0 -->
# Feature Plan: Phase 4E – Entry Suggestion & Learning System

**Date:** 2025-01-XX  
**Phase:** Phase 4E  
**Status:** 🟡 Planning

---

## Feature Overview

### What It Does
Build an AI-assisted workflow that analyzes uploaded chart images, tracks setup progression, recommends entry + stop loss levels, and learns from outcomes using retrieval augmented generation (RAG) so future suggestions improve over time.

### Why It's Needed
- Provide actionable trade assistance instead of manual annotation grading.
- Capture the trader’s strategy logic (setups, confluences, risk rules) and reuse it consistently.
- Create feedback loops (WIN/LOSS/SKIPPED) that let the AI learn which setups succeed.
- Maintain context across a trading session without re-explaining every step.

### User Story
As a trader, I want the AI copilot to watch my session, tell me when conditions are met to enter, suggest entry/stop prices with reasoning, and improve over time by learning from the results so I can trade faster and with higher confidence.

---

## Technical Requirements

### Backend Changes
- [ ] Strategy documentation endpoints for capturing trader-defined setups.
- [ ] Chat session state management with multi-turn context.
- [ ] Entry suggestion logic using GPT-5 Vision + strategy context.
- [ ] Outcome tracking endpoints to store result feedback.
- [ ] RAG indexing and retrieval for similar past setups and patterns.
- [ ] Visual marker utilities to convert price levels to pixel coordinates.
- [ ] Background tasks or utilities for pattern extraction from outcomes.

### Frontend Changes
- [ ] Strategy documentation page (web app).
- [ ] Teach/Annotate navigation update to include Strategy + Progress.
- [ ] Chat UI enhancements (state badge, entry suggestion cards, outcome buttons).
- [ ] Visual overlay display for entry/stop coordinates (text first, optional canvas overlay).
- [ ] Session state summary surfaced in extension header.
- [ ] Error handling and status feedback for image uploads + analysis.

### Database Changes
- [ ] `strategies` table to persist documented strategy data.
- [ ] `chat_sessions` table for per-session state JSON.
- [ ] `entry_suggestions` table with price/stop/reasoning and metadata.
- [ ] `entry_outcomes` table linked to suggestions, capturing result + notes.
- [ ] Migrations for above tables (Phase 4E migration set).

### API Endpoints
| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| POST | `/strategy` | Create/update strategy definition | Planned |
| GET | `/strategy` | Fetch active strategy content | Planned |
| GET | `/chat/session/{session_id}/state` | Retrieve current session state | Planned |
| POST | `/chat/session/{session_id}/analyze` | Analyze chart + suggest entry | Planned |
| POST | `/chat/outcome` | Record WIN/LOSS/SKIPPED outcome | Planned |
| GET | `/chat/outcome/stats` | Aggregate stats for outcomes | Planned |

---

## Implementation Details

### Architecture Approach
1. **Strategy Capture Layer** – web form saves structured strategy, setups, stop rules. Data feeds prompts and RAG.
2. **Session State Engine** – `state_manager` maintains session JSON (waiting-for, met, reasoning) keyed by session_id.
3. **Entry Suggestion Service** – `entry_suggester` composes prompts with strategy + state + similar outcomes, calls GPT-5 Vision, parses JSON response.
4. **Outcome Learning Loop** – outcome tracker stores results, indexes suggestion/outcome pairs in Chroma, pattern extractor summarizes success factors.
5. **Frontend Integration** – extension content script orchestrates uploads, displays suggestions, collects outcomes, and surfaces state badges.

### File Structure
```
server/
├── app.py
├── strategy/
│   ├── __init__.py
│   └── routes.py
├── chat/
│   ├── __init__.py
│   ├── routes.py
│   ├── state_manager.py
│   ├── entry_suggester.py
│   ├── visual_markers.py
│   └── outcome_tracker.py
├── ai/
│   └── rag/
│       ├── entry_learning.py
│       └── pattern_extractor.py
└── db/
    ├── models.py
    └── migrations/

visual-trade-extension/
└── content/
    └── content.js
```

### Component Breakdown
- **Strategy Routes:** CRUD for user strategy, served via `strategy.html`.
- **State Manager:** Create/update session state, expose summary for UI badges.
- **Entry Suggester:** Build prompts, call GPT-5 Vision, return structured suggestion JSON.
- **Visual Markers:** Translate price levels into pixel overlays (phase-in).
- **Outcome Tracker:** Persist outcomes, update stats, trigger RAG indexing.
- **Pattern Extractor:** Use LLM to summarize patterns from similar outcomes.
- **Extension UI:** Detect entry-related intents, call backend, render suggestions, collect outcomes.

### Data Flow
1. User uploads image + question → extension sends to `/chat/session/{id}/analyze`.
2. Backend loads strategy + state + similar outcomes → prompt → GPT-5 Vision output.
3. Response saved in `entry_suggestions`, state updated, returned to extension.
4. Extension renders suggestion card, adds outcome buttons.
5. User clicks WIN/LOSS/SKIPPED → `/chat/outcome`, stored + indexed.
6. Future analyses query RAG for similar suggestions/outcomes and include findings in prompt.

---

## Testing Requirements

### Test Scenarios

#### Happy Path
1. **Scenario:** Entry suggestion after required confluences met  
   - **Steps:** Upload baseline chart, AI waits for confluences → upload updated chart meeting conditions → request analysis  
   - **Expected Frontend:** Card shows entry price, stop loss, reasoning, outcome buttons, state badge updates  
   - **Expected Backend:** New `entry_suggestions` record, session state updated to ready, overlay coordinates returned  
   - **Success Criteria:** HUD displays correct coordinates, outcome buttons functional, stats update after selection

#### Edge Cases
1. **Scenario:** Image uploaded without entry question  
   - **Steps:** Upload chart with unrelated prompt  
   - **Expected:** System declines to analyze (no suggestion), state unchanged
2. **Scenario:** Strategy missing required fields  
   - **Steps:** Clear strategy data, attempt analyze  
   - **Expected:** Error message prompting completion of strategy doc

#### Error Handling
1. **Scenario:** Backend returns model error  
   - **Steps:** Force API failure (simulate)  
   - **Expected:** Extension surfaces error, no state corruption, retry available

### Integration Testing
- [ ] Entry suggestion endpoint returns expected JSON schema.
- [ ] State manager persists across multiple image uploads.
- [ ] Outcome endpoint updates stats and triggers RAG indexing.
- [ ] Extension UI renders suggestion + outcome controls correctly.

### Regression Testing
- [ ] Existing annotation workflow unaffected.
- [ ] Teach/Annotate pages still reachable with new nav items.
- [ ] No breaking changes to Phase 4D lessons data.

---

## Deliverables

### Final Output
- Strategy documentation UI + API.
- Chat session state engine with entry suggestion endpoint.
- Extension UI that displays suggestions, state, and outcome controls.
- Outcome learning pipeline (storage + RAG indexing + pattern extraction).
- Documentation summarizing architecture and testing.

### Acceptance Criteria
- [ ] AI can cite strategy definitions and current state in reasoning.
- [ ] Entry/stop suggestions returned with coherent reasoning and markers.
- [ ] Session badge reflects waiting-for vs met confluences.
- [ ] Outcomes recorded and reflected in stats API.
- [ ] RAG retrieval influences prompt (see logs).

### What "Done" Looks Like
Trader uploads charts through the extension, receives actionable entry/stop guidance with state awareness, records outcomes, and the AI leverages past results to adjust future recommendations.

---

## Dependencies

### Prerequisites
- [ ] Phase 4D backend infrastructure running (FastAPI, DB migrations).
- [ ] GPT-5 Vision API availability and credentials.
- [ ] ChromaDB configured for outcome indexing.

### Blockers
- [ ] Coordinate accuracy bugs in Teach HUD (monitored, but not blocking Phase 4E backend).
- [ ] Screenshot capture permissions in extension (tracked separately).

---

## Notes
- Coordinate issues from Phase 4D teaching flow remain but do not block entry suggestion logic (overlay accuracy to be iteratively refined).
- Existing teaching/lesson infrastructure kept intact but no longer central to Phase 4E workflow.
- Emphasize logic-driven learning: coordinates supplement but do not replace strategy reasoning.
- Integrate Playwright MCP visual testing into QA pass for extension UI.

---

## Implementation Status

### Completed
- [x] Initial plan draft (this document).
- [x] Strategy routes, models, and page scaffolding.
- [x] Chat session state + entry suggestion endpoint.
- [x] Outcome tracking routes and DB models.
- [x] RAG indexing utilities and pattern extractor.
- [x] Extension UI integration for suggestions and outcomes.

### In Progress
- [ ] Visual overlay refinement (price → pixel accuracy).
- [ ] Prompt tuning for improved suggestion quality.

### Pending
- [ ] Long-term memory summarization enhancements.
- [ ] Advanced analytics dashboard for outcomes.

---

## Testing Status

### Passed
- [x] Backend unit tests for state manager and entry suggester.
- [x] API contract tests for outcome tracking.
- [x] Extension manual tests for entry suggestion flow.

### Failed
- [ ] Visual overlay coordinate alignment (Teach vs Annotate variance) – needs follow-up.

### Pending
- [ ] Playwright MCP visual regression tests for extension UI.
- [ ] Load testing for multi-session concurrency.

---

## Changes from Original Plan
- Pivoted away from forcing AI to replicate exact user annotations; focus shifted to entry suggestion logic and outcome learning.
- Added dedicated strategy documentation phase to ground reasoning.
- Replaced overlay-first approach with text-first suggestions, overlay optional while coordinate bugs persist.
- Introduced Playwright MCP testing workflow for frontend validation.

---

**Remember:** This plan is the contract. Refer back to it during implementation and testing to stay on track!