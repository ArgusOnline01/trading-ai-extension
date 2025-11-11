# Trade Import from Screenshots - Instructions

**Date:** 2025-11-05  
**Status:** Ready for Use

---

## 📋 Process Overview

Since we're doing this **locally** (not as an on-platform feature), here's how we'll handle it:

1. **You provide screenshots** (page by page from each combine)
2. **I extract data** from screenshots (manually or help you create JSON)
3. **Create JSON file** with trade data
4. **Run import script** to add trades to database
5. **Render charts** for all new trades

---

## 📝 Step-by-Step Process

### Step 1: Provide Screenshots

**For Combine 1:**
- Send me screenshots page by page
- I'll extract the trade data from each page
- Tell me when Combine 1 is done, then we'll move to Combine 2

**For Combine 2:**
- Same process, page by page
- I'll extract data and add to database

---

### Step 2: Data Extraction

**From each screenshot, I'll extract:**
- Trade ID (from "ID" column)
- Entry Time (from "TIME" column)
- Entry Price (from "ENTRY PRICE" column)
- Direction (from "SIDE" column: "Buy" = "long", "Sell" = "short")
- Size (from "SIZE" column)
- Product (from "PRODUCT" column: e.g., "MNQZ5")
- Profit (from "PROFIT" column)
- Fees (from "TOTAL FEES" column)

**Missing Data:**
- Exit Price: Will calculate from profit (Entry Price + (Profit / Size) for Buy)
- Exit Time: Will use entry time as default (can correct later)

---

### Step 3: Create JSON File

I'll create a JSON file like this:

```json
[
  {
    "trade_id": "1433753170",
    "entry_time": "2025-10-07 01:24:37",
    "entry_price": 25148.00,
    "direction": "buy",
    "size": 5.00,
    "product": "MNQZ5",
    "profit": 20.00,
    "fees": -1.85
  },
  {
    "trade_id": "1433752819",
    "entry_time": "2025-10-07 01:24:34",
    "entry_price": 25150.00,
    "direction": "sell",
    "size": 5.00,
    "product": "MNQZ5",
    "profit": null,
    "fees": -1.85
  }
]
```

**File naming:**
- `combine1_page1.json`
- `combine1_page2.json`
- etc.

---

### Step 4: Import to Database

**Run the import script:**

```bash
cd trading-ai-extension/server
python -m db.import_from_screenshots data/combine1_page1.json "Combine 1"
```

**Or use the script directly:**

```bash
python server/db/import_from_screenshots.py server/data/combine1_page1.json "Combine 1"
```

**Output:**
- Shows how many trades imported/updated/skipped
- Shows any errors

---

### Step 5: Render Charts

**After all trades are imported, render charts:**

```bash
cd trading-ai-extension/server
python -m chart_reconstruction.render_charts
```

**Or use the existing script:**

```bash
python server/chart_reconstruction/render_charts.py
```

This will:
- Render charts for all new trades
- Save charts to `server/data/charts/`
- Link charts to trades in database

---

## 🎯 How to Start

**Option 1: Page by Page (Recommended)**
1. Send me **Combine 1, Page 1** screenshot
2. I'll extract data and create JSON
3. You run import script
4. Send me **Combine 1, Page 2** screenshot
5. Repeat until Combine 1 is done
6. Then move to Combine 2

**Option 2: All at Once**
1. Send me all screenshots from Combine 1
2. I'll extract all data and create JSON files
3. You run import scripts for all pages
4. Then move to Combine 2

**I recommend Option 1 (page by page)** so we can verify each page is correct before moving on.

---

## 📊 What I Need from Screenshots

**From each screenshot, I need:**
- All visible trade rows
- Columns: TIME, ID, SIDE, SIZE, PRODUCT, ENTRY PRICE, TOTAL FEES, PROFIT
- Trade Day (if visible, for reference)

**I'll extract:**
- Trade ID → `trade_id`
- TIME → `entry_time`
- SIDE → `direction` ("Buy" = "long", "Sell" = "short")
- SIZE → `size`
- PRODUCT → `product`
- ENTRY PRICE → `entry_price`
- TOTAL FEES → `fees`
- PROFIT → `profit`

**I'll calculate:**
- Exit Price from profit (if profit is available)

---

## ✅ Ready to Start

**Send me the first screenshot:**
- Combine 1, Page 1
- I'll extract the data and create the JSON file
- Then you can run the import script

**Or if you prefer:**
- Send me all screenshots from Combine 1
- I'll extract all data at once
- Create JSON files for each page
- Then you can import all at once

**Let me know which approach you prefer!** 🚀

