# Development Workflow Guidelines

**Last Updated:** 2025-11-12  
**Status:** Active Development Guidelines  
**Version:** 2.0 (Added Visual UI Testing with MCP Browser Tools)

---

## Overview

This document defines the **standard development cycle** that must be followed for every feature, enhancement, or bug fix in the Ingerios project. This workflow ensures consistent quality, thorough testing, and efficient development cycles.

---

## Development Cycle: Plan → Implement → Test

Every feature development follows this strict 3-phase cycle:

```
┌─────────┐      ┌──────────────┐      ┌─────────┐
│  PLAN   │─────▶│  IMPLEMENT   │─────▶│  TEST   │
└─────────┘      └──────────────┘      └─────────┘
     ▲                                      │
     │                                      │
     └──────────────────────────────────────┘
         (Iterate if needed)
```

---

## Phase 1: PLAN

### Purpose
Before any code is written, we must thoroughly plan the feature, discuss implementation approaches, define requirements, and establish success criteria.

### Process

#### Step 1: Feature Discussion
- **User describes the idea/feature** - What they want to build
- **AI analyzes feasibility** - Is it possible? What are the technical considerations?
- **AI suggests implementation approaches** - Best way to implement it
- **Both discuss alternatives** - Pros/cons of different approaches
- **Agree on approach** - Final decision on how to proceed

#### Step 2: Plan Documentation
The plan must include:

1. **Feature Overview**
   - What the feature does
   - Why it's needed
   - User story/use case

2. **Technical Requirements**
   - What needs to be built (backend, frontend, database, etc.)
   - API endpoints (if applicable)
   - Database schema changes (if any)
   - External API integrations (if any)
   - Dependencies required

3. **Implementation Details**
   - Architecture/design approach
   - File structure changes
   - Component/module breakdown
   - Data flow

4. **Testing Requirements**
   - What scenarios need to be tested
   - Success criteria for each scenario
   - Edge cases to consider
   - Error handling cases
   - User experience validation points

5. **Deliverables**
   - Final output expected
   - What "done" looks like
   - Acceptance criteria

6. **Dependencies**
   - What needs to be done first
   - Blockers or prerequisites

### Deliverable
A comprehensive plan document that serves as the blueprint for implementation and testing.

---

## Phase 2: IMPLEMENT

### Purpose
Build the feature according to the plan established in Phase 1.

### Process

1. **Follow the plan strictly** - Implement exactly what was agreed upon
2. **Code incrementally** - Build in logical steps
3. **Document as you go** - Add comments for complex logic
4. **Check dependencies** - Ensure all prerequisites are met
5. **Handle edge cases** - Implement error handling as defined in plan

### Guidelines
- Do not deviate from the plan without discussing first
- If implementation reveals issues with the plan, pause and discuss
- Keep code clean, readable, and maintainable
- Follow existing code patterns and conventions

### Deliverable
Complete, working implementation that matches the plan.

---

## Phase 3: TEST

### Purpose
Comprehensive testing from both technical and user perspectives to catch issues before manual testing. Testing now includes **visual UI validation** using browser automation tools (MCP servers like Playwright or browser extension).

### Process

#### Testing Philosophy
**Test as if you are the user** - Not just backend validation, but full user experience testing with **visual verification** of UI elements, interactions, and workflows.

#### Test Scope

1. **Happy Path Testing**
   - Normal user flow works end-to-end
   - All user interactions work as expected
   - Data is saved/retrieved correctly
   - **Visual verification:** UI elements appear correctly, workflows are visually smooth

2. **Edge Case Testing**
   - Empty inputs
   - Invalid inputs
   - Boundary conditions
   - Large data sets
   - Concurrent operations
   - **Visual verification:** Error states display correctly, UI handles edge cases gracefully

3. **Error Handling Testing**
   - Network failures
   - API failures
   - Database errors
   - Validation errors
   - User-friendly error messages displayed
   - **Visual verification:** Error messages are visible, styled correctly, and actionable

4. **Frontend Testing** (User Perspective) - **NOW WITH VISUAL VALIDATION**
   - ✅ UI elements render correctly (**VISUALLY VERIFIED**)
   - ✅ Forms submit properly (**VISUALLY VERIFIED**)
   - ✅ Loading states appear/disappear (**VISUALLY VERIFIED**)
   - ✅ Success messages display (**VISUALLY VERIFIED**)
   - ✅ Error messages are clear (**VISUALLY VERIFIED**)
   - ✅ Navigation works correctly (**VISUALLY VERIFIED**)
   - ✅ Responsive design (if applicable) (**VISUALLY VERIFIED**)
   - ✅ Buttons/links are clickable (**VISUALLY VERIFIED**)
   - ✅ Data displays correctly in UI (**VISUALLY VERIFIED**)
   - ✅ User can complete the intended workflow (**VISUALLY VERIFIED**)
   - ✅ **NEW:** Visual layout matches design expectations
   - ✅ **NEW:** Colors, fonts, spacing are correct
   - ✅ **NEW:** Animations/transitions work smoothly
   - ✅ **NEW:** Extension UI (if applicable) renders correctly
   - ✅ **NEW:** Chart annotations display correctly (for trading projects)

5. **Backend Testing** (Technical Validation)
   - ✅ API endpoints return correct status codes
   - ✅ Response data matches expected format
   - ✅ Database operations succeed
   - ✅ Data validation works
   - ✅ Business logic executes correctly
   - ✅ Logs show expected behavior
   - ✅ Performance is acceptable

6. **Integration Testing**
   - ✅ Components work together
   - ✅ API calls succeed
   - ✅ Database queries work
   - ✅ External services integrate properly
   - ✅ **NEW:** Frontend-backend integration visually verified

7. **Regression Testing**
   - ✅ Existing features still work
   - ✅ No breaking changes
   - ✅ **NEW:** Visual regression - UI hasn't broken visually

### Testing Methods

#### For Backend/API Testing:
```bash
# Test endpoints directly
- Make actual HTTP requests
- Verify response status codes
- Check response data structure
- Validate error handling
- Check database state
- Review logs
```

#### For Frontend Testing - **NOW WITH VISUAL AUTOMATION:**
```
TRADITIONAL METHODS (Still Valid):
- Simulate user interactions
- Check UI rendering
- Verify form submissions
- Test navigation flows
- Validate data display
- Check error/success messages
- Test loading states

NEW: VISUAL AUTOMATION (Using MCP Browser Tools):
- Navigate to pages using browser automation
- Take visual snapshots of UI states
- Verify UI elements are present and correctly positioned
- Test user interactions (clicks, form fills, navigation)
- Verify visual feedback (loading states, success/error messages)
- Check responsive design at different viewport sizes
- Validate extension UI (if applicable)
- Debug visual issues directly without user screenshots
- Test complex workflows end-to-end visually
```

#### Visual Testing Workflow (NEW)

**Using Browser MCP Tools (Playwright/Browser Extension):**

1. **Navigate to the feature/page**
   ```javascript
   // AI can now navigate directly
   browser.navigate("http://localhost:8765/app/teach.html")
   ```

2. **Take visual snapshot**
   ```javascript
   // AI can see the page structure
   browser.snapshot() // Returns page structure, elements, layout
   ```

3. **Verify UI elements**
   - Check if expected elements are present
   - Verify element positions and styling
   - Confirm interactive elements are clickable

4. **Test user interactions**
   ```javascript
   // AI can click buttons, fill forms, navigate
   browser.click("button#save")
   browser.type("input#name", "Test Value")
   ```

5. **Verify visual feedback**
   - Check loading states appear/disappear
   - Verify success/error messages display
   - Confirm navigation changes are visible

6. **Debug visual issues**
   - AI can see the actual UI state
   - Identify layout problems
   - Spot missing elements
   - Verify styling issues

**Benefits:**
- ✅ **No more user screenshots needed** - AI can see UI directly
- ✅ **Faster debugging** - Issues identified immediately
- ✅ **Consistent testing** - Same visual checks every time
- ✅ **Extension testing** - Can test Chrome extension UI
- ✅ **End-to-end visual validation** - Complete workflows verified visually

### Test Execution

1. **Create test scenarios** based on the plan
2. **Execute each scenario** systematically
3. **Verify both frontend and backend** for each test
   - **Backend:** API calls, database state, logs
   - **Frontend:** Visual verification using browser automation
4. **Document results** - what worked, what didn't
5. **Test against plan deliverables** - Does it meet acceptance criteria?

**Visual Testing Execution:**
- Navigate to the feature/page using browser automation
- Take visual snapshots at each step
- Interact with UI elements (click, type, navigate)
- Verify visual feedback and state changes
- Document any visual issues found

### Test Reporting

For each test, report:
- ✅ **Test Scenario**: What was tested
- ✅ **Frontend Result**: What user sees (visual state, messages, behavior)
  - **NEW:** Visual verification status (elements present, correctly positioned, styled)
  - **NEW:** Screenshot/snapshot reference (if issues found)
- ✅ **Backend Result**: API response, database state, logs
- ✅ **Pass/Fail**: Clear status
- ✅ **Issues Found**: Any bugs or unexpected behavior
  - **NEW:** Visual issues (layout problems, missing elements, styling issues)
  - **NEW:** Interaction issues (buttons not clickable, forms not submitting)

**Visual Test Report Format:**
```
✅ Test: User can load trade on Teach AI page
   Frontend (Visual):
   - ✅ Page loads correctly
   - ✅ Trade dropdown is visible and populated
   - ✅ "Load Trade" button is clickable
   - ✅ Navigation links are present
   - ❌ Issue: Chart canvas not rendering (needs investigation)
   Backend:
   - ✅ GET /trades returns 200 with trade list
   - ✅ Trade data structure is correct
   Status: ⚠️ Partial Pass (chart rendering issue)
```

### Deliverable
Comprehensive test report showing:
- All scenarios tested
- Frontend and backend validation for each
- Pass/fail status
- Any issues discovered
- Ready for user review (minimal surprises)

---

## Workflow Rules

### ⚠️ Strict Rules

1. **Never skip the PLAN phase** - Always discuss and plan before implementing
2. **Never skip the TEST phase** - Always test thoroughly before marking complete
3. **Follow the cycle order** - Plan → Implement → Test (in that order)
4. **Don't deviate from plan** - If changes needed, revisit PLAN phase first
5. **Test from user perspective** - Always verify what the user sees, not just backend

### 🔄 Iteration/Refinement Phase

When initial testing reveals issues or missing features, we enter the **Iteration/Refinement Phase**:

#### Process
1. **Initial Testing** - Complete initial test cycle (Plan → Implement → Test)
2. **Issue Identification** - Document what was tested, what issues were found, what's missing
3. **Fix/Enhancement** - Implement fixes or enhancements
4. **Re-test** - Verify fixes work correctly
5. **Documentation** - Update both TEST_RESULTS.md and IMPLEMENTATION.md

#### When to Use
- **Missing features** discovered during initial testing
- **UX issues** found during manual testing
- **Bugs** discovered during testing
- **Edge cases** not initially considered
- **User feedback** from initial testing

#### Documentation Requirements

For each iteration, document:

1. **In TEST_RESULTS.md:**
   - Initial test results (what was tested)
   - Issues found (what was missing or broken)
   - Fixes applied (what was changed)
   - Re-test results (verification that fixes work)

2. **In IMPLEMENTATION.md:**
   - What was fixed/enhanced
   - Code changes made
   - Why the fix was needed
   - Impact on existing functionality

#### Iteration Template

```markdown
## Iteration 1: [Brief Description]

**Date:** [Date]
**Trigger:** [What initiated this iteration - e.g., "Initial manual testing revealed missing pagination"]

### Initial Testing Results
- **What was tested:** [Description of initial tests]
- **Status:** ✅ Passed / ❌ Failed / ⚠️ Partial

### Issues Identified
1. **Issue:** [Description]
   - **Severity:** Critical / High / Medium / Low
   - **Impact:** [What functionality is affected]
   - **User Impact:** [How this affects user experience]

### Fixes Applied
1. **Fix:** [Description of fix]
   - **Files Changed:** [List of files]
   - **Implementation:** [Brief description of code changes]
   - **Testing:** [How fix was verified]

### Re-test Results
- **Status:** ✅ Passed / ❌ Failed
- **Verification:** [How the fix was verified]
- **Impact:** [Any side effects or improvements]
```

#### Iteration Rules
- **Minor fixes** can be fixed and re-tested immediately
- **Major changes** should return to PLAN phase first
- **Always document** what was tested, what was found, what was fixed
- **Always re-test** after fixes
- **Update both** TEST_RESULTS.md and IMPLEMENTATION.md

---

### Original Iteration (Simplified)

If testing reveals issues:
1. Document the issues
2. Return to PLAN phase if major changes needed
3. Or fix implementation and re-test
4. Repeat until all tests pass

### 📋 Documentation

- **Plan documents** - Keep all feature plans
- **Test reports** - Document test results
- **Issue logs** - Track bugs found during testing

---

## Example Workflow

### Feature: "Add Product Search by UPC"

#### Phase 1: PLAN
```
1. Discussion:
   - User: "I want to search products by UPC"
   - AI: "We can add a search endpoint. Should it be exact match or fuzzy?"
   - User: "Exact match first"
   - AI: "We'll add GET /products/search?upc=xxx endpoint"

2. Plan Document:
   - Feature: UPC search endpoint
   - Backend: Add search endpoint in products router
   - Frontend: Add search input to products page
   - Testing: Test exact match, no match, invalid UPC
   - Deliverables: User can search products by UPC, see results
```

#### Phase 2: IMPLEMENT
```
- Add search endpoint to products router
- Add search functionality to frontend
- Connect frontend to backend
- Implement error handling
```

#### Phase 3: TEST
```
✅ Test: Valid UPC exists
   Frontend: User enters UPC, sees product in results
   Backend: API returns 200 with product data

✅ Test: Valid UPC doesn't exist
   Frontend: User sees "No products found" message
   Backend: API returns 200 with empty array

✅ Test: Invalid UPC format
   Frontend: User sees validation error
   Backend: API returns 400 with error message

✅ Test: Empty search
   Frontend: User sees validation message
   Backend: API returns 400
```

---

## Benefits of This Workflow

1. **Reduces feedback cycles** - Catch issues before user testing
2. **Clear expectations** - Plan defines exactly what will be built
3. **Comprehensive testing** - User perspective testing catches UX issues
4. **Consistent quality** - Every feature follows same process
5. **Better communication** - Plan phase ensures alignment
6. **Faster development** - Less back-and-forth, clearer requirements
7. **NEW: Visual debugging** - AI can see and fix UI issues directly without user screenshots
8. **NEW: Faster UI testing** - Visual validation happens automatically during testing phase
9. **NEW: Extension testing** - Can test Chrome extension UI and interactions
10. **NEW: End-to-end visual validation** - Complete workflows verified visually

---

## Visual Testing for Debugging

### When to Use Visual Testing

Visual testing with browser automation is especially useful for:

1. **UI/UX Issues**
   - Layout problems
   - Missing elements
   - Styling issues
   - Responsive design problems

2. **Extension Testing**
   - Chrome extension UI rendering
   - Extension popup functionality
   - Content script injection
   - Extension-backend communication

3. **Complex Workflows**
   - Multi-step processes
   - Form submissions
   - Navigation flows
   - State management

4. **Debugging Existing Issues**
   - When user reports a visual bug
   - When coordinate/layout issues occur
   - When elements don't appear correctly
   - When interactions don't work as expected

### Debugging Workflow with Visual Testing

**Example: Debugging Phase 4D Coordinate Issues**

1. **Navigate to the problematic page**
   ```javascript
   browser.navigate("http://127.0.0.1:8765/app/teach.html")
   ```

2. **Take snapshot to see current state**
   ```javascript
   browser.snapshot() // See page structure, elements, layout
   ```

3. **Identify the issue visually**
   - Check if elements are present
   - Verify element positions
   - Check for styling issues
   - Identify missing or misplaced elements

4. **Interact to reproduce the issue**
   ```javascript
   browser.click("button#loadTrade")
   browser.selectOption("select#tradeSelect", "trade-id-123")
   // Take another snapshot to see state after interaction
   ```

5. **Fix the issue**
   - Based on visual evidence, fix the code
   - Re-test visually to verify fix

6. **Document the fix**
   - What was the visual issue?
   - What caused it?
   - How was it fixed?
   - Visual verification of fix

**Benefits:**
- ✅ **No screenshots needed** - AI can see the issue directly
- ✅ **Faster debugging** - Issues identified immediately
- ✅ **Better fixes** - Visual evidence guides the fix
- ✅ **Verification** - Can visually verify the fix works

---

## Notes

- **This workflow is mandatory** - Every feature must follow this cycle
- **AI must remember this workflow** - Always reference this document
- **User can pause at any phase** - To discuss or adjust direction
- **Plan is the contract** - Implementation and testing must match plan
- **Visual testing is now part of standard testing** - Use browser automation for all UI testing
- **Visual debugging replaces screenshot-based debugging** - AI can see UI directly

---

## Quick Reference

**Starting a new feature?**
1. Discuss idea → PLAN phase
2. Create plan document
3. Get approval on plan
4. Implement according to plan
5. Test comprehensively (frontend + backend)
6. Report test results
7. Done!

**Found an issue during testing?**
1. Document the issue
2. Determine if it's a bug or plan issue
3. Fix implementation or revisit plan
4. Re-test
5. Repeat until all tests pass

---

**Remember:** This workflow ensures quality, reduces surprises, and makes development efficient. Always follow it strictly.

