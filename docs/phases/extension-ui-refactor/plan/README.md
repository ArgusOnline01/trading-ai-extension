# Phase 4B - Extension UI Refactor (Plan Draft v0.1)

## Summary
Refactor the Chrome extension UI into a modern, always-available overlay with pure AI chat, black+yellow design, and quick access to the Web App trades view.

## Goals
- Pure AI chat (no trade logging/upload in chat)
- Auto-open overlay on target domains (Topstep) with toggle
- Modern UI (dark theme, micro-animations)
- Button to open `/app` trades web view
- Keep model selector; remove quick chart analysis action from chat
- Prepare Teach Copilot and Analytics for later iterations (not in this iteration)

## Scope (Iteration 1)
- Overlay shell (header, chat area, footer input)
- Fixed-position toggle to show/hide overlay
- Minimal settings (model select)
- Link to `/app` in header
- Content script + background messaging wiring (no commands)

## Non-Goals (Iteration 1)
- Teach Copilot UI changes
- Analytics dashboard
- Command execution pipeline

## Technical Notes
- Manifest v3 remains
- `content/content.js`: mount overlay root and inject styles
- `background.js`: forward chat requests to `/ask`
- CSS: dark theme palette to match web app (black + yellow accent)

## Deliverables
- Updated extension assets (content script, overlay HTML/CSS-in-JS or injected CSS)
- Plan → Implement → Test docs

## Acceptance Criteria
- Overlay auto-appears on Topstep pages and can be toggled
- Chat sends to `/ask` and displays responses
- Header includes a button to open `/app` in a new tab
- No trade management UI in the extension

## Open Questions
- Which host patterns to auto-open on besides Topstep?
- Should overlay size/position be configurable and persisted?


