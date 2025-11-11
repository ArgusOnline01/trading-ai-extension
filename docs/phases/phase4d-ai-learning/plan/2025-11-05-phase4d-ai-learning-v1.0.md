# Feature Plan: Phase 4D - AI Learning System

**Date:** 2025-11-05  
**Phase:** Phase 4D  
**Status:** 🟡 Planning

---

## Feature Overview

### What It Does
Teaches AI your trading strategy using RAG (Retrieval Augmented Generation) so it can:
1. **Identify setups from scratch** - Given a blank chart, identify POI and BOS based on your strategy
2. **Learn from annotated trades** - AI learns from your annotations, notes, and corrections
3. **Visual annotation** - AI can draw annotations (POI, BOS) on charts so you can visually see what it learned
4. **Interactive teaching** - AI asks questions during teaching, you answer, AI learns your reasoning
5. **Progress tracking** - Visual dashboard showing AI learning progress and accuracy
6. **Infinite teaching loop** - Any chart (even blank ones) can be used for teaching; corrections become new lessons

**Key Components:**
1. **RAG System** - Chroma vector database storing annotated trades as teaching examples
2. **AI Visual Annotation** - AI can draw POI/BOS on charts (different color/style from your annotations)
3. **Interactive Teaching** - Conversational teaching where AI asks questions, you answer
4. **Progress Tracking** - Dashboard showing AI accuracy, learning curve, improvement over time
5. **Verification System** - Multiple methods to verify AI is learning correctly
6. **Hybrid Interface** - Extension chat for quick testing + Web app for structured teaching

### Why It's Needed
- **Foundation for Phase 4E:** AI needs to understand your strategy before it can suggest entries
- **Foundation for Phase 4F:** AI needs to identify setups accurately before backtesting
- **Ultimate Goal:** AI that can analyze a blank chart and identify setups (POI, BOS) accurately
- **Learning from Your Experience:** AI learns from your 60+ annotated trades, not generic trading knowledge

### User Story
As a trader, I want to teach AI my strategy so that:
- AI can identify setups (POI, BOS) on any chart (even blank ones)
- AI can visually show me what it learned (draw annotations)
- AI can ask questions to understand my reasoning
- I can see AI's learning progress and accuracy
- AI gets better with each lesson I teach
- I can test AI by going back to earlier lessons and seeing if it recreates them better
- Teaching is infinite - any chart can be a lesson, any correction is a learning opportunity

### Real Workflow (Updated from User Feedback)

**Step 1: You Annotate Trades**
- You go to `/app/annotate.html?trade_id=XXX`
- You draw POI, BOS, circles on the chart
- You write notes explaining WHY this was the setup (critical for teaching!)
- You click "Save Annotations"
- **System automatically creates Chroma embedding** with your annotations + notes

**Step 2: AI Analyzes New Chart**
- You go to `/app/teach.html?trade_id=YYY` (new trade, could be blank)
- You click "Analyze Chart"
- RAG finds similar trades from your history
- **Prompt includes your actual annotations** (POI price levels, BOS price levels, your notes)
- AI sees: "In similar trade 6EZ5, user placed POI at 1.1650 after liquidity sweep"
- AI sees: "User's notes: 'Early long entry after liquidity sweep, confirmed by bullish BOS'"
- AI tries to recreate similar patterns on the new chart

**Step 3: You Correct AI**
- AI's annotations appear on chart (blue dashed)
- You drag/move them to correct positions
- You add/remove annotations
- You click "Save Corrections"
- **System automatically updates Chroma embedding** with your corrections
- Corrections become new training examples

**Step 4: Infinite Learning Loop**
- Next time AI analyzes a similar chart, it uses your corrections
- You can go back to lesson 1 after teaching 100 lessons and see if AI recreates it better
- Any chart (even without your annotations) can be used for teaching
- Every correction is a lesson
- AI gets better over time as it accumulates more examples

**Step 5: Interactive Teaching (Phase 4D.2)**
- AI asks questions about your annotations: "Why did you place POI here?"
- You answer: "Because this was a liquidity sweep zone"
- AI stores your answer and learns your reasoning
- This deepens AI's understanding beyond just coordinates

---

## Technical Requirements

### Backend Changes

#### 1. RAG System with Chroma
- [ ] **Vector Database Setup**
  - [ ] Install and configure Chroma (local, free)
  - [ ] Create Chroma collection for annotated trades
  - [ ] Store trade embeddings (chart + annotations + notes)

- [ ] **Embedding Generation** ✅ IMPLEMENTED
  - [x] Convert annotated trades to embeddings
  - [x] Store annotation data + notes as vectors (includes POI/BOS price levels + notes)
  - [x] Use OpenAI embeddings API (text-embedding-3-small)
  - [x] Auto-create embeddings when annotations are saved
  - [x] Auto-update embeddings when corrections are saved

- [ ] **Retrieval System** ✅ IMPLEMENTED
  - [x] Function to find similar trades when AI sees new chart
  - [x] Return top 3-5 most similar examples
  - [x] Use similarity search in Chroma
  - [x] Include actual annotation data (POI/BOS price levels + notes) in prompt, not just metadata

#### 2. AI Visual Annotation System
- [ ] **AI Annotation API**
  - [ ] Endpoint: `POST /ai/analyze-chart` - AI analyzes chart and returns annotation data
  - [ ] AI returns: POI boxes, BOS lines, circles with coordinates
  - [ ] Format: JSON with annotation coordinates (same format as your annotations)

- [ ] **Annotation Data Format**
  - [ ] POI: `{left, top, width, height, color, label}`
  - [ ] BOS: `{x1, y1, x2, y2, color, label}`
  - [ ] Circles: `{x, y, radius, color, label}`
  - [ ] Notes: `{text, position}`

- [ ] **Learning from Corrections** ✅ IMPLEMENTED
  - [x] Store AI's original annotations (in `ai_lessons` table)
  - [x] Store your corrections (in `ai_lessons` table)
  - [x] Auto-update Chroma with corrected annotations (when saving corrections)
  - [x] AI learns from corrections for future suggestions
  - [x] Auto-index annotations when saved (creates embeddings automatically)

#### 3. Interactive Teaching System
- [ ] **Question Generation**
  - [ ] AI analyzes your annotations
  - [ ] AI identifies unclear or interesting patterns
  - [ ] AI generates relevant questions (e.g., "Why is POI here?")
  - [ ] Questions are optional (conversational, not forced)

- [ ] **Answer Storage**
  - [ ] Store your answers to AI's questions
  - [ ] Link answers to specific annotations/trades
  - [ ] Use answers to improve AI's understanding

- [ ] **Conversational Flow**
  - [ ] AI asks questions during annotation review
  - [ ] You answer, AI confirms understanding
  - [ ] Natural conversation flow (not forced)

#### 4. Progress Tracking System
- [ ] **Accuracy Metrics**
  - [ ] Track POI detection accuracy
  - [ ] Track BOS detection accuracy
  - [ ] Track setup type accuracy (bullish/bearish)
  - [ ] Track overall accuracy

- [ ] **Learning Dashboard**
  - [ ] API endpoint: `GET /ai/progress` - Returns learning progress
  - [ ] Visual dashboard showing:
    - Total lessons taught
    - Accuracy over time (line graph)
    - Accuracy by category (POI, BOS, setup type)
    - Recent performance (last 10 tests)
    - Learning curve

- [ ] **Milestones**
  - [ ] Foundation (20-30 trades): Basic setup identification
  - [ ] Intermediate (50+ trades): 80%+ accuracy
  - [ ] Advanced (100+ trades): Can identify setups on new charts
  - [ ] Expert (200+ trades): 85-90% accuracy threshold

#### 5. Verification System
- [ ] **Multiple Verification Methods**
  - [ ] Accuracy metrics (track how often AI is correct)
  - [ ] Test on new charts (hold out trades for testing)
  - [ ] Interactive testing (real-time verification during teaching)
  - [ ] Visual comparison (compare AI's annotations to yours)

- [ ] **Verification API**
  - [ ] Endpoint: `POST /ai/verify` - Test AI on new chart
  - [ ] Returns: AI's annotations + accuracy score
  - [ ] Compare AI's annotations to ground truth (your annotations)

### Frontend Changes (Hybrid Approach: Web App + Extension Chat)

#### Extension Chat Interface (Quick Testing)

- [ ] **Chat-Based Chart Analysis**
  - [ ] Enhance existing chat image upload (`📸 Chart` button)
  - [ ] When user uploads chart, AI analyzes and suggests annotations
  - [ ] Display AI's suggestions in chat (text description + visual indicators)
  - [ ] User can provide text feedback: "POI is correct, but BOS should be here"
  - [ ] AI learns from text corrections

- [ ] **Quick Feedback Flow**
  - [ ] User: Uploads chart image in chat
  - [ ] AI: "I see POI here [description] and BOS here [description]"
  - [ ] User: "Correct" or "POI should be at [price level]"
  - [ ] AI: Stores feedback, asks follow-up questions if needed
  - [ ] Works on any website (Topstep, TradingView, etc.)

- [ ] **Chat Integration Points**
  - [ ] Connect chat to `/ai/analyze-chart` API endpoint
  - [ ] Display AI suggestions in chat messages
  - [ ] Allow text-based corrections
  - [ ] Link to web app for full annotation editing (optional: "Edit in Web App" button)

#### Web App Pages (Structured Teaching)

#### 1. AI Annotation Display
- [ ] **Annotation UI Enhancement**
  - [ ] Toggle button: "Show AI Annotations" / "Hide AI Annotations"
  - [ ] AI annotations in different color/style (blue dashed lines)
  - [ ] Your annotations in different color/style (red solid lines)
  - [ ] Both can be visible at the same time (for comparison)

- [ ] **Editable AI Annotations**
  - [ ] You can drag/correct AI's annotations
  - [ ] Corrections are saved and sent to AI
  - [ ] AI learns from corrections

- [ ] **Visual Comparison**
  - [ ] Side-by-side view: AI's annotations vs yours
  - [ ] Highlight differences
  - [ ] Show accuracy score

#### 2. Interactive Teaching Interface
- [ ] **Teaching Page** (`/app/teach`)
  - [ ] Load trade chart
  - [ ] AI analyzes and suggests annotations
  - [ ] AI annotations appear on chart
  - [ ] You review and correct if needed
  - [ ] AI asks questions (optional, conversational)
  - [ ] You answer, AI confirms understanding

- [ ] **Question Display**
  - [ ] Show AI's questions in chat-like interface
  - [ ] You can answer questions
  - [ ] AI confirms understanding
  - [ ] Natural conversation flow

- [ ] **Annotation Review**
  - [ ] Show AI's annotations
  - [ ] You can correct by dragging
  - [ ] Add notes explaining corrections
  - [ ] Save corrections for learning

#### 3. Progress Dashboard
- [ ] **Progress Page** (`/app/ai-progress`)
  - [ ] Overview cards: Total lessons, current accuracy, improvement rate
  - [ ] Line graph: Accuracy over time
  - [ ] Bar chart: Accuracy by category (POI, BOS, setup type)
  - [ ] Recent performance: Last 10 tests
  - [ ] Learning curve visualization

- [ ] **Milestone Display**
  - [ ] Show current milestone
  - [ ] Progress to next milestone
  - [ ] Visual progress indicator

#### 4. Verification Interface
- [ ] **Verification Page** (`/app/verify-ai`)
  - [ ] Upload new chart (not in training set)
  - [ ] AI analyzes and suggests annotations
  - [ ] You review and mark correct/incorrect
  - [ ] System calculates accuracy
  - [ ] Results stored for progress tracking

### Database Changes

#### 1. AI Learning Tables
- [ ] **`ai_lessons` Table**
  - [ ] `id` (primary key)
  - [ ] `trade_id` (foreign key to trades)
  - [ ] `ai_annotations` (JSON - AI's original annotations)
  - [ ] `corrected_annotations` (JSON - your corrections)
  - [ ] `questions` (JSON - AI's questions)
  - [ ] `answers` (JSON - your answers)
  - [ ] `accuracy_score` (float - accuracy for this lesson)
  - [ ] `created_at` (timestamp)

- [ ] **`ai_progress` Table**
  - [ ] `id` (primary key)
  - [ ] `total_lessons` (int)
  - [ ] `poi_accuracy` (float)
  - [ ] `bos_accuracy` (float)
  - [ ] `setup_type_accuracy` (float)
  - [ ] `overall_accuracy` (float)
  - [ ] `updated_at` (timestamp)

- [ ] **`ai_verification_tests` Table**
  - [ ] `id` (primary key)
  - [ ] `test_chart_url` (string)
  - [ ] `ai_annotations` (JSON)
  - [ ] `ground_truth` (JSON - your annotations)
  - [ ] `accuracy_score` (float)
  - [ ] `test_date` (timestamp)

#### 2. Chroma Vector Database
- [ ] **Collection Structure**
  - [ ] Collection name: `annotated_trades`
  - [ ] Embeddings: Chart image + annotations + notes
  - [ ] Metadata: Trade ID, entry method, outcome, session, etc.

---

## Implementation Details

### Architecture Approach

**RAG System:**
- Use Chroma (local, free) for vector database
- Store annotated trades as embeddings
- When AI sees new chart, retrieve similar examples
- AI uses examples to understand new chart

**AI Model:**
- GPT-5 (OpenAI) for chart analysis and annotation generation
- OpenAI embeddings API for vector embeddings
- Can consider self-hosted later if API costs become high

**Data Flow:**
1. You annotate trade → Stored in database + Chroma
2. AI sees new chart → Retrieves similar examples from Chroma
3. AI analyzes chart + examples → Generates annotations
4. You review/correct → Corrections stored, AI learns
5. Progress tracked → Dashboard shows improvement

---

## Success Criteria

### Functional Requirements
- [ ] AI can identify POI on charts (85-90% accuracy)
- [ ] AI can identify BOS on charts (85-90% accuracy)
- [ ] AI can identify setup type (bullish/bearish) (85-90% accuracy)
- [ ] AI can draw annotations on charts (visual verification)
- [ ] AI can ask questions during teaching (interactive)
- [ ] You can correct AI's annotations (editable)
- [ ] Progress dashboard shows learning curve
- [ ] AI gets better with each lesson (progressive learning)

### Performance Requirements
- [ ] AI annotation generation < 5 seconds
- [ ] Similarity search < 1 second
- [ ] Progress dashboard loads < 2 seconds

### User Experience Requirements
- [ ] AI annotations clearly visible (different color/style)
- [ ] Toggle on/off works smoothly
- [ ] Corrections are easy to make (drag and drop)
- [ ] Questions are natural and conversational
- [ ] Progress dashboard is visually appealing

---

## Teaching Workflow

### Workflow 1: Initial Teaching (Annotate Key Trades)

**Step 1: Select Key Trades**
- Choose 20-30 most important trades
- Include: wins, losses, different entry methods, different sessions
- Focus on trades that represent different scenarios

**Step 2: Annotate Each Trade**
- Load trade chart
- Annotate POI, BOS, entry point
- Add notes: "This worked because..." or "This failed because..."
- Link to entry method (IFVG, 50%, etc.)
- Mark outcome (win/loss)

**Step 3: AI Learns**
- Each annotated trade becomes a "teaching example"
- Stored in Chroma database as vector embedding
- AI can now retrieve similar examples

**Step 4: Verify Learning**
- Test AI on new chart: "Can AI identify the setup?"
- Review AI's suggestions
- Correct if needed
- AI learns from corrections

**Time:** ~2-3 hours for 20-30 trades

---

### Workflow 2: Interactive Teaching (Random Charts)

**Option A: Quick Testing via Chat Interface**
- You upload a chart image in the extension chat (`📸 Chart` button)
- AI analyzes and suggests annotations (text description)
- You provide text feedback: "Correct" or "POI should be at [price]"
- AI learns from feedback
- Works on any website (Topstep, TradingView, etc.)

**Option B: Structured Teaching via Web App**
- You navigate to `/app/teach` in web app
- You upload a chart (not necessarily a trade)
- Or AI loads a chart from your trade history
- AI analyzes chart
- AI suggests: "I see a POI here and BOS here"
- AI draws annotations on chart (blue dashed lines)
- You see AI's suggestions visually
- You correct: "No, the POI is here" or "Yes, that's correct"
- You drag AI's annotations to correct position
- You add notes: "The POI is here because..."
- AI asks questions (optional): "Why is POI here?" or "What makes this BOS valid?"
- You answer: "POI is here because..."
- AI confirms understanding
- AI stores your correction and answers
- AI updates its understanding
- Next time AI sees similar chart, it's more accurate
- Repeat with different charts
- AI gradually improves

**Time:** 
- Option A (Chat): ~2-3 minutes per chart (quick text feedback)
- Option B (Web App): ~5-10 minutes per chart (full annotation editing)

---

### Workflow 3: Ongoing Learning (New Trades)

**Step 1: Take New Trade**
- You take a new trade
- Trade is automatically logged (already working!)

**Step 2: Annotate New Trade**
- Load trade chart
- Annotate POI, BOS, entry point
- Add notes about what worked/didn't work
- Link to entry method

**Step 3: AI Learns**
- New trade becomes teaching example
- Added to Chroma database
- AI can now use this example for future analysis

**Step 4: AI Improves**
- AI uses new example to improve suggestions
- System gets better with each new trade
- Continuous learning

**Time:** ~5 minutes per new trade

---

## Verification Methods

### Method 1: Accuracy Metrics
- Track how often AI is correct
- After each lesson, test AI on similar charts
- Compare AI's suggestions to your corrections
- Calculate accuracy: "AI correctly identified POI in 8/10 trades"
- Track improvement over time

### Method 2: Test on New Charts
- Hold out 10-20 trades from teaching
- After teaching phase, test AI on these trades
- See if AI can identify setups correctly
- Measure accuracy on unseen data

### Method 3: Interactive Testing
- Test AI in real-time during conversation
- You upload a chart: "Can you identify the setup?"
- AI suggests: "I see POI here and BOS here"
- You review and provide feedback
- Track how often AI is correct

### Method 4: Visual Comparison
- Compare AI's annotations to yours
- Side-by-side view
- Highlight differences
- Calculate accuracy score

---

## Progress Tracking

### Progress Dashboard
**Metrics to Track:**
1. Total Lessons: How many trades/charts AI has learned from
2. Accuracy Over Time: Graph showing accuracy improving
3. POI Detection: Accuracy for POI identification
4. BOS Detection: Accuracy for BOS identification
5. Setup Type: Accuracy for bullish/bearish identification
6. Recent Performance: Accuracy on last 10 tests
7. Learning Curve: How fast AI is improving

**Visualization:**
- Line graph: Accuracy over time
- Bar chart: Accuracy by category (POI, BOS, setup type)
- Progress indicator: "AI is 70% accurate (improving)"
- Comparison: AI's suggestions vs your corrections

### Learning Milestones
1. **Foundation (20-30 trades):** AI can identify basic setups
2. **Intermediate (50+ trades):** AI can identify setups accurately (80%+)
3. **Advanced (100+ trades):** AI can identify setups on new charts
4. **Expert (200+ trades):** AI can identify setups with 85-90% accuracy

---

## Testing Requirements

### Unit Tests
- [ ] RAG retrieval system (find similar trades)
- [ ] Embedding generation (convert trades to vectors)
- [ ] AI annotation generation (generate annotation data)
- [ ] Accuracy calculation (compare AI vs ground truth)

### Integration Tests
- [ ] AI annotation API endpoints
- [ ] Progress tracking API endpoints
- [ ] Chroma database integration
- [ ] Teaching workflow end-to-end

### Manual Tests
- [ ] AI can identify POI on test charts
- [ ] AI can identify BOS on test charts
- [ ] AI annotations are visible and editable
- [ ] Progress dashboard displays correctly
- [ ] Interactive teaching works smoothly

---

## Timeline

**Phase 4D.1: RAG System + AI Annotation (2-3 weeks)**
- Set up Chroma vector database
- Implement embedding generation
- Implement AI annotation API
- Implement AI annotation display in frontend

**Phase 4D.2: Interactive Teaching (1-2 weeks)**
- Implement question generation
- Implement answer storage
- Implement conversational flow
- Implement teaching interface

**Phase 4D.3: Progress Tracking + Verification (1-2 weeks)**
- Implement progress tracking system
- Implement verification methods
- Implement progress dashboard
- Implement accuracy metrics

**Total: 4-7 weeks**

---

## Dependencies

### External Dependencies
- **Chroma** - Vector database (local, free)
- **OpenAI GPT-5** - Chart analysis and annotation generation
- **OpenAI Embeddings API** - Vector embeddings (or local embeddings)

### Internal Dependencies
- Phase 4B: Strategy Documentation (annotations system)
- Phase 4C: Trade Analysis (trade data, entry methods)
- Chart rendering system (already exists)

---

## Next Steps After Phase 4D

**Phase 4E: Entry Confirmation System**
- AI provides entry advice based on learned strategy
- Uses Phase 4D's setup identification
- Uses Phase 4C's statistics (entry method performance)

**Phase 4F: Backtesting & Data Collection**
- Test AI on historical charts
- Collect training data for fine-tuning
- Use Phase 4D's AI annotation system

---

## Questions for Discussion

1. **Embeddings:** Use OpenAI embeddings API or local embeddings?
2. **AI Model:** GPT-5 or GPT-4o? (GPT-5 recommended for better vision)
3. **Chroma Location:** Local file or separate service?
4. **Question Frequency:** How often should AI ask questions? (Optional, conversational)
5. **Accuracy Threshold:** 85% or 90% for "ready"? (85-90% as discussed)

---

**Ready to start implementation!** 🚀

