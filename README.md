# 🚀 Visual Trade Copilot

**AI-Powered Smart Money Concepts (SMC) Trading Assistant**

A Chrome extension with FastAPI backend that provides real-time trading chart analysis using GPT-4o/GPT-5 vision models. Features persistent conversational memory, draggable chat interface, and context-aware AI responses.

---

## ✨ Features

### 🧠 **Phase 3A: Conversational Memory** (Latest)
- **Persistent Chat Panel** - Continuous conversation thread with draggable interface
- **IndexedDB Storage** - All conversations saved locally, survive browser restarts
- **Context-Aware AI** - Remembers last 5 messages for coherent follow-ups
- **Direct Messaging** - Send questions directly from chat without opening popup
- **Export & Clear** - Full control over conversation data (JSON export)
- **Smart UI** - Drag to reposition, resize, minimize, and beautiful animations

### 📸 **Core Functionality**
- **One-Click Analysis** - Capture and analyze any visible trading chart
- **Multi-Model Support** - Choose between Fast (GPT-4o-mini), Balanced (GPT-4o), or Advanced (GPT-5)
- **Natural Language Q&A** - Ask specific questions about market structure, entries, risk
- **SMC Expertise** - Specialized in Smart Money Concepts, liquidity, market structure
- **Real-Time Responses** - 2-8 seconds depending on model

---

## 🎯 Quick Start

### Prerequisites
- Python 3.8+
- Google Chrome (or Chromium-based browser)
- OpenAI API key with GPT-4/GPT-5 access

### 1. Clone Repository
```bash
git clone https://github.com/ArgusOnline01/trading-ai-extension.git
cd trading-ai-extension
```

### 2. Install Backend Dependencies
```bash
cd server
pip install -r requirements.txt
```

### 3. Start Backend Server
```bash
cd ..
python run_server.py
```

The server will start on `http://localhost:8765`

> **Note:** The API key is configured in `run_server.py`. Update it with your OpenAI key before starting.

### 4. Load Chrome Extension
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle top-right)
3. Click **Load unpacked**
4. Select the `visual-trade-extension/` folder
5. Extension icon appears in toolbar

### 5. Start Trading!
1. Navigate to any trading chart (TradingView, etc.)
2. Click the VTC extension icon
3. Click "📸 Analyze Chart" or "💬 Open Chat Panel"
4. Start conversing with your AI copilot!

---

## 📖 Documentation

- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - Detailed setup instructions
- **[QUICK_START.md](QUICK_START.md)** - Fast track to get running
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[docs/SRS.md](docs/SRS.md)** - Software Requirements Specification
- **[docs/DEVELOPMENT_CONTEXT.md](docs/DEVELOPMENT_CONTEXT.md)** - Development background

---

## 🏗️ Architecture

### Backend (FastAPI)
```
server/
├── app.py              # Main API with 6 endpoints
├── decision.py         # SMC trading logic
├── openai_client.py    # OpenAI API wrapper with budget tracking
└── requirements.txt    # Python dependencies
```

### Frontend (Chrome Extension)
```
visual-trade-extension/
├── manifest.json       # Extension config (Manifest v3)
├── background.js       # Service worker (message handling)
├── popup/              # Extension popup UI
│   ├── popup.html
│   ├── popup.js        # Chart capture & API calls
│   └── popup.css
├── content/            # Injected into web pages
│   ├── content.js      # Chat panel with IndexedDB
│   └── overlay.css     # Dark theme styling
└── icons/              # Extension icons (16/48/128px)
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/analyze` | POST | Structured SMC analysis |
| `/ask` | POST | Conversational Q&A with context |
| `/budget` | GET | API spending status |
| `/models` | GET | List available OpenAI models |
| `/prompt` | GET | View system prompt |

---

## 💬 Usage Examples

### First Analysis
```
1. Open TradingView chart
2. Click VTC icon → "Analyze Chart"
3. Chat panel appears with SMC analysis
```

### Follow-Up Questions
```
1. Type in chat: "What's the risk/reward?"
2. Click 📸 (or Ctrl+Enter)
3. AI captures new chart + responds with context
4. Conversation continues seamlessly
```

### Managing Chat
```
- Drag header to move panel
- Resize from corner
- Export: Click 💾 (saves as JSON)
- Clear: Click 🗑️ (with confirmation)
- Minimize: Click ➖
- Close: Click ✖️
```

---

## 🎨 Model Comparison

| Model | Speed | Cost/1K | Best For |
|-------|-------|---------|----------|
| **⚡ Fast** (GPT-4o-mini) | 2-3s | $0.001 | Quick checks, simple setups |
| **⚖️ Balanced** (GPT-4o) | 3-5s | $0.005 | Standard analysis (default) |
| **🧠 Advanced** (GPT-5-mini) | 5-8s | $0.015 | Complex patterns, deep reasoning |

---

## 🔒 Privacy & Security

- **Local-first architecture** - Conversations stored in browser IndexedDB
- **No cloud storage** - Your trading insights stay private
- **Budget controls** - Built-in spending limits
- **CORS protection** - API only accessible from localhost
- **Export capability** - You own your data

---

## 🛠️ Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Complete | FastAPI backend with 6 endpoints |
| **Phase 1.5** | ✅ Complete | Conversational `/ask` endpoint |
| **Phase 1.6** | ✅ Complete | Dynamic model switching |
| **Phase 1.7** | ✅ Complete | Model discovery & GPT-5 support |
| **Phase 2** | ✅ Complete | Chrome Extension with popup UI |
| **Phase 3A** | ✅ Complete | **Conversational memory & persistent chat** |
| Phase 3B | 📋 Planned | Cloud sync & multi-device support |
| Phase 3C | 📋 Future | Drawing tools & RAG memory |
| Phase 4 | 📋 Future | Chrome Web Store publication |

---

## 🧪 Testing

Run the test suite:
```bash
# Test chat persistence
See TEST_PHASE_3A.md for 10 test scenarios

# Test backend
curl http://127.0.0.1:8765/
curl http://127.0.0.1:8765/models
curl http://127.0.0.1:8765/budget
```

---

## 🐛 Troubleshooting

### "Server offline" error
```bash
# Start the backend
python run_server.py
```

### "Failed to open chat panel"
```bash
# Reload extension
chrome://extensions/ → Click reload on VTC
# Refresh the page
Ctrl+R on your trading chart
```

### More issues?
Check the browser console (F12) for errors and review the [CHANGELOG.md](CHANGELOG.md) for known issues in your version.

---

## 📦 Dependencies

### Backend
- FastAPI 0.95.2
- Uvicorn 0.22.0
- OpenAI 0.28.1
- Pillow 12.0.0
- Python-dotenv 1.0.0
- Pydantic 1.10.24

### Extension
- Chrome Extensions Manifest v3
- IndexedDB API
- Chrome Tabs API
- Chrome Scripting API

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional trading indicators
- More language models
- Voice input/output
- Mobile support
- Backend database for cloud sync

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Smart Money Concepts** methodology
- **OpenAI** for GPT-4o/GPT-5 vision models
- **FastAPI** framework
- **Chrome Extensions** platform

---

## 📧 Support

For issues, questions, or feature requests:
1. Check browser console (F12) for errors
2. Review [CHANGELOG.md](CHANGELOG.md) for version-specific notes
3. Check [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for setup help
4. Open an issue on GitHub

---

## 🚀 Roadmap

### Short-term
- [ ] Chrome Web Store submission
- [ ] User authentication
- [ ] Cloud conversation sync
- [ ] Search through chat history

### Long-term
- [ ] Mobile app version
- [ ] Multi-chart comparison
- [ ] Real-time alerts
- [ ] Integration with brokers
- [ ] Voice commands
- [ ] Advanced drawing tools

---

**Built with ❤️ for traders using Smart Money Concepts**

*Version 3.0.0 - Phase 3A Complete*

**⭐ Star this repo if you find it useful!**

---

## 📊 Project Stats

- **Lines of Code:** ~3,500+
- **Features Implemented:** 20+ major
- **API Endpoints:** 6
- **Documentation Pages:** 10+
- **Test Scenarios:** 10
- **Development Time:** Multiple phases
- **Status:** Production-ready! ✅

