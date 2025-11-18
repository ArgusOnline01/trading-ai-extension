# Plan: Entry Lab Phase 3 – Advisor Integration & Risk Checks

**Date:** 2025-01-XX  
**Initiative:** Entry Lab  
**Status:** Completed (Phase 3 shipped)

---

## 1) Context & Goal
- Wire the heuristic evaluator into the backend/extension so suggestions are rule-based, transparent, and logged.
- Enforce risk discipline on each suggestion (display $ risk, % of remaining drawdown, R/R; warn/refuse if over cap).

## 2) Scope
- Inputs: annotated setup or form fields (symbol, entry_time, direction, POI/IFVG/fractal/BOS, session/discipline flags, size, remaining drawdown or risk cap).
- Processing: pick the best-performing rule (default POI50 mid, extreme SL, fractal TP; optional triggers: mitigation/sweep/IFVG), evaluate on/off-plan, compute WR/PnL stats, compute risk.
- Outputs: decision (enter/wait/skip), entry/SL/TP, rationale (rule applied, triggers), historical WR/PnL for that rule/context, risk metrics, and a log entry.

## 3) Deliverables
- Advisor endpoint that accepts setup data, applies rules, computes risk (tick-size aware), and returns the payload.
- UI hook (form in extension) that shows rationale, risk, decision, and historical WR/PnL.
- Logging/saving via chat history (IDB) for replay; future outcome logging stays in backlog.

## 4) Work Breakdown
- Backend: endpoint; call evaluator; risk calc (tick_size * tick_value * contracts); on/off-plan + decision payload; logging hook (IDB).
- Frontend/UX: modal form in extension; display rationale/WR/PnL/risk; conversational GPT-5 verbalizer for advisor replies; shows warnings/refusals.
- Config: defaults for rule (POI50+fractal TP; IFVG selects R5), risk caps (10% of remaining drawdown by default), grade gate (default A+), optional micro gate.

## 5) Testing & Validation
- Happy path: valid setup → decision/grade/rule + risk metrics and chatty GPT reply (tested via /chat/advisor/evaluate).
- Over-risk: rejects when risk_usd > cap (e.g., CL 59.45→59.32 risk $130 > 10%*$500 → skip).
- Grade gate: rejects below A+ by default (MNQ POI-only, micro/IFVG false → skip).
- IFVG route: selects R5_ifvg_fractal and returns decision/risk (6E example).
- Storage: messages saved via IDB in extension; raw advisor payload kept in metadata.

## 6) Open Questions
- Risk cap rule (fine-tune % of remaining drawdown) and auto-size vs. warn only.
- Require micro gate always, or keep optional?
- Include HTF bias tag now or later?

## 7) Next Steps
- (Optional polish) Add “Details” toggle in UI to hide raw line; expose grade/risk-cap inputs in form.
- (Future) Log outcomes for refreshed rule stats; add HTF bias tags; integrate vision (Phase 4).
