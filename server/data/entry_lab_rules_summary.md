# Entry Lab Rule Metrics (current 15 annotated trades)

Metrics derived from the current CSV (15 research trades), grouped by entry_method:

## R4_counterfactual_poi50
- Total: 10
- Wins: 5, Losses: 4, Breakeven: 0
- Win rate: 55.56%
- Avg R/R: 3.021
- Total PnL: 6,854.00
- Avg PnL: 761.56

## R6_micro_shift
- Total: 5
- Wins: 4, Losses: 1, Breakeven: 0
- Win rate: 80.0%
- Avg R/R: 2.231
- Total PnL: 3,371.00
- Avg PnL: 674.20

Notes:
- Rule routing: entry_method containing “ifvg” → R5 (none in this set); containing “micro” → R6; otherwise → R4.
- PnL is computed from entry/exit using tick specs in risk_utils; R/R uses entry vs. SL vs. exit.
- Metrics will update as more trades are added.***
