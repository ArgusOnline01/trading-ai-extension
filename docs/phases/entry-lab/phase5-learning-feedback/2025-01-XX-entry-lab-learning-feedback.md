# Plan: Entry Lab Phase 5 — Advisor Learning & Feedback Loop

**Date:** 2025-01-XX  
**Initiative:** Entry Lab / Phase 5  
**Status:** Planning

---

## 1. Context Snapshot
- **Goal:** Make the advisor adapt over time by logging its suggestions vs. actual outcomes, refreshing rule stats, and tuning caps/grades/sizing based on real performance.
- **Scope:** Feedback logging, periodic stat recompute, simple auto-tuning of gates; optional lightweight re-ranker. Not in scope: full retraining of advisor scoring.
- **Prior Work:** Phase 3 advisor (rules/risk/grade); Phase 4 vision extraction (image → structured row); cleaned repo.
- **Assumptions/Risks:** Need consistent logging of advisor output + trade outcomes; data volume may be small at first; keep the loop transparent (no black-box surprises).

---

## 2. Discussion & Decisions
| Topic | Decision | Rationale | Owner |
|-------|----------|-----------|-------|
| Logging | Log advisor decision/grade/rule/risk + outcome/PnL per trade | Enables stat refresh | TBD |
| Tuning knobs | Adjust caps/grades/sizing per rule/symbol/session based on rolling stats | Simple, transparent | TBD |
| Model re-ranker (optional) | Only if enough data; otherwise stick to stat refresh | Avoid overfitting | TBD |

---

## 3. Feature Overview
### What We’re Building
A feedback loop that records advisor suggestions and actual outcomes, recomputes rule stats, and tunes risk/grade/sizing gates over time. Optionally, a small re-ranker to bias decisions using past performance.

### Why It Matters
Improves advisor quality as data grows; keeps decisions aligned with what actually works without manual retuning.

### User Story / Scenario
As a trader, I want the advisor to learn from its past calls—tighten when it loses, and reinforce what works—so suggestions stay aligned with real performance.

---

## 4. Implementation Blueprint

### Architecture / Approach
- Logging: persist advisor outputs (decision/grade/rule/risk/cap/grade_req) alongside trade outcome/PnL.
- Stat refresh: periodically recompute win_rate/avg_rr/avg_pnl per rule/symbol/session from logs.
- Tuning: adjust caps/grade requirements/sizing per rule based on refreshed stats (e.g., underperformers → stricter caps; outperformers → maintain).
- Optional: lightweight re-ranker on logged features → enter/skip bias.

### Work Breakdown
| Area | Tasks | Notes |
|------|-------|-------|
| Logging | - [ ] Add advisor log writer (DB/JSON) with outcome fields<br>- [ ] Link outcome updates to logged suggestions | |
| Stat refresh | - [ ] Script/API to recompute rule stats from logs<br>- [ ] Write back to rule summary | |
| Tuning | - [ ] Define caps/grade per rule/symbol/session based on stats<br>- [ ] Apply tuning in advisor inputs | Start simple (rule-level) |
| Re-ranker (opt) | - [ ] If enough data, fit small model to reweight enter/skip | Optional |

### Files / Modules
```
- server/analytics/logs/advisor_log.py (new)
- server/analytics/refresh_rule_stats.py (from logs)
- server/analytics/tuning.py (caps/grades per rule)
```

### Data Inputs
- Source: advisor logs (decision/rule/grade/risk/cap/grade_req) + trade outcome/PnL.
- Fields needed: trade_id, rule, decision, grade, risk_usd, cap, grade_req, outcome, pnl.

---

## 5. Testing & Validation

### Scenarios
1. Log + outcome → stats refresh updates rule summary.
2. Underperforming rule triggers tighter cap/grade; advisor reflects change.
3. Missing outcome handled gracefully (no crash; skipped in stats).

### Automation / Tooling
- [ ] Unit tests for log writer/reader
- [ ] Stat refresh script test with fixtures
- [ ] Tuning rules test (caps/grades adjusted as expected)

### “Done” Checklist
- [ ] Logs captured and queriable
- [ ] Rule stats refresh works from logs
- [ ] Tuning applied and documented
- [ ] (Opt) re-ranker off by default unless data supports it

---

## 6. Deliverables
- [ ] Advisor logging + storage
- [ ] Stats refresh tool
- [ ] Tuning rules (caps/grade per rule)
- [ ] (Opt) re-ranker prototype

## 7. Open Questions
- [ ] Where to store logs (DB table vs. JSON)?
- [ ] How often to refresh stats/tuning?
- [ ] Minimum data needed to enable re-ranker?

---

## 8. Status Tracker

### Implementation Tasks
- [ ] Logging
- [ ] Stats refresh
- [ ] Tuning
- [ ] (Opt) re-ranker

### Testing Tasks
- [ ] Log I/O tests
- [ ] Stats refresh test
- [ ] Tuning behavior test

### Follow-ups
- [ ] Align with vision pipeline output for auto-logging research trades

---

## Changes from Original Plan

N/A (initial draft).
