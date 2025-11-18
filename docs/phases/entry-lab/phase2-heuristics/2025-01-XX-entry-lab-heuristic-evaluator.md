# Plan: Entry Lab Phase 2 – Heuristic Evaluator

**Date:** 2025-01-XX  
**Initiative:** Entry Lab  
**Status:** Completed (baseline sims)

---

## 1. Context Snapshot
- **Goal:** Test concrete entry rules on the 31 funded trades to find rule sets that improve win rate/RR before integrating anything into the advisor.
- **Scope:** Annotate key features (POI/IFVG/fractals/BOS/mitigation) and simulate heuristics vs baseline (19.4% win, -$1,371 PnL).
- **Assumptions/Risks:** Manual annotation accuracy; small sample; sims depend on tagged levels (POI/IFVG/fractals/BOS).

---

## 2. Discussion & Decisions
| Topic | Decision | Rationale | Owner |
|-------|----------|-----------|-------|
| Annotation | Tag funded trades with POI/BOS/IFVG/fractals | Enables deterministic rule tests | Both |
| Rules to test | R1 IFVG + mitigation; R2 sweep before entry; R3 session filter (London/Asia); R4 POI50 counterfactual | Mirrors your methods | Both |
| Tooling | JSON annotations + Python script | Fast iteration | Me |

Open: HTF bias tag? Include/exclude symbols? Handling trades without POI?

---

## 3. Feature Overview
### What We Built
- Annotation file for the 31 trades (POI/IFVG/fractals/BOS, etc.).
- Heuristic evaluator script that ingests baseline + annotations and outputs metrics per rule.

### User Story
As a trader, I want to see which rule tweaks would have improved my funded trades so I can adopt them (and later enforce them via the advisor).

---

## 4. Implementation Blueprint
### Annotation Schema
- `trade_id`, `direction`
- `poi_low`, `poi_high`, `bos_level`
- `ifvg_low`, `ifvg_high` (if applicable)
- `fractal_range_low`, `fractal_range_high`, `fractal_target`
- `liquidity_swept`, `poi_mitigated_50`, `ifvg_present`, `entry_type`, `session`, `discipline_issue`, `exclude`, `note`

### Rules (implemented)
- **R1** IFVG mitigated (IFVG mid entry / IFVG SL / fractal TP; 8h window; $200 cap)
- **R2** Sweep before entry
- **R3** Session (London/Asia)
- **R4** POI50 (POI mid entry / POI extreme SL / fractal TP; 8h window; $200 cap)
- **R5** IFVG fractal (IFVG mid / IFVG SL / fractal TP; 8h window; $200 cap)

### Work Breakdown (done)
| Area | Tasks | Notes |
|------|-------|-------|
| Annotation | Tagged 31 funded trades with POI/BOS/IFVG/fractals; confirmed levels | Annotated PNGs + `entry_lab_annotations.json` |
| Evaluator | Script loads dataset + annotations; rules + counterfactual sims implemented | `server/analytics/entry_lab_heuristics.py` |
| Reporting | Baseline vs rule summaries in MD/JSON | `server/data/entry_lab_rules_summary.md/json` |

### Files / Modules
- `server/analytics/entry_lab_annotations.json`
- `server/analytics/entry_lab_heuristics.py`
- Reports: `server/data/entry_lab_rules_summary.md/json`, `server/data/entry_lab_rule_decisions.json`

---

## 5. Testing & Validation
### Scenarios (run)
1. Evaluator runs with annotations and outputs metrics per rule (pass).
2. Rule check: spot-checked trades (e.g., SILZ5, 6EZ5) to ensure tags drive the sim (pass).
3. Counterfactuals: verified POI50/IFVG sims hit SL/TP per 5m bars, 8h window, $200 cap (pass).

### Automation / Tooling
- CLI: `source venv/bin/activate && python server/analytics/entry_lab_heuristics.py`
- Outputs: `server/data/entry_lab_rules_summary.md/json`, `server/data/entry_lab_rule_decisions.json`

### “Done” Checklist
- Annotations completed/validated.
- Evaluator report saved (baseline + rules).
- Docs updated (this file + summary note in `entry_lab_rules_summary.md`).

---

## 6. Deliverables
- `server/analytics/entry_lab_annotations.json` (POI/IFVG/fractal tags)
- `server/analytics/entry_lab_heuristics.py` + reports (`entry_lab_rules_summary.md/json`, `entry_lab_rule_decisions.json`)
- Updated implementation/test docs for Phase 2

## 7. Results Snapshot (baseline vs rules)
- Baseline clean: n=26, win=23.1%, PnL=-776.
- R1 IFVG mitigated (simulated): n=9, win=33.3%, PnL=100.49.
- R2 sweep: n=10 clean, win=20.0%, PnL=17.50.
- R3 session (London/Asia): n=14 clean, win=28.6%, PnL=-169.00.
- R4 POI50 (fractal TP): n=10 clean, win=50.0%, PnL=338.38.
- R5 IFVG fractal: n=8, win=25.0%, PnL=-339.51.

## 8. Next Steps
- Use these sims as the baseline; revisit after adding more trades (live or research). New trades need full annotations (POI, IFVG, fractals, BOS, entry/exit/time/symbol) before rerunning heuristics.
- Optional: experiment with different caps/windows or closer TPs for IFVG to improve PnL.

## 9. Open Questions
- Add HTF bias tag now or later?
- Include/exclude specific symbols or sessions?
- How to handle trades without clear POI bounds (skip or approximate)?

