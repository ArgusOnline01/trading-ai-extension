# Visual Trade Copilot - Software Requirements Specification

## Project Overview
Visual Trade Copilot is an AI-powered trading analysis system that uses Smart Money Concepts (SMC) to analyze trading charts and provide actionable insights through both structured analysis and conversational AI.

## Phase 1 - Backend API ✅ COMPLETE

### Core Features
- **Real-time Chart Analysis** using GPT-4o Vision API
- **Smart Money Concepts (SMC)** analysis including:
  - Market bias detection (bullish/bearish/neutral)
  - Point of Interest (POI) identification
  - Liquidity sweep detection
  - Displacement analysis
  - Fair Value Gap (FVG) identification
  - 50% mitigation level analysis
- **Rule-based Validation** for trading consistency
- **Image Processing** with PIL/Pillow and pypng fallback
- **CORS-enabled API** for browser extension integration

### API Endpoints
| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/` | GET | Health check | ✅ |
| `/prompt` | GET | View analysis prompt | ✅ |
| `/analyze` | POST | Structured chart analysis (with model selection) | ✅ |
| `/ask` | POST | Conversational chart Q&A (with model selection) | ✅ |
| `/budget` | GET | Budget status tracking | ✅ |
| `/models` | GET | List available OpenAI models & detect GPT-5 | ✅ |

## Phase 1.5 - Conversational Agent Endpoint ✅ COMPLETE

### New Features Added
- **Natural Language Q&A** about trading charts
- **Conversational AI** with SMC expertise
- **Budget Enforcement** with cost tracking
- **Enhanced User Experience** for interactive analysis

### `/ask` Endpoint Details
- **Input**: Chart image + freeform question (FormData)
- **Output**: JSON with natural-language response
- **Purpose**: Provide contextual trading insight rather than rule-based output
- **Model**: GPT-4o (upgradable to GPT-5)
- **Integration**: Chrome extension (Phase 2) will use this endpoint for "Ask AI" overlay

### Example Usage
```bash
curl -s -X POST http://127.0.0.1:8765/ask \
  -F "question=Would you enter this trade or wait?" \
  -F "image=@/path/to/chart.png"
```

**Expected Response:**
```json
{
  "model": "gpt-4o",
  "answer": "I'd wait for confirmation — price swept liquidity above the prior high but displacement is weak."
}
```

## Phase 1.6 - Dynamic Model Switching ✅ COMPLETE

### New Features Added
- **Per-Request Model Selection** for `/ask` and `/analyze` endpoints
- **Model Aliases** for convenient switching:
  - `fast` → `gpt-4o-mini` (fastest, cheapest)
  - `balanced` → `gpt-4o` (default, stable)
  - `advanced` → `gpt-5` (deep reasoning - not yet released, will use when available)
- **Direct Model Names** also supported (e.g., `gpt-4o-mini`)
- **Backward Compatible** - defaults to `.env` model when not specified

### Implementation Details
- **`resolve_model()` Helper** in `openai_client.py` - Resolves aliases to actual model names
- **Enhanced Endpoints** - Both `/ask` and `/analyze` accept optional `model` parameter
- **Fallback Logic** - Invalid/missing model defaults to `DEFAULT_MODEL` from `.env`

### Example Usage

#### Default (No Model Specified)
```bash
curl -s -X POST http://127.0.0.1:8765/ask \
  -F "question=Would you enter this trade?" \
  -F "image=@/path/to/chart.png"
# Uses model from .env (gpt-4o)
```

#### Fast Mode (GPT-4o-mini)
```bash
curl -s -X POST http://127.0.0.1:8765/ask \
  -F "question=Quick overview please" \
  -F "model=fast" \
  -F "image=@/path/to/chart.png"
# Uses gpt-4o-mini (~6s response time)
```

#### Balanced Mode (GPT-4o)
```bash
curl -s -X POST http://127.0.0.1:8765/ask \
  -F "question=Detailed market structure analysis" \
  -F "model=balanced" \
  -F "image=@/path/to/chart.png"
# Uses gpt-4o (~11s response time)
```

#### Direct Model Name
```bash
curl -s -X POST http://127.0.0.1:8765/ask \
  -F "question=Analysis please" \
  -F "model=gpt-4o-mini" \
  -F "image=@/path/to/chart.png"
# Uses gpt-4o-mini directly
```

### Test Results
All model switching modes verified:
- ✅ **Default**: Uses `gpt-4o` from `.env` (15.89s response)
- ✅ **Fast Mode** (`fast`): Uses `gpt-4o-mini` (6.56s response)
- ✅ **Balanced Mode** (`balanced`): Uses `gpt-4o` (10.76s response)
- ✅ **Advanced Mode** (`advanced`): Set to `gpt-5` (will use when released by OpenAI)
- ✅ **Direct Model**: Uses `gpt-4o-mini` directly (5.74s response)

**Note:** GPT-5 is not yet publicly available. When using `model=advanced`, the system will attempt to use GPT-5, and OpenAI will return an error if unavailable. You can update to a working model like `gpt-4-turbo` or `gpt-4o` temporarily.

### Chrome Extension Integration
Phase 2 will include a dropdown UI:
```
[⚡ Fast] [⚖️ Balanced] [🧠 Advanced]
```
Extension sends `model=<alias>` in FormData to dynamically switch models per request.

## Phase 1.7 - Model Discovery & Alias Sync ✅ COMPLETE

### New Features Added
- **`/models` Endpoint** - Lists all OpenAI models available to the API key
- **GPT-5 Detection** - Automatically detects if GPT-5 variants are accessible
- **Auto-Sync Aliases** - Updates `MODEL_ALIASES` at server startup
- **Diagnostic Information** - Provides counts and categorization of available models

### Implementation Details
- **`list_available_models()`** in `openai_client.py` - Queries OpenAI API for model list
- **`sync_model_aliases()`** in `openai_client.py` - Auto-updates aliases based on availability
- **Startup Hook** - `@app.on_event("startup")` calls sync function automatically
- **Model Categorization** - Detects GPT-5, GPT-4, and vision-capable models

### `/models` Endpoint Details
- **Method**: `GET`
- **Purpose**: List all accessible OpenAI models and detect GPT-5 availability
- **Output**: JSON with model list, counts, GPT-5 detection, and current aliases

### Example Usage
```bash
curl -s http://127.0.0.1:8765/models | jq
```

**Example Response:**
```json
{
  "total_models": 96,
  "models": ["gpt-4o-mini", "gpt-4o", "gpt-5", "gpt-5-mini", "gpt-5-pro", ...],
  "gpt_5_detected": true,
  "gpt_5_variants": [
    "gpt-5",
    "gpt-5-2025-08-07",
    "gpt-5-chat-latest",
    "gpt-5-codex",
    "gpt-5-mini",
    "gpt-5-mini-2025-08-07",
    "gpt-5-nano",
    "gpt-5-nano-2025-08-07",
    "gpt-5-pro",
    "gpt-5-pro-2025-10-06",
    "gpt-5-search-api",
    "gpt-5-search-api-2025-10-14"
  ],
  "gpt_4_variants": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", ...],
  "vision_models": ["gpt-4o", "gpt-4o-mini", "gpt-5", "gpt-5-mini", ...],
  "current_aliases": {
    "fast": "gpt-4o-mini",
    "balanced": "gpt-4o",
    "advanced": "gpt-5"
  }
}
```

### Auto-Sync Behavior
At server startup:
1. Queries OpenAI API for available models
2. Detects if GPT-5 or variants exist
3. **If GPT-5 found**: Updates `advanced` alias to `gpt-5`
4. **If GPT-5 not found**: Falls back to `gpt-4o`
5. Logs sync status to console

Console output on startup:
```
Syncing model aliases with OpenAI API...
GPT-5 detected! Updated 'advanced' alias to: gpt-5
```

### Benefits
- ✅ **No Manual Updates** - Aliases automatically adjust to API key capabilities
- ✅ **Future-Proof** - Works with new model releases without code changes
- ✅ **Diagnostic Tool** - Quickly verify account access to specific models
- ✅ **Transparency** - See exactly which models your API key can use

## Technical Architecture

### Backend Components
- **FastAPI Server** (`app.py`) - Main API server
- **Trading Logic** (`decision.py`) - SMC analysis and validation
- **OpenAI Client** (`openai_client.py`) - API wrapper with budget enforcement
- **Image Processing** - PIL/Pillow with pypng fallback

### Dependencies
- FastAPI 0.95.2
- OpenAI 0.28.1
- PIL/Pillow 12.0.0
- pypng 0.20220715.0
- python-dotenv 1.0.0
- uvicorn 0.22.0

### Environment Variables
- `OPENAI_API_KEY` - OpenAI API key
- `MAX_BUDGET` - Maximum spending limit (default: $10)

## Phase 2 - Chrome Extension (Upcoming)
- Browser integration for real-time analysis
- UI/UX for trading interface
- Screenshot capture and analysis
- Interactive chat interface

## Future Phases
- Real-time copilot with memory
- RAG context integration
- Voice/chat interface
- Advanced trading features

---

*Last updated: Phase 1.7 Complete - Model Discovery & Auto-Sync Added | GPT-5 DETECTED!* ✅
