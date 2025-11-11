# Feature Ideas (Backlog)

This document captures future ideas to consider. When we decide to build one, we'll create a phase/iteration plan.

**Status:** Updated 2025-11-05 - Phase 4C Complete

---

## ✅ Completed Features (Moved to Phases)

### Phase 4A: Foundation ✅
- Pure AI chat (natural language only)
- Separate trade management UI
- Chart recreation viewer
- Clean data models

### Phase 4B: Strategy Documentation ✅
- Setup definition interface
- Chart annotation tools (POI, BOS, circles)
- Entry method documentation
- Trade-to-setup/entry-method linking

### Phase 4C: Trade Analysis & Linking ✅
- Analytics dashboard (`/app/analytics`)
- Statistics calculation (win rate, avg P&L, R-multiple)
- Pattern recognition (time-based, direction-based)
- Trade filtering & grouping
- CSV export
- Session detection (London, NY, Asian)

---

## 🔄 In Progress / Next Up

### Phase 4D: AI Learning System 🟡
**Status:** Discussion Phase - See `docs/phases/phase4d-ai-learning/DISCUSSION_PHASE4D.md`

**What It Will Do:**
- RAG system with Chroma vector database
- AI learns from annotated trades
- Interactive teaching (AI suggests, you correct)
- Setup detection from charts
- Progress tracking and verification

**When:** After Phase 4D discussion is complete

---

## 📋 Future Features (Backlog)

## 1) Extension UI Refactor (New Overlay Experience)
- Auto-open overlay on Topstep (and other target pages) without clicking the action button
- Pure AI chat only in the extension (no upload/log trade in chat)
- Fresh black+yellow visual design and typography; smooth micro-animations for open/close and buttons
- Left pane: conversation; right pane: quick context (selected symbol, last few trades, session switcher)
- Large, readable message input; clear send/stop controls
- Model selector retained; remove quick chart analysis action from chat
- Teach Copilot refactor:
  - Open from chat with clear UI affordance
  - Better chart viewer and annotation surface
  - Streamlined “review next trade” workflow
- Analytics dashboard refactor:
  - Clean KPIs (win rate, avg R, profit factor)
  - Filter by session/symbol/date; export CSV
- Button to open the Web App Trades page (`/app`) from the overlay header

## 2) Web App Enhancements (Future)
- Paginated, sortable trades table with fuzzy search
- Trade detail page with full metadata and chart
- Batch actions (tagging, notes) - CSV export already done ✅

## 3) DB + Export Tools (Future)
- DB migration/versioning - Already have migrations ✅
- "Export JSON" (generate performance_logs-like JSON from DB on demand)
- "Import CSV" tool in admin

## 4) Phase 4E: Entry Confirmation System (After Phase 4D)
**Vision:** After Phase 4D (AI Learning), the AI should be able to:
- **Identify setups from scratch:** ✅ Part of Phase 4D - Given a random chart, identify POI and BOS based on your strategy
- **Suggest optimal entries:** ✅ Part of Phase 4E - Based on your trade history, suggest the best entry point for a current setup
- **Provide entry confirmation:** ✅ Part of Phase 4E - "Should I enter now?" → AI analyzes current setup vs. historical patterns
- **Explain reasoning:** ✅ Part of Phase 4E - "I would enter here because..." with data-backed reasoning

**How it differs from regular chat:**
- **Regular chat:** Generic trading advice based on general knowledge
- **Trained AI:** Specific to YOUR strategy, YOUR entry methods, YOUR historical performance data
- **Example:** Regular chat might say "look for support/resistance" → Trained AI says "POI at 1.1450 looks good based on your 73% win rate with POI+50% entries in similar setups"

**Entry Confirmation Workflow:**
1. User sees a setup forming
2. User asks: "Should I enter now?"
3. AI analyzes:
   - Current chart structure (POI, BOS)
   - Historical trades with similar setups
   - Win rate for this setup + entry method combination
   - Risk factors (time of day, market conditions)
4. AI responds: "Wait for price to reach POI + 50% level, then enter. Based on your 12 similar trades, this has a 75% win rate."
5. User waits, price reaches level
6. User asks again: "Should I enter now?"
7. AI: "Yes, enter now. All criteria met. Expected R: 2.5 based on your historical data."

## 5) Mobile App & Real-Time Notifications (Future - Post Phase 4E)
**Vision:** Mobile app that monitors markets and sends notifications

**Notification Types:**
- "Setup forming: Bullish POI + BOS detected on MNQ"
- "Price approaching POI: 1.1450 level on CLZ5"
- "Good entry opportunity: All criteria met for POI+50% entry"
- "Trade alert: Your setup is complete, click to see analysis"

**Market Scanning:**
- **Option 1:** Screenshot-based (every 15 minutes)
  - Take screenshot of chart
  - Send to AI for analysis
  - Check for setups, POI levels, entry opportunities
  - Pros: Works with any charting platform
  - Cons: API costs (OpenAI Vision API)
  
- **Option 2:** API-based (Topstep/TradingView)
  - Use platform APIs to get real-time data
  - Analyze price data directly
  - Pros: More efficient, real-time
  - Cons: Requires paid API access ($30+/month)

**Implementation Considerations:**
- Start with screenshot-based approach (easier, no API costs initially)
- Move to API-based if volume/accuracy requires it
- Focus on accuracy first, then optimize costs

**Mobile App Features:**
- View all trades
- View performance dashboard
- Receive push notifications
- Quick entry confirmation queries
- View annotated charts
- Review AI suggestions

## 6) Automated Market Analysis Bot (Future - Post Phase 4E)
**Vision:** AI that continuously analyzes markets and suggests entries (not auto-trading)

**Capabilities:**
- Scan multiple symbols simultaneously
- Identify setups in real-time
- Suggest optimal entry points
- Provide reasoning based on your strategy
- Learn from new trades you take

**Not a Trading Bot:**
- Does NOT automatically place trades
- Only provides suggestions and analysis
- User makes final decision
- User executes trades manually

**Workflow:**
1. AI scans market (every 15 min or via API)
2. AI identifies setups matching your strategy
3. AI suggests: "MNQ showing POI+BOS setup, entry at 1.1450"
4. User reviews, decides, executes
5. User provides feedback (win/loss)
6. AI learns and improves suggestions

---

When promoting an item to implementation, move it into the appropriate phase plan and create the iteration docs (plan → implementation → test).

