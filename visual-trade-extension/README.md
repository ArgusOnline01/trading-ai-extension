# 🚀 Visual Trade Copilot - Chrome Extension

AI-powered trading chart analysis extension using Smart Money Concepts (SMC). Analyze any chart directly in your browser with GPT-4o/GPT-5 vision models.

---

## ✨ Features

### Phase 3A: Conversational Memory 🧠
- **💬 Persistent Chat Panel** - Continuous conversation thread on the right side
- **🗄️ Local Memory** - Chat history saved in IndexedDB, survives restarts
- **🔗 Context-Aware AI** - AI remembers previous messages and provides coherent follow-ups
- **💾 Export Chat** - Save conversations as JSON for your trading journal
- **🗑️ Clear History** - Full control over your conversation data

### Core Features
- **📸 One-Click Chart Capture** - Capture visible trading charts instantly
- **🧠 AI-Powered Analysis** - Get SMC analysis using GPT-4o or GPT-5
- **⚡ Model Selection** - Choose between Fast (GPT-4o-mini), Balanced (GPT-4o), or Advanced (GPT-5)
- **💬 Natural Language Q&A** - Ask specific questions about the chart
- **🎨 Beautiful Dark UI** - Sleek chat interface that doesn't interrupt workflow

---

## 🛠️ Installation

### Prerequisites

1. **Backend Server Running**
   ```bash
   cd ../server
   python run_server.py
   ```
   Server must be running on `http://127.0.0.1:8765`

2. **Chrome Browser** (or Chromium-based: Edge, Brave, Opera)

### Load Extension

1. Open Chrome and navigate to `chrome://extensions/`

2. Enable **Developer mode** (toggle in top-right corner)

3. Click **Load unpacked**

4. Navigate to and select: `trading-ai-extension/visual-trade-extension/`

5. The extension icon should appear in your toolbar

---

## 📖 Usage

### Basic Workflow

1. **Open a Trading Chart**
   - Navigate to any page with a visible trading chart
   - TradingView, TrendSpider, MetaTrader WebTrader, etc.

2. **Click Extension Icon**
   - Click the Visual Trade Copilot icon in your toolbar
   - Check that server status shows "Server online" (green dot)

3. **Select Model** (optional)
   - ⚡ **Fast** - GPT-4o-mini (fastest, cheapest)
   - ⚖️ **Balanced** - GPT-4o (default, best balance)
   - 🧠 **Advanced** - GPT-5 (deepest analysis, experimental)

4. **Ask a Question** (optional)
   - Leave blank for general analysis
   - Or ask specific questions:
     - "Should I enter long or wait?"
     - "Where are the key liquidity zones?"
     - "Is this a valid market structure break?"

5. **Analyze**
   - Click "📸 Analyze Chart"
   - Wait 3-5 seconds for AI response
   - Analysis appears in beautiful dark overlay

6. **Read & Copy**
   - Review the AI analysis
   - Click "📋 Copy" to copy text
   - Click "✓ Close" or press `Escape` to close

---

## 🎯 Model Comparison

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| **⚡ Fast** | 2-3s | $0.001 | Quick checks, simple setups |
| **⚖️ Balanced** | 3-5s | $0.005 | Most trades, detailed analysis |
| **🧠 Advanced** | 5-8s | $0.015 | Complex patterns, deep reasoning |

---

## 🔧 Troubleshooting

### "Server offline" Error

**Problem:** Red dot in popup footer, can't analyze

**Solution:**
```bash
# Navigate to server directory
cd trading-ai-extension/server

# Start the backend
python run_server.py
```

### Chart Not Captured Correctly

**Problem:** Overlay shows wrong/blank image

**Solution:**
- Make sure chart is **fully visible** in browser window
- Scroll so chart fills most of the screen
- Avoid capturing when chart is loading

### Extension Not Loading

**Problem:** Can't find extension in Chrome

**Solution:**
1. Check `chrome://extensions/` shows the extension
2. Make sure "Enabled" toggle is ON
3. Try removing and re-loading the extension
4. Check browser console (F12) for errors

### Analysis Taking Too Long

**Problem:** "Analyzing..." stuck for >15 seconds

**Solution:**
- Check backend server logs for errors
- Verify OpenAI API key is valid in `.env`
- Try switching to "Fast" model
- Check internet connection

---

## 🎨 Keyboard Shortcuts

- `Ctrl/Cmd + Enter` in question box → Analyze
- `Escape` → Close overlay

---

## 📁 File Structure

```
visual-trade-extension/
├── manifest.json          # Extension configuration
├── background.js          # Service worker
├── popup/
│   ├── popup.html        # Extension popup UI
│   ├── popup.js          # Popup logic & API calls
│   └── popup.css         # Popup styling
├── content/
│   ├── content.js        # Overlay rendering
│   └── overlay.css       # Overlay styling
├── icons/
│   ├── icon16.png        # 16x16 icon
│   ├── icon48.png        # 48x48 icon
│   └── icon128.png       # 128x128 icon
├── create_icons.py       # Icon generator script
└── README.md            # This file
```

---

## 🔐 Permissions

The extension requests these permissions:

- **activeTab** - Capture visible tab image
- **scripting** - Inject overlay into page
- **tabs** - Query active tab info
- **host_permissions** - Connect to localhost:8765 API

All data is processed locally. No external tracking.

---

## 🚀 Phase 2 Complete

### ✅ Implemented Features

- [x] Manifest v3 configuration
- [x] Popup UI with model selection
- [x] Chart capture via `captureVisibleTab()`
- [x] Backend integration (`/ask` endpoint)
- [x] Beautiful dark overlay renderer
- [x] Copy to clipboard functionality
- [x] Server status indicator
- [x] Error handling & user feedback
- [x] Keyboard shortcuts
- [x] Mobile-responsive design

---

## 📝 Next Steps (Phase 3)

- [ ] Chrome Web Store packaging
- [ ] Advanced settings panel
- [ ] Analysis history/cache
- [ ] Multi-chart comparison
- [ ] Voice input integration
- [ ] Real-time alerts

---

## 🐛 Known Issues

1. **GPT-5 base model** returns empty content for vision - using `gpt-5-mini` for Advanced mode instead
2. **Some trading platforms** use canvas/WebGL charts that may not capture correctly
3. **Dark mode compatibility** - overlay may blend with some dark themes

---

## 💡 Tips

1. **Best Results**: Zoom chart to focus on specific timeframe before analyzing
2. **Specific Questions**: Ask targeted questions for better answers
3. **Model Selection**: Start with Balanced, upgrade to Advanced for complex patterns
4. **Copy Feature**: Use copy button to save analysis to notes/journal

---

## 📧 Support

For issues or questions:
1. Check backend server logs: `trading-ai-extension/server/`
2. Check browser console: `F12` → Console tab
3. Verify OpenAI API key and budget

---

**Built with ❤️ for traders using Smart Money Concepts**

*Version 2.0.0 - Phase 2 Complete*

