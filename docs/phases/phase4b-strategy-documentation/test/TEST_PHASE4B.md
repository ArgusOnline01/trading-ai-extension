# Phase 4B API Testing Guide

## Quick Start

### Option 1: FastAPI Interactive Docs (Easiest)
1. Start the server: `docker-compose up backend` (or run `python -m uvicorn app:app --reload`)
2. Open browser: http://127.0.0.1:8765/docs
3. Test endpoints interactively - click "Try it out" on any endpoint

### Option 2: PowerShell Test Script
1. Make sure server is running
2. Run: `.\test_phase4b_apis.ps1`
3. This will test all endpoints automatically

### Option 3: Manual Testing with PowerShell

#### Test Setup Endpoints

```powershell
# Create a setup
$body = @{
    name = "Bullish POI + BOS"
    description = "Bullish setup with POI and Break of Structure"
    setup_type = "bullish"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8765/setups" -Method POST -Body $body -ContentType "application/json"

# List all setups
Invoke-RestMethod -Uri "http://127.0.0.1:8765/setups" -Method GET

# Get a specific setup (replace {id} with actual ID)
Invoke-RestMethod -Uri "http://127.0.0.1:8765/setups/1" -Method GET
```

#### Test Entry Method Endpoints

```powershell
# Create an entry method
$body = @{
    name = "POI + 50%"
    description = "Entry at POI plus 50% of the range"
    setup_id = 1  # Optional: link to a setup
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8765/entry-methods" -Method POST -Body $body -ContentType "application/json"

# List all entry methods
Invoke-RestMethod -Uri "http://127.0.0.1:8765/entry-methods" -Method GET

# List entry methods for a specific setup
Invoke-RestMethod -Uri "http://127.0.0.1:8765/entry-methods?setup_id=1" -Method GET
```

#### Test Annotation Endpoints

```powershell
# First, get a trade ID
$trades = Invoke-RestMethod -Uri "http://127.0.0.1:8765/trades?limit=1" -Method GET
$tradeId = $trades.items[0].trade_id

# Create an annotation
$body = @{
    trade_id = $tradeId
    poi_locations = @(
        @{
            x = 100
            y = 200
            price = 1.1450
            timestamp = "2024-01-01T10:00:00"
        }
    )
    bos_locations = @(
        @{
            x = 150
            y = 180
            price = 1.1480
            timestamp = "2024-01-01T10:30:00"
        }
    )
    notes = "POI and BOS marked on chart"
    ai_detected = $false
    user_corrected = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8765/annotations" -Method POST -Body $body -ContentType "application/json"

# Get annotations for a trade
Invoke-RestMethod -Uri "http://127.0.0.1:8765/annotations/trade/$tradeId" -Method GET
```

#### Test Trade Linking

```powershell
# Link a trade to a setup and entry method
$tradeId = "your-trade-id"
$setupId = 1
$entryMethodId = 1

Invoke-RestMethod -Uri "http://127.0.0.1:8765/trades/$tradeId/link-setup?setup_id=$setupId&entry_method_id=$entryMethodId" -Method POST
```

### Option 4: Using curl (if you have it)

```bash
# Create a setup
curl -X POST "http://127.0.0.1:8765/setups" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bullish POI + BOS",
    "description": "Bullish setup with POI and Break of Structure",
    "setup_type": "bullish"
  }'

# List setups
curl -X GET "http://127.0.0.1:8765/setups"

# Create entry method
curl -X POST "http://127.0.0.1:8765/entry-methods" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "POI + 50%",
    "description": "Entry at POI plus 50% of the range"
  }'
```

## API Endpoints Summary

### Setups
- `POST /setups` - Create a setup
- `GET /setups` - List all setups
- `GET /setups/{id}` - Get a specific setup
- `PUT /setups/{id}` - Update a setup
- `DELETE /setups/{id}` - Delete a setup

### Entry Methods
- `POST /entry-methods` - Create an entry method
- `GET /entry-methods` - List all entry methods (optional: `?setup_id=1`)
- `GET /entry-methods/{id}` - Get a specific entry method
- `PUT /entry-methods/{id}` - Update an entry method
- `DELETE /entry-methods/{id}` - Delete an entry method

### Annotations
- `POST /annotations` - Create an annotation
- `GET /annotations/trade/{trade_id}` - Get all annotations for a trade
- `GET /annotations/{id}` - Get a specific annotation
- `PUT /annotations/{id}` - Update an annotation
- `DELETE /annotations/{id}` - Delete an annotation

### Trade Linking
- `POST /trades/{trade_id}/link-setup?setup_id=1&entry_method_id=1` - Link a trade to a setup and/or entry method

## Expected Responses

All endpoints return JSON. Successful responses include:
- `POST` requests return `201 Created` with the created object
- `GET` requests return `200 OK` with the data
- `PUT` requests return `200 OK` with the updated object
- `DELETE` requests return `200 OK` with a success message

Error responses include:
- `400 Bad Request` - Invalid input (e.g., duplicate name)
- `404 Not Found` - Resource doesn't exist
- `500 Internal Server Error` - Server error

## Troubleshooting

1. **Server not running?**
   - Check: `docker-compose ps`
   - Start: `docker-compose up backend`

2. **Connection refused?**
   - Make sure server is running on port 8765
   - Check firewall settings

3. **CORS errors?**
   - Backend should allow all origins (for development)
   - Check `app.py` CORS middleware

4. **Database errors?**
   - Make sure database is initialized
   - Check `server/data/vtc.db` exists
   - Run migrations if needed

