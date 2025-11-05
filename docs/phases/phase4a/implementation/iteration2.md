# Phase 4A - Iteration 2 (In Progress)

## Plan
- Correct timestamps (entry/exit) and r_multiple from original CSV→JSON pipeline
- UI polish: currency formatting, button styling, ensure dates visible per trade

## Approach
- Source: `server/data/Trading-Images/trades_export.csv`
- Existing JSON: `server/data/performance_logs.json`
- Enrichment:
  - `server/db/enrich_from_logs.py` reads JSON and updates DB where fields are missing
  - If JSON lacks proper time fields, reconstruct the CSV→JSON merge

## Implementation (so far)
- `server/db/enrich_from_logs.py` added
- `server/app.py` invokes enrichment after backfill
- Web UI updated to show `$PnL`, date columns, and styled chart button

## Next
- Parse the CSV columns (EnteredAt/ExitedAt/TradeDay) into DB entry_time/exit_time with timezone
- If needed, regenerate `performance_logs.json` from CSV and re-run migration+enrichment
- Retest and update test docs

