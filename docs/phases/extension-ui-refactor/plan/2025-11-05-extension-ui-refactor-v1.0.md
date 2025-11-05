# Feature Plan: Extension UI Refactor

**Date:** 2025-11-05  
**Phase:** Phase 4B  
**Status:** Planning

---

## Feature Overview

### What It Does
Refactors the Chrome extension into a modern, always-available overlay with a redesigned Overlay Home (auto-opens on Topstep and TradingView) and a pure AI Chat view. The overlay uses a black + yellow theme, smooth micro-animations, and a left/right layout (Chat left, Quick Context right). Trade management is removed from the extension; a button opens the Trades Web App at `/app`.

### Why It's Needed
- Reduce UI complexity by separating chat from trade management
- Improve usability, performance, and visual consistency
- Align with the new architecture (chat in extension, management in Web App)

### User Story
As a trader, I want a clean overlay chat that auto-appears on Topstep so I can ask questions immediately, and a one‑click button to open the Trades Web App to manage and review trades.

---

## Technical Requirements

### Backend Changes
- [ ] None for Iteration 1 (reuse existing `/ask`)
- [ ] (Future) Streaming responses support (optional)

### Frontend Changes (Extension)
- [ ] Overlay Home view (default screen on auto-open)
  - [ ] Sections: New Conversation, Continue Chat, Past Sessions, My Performance, Analytics Dashboard, Teach Copilot
  - [ ] Black + yellow redesign; micro-animations
  - [ ] Button/link to open `/app`
- [ ] Pure AI Chat view (separate from Home)
  - [ ] Left pane: conversation transcript
  - [ ] Right pane: Quick Context (selected symbol, last few trades summary, session switcher)
  - [ ] Header model selector (default GPT-5 latest)
  - [ ] Remove upload and log-trade buttons
- [ ] Auto-open Overlay Home (not Chat) on Topstep/TradingView; persisted toggle in `chrome.storage`
- [ ] Resizable overlay (persist size/position)
- [ ] Content → Background messaging to call `/ask` with recent history

### Database Changes
- [ ] None

### API Endpoints
| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| POST | `/ask` | Pure AI chat (already implemented) | Existing |

---

## Implementation Details

### Architecture Approach
MV3 extension with two overlay routes/views:
- Overlay Home (default on auto-open)
- Chat (navigated from Home)
`content.js` mounts overlay, manages view switching (home ↔ chat) and Quick Context; `background.js` forwards `/ask`. Scoped CSS; settings persisted in `chrome.storage` (auto-open, size, last model, last view).

### File Structure
```
visual-trade-extension/
  content/content.js      # inject overlay, UI interactions
  content/overlay.css     # overlay styles (dark theme)
  background.js           # forwards chat to /ask; no command hooks
```

### Component Breakdown
- OverlayHeader: logo/title, close, open `/app`; on Chat view also shows model selector
- OverlayHome: menu cards (New Conversation, Continue Chat, Past Sessions, My Performance, Analytics, Teach Copilot)
- ChatView: ChatList (left), ChatInput; QuickContext (right)
- QuickContext: symbol, last N trades summary (from backend DB), session switcher
- ToggleButton: show/hide; ResizeHandle persists size

### Data Flow
- Auto-open: On target hosts, Overlay Home mounts (if enabled)
- Start chat: Home → Chat; user input → content → background → `/ask` → render assistant
- Quick Context: content fetches lightweight stats from backend
- Preferences (auto-open, size/pos, last model/view) stored in `chrome.storage`

### UI/UX Design Requirements
- Global
  - Black + yellow theme, but fully refreshed components (cards, buttons, inputs)
  - Typography scale and spacing updated for readability; 14/16/18/24rem steps
  - Smooth micro-animations (200–300ms) for hover, press, open/close, route transitions
  - Shadows and elevation tokens for layers (overlay, modals, menus)
- Overlay Home
  - Card-based menu with icons and subtitles; staggered fade/slide-in on mount
  - Responsive layout; looks good from 1200px to 1366px typical desktop
  - Keyboard focus styles; tab/navigate through cards
- Chat View
  - Left pane conversation with chat bubbles, timestamps, and subtle message-in animation
  - Right pane Quick Context panel with compact KPIs and session switcher
  - Header contains model select (defaults GPT-5 latest) and clear affordance to return to Home
  - Remove upload/log-trade buttons; only text input and send
  - Loading indicators for in-flight requests; error toasts on failures

---

## Testing Requirements

### Test Scenarios

#### Happy Path
1. **Scenario:** Auto-open overlay on Topstep
   - **Steps:** Navigate to Topstep
   - **Expected Frontend:** Overlay visible; dark theme; toggle works
   - **Expected Backend:** `/ask` is reachable and stable
   - **Success Criteria:** No toolbar click needed to access chat

2. **Scenario:** Chat round-trip
   - **Steps:** Send a question; receive a response
   - **Expected Frontend:** User/assistant messages render with loading feedback
   - **Expected Backend:** 200 OK from `/ask`
   - **Success Criteria:** Consistent and timely response

3. **Scenario:** Open Trades Web App
   - **Steps:** Click header button
   - **Expected Frontend:** New tab opens `/app`
   - **Success Criteria:** Trades page loads

#### Edge Cases
1. **Scenario:** Backend unavailable
   - **Steps:** Stop backend; send message
   - **Expected:** Graceful error and retry affordance

2. **Scenario:** Auto-open disabled
   - **Steps:** Toggle off in settings; reload page
   - **Expected:** Overlay remains hidden until toggled on

#### Error Handling
1. **Scenario:** Network timeout
   - **Steps:** Simulate slow network
   - **Expected:** Loading → timeout notice → retry option

### Integration Testing
- [ ] Content ⇄ Background messaging works
- [ ] Background → `/ask` request path works
- [ ] Settings persist across reloads

### Regression Testing
- [ ] Toolbar click still opens overlay
- [ ] No trade-management UI remains in extension

---

## Deliverables

### Final Output
Updated extension overlay for chat with `/app` button; no trade-management UI in extension.

### Acceptance Criteria
- [ ] Auto-open shows Overlay Home (not Chat) on Topstep/TradingView (configurable)
- [ ] Overlay Home displays redesigned menu items and transitions to Chat
- [ ] Chat sends to `/ask` and renders responses with loading/error states
- [ ] Quick Context shows symbol, last few trades, session switcher
- [ ] Open App button launches `/app` in new tab
- [ ] Visual style fully refreshed (cards, buttons, inputs, bubbles) within black + yellow theme; micro-animations on hover/press/open/route
- [ ] Overlay is user-resizable; size/position persisted
- [ ] Default model is GPT-5 latest; current logo retained; no upload/log-trade in chat

### What "Done" Looks Like
A streamlined, branded overlay chat experience in the extension, with the Web App as the place for reviewing and managing trades.

---

## Dependencies

### Prerequisites
- [ ] Backend `/ask` live (done)
- [ ] Web App `/app` available (done)

### Blockers
- [ ] None identified

---

## Notes
- Teach Copilot and Analytics overlays will be separate iterations later in Phase 4B
- Animations should be subtle for performance

---

## Implementation Status

### Completed
- [ ] (TBD)

### In Progress
- [x] Plan document

### Pending
- [ ] Overlay shell implementation
- [ ] Chat wiring to `/ask`
- [ ] Settings persistence
- [ ] Polish and tests

---

## Testing Status

### Passed
- [ ] (TBD)

### Failed
- [ ] (TBD)

### Pending
- [ ] Auto-open tests
- [ ] Chat round-trip tests
- [ ] `/app` button tests

---

## Changes from Original Plan
- N/A (initial plan)

---

## Decisions (from Q&A)
1) Host patterns: Auto-open on Topstep and TradingView.  
2) Default behavior: Auto-open ON by default for new installs.  
3) Overlay: User-resizable; size persisted in `chrome.storage`.  
4) Model selector: Default to GPT-5 latest.  
5) Branding: Keep current logo (can update later).  
6) Keyboard shortcut: None for now; rely on close/toggle UI.  
7) Telemetry: Minimal local-only counters (e.g., toggles/opens), not transmitted.

---

## Session Reliability (Fixes)
- [ ] Ensure session boot (IndexedDB) never blocks UI; show skeletons instead of indefinite "Loading..."
- [ ] Retry/backoff for session load; console diagnostics
- [ ] Persist last view (home/chat) and reopen appropriately


