# 🧪 Testing Phase 4D.0: CSV Import

## ✅ Quick Test Checklist

- [ ] Server starts without errors
- [ ] `/trades/stats` returns empty stats
- [ ] CSV upload works
- [ ] Terminal shows import summary
- [ ] Trades appear in `/trades/imported`
- [ ] Stats show correct counts

---

## 🚀 Testing Steps

### **1. Verify Server is Running**

```bash
curl http://127.0.0.1:8765/trades/stats
```

**Expected:**
```json
{"total":0,"merged":0,"pending":0,"symbols":[]}
```

✅ Server is ready!

---

### **2. Import a Topstep CSV**

**Method A: Using PowerShell (Windows)**

```powershell
$filePath = "C:\path\to\your\topstep_export.csv"
$uri = "http://127.0.0.1:8765/trades/import"

$form = @{
    file = Get-Item -Path $filePath
}

$response = Invoke-RestMethod -Uri $uri -Method Post -Form $form
$response | ConvertTo-Json
```

**Method B: Using curl (if available)**

```bash
curl -X POST http://127.0.0.1:8765/trades/import \
  -F "file=@C:/path/to/topstep_export.csv"
```

**Expected API Response:**
```json
{
  "success": true,
  "count": 183,
  "message": "Successfully imported 183 trades from topstep_export.csv"
}
```

**Expected Terminal Output:**
```
[IMPORT] Reading CSV from: /tmp/tmpXYZ.csv
[IMPORT] Successfully parsed 183 trades
[IMPORT] Saved 183 trades to: server/data/imported_trades.json

============================================================
[IMPORT SUMMARY]
 Total Trades: 183
 Wins: 104 | Losses: 74 | Breakeven: 5
 Win Rate: 56.8%
 Total PnL: $7,916.58
 Avg PnL: $43.26
 Most common contracts: 6E (42), NQ (39), ES (28), CL (20), YM (18)
------------------------------------------------------------
 Avg PnL per Contract:
  6E: +$42.81       <- GREEN in terminal
  NQ: +$31.44       <- GREEN in terminal
  ES: +$15.27       <- GREEN in terminal
  CL: -$3.55        <- RED in terminal
  YM: -$18.20       <- RED in terminal
============================================================

╒═════════╤══════╤═══════════╤═══════════╤════════╤════════════╕
│ Symbol  │ Dir  │ Entry     │ Exit      │ PnL    │ Day        │
├─────────┼──────┼───────────┼───────────┼────────┼────────────┤
│ 6E      │ long │ $1.07     │ $1.07     │ $125.00│ 2025-10-27 │
│ NQ      │ long │ $17764.25 │ $17772.75 │ $150.00│ 2025-10-27 │
│ ...     │ ...  │ ...       │ ...       │ ...    │ ...        │
╘═════════╧══════╧═══════════╧═══════════╧════════╧════════════╛

... 173 more trades not shown ...
```

✅ Import successful with full analytics!

---

### **3. Verify Stats**

```bash
curl http://127.0.0.1:8765/trades/stats
```

**Expected:**
```json
{
  "total": 183,
  "merged": 0,
  "pending": 183,
  "symbols": ["6E", "NQ", "ES", "CL", "YM", "GC", "ZN", "RTY"]
}
```

✅ Stats updated correctly!

---

### **4. View First 10 Trades**

```bash
curl "http://127.0.0.1:8765/trades/imported?limit=10"
```

**Expected:**
```json
{
  "total": 183,
  "showing": 10,
  "trades": [
    {
      "id": 1,
      "symbol": "6E",
      "entry_time": "2025-10-27T09:30:00-05:00",
      "exit_time": "2025-10-27T09:45:15-05:00",
      "entry_price": 1.0659,
      "exit_price": 1.0668,
      "direction": "long",
      "pnl": 125.0,
      "contracts": 1.0,
      "fees": 4.24,
      "trade_day": "2025-10-27",
      "duration": "15m 15s",
      "source": "topstep",
      "merged": false
    },
    ...
  ]
}
```

✅ Trades are properly formatted!

---

### **5. Test Merge Endpoints (Stubs)**

```bash
curl -X POST http://127.0.0.1:8765/trades/merge/1
```

**Expected:**
```json
{
  "success": false,
  "message": "Merge logic not implemented yet. Coming in Phase 4D.2!",
  "trade_id": 1
}
```

✅ Stubs working as expected!

---

### **6. Clear Imported Trades (Optional)**

```bash
curl -X DELETE http://127.0.0.1:8765/trades/imported
```

**Expected:**
```json
{
  "success": true,
  "message": "All imported trades cleared"
}
```

Then verify:
```bash
curl http://127.0.0.1:8765/trades/stats
```

Should return: `{"total":0,"merged":0,"pending":0,"symbols":[]}`

✅ Clear function works!

---

## 🧾 Sample CSV Format

If you don't have a Topstep CSV yet, here's the expected format:

```csv
Id,ContractName,EnteredAt,ExitedAt,EntryPrice,ExitPrice,Type,PnL,Size,Fees,Commissions,TradeDay,TradeDuration
1,/6E,2025-10-27 09:30:00 CST,2025-10-27 09:45:15 CST,1.0659,1.0668,Buy,125.00,1,2.12,2.12,2025-10-27,15m 15s
2,/NQ,2025-10-27 10:15:30 CST,2025-10-27 10:22:45 CST,17764.25,17772.75,Buy,150.00,1,2.12,2.12,2025-10-27,7m 15s
3,/CL,2025-10-27 11:05:00 CST,2025-10-27 11:18:30 CST,82.38,82.44,Sell,-60.00,1,2.12,2.12,2025-10-27,13m 30s
```

**Required Columns:**
- `Id` - Unique trade ID
- `ContractName` - Symbol (e.g., "/6E", "NQ")
- `EnteredAt` - Entry timestamp
- `ExitedAt` - Exit timestamp
- `EntryPrice` - Entry price
- `ExitPrice` - Exit price
- `Type` - "Buy" or "Sell"
- `PnL` - Profit/Loss
- `Size` - Number of contracts
- `Fees` - Transaction fees
- `Commissions` - Broker commissions
- `TradeDay` - Date
- `TradeDuration` - Duration string

---

## 🐛 Troubleshooting

### **Issue: "Only CSV files are allowed"**
**Solution:** Make sure your file has a `.csv` extension.

---

### **Issue: No terminal output shown**
**Solution:** Look at the terminal where you ran `python run_server.py`. The import summary appears there, not in the API response.

---

### **Issue: Malformed dates**
**Solution:** Install `python-dateutil` for better timezone parsing:
```bash
cd server
pip install python-dateutil
```

---

### **Issue: No pretty table**
**Solution:** Install `tabulate` for formatted tables:
```bash
cd server
pip install tabulate
```

---

### **Issue: Symbol has "/" characters**
**Solution:** This is normal - the parser automatically removes them. "/6E" becomes "6E".

---

## 📊 What to Check

After import, verify:

1. ✅ **Total count matches** - API response should match CSV row count
2. ✅ **Win rate makes sense** - Check terminal summary
3. ✅ **Symbols are clean** - No "/" characters in JSON
4. ✅ **PnL totals correct** - Compare to your Topstep report
5. ✅ **Timestamps parsed** - Should be ISO format with timezone
6. ✅ **Fees combined** - Should be sum of Fees + Commissions
7. ✅ **Direction correct** - "Buy" = "long", "Sell" = "short"

---

## 🎯 Success Criteria

Phase 4D.0 is working if:

- [x] Server starts without errors
- [x] CSV upload endpoint accepts files
- [x] Terminal shows colorful import summary
- [x] Data saved to `imported_trades.json`
- [x] API returns correct trade count
- [x] Stats endpoint shows accurate numbers
- [x] Trades are properly normalized
- [x] Merge endpoints return "stub" messages

---

## 🚀 Next Steps After Testing

Once Phase 4D.0 is confirmed working:

1. **Import your real Topstep CSV** - Get actual trading data loaded
2. **Review terminal analytics** - Check win rate, best/worst contracts
3. **Verify data quality** - Spot-check a few trades in `/trades/imported`
4. **Proceed to Phase 4D.2** - Implement merge functionality

**Phase 4D.0 is complete and ready for real-world data!** 🎉

