# Entry Lab – Learning & Strategy Discussion

**Goal:** Build an AI-assisted entry advisor that recommends only data-backed entries for your SMC strategy, with the long-term target of materially improving win rate (aspirationally ~80% if the data supports it).

## Where We Stand
- Dataset: 31 funded trades (mostly IFVG). Clean subset win rate ~23% with negative PnL. Best subset so far: IFVG + ≥50% mitigation (tiny sample, positive PnL but low win%).
- Rules evaluated: baseline/clean, IFVG+mitigation, sweep required, session filter, and a placeholder counterfactual for POI50 (needs SL/TP assumptions).
- Limitations: Small, IFVG-heavy dataset; not enough variety/volume to discover robust new patterns or reach high win% yet.

## How the Advisor Works (Now & Later)
- **Now:** Detect POI/BOS/sweeps/IFVG on a chart, apply the best-performing rules from our data, and recommend “enter / wait” with cited stats. No generic advice.
- **Progressive Learning:** Every on-plan recommendation gets logged; pattern scores (context + entry method) update over time. Good patterns get prioritized; bad ones demoted. Effectiveness hinges on having enough tagged examples.
- **Future “Thinking”:** The model can propose entries only if they match historically strong patterns (retrieval/scoring). For new/untested ideas, it must see similar contexts with good outcomes before recommending.

## Path to a Higher Win Rate
1) Simulate POI50 vs IFVG for existing trades (enter at POI mid, SL at POI extreme, TP at structural HH/LL) to see if win%/PnL improves.
2) Enforce the strongest rule set for live trading; log only on-plan trades; update stats continuously.
3) Grow the dataset with backtestable, well-tagged examples (including curated historical setups with known outcomes). Aim for tens of examples per pattern and 100–200+ clean trades overall for reliable cluster/embedding-based recommendations.

## About “Crazy Stats” Trading Bots
- Many high-win-rate bots use:
  - **Mean reversion/scalping/grid/martingale:** Many small wins, few large losses (win% looks great until it doesn’t).
  - **Overfit indicator mixes/backtests:** Curve-fitting past data; fragile live performance.
  - **HFT/stat-arb/microstructure edges:** Require massive data, latency advantages, and specialized infra.
- They often don’t follow discretionary SMC logic; edges can be narrow or short-lived. High win% ≠ robust profitability.

## Why Our Approach Is Different (and Better for You)
- It’s your SMC playbook, with transparent rules, tagged examples, and reproducible metrics.
- Recommendations are grounded in your data; no generic “AI guesses.”
- The learning loop is explicit: detect → retrieve patterns → apply rules → log outcomes → update pattern scores.

## What You Can Do Next
- Approve the POI50 counterfactual simulation and rerun metrics.
- If possible, add more tagged, backtestable trades (with POI/BOS/sweep/IFVG/entry/SL/TP/outcome), including curated historical examples you didn’t trade but can score.
- Stick to on-plan trades in live use; session-filter if needed; avoid off-plan entries that distort stats.
