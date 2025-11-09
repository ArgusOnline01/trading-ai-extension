# Phase 4B UI Manual Test Guide

Manual testing scenarios for the web pages (Setups, Entry Methods, Annotation).

## Prerequisites
- Server running: `docker-compose up backend`
- Open browser: http://127.0.0.1:8765/app/

## Test Scenarios

### 1. Setup Management Page (`/app/setups.html`)

#### Happy Path
1. **Create a new setup**
   - Navigate to `/app/setups.html`
   - Click "Create Setup" button
   - Fill in form:
     - Name: "Test Bullish Setup"
     - Description: "Test setup for manual testing"
     - Setup Type: "bullish"
   - Click "Save"
   - **Expected:** Setup appears in the list
   - **Verify:** Can see setup in list, can edit/delete

2. **Edit an existing setup**
   - Click "Edit" on a setup
   - Modify description
   - Click "Save"
   - **Expected:** Changes saved, updated in list

3. **Delete a setup**
   - Click "Delete" on a setup
   - Confirm deletion
   - **Expected:** Setup removed from list

#### Edge Cases
1. **Create setup with duplicate name**
   - Try to create a setup with the same name as existing
   - **Expected:** Error message, setup not created

2. **Delete setup with linked trades**
   - Create a setup
   - Link a trade to it (via annotation page)
   - Try to delete the setup
   - **Expected:** Warning message or prevented deletion

### 2. Entry Methods Page (`/app/entry-methods.html`)

#### Happy Path
1. **Create a new entry method**
   - Navigate to `/app/entry-methods.html`
   - Click "Create Entry Method" button
   - Fill in form:
     - Name: "POI + 50%"
     - Description: "Entry at POI plus 50% of range"
     - Setup: (optional) Select a setup
   - Click "Save"
   - **Expected:** Entry method appears in list

2. **Link entry method to setup**
   - Create entry method with setup selected
   - **Expected:** Entry method shows linked setup in list

#### Edge Cases
1. **Create entry method with duplicate name**
   - Try to create entry method with same name
   - **Expected:** Error message, not created

### 3. Chart Annotation Page (`/app/annotate.html?trade_id=XXX`)

#### Happy Path
1. **Annotate chart (mark POI and BOS)**
   - Navigate to trades page
   - Click "Annotate" on a trade
   - **Expected:** Chart loads, annotation tools visible
   
   - Click "POI" tool button
   - Click on chart where POI should be
   - **Expected:** POI marker appears (no price prompt)
   
   - Double-click POI marker
   - **Expected:** Price prompt appears
   - Enter price: "1.1450"
   - **Expected:** Price saved, marker shows price
   
   - Click "BOS" tool button
   - Click on chart where BOS should be
   - **Expected:** BOS line appears (horizontal line, no price prompt)
   
   - Double-click BOS line
   - **Expected:** Price prompt appears
   - Enter price: "1.1480"
   - **Expected:** Price saved, line shows price
   
   - Click "Save" button
   - **Expected:** Success message, annotation saved

2. **Load existing annotations**
   - Annotate a chart, save
   - Reload the page
   - **Expected:** POI and BOS markers appear at saved locations

3. **Link trade to setup and entry method**
   - After annotating, click "Link Setup" button
   - Select a setup and entry method
   - Click "Save"
   - **Expected:** Trade linked, can see in trade list

#### Edge Cases
1. **Annotate without linking to setup**
   - Mark POI/BOS, save annotation
   - Don't link to setup
   - **Expected:** Annotation saved, trade remains unlinked (can link later)

2. **Multiple annotations per trade**
   - Mark multiple POIs (3-4 points)
   - Mark multiple BOS levels (2-3 lines)
   - Save
   - **Expected:** All annotations saved and visible

3. **Move/edit annotations**
   - Create POI marker
   - Drag marker to new position
   - **Expected:** Marker moves, coordinates update
   - Double-click to edit price
   - **Expected:** Price updates

4. **Delete annotations**
   - Create POI marker
   - Click "Delete" tool
   - Click on POI marker
   - **Expected:** Marker removed

5. **Clear all annotations**
   - Create multiple annotations
   - Click "Clear All" button
   - Confirm
   - **Expected:** All annotations removed

#### Error Handling
1. **Network error during save**
   - Disconnect network (or stop server)
   - Try to save annotation
   - **Expected:** Error message, option to retry
   - Reconnect network
   - Retry save
   - **Expected:** Annotation saved successfully

2. **Invalid trade_id**
   - Navigate to `/app/annotate.html?trade_id=INVALID`
   - **Expected:** Error message, link back to trades

### 4. Integration Tests (End-to-End)

#### Full Workflow
1. **Complete workflow: Setup → Annotation → Linking**
   - Create a setup: "Test Bullish Setup"
   - Create an entry method: "POI + 50%"
   - Navigate to trades page
   - Click "Annotate" on a trade
   - Mark POI and BOS on chart
   - Save annotation
   - Click "Link Setup"
   - Select setup and entry method
   - Save
   - **Expected:** Trade shows linked setup/entry method in trades list

2. **Filter trades by setup**
   - Link multiple trades to same setup
   - In trades page, filter by setup
   - **Expected:** Only trades with that setup shown

3. **Statistics calculation**
   - Link trades to setups/entry methods
   - View statistics (if available)
   - **Expected:** Win rate per setup/entry method calculated correctly

### 5. Regression Tests

1. **Existing trade viewing**
   - Navigate to `/app/`
   - **Expected:** Trades list loads, all 31 trades visible
   - Click "View Chart" on a trade
   - **Expected:** Chart image loads correctly

2. **Chart images loading**
   - Navigate to trades page
   - Click "View Chart" on multiple trades
   - **Expected:** All chart images load correctly

3. **Extension chat**
   - Open extension on Topstep/TradingView
   - **Expected:** Chat works, no errors
   - Ask a question
   - **Expected:** AI responds correctly

## Test Checklist

### Setup Management
- [ ] Create setup
- [ ] Edit setup
- [ ] Delete setup
- [ ] Duplicate name error
- [ ] Delete with linked trades

### Entry Methods
- [ ] Create entry method
- [ ] Link to setup
- [ ] Edit entry method
- [ ] Delete entry method
- [ ] Duplicate name error

### Chart Annotation
- [ ] Load chart
- [ ] Mark POI (click, no prompt)
- [ ] Edit POI price (double-click)
- [ ] Mark BOS (click, no prompt)
- [ ] Edit BOS price (double-click)
- [ ] Save annotation
- [ ] Load existing annotations
- [ ] Multiple POIs/BOS
- [ ] Move annotations
- [ ] Delete annotation
- [ ] Clear all
- [ ] Link trade to setup/entry method
- [ ] Network error handling

### Integration
- [ ] Full workflow (Setup → Annotation → Linking)
- [ ] Filter trades by setup
- [ ] Statistics calculation

### Regression
- [ ] Trades list loads
- [ ] Chart images load
- [ ] Extension chat works

## Notes
- Test on different browsers (Chrome, Firefox, Edge)
- Test on different screen sizes (desktop, tablet)
- Test with different trade data (winning, losing, breakeven)
- Document any issues found

