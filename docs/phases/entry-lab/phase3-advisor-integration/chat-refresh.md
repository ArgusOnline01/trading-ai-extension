# Chat Refresh (pre-Phase 3 wiring)

This note captures what we are keeping, trimming, and simplifying for the chat before wiring the Phase 3 advisor.

Keep (minimal core)
- Basic chat thread with short-term history.
- Ability to accept chart images (vision-capable model) and a selected trade/setup ID for structured context.
- Thin tool layer: call `POST /analytics/advisor/evaluate` when asked for a suggestion; use `risk_utils` for quick risk answers.
- Context sources: current trade/setup (symbol, direction, POI low/high, fractal target, micro_shift, entry_method, contracts, entry/sl/tp, session), recent turns, optional uploaded image.

Drop/trim (legacy/low-value for current scope)
- Old command zoo/copilot bridge commands not tied to advisor or chart Q&A.
- Phase 4D teaching/learning hooks inside chat loop (keep separate flows).
- Navigation helpers that duplicate UI state (keep only “set current trade/setup”).
- Extra analytics lookups in chat (keep advisor; optional simple stats later).
- Overly verbose fallbacks; keep one friendly fallback.

Target behavior
- General Q&A about the current trade/setup and strategy rules.
- “Evaluate this setup” → call advisor → return decision, grade/score, rule used, risk numbers, reasons.
- “What’s my risk?” → compute via `risk_utils` with entry/SL/TP/contracts/symbol.
- Optional: fetch last X trades (defer if not needed).

Next implementation steps
- Backend: legacy vision/outcome chat endpoints removed. Next: simplify prompt builder to include instructions + current trade/setup data + recent turns + advisor result (if present); no extra tool prompts.
- Frontend: add a simple “Evaluate with Advisor” action in chat UI that posts key fields to `/analytics/advisor/evaluate`; keep image upload; drop old command shortcuts.
- Logging: keep per-session log; no RAG wiring for now.

Files touched (so far)
- Added: `docs/phases/entry-lab/phase3-advisor-integration/chat-refresh.md` (this file).
- Added chat hook: `/chat/advisor/evaluate` for Phase 3 advisor.
- Removed legacy chat vision/outcome endpoints from `server/chat/routes.py`.
