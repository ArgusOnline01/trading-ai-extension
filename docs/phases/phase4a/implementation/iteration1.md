# Phase 4A - Iteration 1

## Plan
- Fix `/trades` filters and sorting (outcome derivation, date filters, null-safe sorting, partial symbol match)
- Add minimal web UI (dark theme, basic filters, chart links)
- Add DB backfill for missing outcome/entry_time

## Implementation
- `server/trades/routes.py`: ilike symbol; derived outcome filter; date filters on entry/exit; null-last sorting
- `server/db/maintenance.py`: derive outcome from PnL; set entry_time from created_at if missing
- `server/app.py`: execute backfill at startup
- Web UI: `server/web/index.html`, `app.js`, `styles.css`

## Tests
- Verified filters/sorting and list responses
- Verified `/app` loads and renders table; chart link works
- Docs: see `../test/api_restructure_test.md`, `../test/web_app_test.md`

