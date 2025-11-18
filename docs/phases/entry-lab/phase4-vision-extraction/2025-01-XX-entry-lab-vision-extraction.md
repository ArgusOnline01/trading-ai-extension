# Plan: Entry Lab Phase 4 — Vision Extraction

**Date:** 2025-01-XX  
**Initiative:** Entry Lab / Phase 4  
**Status:** Planning

---

## 1. Context Snapshot
- **Goal:** Auto-extract POI/BOS/IFVG bounds and 1m micro-structure (micro_shift) from screenshots, feed structured data into the advisor, and cut manual annotation time.
- **Scope:** Vision-only extraction + mapping pixel→price; micro-shift classification; wire outputs into the existing advisor flow; basic logging/validation. Not in scope: full retraining of advisor scoring.
- **Prior Work:** Phase 3 advisor/risk/scoring + chat UI (Phase 3); 15 annotated trades in CSV with updated rule stats (R4/R6); cleanup/archive completed.
- **Assumptions/Risks:** Need labeled screenshots for POI/BOS/IFVG/micro; y-axis OCR must be reliable for pixel→price; micro_shift definition must match our rules (not generic BOS).

---

## 2. Discussion & Decisions
| Topic | Decision | Rationale | Owner |
|-------|----------|-----------|-------|
| Pixel→price mapping | Use y-axis OCR + linear fit; tolerate label noise with sanity checks | Needed to convert boxes/lines to prices | TBD |
| Micro shift detection | Treat as separate classifier (true/false, optional direction), instructed with our 1m BOS/CHOCH rule | Avoid conflating with POI/IFVG extraction | TBD |
| Color/markup conventions | Enforce consistent colors/labels for POI/BOS/IFVG in screenshots | Boost detection accuracy | TBD |

---

## 3. Feature Overview
### What We’re Building
Vision pipeline that reads a chart image, extracts POI/BOS/IFVG bounds and micro_shift flag, converts to prices, and produces a structured row the advisor can consume.

### Why It Matters
Removes most manual data entry; lets us expand the dataset faster and auto-run the advisor on research trades (tagging “advisor would have said X”).

### User Story / Scenario
As a trader, I want to drop in a marked-up screenshot and get back a structured trade row (POI/BOS/IFVG/micro, prices) so I can log research trades and see the advisor’s suggestion without hand-entering fields.

---

## 4. Implementation Blueprint

### Architecture / Approach
- Extract y-axis labels via OCR → fit pixel→price linear map.
- Detect shapes/lines/text: POI/IFVG rectangles, BOS lines/labels, micro markers.
- Convert detected spans to price coords using pixel→price map; sanity-check ranges.
- Micro_shift: classify true/false (and direction) using a separate prompt/model guided by our micro BOS/CHOCH definition.
- Emit structured JSON row compatible with advisor (entry_method, POI/IFVG/BOS/micro_shift, fractal target if marked).

### Work Breakdown
| Area | Tasks | Notes |
|------|-------|-------|
| Backend/Vision | - [ ] OCR y-axis, fit pixel→price<br>- [ ] Detect POI/BOS/IFVG shapes/labels<br>- [ ] Map to prices + sanity checks<br>- [ ] Micro_shift classifier (rule-driven) | Keep detections tolerant; log confidences |
| Integration | - [ ] Map vision output → advisor payload<br>- [ ] Batch script: image → structured row → advisor | Save advisor verdict alongside extracted row |
| Data/Infra | - [ ] Assemble labeled screenshot set (POI/BOS/IFVG/micro)<br>- [ ] Eval harness (IoU/price error for boxes, precision/recall for micro) | Start with ~20–50 labeled imgs |
| UI (optional) | - [ ] Minimal upload hook or reuse tooling; no major UI required in Phase 4 draft | |

### Files / Modules
```
- server/vision/extract.py (new)  # OCR + detection + pixel→price
- server/vision/micro_classifier.py (new)  # micro_shift rule-based classifier/prompt
- server/analytics/run_vision_advisor.py (new)  # image → row → advisor batch
- docs/phases/entry-lab/phase4-vision-extraction/README.md (link to plan)
```

### Data Inputs
- Source: Marked-up screenshots (consistent POI/BOS/IFVG/micro colors/labels)
- Fields needed: y-axis labels, chart image with overlays; optional text labels for BOS/micro
- Transformations: OCR y-axis → pixel→price; detect shapes → price spans; classify micro_shift per rule.

---

## 5. Testing & Validation

### Scenarios
1. **Happy Path:** Image with POI rectangle + BOS line + IFVG box + micro marker → extract prices within tolerance; advisor accepts row.
2. **Edge Case:** Missing IFVG or BOS; still returns POI/micro; advisor handles partial data.
3. **Error Handling:** OCR fails or no shapes found → return structured warning, no crash.

### Automation / Tooling
- [ ] Eval script: IoU/price error for POI/BOS/IFVG vs. labels
- [ ] Precision/recall/F1 for micro_shift on labeled set
- [ ] Batch image→advisor script for regression

### “Done” Checklist
- [ ] Acceptance criteria met (tolerances, micro F1 target)
- [ ] Docs updated (plan/implementation notes)
- [ ] Sample run(s) logged with advisor outputs

---

## 6. Deliverables
- [ ] Vision extraction module (image → structured row)
- [ ] Evaluation harness + sample metrics
- [ ] Batch tool to run advisor on extracted rows

## 7. Open Questions
- [ ] Labeling: how many screenshots and what conventions/colors?
- [ ] Model choice: OCR + shape detection + prompt, or lightweight detector?
- [ ] Tolerances: acceptable price error (ticks) and micro F1 threshold?

---

## 8. Status Tracker

### Implementation Tasks
- [ ] OCR + pixel→price map
- [ ] Shape/label detection (POI/BOS/IFVG)
- [ ] Micro_shift classifier
- [ ] Adapter to advisor payload

### Testing Tasks
- [ ] Eval on labeled set (coords + micro)
- [ ] Batch advisor sanity run

### Follow-ups
- [ ] Decide color/label conventions for annotations
- [ ] Collect initial labeled images (~20–50)

---

## Changes from Original Plan

N/A (initial draft).
