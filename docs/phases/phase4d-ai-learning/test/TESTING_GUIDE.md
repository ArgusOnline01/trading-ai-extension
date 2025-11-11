# Phase 4D.1 Testing Guide

## Overview

This guide explains how to test the new AI Learning System endpoints (Phase 4D.1).

## Prerequisites

1. **Server must be running:**
   ```powershell
   # Option 1: Docker
   docker-compose -f trading-ai-extension/docker-compose.yml up -d backend
   
   # Option 2: Local
   cd trading-ai-extension/server
   python -m uvicorn app:app --reload --port 8765
   ```

2. **Database migration applied:**
   ```powershell
   cd trading-ai-extension/server
   python migrations/apply_008.py
   ```

3. **ChromaDB installed:**
   ```powershell
   pip install chromadb>=0.4.0
   ```

4. **OpenAI API key configured:**
   - Set `OPENAI_API_KEY` in your `.env` file or environment

---

## Testing Methods

### Method 1: FastAPI Interactive Docs (Easiest) ⭐ RECOMMENDED

1. **Start the server** (if not already running)

2. **Open browser:** http://127.0.0.1:8765/docs

3. **Find the AI endpoints:**
   - Look for `/ai/analyze-chart` (POST)
   - Look for `/ai/progress` (GET)

4. **Test `/ai/analyze-chart`:**
   - Click on `POST /ai/analyze-chart`
   - Click "Try it out"
   - **Option A: Upload a chart image**
     - Click "Choose File" under `file`
     - Select a chart image (PNG, JPEG)
     - Click "Execute"
   - **Option B: Use trade_id**
     - Enter a `trade_id` (e.g., from your trades)
     - Leave `file` empty
     - Click "Execute"
   - **Review response:**
     - Should return `success: true`
     - Should include `annotations` with POI, BOS, circles
     - Should include `similar_trades` array
     - Should include `reasoning` text

5. **Test `/ai/progress`:**
   - Click on `GET /ai/progress`
   - Click "Try it out"
   - Click "Execute"
   - **Review response:**
     - Should return progress metrics (all 0.0 initially)
     - Should include `total_lessons`, `poi_accuracy`, etc.

---

### Method 2: PowerShell Script

Create a test script `test_phase4d_ai.ps1`:

```powershell
# Test AI Progress Endpoint
Write-Host "Testing GET /ai/progress..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8765/ai/progress" -Method GET
    Write-Host "✅ Success!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

# Test AI Analyze Chart Endpoint (with trade_id)
Write-Host "`nTesting POST /ai/analyze-chart (with trade_id)..." -ForegroundColor Cyan
try {
    # First, get a trade with a chart
    $trades = Invoke-RestMethod -Uri "http://127.0.0.1:8765/trades?limit=10" -Method GET
    $tradeWithChart = $trades.items | Where-Object { $_.chart_url -ne $null } | Select-Object -First 1
    
    if ($tradeWithChart) {
        $body = @{
            trade_id = $tradeWithChart.trade_id
        }
        
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8765/ai/analyze-chart" -Method POST -Body $body -ContentType "multipart/form-data"
        Write-Host "✅ Success!" -ForegroundColor Green
        Write-Host "Annotations found:" -ForegroundColor Yellow
        Write-Host "  POI: $($response.annotations.poi.Count)" -ForegroundColor Yellow
        Write-Host "  BOS: $($response.annotations.bos.Count)" -ForegroundColor Yellow
        Write-Host "  Circles: $($response.annotations.circles.Count)" -ForegroundColor Yellow
        Write-Host "  Similar trades: $($response.similar_trades.Count)" -ForegroundColor Yellow
    } else {
        Write-Host "⚠️  No trades with charts found. Skipping chart analysis test." -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host "Response: $($_.Exception.Response)" -ForegroundColor Red
}
```

**Run the script:**
```powershell
cd trading-ai-extension/docs/phases/phase4d-ai-learning/test
.\test_phase4d_ai.ps1
```

---

### Method 3: Python Script

Create a test script `test_phase4d_ai.py`:

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8765"

# Test 1: Get AI Progress
print("Testing GET /ai/progress...")
response = requests.get(f"{BASE_URL}/ai/progress")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

# Test 2: Analyze Chart (with trade_id)
print("Testing POST /ai/analyze-chart (with trade_id)...")

# First, get a trade with a chart
trades_response = requests.get(f"{BASE_URL}/trades?limit=10")
trades = trades_response.json()

trade_with_chart = None
for trade in trades.get("items", []):
    if trade.get("chart_url"):
        trade_with_chart = trade
        break

if trade_with_chart:
    trade_id = trade_with_chart["trade_id"]
    print(f"Using trade_id: {trade_id}")
    
    # Analyze chart
    response = requests.post(
        f"{BASE_URL}/ai/analyze-chart",
        data={"trade_id": trade_id}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"POI annotations: {len(result.get('annotations', {}).get('poi', []))}")
        print(f"BOS annotations: {len(result.get('annotations', {}).get('bos', []))}")
        print(f"Similar trades: {len(result.get('similar_trades', []))}")
    else:
        print(f"Error: {response.text}")
else:
    print("No trades with charts found. Skipping chart analysis test.")
```

**Run the script:**
```powershell
cd trading-ai-extension/docs/phases/phase4d-ai-learning/test
python test_phase4d_ai.py
```

---

### Method 4: cURL (Command Line)

```bash
# Test AI Progress
curl http://127.0.0.1:8765/ai/progress

# Test Analyze Chart (with trade_id)
curl -X POST "http://127.0.0.1:8765/ai/analyze-chart" \
  -F "trade_id=YOUR_TRADE_ID"

# Test Analyze Chart (with file upload)
curl -X POST "http://127.0.0.1:8765/ai/analyze-chart" \
  -F "file=@/path/to/chart.png"
```

---

## Expected Results

### `/ai/progress` Response:
```json
{
  "total_lessons": 0,
  "poi_accuracy": 0.0,
  "bos_accuracy": 0.0,
  "setup_type_accuracy": 0.0,
  "overall_accuracy": 0.0,
  "updated_at": "2025-01-XX..."
}
```

### `/ai/analyze-chart` Response:
```json
{
  "success": true,
  "annotations": {
    "poi": [
      {
        "left": 100,
        "top": 200,
        "width": 50,
        "height": 30,
        "price": 1.0850
      }
    ],
    "bos": [
      {
        "x1": 50,
        "y1": 300,
        "x2": 150,
        "y2": 300,
        "price": 1.0840
      }
    ],
    "circles": [],
    "notes": "Bullish setup with POI at 1.0850 and BOS at 1.0840"
  },
  "similar_trades": [
    {
      "trade_id": "6EZ5_5m_1540306142",
      "symbol": "6E",
      "direction": "long",
      "outcome": "win",
      "has_annotations": true,
      "distance": 0.23
    }
  ],
  "reasoning": "Identified POI at previous support level and BOS at structure break..."
}
```

---

## Troubleshooting

### Error: "ChromaDB not found"
- **Solution:** Install ChromaDB: `pip install chromadb>=0.4.0`

### Error: "Database migration not applied"
- **Solution:** Run migration: `python trading-ai-extension/server/migrations/apply_008.py`

### Error: "OpenAI API key not configured"
- **Solution:** Set `OPENAI_API_KEY` in your `.env` file

### Error: "No similar trades found"
- **This is normal** if you haven't added any trades to ChromaDB yet
- The RAG system will work once you start teaching AI (Phase 4D.2)

### Error: "Chart file not found"
- **Solution:** Make sure the trade has a `chart_url` and the file exists in `server/data/charts/`

---

## Next Steps

After testing:
1. **Frontend Implementation:** Create teaching page UI (Phase 4D.1 remaining)
2. **Phase 4D.2:** Interactive Teaching (question generation, answer storage)
3. **Phase 4D.3:** Progress Tracking + Verification (dashboard, accuracy metrics)

