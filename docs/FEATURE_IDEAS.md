# Feature Ideas (Backlog)

This document captures future ideas to consider. When we decide to build one, we’ll create a phase/iteration plan.

## 1) Extension UI Refactor (New Overlay Experience)
- Auto-open overlay on Topstep (and other target pages) without clicking the action button
- Pure AI chat only in the extension (no upload/log trade in chat)
- Fresh black+yellow visual design and typography; smooth micro-animations for open/close and buttons
- Left pane: conversation; right pane: quick context (selected symbol, last few trades, session switcher)
- Large, readable message input; clear send/stop controls
- Model selector retained; remove quick chart analysis action from chat
- Teach Copilot refactor:
  - Open from chat with clear UI affordance
  - Better chart viewer and annotation surface
  - Streamlined “review next trade” workflow
- Analytics dashboard refactor:
  - Clean KPIs (win rate, avg R, profit factor)
  - Filter by session/symbol/date; export CSV
- Button to open the Web App Trades page (`/app`) from the overlay header

## 2) Web App Enhancements
- Paginated, sortable trades table with fuzzy search
- Trade detail page with full metadata and chart
- Batch actions (tagging, notes), CSV export

## 3) DB + Export Tools
- DB migration/versioning
- “Export JSON” (generate performance_logs-like JSON from DB on demand)
- “Import CSV” tool in admin

## 4) Strategy/Teaching (Phase 4B+)
- Strategy module scaffolding
- Teaching session flows and accuracy dashboards

---

When promoting an item to implementation, move it into the appropriate phase plan and create the iteration docs (plan → implementation → test).

