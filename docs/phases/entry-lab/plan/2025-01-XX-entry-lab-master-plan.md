# Plan: Entry Lab Master Roadmap

**Date:** 2025-01-XX  
**Initiative:** Entry Lab  
**Status:** Planning

---

## 1. Context Snapshot
- **Goal:** Build an AI-assisted entry advisor that consistently recommends, explains, and verifies higher-probability entries for your SMC strategy.
- **Scope:** Entry Lab will roll out in four subphases—Data Intake, Heuristic Evaluator, Advisor Integration, and AI Enhancements—each following Plan→Implement→Test.
- **Prior Work:** Phase 4 documentation, existing extension/backend, chart renderer, trade CSV imports, strategy notes in `docs/entry-lab/strategy.md`.
- **Assumptions/Risks:** Limited sample size (31 funded trades); need measurable baselines before AI; avoid derailing existing extension while iterating.

---

## 2. Discussion & Decisions
| Topic | Decision | Rationale | Owner |
|-------|----------|-----------|-------|
| Architecture | Data + metrics first, AI later | Prevents repeating Phase 4 mistakes | Both |
| Work breakdown | Four subphases (see below) | Each outputs measurable artifacts | Me |
| Documentation | Keep Plan→Implement→Test per subphase | Traceability, reuse | Both |

Open questions: When to expand beyond funded trades? How to incorporate qualitative notes (discipline, news)?

---

## 3. Feature Overview
### What Entry Lab Does
Creates a feedback loop where trades are captured, heuristics tested offline, and only proven logic is surfaced to the extension/AI chat. Final deliverable: an entry assistant that can analyze a chart, reference stats, and advise “enter / wait” with confidence.

### Why It Matters
Your existing AI chat can describe charts but can’t demonstrably improve win rate. Entry Lab ensures every recommendation is backed by data and can be backtested before risking capital.

### User Story
As a trader, I want the AI copilot to recommend entries that are statistically aligned with my strategy so I can increase win rate and protect funded accounts.

---

## 4. Implementation Blueprint (Subphases)

### Phase 1 – Data Intake & Baseline Metrics (in progress)
- Clean funded CSV, document render pipeline, compute baseline stats.
- Output: canonical dataset + metrics summary. (See `2025-01-XX-entry-lab-data-intake.md`).

### Phase 2 – Heuristic Entry Evaluator
- Use the dataset to test deterministic rules (50% POI, IFVG variants, hold filters).
- Build scripts/notebooks that simulate alternate entries, record MAE/MFE, and compare to baseline.
- Deliverable: evaluator module + report indicating which heuristics improve win rate/RR.

### Phase 3 – Advisor Integration
- Wire the validated evaluator into the backend/extension. Entry requests call the evaluator, produce suggestions, and log outcomes.
- UI shows rationale (“POI mitigated, IFVG formed, win rate X%”) and records actual result for feedback.

### Phase 4 – AI Enhancements / Learning
- Layer AI (vision/RAG) on top of the evaluator: auto-detect structure from charts (POI/BOS/IFVG/fractal targets, and 1m micro-structure flips), retrieve heuristic stats, and converse in chat.
- Expand dataset (live + research trades), rerun sims at scale, and explore lightweight pattern memory/clustered stats so the advisor can learn from more examples over time.

### Work Breakdown Table
| Phase | Key Tasks | Dependencies |
|-------|-----------|--------------|
| Phase 1 | Data cleaning, metrics | existing CSV, renderer |
| Phase 2 | Heuristic simulation, reporting | Phase 1 dataset |
| Phase 3 | Backend/extension integration, logging | Phase 2 evaluator |
| Phase 4 | AI + RAG integration, auto-detection | Phase 3 advisor |

---

## 5. Testing & Validation
- Each phase must produce reproducible scripts/notebooks + documented test results.
- Phase 2+ require “before vs after” comparisons to prove improvement.
- UI/extension changes must include MCP visual tests as per workflow guidelines.

---

## 6. Deliverables
- [ ] Phase 1 artifacts (dataset, metrics).
- [ ] Phase 2 evaluator report.
- [ ] Phase 3 advisor endpoints + UI.
- [ ] Phase 4 AI-enhanced advisor with learning loop.

## 7. Open Questions
- [ ] When to expand dataset beyond 31 trades?
- [ ] How to capture manual notes/exceptions for each trade?
- [ ] Budget/time allocation for AI API vs self-hosted models?

---

## 8. Status Tracker
### Phases
- [ ] Phase 1 – Data Intake (plan drafted)
- [ ] Phase 2 – Heuristic Evaluator
- [ ] Phase 3 – Advisor Integration
- [ ] Phase 4 – AI Enhancements

### Follow-ups
- [ ] Approve Phase 1 plan and start implementation.
- [ ] Schedule review after each phase before moving on.

---
