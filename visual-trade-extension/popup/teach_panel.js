// Phase 5A: Teach Copilot Panel Logic (embedded in popup)
let teachRecognizing = false;
let teachRecognition = null;
let teachSelectedTrade = null;
let teachAvailableTrades = [];

// Declare API_BASE_URL first (this script loads before popup.js)
// Set window property and local const
if (typeof window.API_BASE_URL === 'undefined') {
  window.API_BASE_URL = "http://127.0.0.1:8765";
}
// Use var instead of const to allow it to be used across scripts
var API_BASE_URL = window.API_BASE_URL || "http://127.0.0.1:8765";

/**
 * Initialize Teach Copilot functionality when panel is opened
 * Make it globally accessible so popup.js can call it
 */
async function initTeachCopilot() {
  // Wait a moment for DOM to be ready
  await new Promise(resolve => setTimeout(resolve, 100));
  
  const tradeSelect = document.getElementById("teach-tradeSelect");
  const saveBtn = document.getElementById("teach-saveLesson");
  const feedbackBtn = document.getElementById("teach-getFeedback");
  const voiceBtn = document.getElementById("teach-voiceToggle");
  
  if (!tradeSelect || !saveBtn || !feedbackBtn || !voiceBtn) {
    console.error("[Teach] Missing DOM elements:", {
      tradeSelect: !!tradeSelect,
      saveBtn: !!saveBtn,
      feedbackBtn: !!feedbackBtn,
      voiceBtn: !!voiceBtn
    });
    updateTeachStatus("Error: UI elements not found", "error");
    return;
  }
  
  // Event listeners
  tradeSelect.addEventListener("change", onTeachTradeSelected);
  saveBtn.addEventListener("click", saveTeachLesson);
  feedbackBtn.addEventListener("click", getTeachFeedback);
  voiceBtn.addEventListener("click", toggleTeachVoice);
  
  // Load trades
  await loadTeachTrades();
  
  // Initialize speech recognition
  initTeachSpeechRecognition();
}

// Make function globally accessible
if (typeof window !== 'undefined') {
  window.initTeachCopilot = initTeachCopilot;
}

/**
 * Test server connection
 */
async function testServerConnection() {
  try {
    const response = await fetch(`${API_BASE_URL}/`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.ok;
  } catch (error) {
    console.error("[Teach] Server connection test failed:", error);
    return false;
  }
}

/**
 * Load available trades from backend
 */
async function loadTeachTrades() {
  const selectEl = document.getElementById("teach-tradeSelect");
  
  try {
    updateTeachStatus("Checking server connection...", "info");
    
    // Test server connection first
    const serverOk = await testServerConnection();
    if (!serverOk) {
      throw new Error("Cannot connect to server. Please ensure the backend is running on http://127.0.0.1:8765");
    }
    
    updateTeachStatus("Loading trades...", "info");
    selectEl.disabled = true;
    
    console.log(`[Teach] Fetching from: ${API_BASE_URL}/performance/all`);
    const response = await fetch(`${API_BASE_URL}/performance/all?limit=100`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[Teach] Server returned ${response.status}:`, errorText);
      throw new Error(`Server error ${response.status}: ${errorText}`);
    }
    
    const trades = await response.json();
    console.log(`[Teach] Received ${Array.isArray(trades) ? trades.length : 0} trades`);
    teachAvailableTrades = Array.isArray(trades) ? trades : [];
    
    selectEl.innerHTML = '<option value="">-- Select a trade --</option>';
    
    if (teachAvailableTrades.length === 0) {
      selectEl.innerHTML = '<option value="">No trades found</option>';
      updateTeachStatus("No trades available. Log some trades first!", "error");
      return;
    }
    
    teachAvailableTrades.forEach((trade, index) => {
      const symbol = trade.symbol || "Unknown";
      const outcome = trade.outcome || trade.label || (trade.pnl > 0 ? "win" : (trade.pnl < 0 ? "loss" : "pending"));
      const rMultiple = trade.r_multiple || trade.rr || "?";
      const date = trade.timestamp || trade.entry_time || "";
      const dateStr = date ? new Date(date).toLocaleDateString() : `Trade ${index + 1}`;
      
      // Use the correct ID field (id, trade_id, or session_id)
      const tradeId = trade.id || trade.trade_id || trade.session_id || index.toString();
      
      const option = document.createElement("option");
      option.value = tradeId;
      option.textContent = `${symbol} | ${outcome.toUpperCase()} | ${rMultiple}R | ${dateStr}`;
      option.dataset.tradeIndex = index;
      selectEl.appendChild(option);
    });
    
    selectEl.disabled = false;
    updateTeachStatus(`Loaded ${teachAvailableTrades.length} trades`, "success");
    
  } catch (error) {
    console.error("[Teach] Failed to load trades:", error);
    console.error("[Teach] Error details:", {
      message: error.message,
      stack: error.stack,
      apiUrl: `${API_BASE_URL}/performance/all`
    });
    selectEl.innerHTML = '<option value="">Error loading trades</option>';
    
    // More helpful error message
    let errorMsg = `Error: ${error.message}`;
    if (error.message.includes("Failed to fetch") || error.message.includes("network")) {
      errorMsg = "Cannot connect to server. Make sure the backend is running on http://127.0.0.1:8765";
    } else if (error.message.includes("CORS")) {
      errorMsg = "CORS error. Check server CORS settings.";
    }
    
    updateTeachStatus(errorMsg, "error");
  }
}

/**
 * Handle trade selection
 */
async function onTeachTradeSelected(event) {
  const tradeId = event.target.value;
  
  if (!tradeId) {
    teachSelectedTrade = null;
    document.getElementById("teach-tradeInfo").classList.add("hidden");
    document.getElementById("teach-chartPreview").style.display = "none";
    return;
  }
  
  const option = event.target.options[event.target.selectedIndex];
  const tradeIndex = parseInt(option.dataset.tradeIndex);
  teachSelectedTrade = teachAvailableTrades[tradeIndex];
  
  if (!teachSelectedTrade) {
    updateTeachStatus("Trade not found", "error");
    return;
  }
  
  // Display trade info
  displayTeachTradeInfo(teachSelectedTrade);
  
  // Load chart preview
  await loadTeachChartForTrade(teachSelectedTrade);
}

/**
 * Display selected trade information
 */
function displayTeachTradeInfo(trade) {
  const infoEl = document.getElementById("teach-tradeInfo");
  const symbol = trade.symbol || "Unknown";
  const outcome = trade.outcome || (trade.pnl > 0 ? "win" : (trade.pnl < 0 ? "loss" : "pending"));
  const rMultiple = trade.r_multiple || trade.rr || "?";
  const pnl = trade.pnl !== undefined ? `${trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}` : "N/A";
  const date = trade.timestamp || trade.entry_time || "";
  const dateStr = date ? new Date(date).toLocaleDateString() + " " + new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Unknown date";
  
  const outcomeClass = outcome === "win" ? "good" : (outcome === "loss" ? "bad" : "neutral");
  
  infoEl.innerHTML = `
    <div style="margin-top:8px; padding:8px; background:#1e1e1e; border-radius:4px; font-size:12px;">
      <div><strong style="color:#4fc3f7;">${symbol}</strong> <span class="stat-value ${outcomeClass}">${outcome.toUpperCase()}</span></div>
      <div style="color:#aaa; margin-top:4px;">R-Multiple: ${rMultiple}R | PnL: ${pnl} | ${dateStr}</div>
    </div>
  `;
  
  infoEl.classList.remove("hidden");
}

/**
 * Load chart preview for selected trade
 */
async function loadTeachChartForTrade(trade) {
  const previewEl = document.getElementById("teach-chartPreview");
  // Trade ID can be in different fields
  const tradeId = trade.id || trade.trade_id || trade.session_id;
  const symbol = trade.symbol || "";
  
  if (!tradeId || !symbol) {
    previewEl.style.display = "none";
    updateTeachStatus("Trade ID or symbol missing", "info");
    return;
  }
  
  updateTeachStatus("Loading chart...", "info");
  
  try {
    // First, check if chart_path is already in trade object
    if (trade.chart_path) {
      const fileName = trade.chart_path.split(/[/\\]/).pop();
      previewEl.src = `${API_BASE_URL}/charts/${fileName}`;
      previewEl.onerror = () => {
        tryMetadataLookup(previewEl, symbol, tradeId);
      };
      previewEl.onload = () => {
        previewEl.style.display = "block";
        updateTeachStatus("Chart loaded", "success");
      };
      return;
    }
    
    // Try metadata lookup
    await tryMetadataLookup(previewEl, symbol, tradeId);
    
  } catch (error) {
    console.error("Failed to load chart:", error);
    previewEl.style.display = "none";
    updateTeachStatus("Could not load chart", "error");
  }
}

/**
 * Try to load chart via metadata API
 */
async function tryMetadataLookup(previewEl, symbol, tradeId) {
  try {
    const metaResponse = await fetch(`${API_BASE_URL}/charts/chart/${tradeId}`);
    if (metaResponse.ok) {
      const chartMeta = await metaResponse.json();
      if (chartMeta.chart_path) {
        const fileName = chartMeta.chart_path.split(/[/\\]/).pop();
        previewEl.src = `${API_BASE_URL}/charts/${fileName}`;
        previewEl.onerror = () => {
          // If metadata file doesn't work, try pattern matching
          tryPatternMatch(previewEl, symbol, tradeId);
        };
        previewEl.onload = () => {
          previewEl.style.display = "block";
          updateTeachStatus("Chart loaded", "success");
        };
        return;
      }
    }
  } catch (metaError) {
    console.log("Metadata endpoint failed, trying pattern match:", metaError);
  }
  
  // Fallback: Try pattern matching
  tryPatternMatch(previewEl, symbol, tradeId);
}

/**
 * Try to load chart using pattern matching
 */
function tryPatternMatch(previewEl, symbol, tradeId) {
  // Common pattern: SYMBOL_5m_TRADE_ID.png
  const patterns = [
    `${symbol}_5m_${tradeId}.png`,
    `${symbol.toUpperCase()}_5m_${tradeId}.png`,
    `${symbol}_5m_${String(tradeId).slice(-10)}.png` // Last 10 digits
  ];
  
  let patternIndex = 0;
  
  function tryNextPattern() {
    if (patternIndex >= patterns.length) {
      previewEl.style.display = "none";
      updateTeachStatus("Chart not found. Make sure chart was reconstructed.", "info");
      return;
    }
    
    previewEl.src = `${API_BASE_URL}/charts/${patterns[patternIndex]}`;
    previewEl.onerror = () => {
      patternIndex++;
      tryNextPattern();
    };
    previewEl.onload = () => {
      previewEl.style.display = "block";
      updateTeachStatus("Chart loaded", "success");
    };
  }
  
  tryNextPattern();
}

/**
 * Save lesson text
 */
function saveTeachLesson() {
  const text = document.getElementById("teach-lessonInput").value.trim();
  
  if (!teachSelectedTrade) {
    updateTeachStatus("Please select a trade first.", "error");
    return;
  }
  
  if (!text) {
    updateTeachStatus("Please describe the setup first.", "error");
    return;
  }

  const lessonData = {
    trade_id: teachSelectedTrade.session_id || teachSelectedTrade.trade_id,
    symbol: teachSelectedTrade.symbol,
    outcome: teachSelectedTrade.outcome,
    explanation: text,
    timestamp: new Date().toISOString()
  };

  // Save to chrome.storage.local (temporary until backend API is ready)
  if (!chrome || !chrome.storage || !chrome.storage.local) {
    updateTeachStatus("Chrome storage API not available", "error");
    console.error("[Teach] chrome.storage.local is not available");
    return;
  }
  
  chrome.storage.local.set({ 
    lastLesson: lessonData,
    [`lesson_${lessonData.trade_id}`]: lessonData
  }, () => {
    updateTeachStatus(`✅ Lesson saved for ${teachSelectedTrade.symbol}. (Backend integration in Phase 5B)`, "success");
  });
}

/**
 * Get AI feedback
 */
function getTeachFeedback() {
  if (!teachSelectedTrade) {
    updateTeachStatus("Please select a trade first.", "error");
    return;
  }
  
  const text = document.getElementById("teach-lessonInput").value.trim();
  
  if (!text) {
    updateTeachStatus("Please enter lesson text first.", "error");
    return;
  }

  updateTeachStatus(`⏳ Requesting feedback for ${teachSelectedTrade.symbol}... (Backend API coming in Phase 5B)`, "info");
}

/**
 * Initialize speech recognition
 */
function initTeachSpeechRecognition() {
  if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
    const voiceBtn = document.getElementById("teach-voiceToggle");
    if (voiceBtn) {
      voiceBtn.disabled = true;
      voiceBtn.title = "Speech recognition not supported";
    }
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  
  if (!SpeechRecognition) return;

  teachRecognition = new SpeechRecognition();
  teachRecognition.lang = "en-US";
  teachRecognition.continuous = false;
  teachRecognition.interimResults = false;

  teachRecognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    const input = document.getElementById("teach-lessonInput");
    const currentText = input.value;
    input.value = currentText ? currentText + " " + transcript : transcript;
    updateTeachStatus(`🎙️ Transcribed: "${transcript}"`, "success");
  };

  teachRecognition.onerror = (event) => {
    let errorMsg = "Speech recognition error";
    if (event.error === "no-speech") {
      errorMsg = "No speech detected. Try again.";
    } else if (event.error === "network") {
      errorMsg = "Network error. Check your connection.";
    } else if (event.error === "not-allowed") {
      errorMsg = "Microphone permission denied. Please enable in browser settings.";
    }
    updateTeachStatus(errorMsg, "error");
    teachRecognizing = false;
    const voiceBtn = document.getElementById("teach-voiceToggle");
    if (voiceBtn) voiceBtn.classList.remove("active");
  };

  teachRecognition.onend = () => {
    teachRecognizing = false;
    const voiceBtn = document.getElementById("teach-voiceToggle");
    if (voiceBtn) voiceBtn.classList.remove("active");
  };
}

/**
 * Toggle voice recognition
 */
function toggleTeachVoice() {
  if (!teachRecognition) {
    updateTeachStatus("Speech recognition not available. Use Chrome browser.", "error");
    return;
  }

  if (!teachRecognizing) {
    try {
      teachRecognition.start();
      teachRecognizing = true;
      const voiceBtn = document.getElementById("teach-voiceToggle");
      if (voiceBtn) voiceBtn.classList.add("active");
      updateTeachStatus("🎙️ Listening... Speak now.", "info");
    } catch (error) {
      console.error("Failed to start recognition:", error);
      updateTeachStatus("Failed to start voice recognition. Try again.", "error");
    }
  } else {
    teachRecognition.stop();
    updateTeachStatus("Voice recognition stopped.", "info");
  }
}

/**
 * Update status message
 */
function updateTeachStatus(msg, type = "info") {
  const statusEl = document.getElementById("teach-status");
  if (!statusEl) return;
  
  statusEl.textContent = msg;
  statusEl.className = type || "";
  
  if (type === "success" || type === "info") {
    setTimeout(() => {
      if (statusEl.textContent === msg) {
        statusEl.textContent = "";
        statusEl.className = "";
      }
    }, 3000);
  }
}

