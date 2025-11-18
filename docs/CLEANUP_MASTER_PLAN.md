# Cleanup Master Plan (Repository Purge & Organization)

**Date:** 2025-11-18  
**Goal:** Separate legacy vs. current work, define what to keep/archive/remove, and stabilize the directory for Entry Lab + current chat/advisor flows.

---

## 1) Scope & Principles
- Keep: everything powering current Entry Lab (Phase 1–3) + chat/advisor UI, tick-aware risk, annotation templates/guides, and Phase 4 prep.
- Archive (move to `/archive` folders or clearly tag `legacy`): older chat command scaffolding, unused decision/vision stubs, legacy combine/import artifacts, superseded docs.
- Remove: dead/unreferenced code/docs/seeds/screenshots that will not return.
- Do not delete data you still need for rule stats/analytics. Prefer archiving if unsure.

---

## 2) Current State (high-level map)
- **server/**
  - Analytics (advisor_scoring, risk_utils, advisor, routes) → current, keep.
  - Chat (routes with refreshed advisor verbalizer) → current, keep.
  - Decision/vision legacy (e.g., `decision.py`, old vision hooks) → likely archive/remove if unused.
  - Data (`server/data/entry_lab_*`, rule summaries) → keep current; audit old JSONs.
  - DB/migrations/config → keep in-use migrations/config; audit seeds/old imports.
  - Misc modules (ai, memory, performance, navigation, etc.) → classify per usage; archive unused submodules.
- **visual-trade-extension/**
  - content/popup with advisor modal + chat refresh → current, keep.
  - Any legacy command UIs/helpers → archive/remove if unused.
- **docs/**
  - Phases/entry-lab (Phase 1–4) → current, keep.
  - PURGE_SUMMARY, New_Files_to_see, etc. → keep as references.
  - Older specs/ideas (LATV2 removal, etc.) → archive if no longer relevant.
- **ops/scripts/docker**
  - docker-compose and helpers → keep if still used; otherwise archive/remove stale variants.

---

## 3) Proposed Actions (Keep / Archive / Remove)
### Keep (move to clarified structure, no action besides confirming)
- `server/analytics/` (advisor, scoring, risk_utils, routes)
- `server/chat/routes.py` (refreshed chat + advisor verbalizer)
- `server/data/entry_lab_rules_summary.*`, `entry_lab_annotations_template.csv`
- `docs/phases/entry-lab/*` (Phase 1–4), `docs/entry-lab/ANNOTATION_CSV_GUIDE.md`
- `visual-trade-extension/content/*`, `visual-trade-extension/popup/*`
- Core config: `server/requirements.txt`, `docker-compose.yml` (if used), `server/config/*`

### Archive (move to `/archive` under the same root or tag with `legacy/`)
- `server/decision.py` and any old vision/command handlers not wired to chat/advisor
- Legacy chat command scaffolding (old intents/handlers) if not used
- Legacy combine/trade import utilities not part of Entry Lab (e.g., “invalid combine trades” handling)
- Old JSON datasets no longer used for stats (keep rule summaries/annotation templates)
- Docs: legacy specs/ideas not informing current roadmap (move to `docs/archive/`)
- Any unused scripts/ops helpers or alt docker files

### Remove (only after confirmation; safe-delete if unreferenced)
- Stale screenshots, duplicate/outdated specs already superseded
- Dead seeds/fixtures not referenced by tests or runtime
- Any untouched logs/temp files (if reintroduced)

---

## 4) Execution Plan
1) **Label & Stage**
   - Create `server/archive/` and `docs/archive/` for parked items.
   - Move identified legacy code/docs there (no behavioral change).
2) **Reference Scan**
   - `rg` for imports/references to candidates before removal.
   - Verify extension build and API startup after each move.
3) **Validate Runtime**
   - Start API; run a quick advisor call; open extension advisor modal.
4) **Prune**
   - Delete only items confirmed unused and already archived for a grace period (or after explicit approval).

---

## 5) Open Decisions
- Do we keep any legacy vision entry points for Phase 4 reference, or archive now?
- Are combine/import utilities still needed? If not, archive/remove.
- Which docker/ops scripts are actually used in your workflow?

---

## 6) Recommendations to Proceed
- Approve creation of `server/archive/` and `docs/archive/` and moving legacy items there first.
- Approve removal of clearly dead assets (stale screenshots, temp logs).
- Optionally add a short `README` in each `archive/` directory noting what was parked and why.

Once you confirm, I’ll execute: move legacy items to `archive/`, prune dead files, and leave keepers in place.***
