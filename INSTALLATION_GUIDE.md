# 🚀 Visual Trade Copilot - Complete Installation Guide

Step-by-step instructions to get the Chrome extension and backend running.

---

## 📋 Prerequisites

- **Python 3.8+** installed
- **Google Chrome** (or Chromium-based browser)
- **OpenAI API Key** with GPT-4/GPT-5 access
- **Internet connection**

---

## 🔧 Part 1: Backend Setup (5 minutes)

### Step 1: Navigate to Server Directory

```bash
cd trading-ai-extension/server
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Packages installed:**
- FastAPI (web framework)
- Uvicorn (ASGI server)
- OpenAI (API client)
- Pillow (image processing)
- Python-dotenv (environment variables)

### Step 3: Configure API Key

The API key is already set in `run_server.py`. If you need to update it:

1. Open `run_server.py`
2. Find line with `OPENAI_API_KEY=`
3. Replace with your key

**Or** create a `.env` file:
```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o
MAX_TOKENS=500
TEMPERATURE=0.1
```

### Step 4: Start Backend Server

```bash
cd ..
python run_server.py
```

**Expected output:**
```
Visual Trade Copilot Server
Starting FastAPI server...
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8765
Syncing model aliases with OpenAI API...
GPT-5 detected! Updated 'advanced' alias to: gpt-5-mini
```

**✅ Server is ready when you see:** `Uvicorn running on http://0.0.0.0:8765`

**Keep this terminal window open!**

---

## 🌐 Part 2: Chrome Extension Setup (3 minutes)

### Step 1: Open Chrome Extensions Page

1. Open **Google Chrome**
2. Navigate to: `chrome://extensions/`
3. Or: Menu → More Tools → Extensions

### Step 2: Enable Developer Mode

Look for **Developer mode** toggle in the **top-right corner**

Click to **enable** it (should turn blue/on)

### Step 3: Load Extension

1. Click **"Load unpacked"** button (top-left area)

2. Navigate to: `trading-ai-extension/visual-trade-extension/`

3. Click **"Select Folder"**

### Step 4: Verify Installation

You should see:

- **Visual Trade Copilot** card in extensions list
- Extension **enabled** (toggle is ON)
- **VTC icon** in Chrome toolbar (top-right, next to address bar)

**Troubleshooting:**
- If icon not visible: Click puzzle icon → Pin "Visual Trade Copilot"
- If errors shown: Check all files are present in extension folder

---

## 🧪 Part 3: Testing (2 minutes)

### Test 1: Server Status Check

1. Click the **VTC icon** in Chrome toolbar
2. Popup should open
3. Look at bottom: Should say **"Server online"** with green dot ●

**If "Server offline":**
- Make sure backend is running (Step 4 from Part 1)
- Check terminal for errors
- Try restarting server

### Test 2: Analyze a Chart

1. **Open a trading chart** in a new tab:
   - TradingView: `https://www.tradingview.com/chart/`
   - Any chart image in Google Images
   - Or open the test chart: `trading-ai-extension/docs/Screenshot 2025-10-27 213538.png`

2. **Click VTC icon** again

3. **Select model:** Choose "⚖️ Balanced (GPT-4o)"

4. **Optional:** Enter a question like "Analyze this chart"

5. **Click "📸 Analyze Chart"**

6. **Wait 3-5 seconds**

**Expected result:**
- Status shows: "📸 Capturing chart..." → "🧠 Sending to AI..." → "✅ Analysis complete!"
- **Dark overlay appears** on the page with AI analysis
- Analysis text is readable and relevant

7. **Test features:**
   - Click **"📋 Copy"** - should copy to clipboard
   - Click **"✓ Close"** or press **Escape** - overlay closes

**✅ If this works, installation is complete!**

---

## 🎯 Usage Examples

### Example 1: Quick Analysis
1. Open TradingView chart
2. Click VTC icon
3. Leave question blank
4. Click Analyze
5. Review AI's market structure analysis

### Example 2: Specific Question
1. Open chart showing potential entry
2. Click VTC icon
3. Type: "Should I enter long here? What's the risk/reward?"
4. Click Analyze
5. Get personalized trade advice

### Example 3: Fast Mode for Quick Check
1. Open chart
2. Click VTC icon
3. Select "⚡ Fast (GPT-4o-mini)"
4. Type: "Quick bias check"
5. Click Analyze (faster response, 2-3s)

---

## 🔍 Verification Checklist

Use this to ensure everything is working:

### Backend
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Server starts without errors (`python run_server.py`)
- [ ] Shows "Uvicorn running on http://0.0.0.0:8765"
- [ ] Browser can access `http://127.0.0.1:8765/` (shows welcome message)

### Extension
- [ ] Extension loaded in `chrome://extensions/`
- [ ] Extension enabled (toggle is ON)
- [ ] No errors shown in extension card
- [ ] VTC icon visible in toolbar

### Functionality
- [ ] Clicking icon opens popup
- [ ] Popup shows "Server online" (green)
- [ ] Model dropdown has 3 options
- [ ] Question input accepts text
- [ ] Analyze button clickable
- [ ] Chart capture works
- [ ] Overlay appears with analysis
- [ ] Copy button works
- [ ] Close button works

---

## ❗ Common Issues & Solutions

### Issue 1: "Server offline" in popup

**Symptoms:** Red dot, can't analyze

**Solutions:**
```bash
# Check if server is running
# Terminal should show: "Uvicorn running on http://0.0.0.0:8765"

# If not running:
cd trading-ai-extension
python run_server.py

# If running but still offline:
# Check firewall isn't blocking port 8765
```

### Issue 2: Extension won't load

**Symptoms:** Error when loading unpacked

**Solutions:**
1. Verify folder structure:
   ```
   visual-trade-extension/
   ├── manifest.json  ← Must exist
   ├── background.js
   ├── popup/
   └── content/
   ```

2. Check manifest.json is valid JSON:
   ```bash
   # In extension folder
   python -m json.tool manifest.json
   ```

3. Reload extension:
   - chrome://extensions/ → Click refresh icon on VTC card

### Issue 3: Analysis fails with error

**Symptoms:** "❌ Error: ..." message in popup

**Common causes:**

1. **Invalid API Key**
   - Check `run_server.py` has correct key
   - Restart server after updating

2. **OpenAI API Rate Limit**
   - Wait 60 seconds and try again
   - Or upgrade OpenAI account

3. **Budget exceeded**
   - Check backend logs
   - Adjust `MAX_BUDGET` in `openai_client.py`

4. **No chart visible**
   - Make sure a chart is actually visible in browser
   - Scroll so chart fills most of screen

### Issue 4: Blank/empty overlay

**Symptoms:** Overlay shows but no text

**Solutions:**
- Check backend terminal for errors
- Verify model is returning responses
- Try different model (switch to "Balanced")

### Issue 5: Can't see VTC icon

**Symptoms:** Extension loaded but icon not in toolbar

**Solutions:**
1. Click puzzle icon (🧩) in Chrome toolbar
2. Find "Visual Trade Copilot"
3. Click pin icon to add to toolbar

---

## 🔄 Restart/Reload Instructions

### When to Restart Backend:
- After changing API key
- After updating Python code
- If server becomes unresponsive

**How to restart:**
1. In server terminal: Press `Ctrl + C`
2. Wait for shutdown
3. Run: `python run_server.py`

### When to Reload Extension:
- After changing extension code
- After updating manifest.json
- If popup stops working

**How to reload:**
1. Go to `chrome://extensions/`
2. Find "Visual Trade Copilot" card
3. Click refresh icon (🔄)

---

## 📊 System Requirements

### Minimum
- **OS:** Windows 10, macOS 10.14, Linux (Ubuntu 18.04+)
- **RAM:** 4GB
- **Python:** 3.8+
- **Chrome:** Version 88+

### Recommended
- **OS:** Windows 11, macOS 13+, Linux (Ubuntu 22.04+)
- **RAM:** 8GB+
- **Python:** 3.10+
- **Chrome:** Latest version
- **Internet:** 10 Mbps+

---

## 🎓 Next Steps After Installation

1. **Read the docs:**
   - Extension: `visual-trade-extension/README.md`
   - Backend: `QUICK_START.md`
   - Phase summaries: `PHASE_*_SUMMARY.md`

2. **Explore models:**
   - Try all 3 models to find your preference
   - Compare speed vs. quality

3. **Experiment with questions:**
   - Try different question styles
   - See what prompts give best results

4. **Integrate into workflow:**
   - Use before entering trades
   - Confirm your analysis with AI
   - Learn from AI's perspective

---

## 🆘 Still Having Issues?

1. **Check terminal logs:**
   - Backend errors appear in server terminal
   - Chrome errors in DevTools console (F12)

2. **Verify endpoints:**
   - Visit `http://127.0.0.1:8765/` in browser
   - Should show welcome message
   - Check `/models` endpoint for available models

3. **Test backend directly:**
   ```bash
   # In new terminal
   cd trading-ai-extension
   
   # Test health endpoint
   curl http://127.0.0.1:8765/
   
   # Test models endpoint  
   curl http://127.0.0.1:8765/models
   ```

4. **Review logs:**
   - Backend: Check server terminal output
   - Extension: chrome://extensions/ → Details → Inspect views: service worker

---

## ✅ Installation Complete!

If you've reached this point and everything works:

🎉 **Congratulations!** You're ready to use Visual Trade Copilot.

**Quick Reference:**
- **Start Server:** `python run_server.py` (from project root)
- **Open Extension:** Click VTC icon in Chrome
- **Analyze Chart:** Select model → Click "Analyze Chart"
- **Get Help:** Check README files or terminal logs

---

**Happy Trading! 📈✨**

*Visual Trade Copilot - AI-Powered Smart Money Concepts Analysis*

