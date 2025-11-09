# Phase 4B Comprehensive Test Plan

Based on testing requirements from the Phase 4B plan.

## Test Coverage Checklist

### Happy Path Tests ✅
- [x] Create a new setup definition (API tested)
- [ ] Create a new setup definition (UI tested)
- [ ] Annotate a chart (mark POI and BOS) - UI
- [x] Link trade to setup and entry method (API tested)
- [ ] Link trade to setup and entry method (UI tested)

### Edge Cases Tests ❌
- [ ] Annotate chart without linking to setup
- [ ] Delete setup that has linked trades
- [ ] Multiple annotations per trade (multiple POIs, multiple BOS levels)

### Error Handling Tests ❌
- [ ] Invalid annotation coordinates (negative, out of bounds)
- [ ] Network error during save (simulate offline)
- [ ] Duplicate setup name
- [ ] Missing required fields
- [ ] Invalid trade_id in annotation
- [ ] Invalid setup_id/entry_method_id in trade linking

### Integration Tests ❌
- [ ] Setup creation → Annotation → Trade linking flow (end-to-end)
- [ ] Chart annotation coordinates match visual markers
- [ ] Trade filtering by setup
- [ ] Statistics (win rate per setup/entry method)

### Regression Tests ❌
- [ ] Existing trade viewing still works
- [ ] Chart images still load correctly
- [ ] Extension chat still works (no changes to extension)

## Test Scripts

### 1. API Edge Cases & Error Handling
File: `test_phase4b_edge_cases.ps1`

### 2. Integration Tests
File: `test_phase4b_integration.ps1`

### 3. UI Tests (Manual)
File: `test_phase4b_ui_manual.md`

