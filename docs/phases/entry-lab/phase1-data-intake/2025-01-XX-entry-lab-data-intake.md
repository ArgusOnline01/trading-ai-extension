# Entry Lab Phase 1 – Data Intake Testing

**Date:** 2025-01-XX  
**Status:** ✅ Pass

## Test Scenarios
1. **Happy Path:**
   - Command: `python3 server/analytics/entry_lab_intake.py`
   - Result: Script processed 31 trades, emitted dataset + metrics files, printed win rate (19.4%) and total PnL (-1371.00).
2. **Data Validation Spot Check:**
   - Manually compared trade `1540212786` across CSV, JSON output, and chart path to confirm timestamps/prices match.
   - Verified sessions were assigned (London for early-morning entries).
3. **Artifact Inspection:**
   - Reviewed `server/data/entry_lab_metrics.md` to ensure per-symbol and per-session stats populate correctly.

## Outputs Verified
- `server/data/entry_lab_trades.json`
- `server/data/entry_lab_metrics.json`
- `server/data/entry_lab_metrics.md`

## Result
All tests passed; artifacts generated and reproducible via the intake script.
