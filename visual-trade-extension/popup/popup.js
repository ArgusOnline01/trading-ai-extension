// Visual Trade Copilot - Popup Script (Phase 3B.1: Redesigned UI)
// Handles quick actions and model selection

// API_BASE_URL is set by teach_panel.js (which loads first)
// Just ensure it exists, then use window.API_BASE_URL directly throughout
if (typeof window.API_BASE_URL === 'undefined') {
  window.API_BASE_URL = "http://127.0.0.1:8765";
}
// Create a local reference function to avoid redeclaring const
// We'll replace all API_BASE_URL references with window.API_BASE_URL

// DOM Elements
const newConversationBtn = document.getElementById("newConversation");
const toggleChatBtn = document.getElementById("toggleChat");
const viewSessionsBtn = document.getElementById("viewSessions");
const viewPerformanceBtn = document.getElementById("viewPerformance");
const teachCopilotBtn = document.getElementById("teachCopilot");
const quickAnalyzeBtn = document.getElementById("quickAnalyze");
const performancePanel = document.getElementById("performancePanel");
const closePerformanceBtn = document.getElementById("closePerformance");
const statsContent = document.getElementById("statsContent");
const teachPanel = document.getElementById("teachPanel");
const closeTeachBtn = document.getElementById("closeTeach");
const teachContent = document.getElementById("teachContent");
const statusDiv = document.getElementById("status");
const serverIndicator = document.getElementById("server-indicator");
const serverText = document.getElementById("server-text");
const modelOptions = document.querySelectorAll(".model-option");

// Selected model state
let selectedModel = "fast"; // GPT-5 Chat (native vision)

// Immediate initialization check
console.log("[Popup] Script loaded");
console.log("[Popup] API_BASE_URL:", window.API_BASE_URL);
console.log("[Popup] Initial DOM state:", {
  readyState: document.readyState,
  serverIndicator: !!serverIndicator,
  serverText: !!serverText
});

// Check server status - multiple strategies to ensure it runs
function initializeServerCheck() {
  console.log("[Popup] initializeServerCheck called");
  
  // Re-query DOM elements in case they weren't available initially
  const indicator = document.getElementById("server-indicator");
  const text = document.getElementById("server-text");
  
  if (!indicator || !text) {
    console.error("[Popup] Server status elements still not found after delay!");
    console.error("[Popup] Available elements:", {
      indicator: !!indicator,
      text: !!text,
      allIds: Array.from(document.querySelectorAll('[id]')).map(el => el.id)
    });
    return;
  }
  
  console.log("[Popup] DOM elements confirmed, calling checkServerStatus");
  checkServerStatus();
}

// Strategy 1: If DOM is ready, check immediately
if (document.readyState === 'complete') {
  console.log("[Popup] Document already complete");
  setTimeout(initializeServerCheck, 100);
} else if (document.readyState === 'interactive') {
  console.log("[Popup] Document interactive");
  setTimeout(initializeServerCheck, 150);
} else {
  console.log("[Popup] Document loading, waiting for DOMContentLoaded");
  document.addEventListener('DOMContentLoaded', () => {
    console.log("[Popup] DOMContentLoaded event fired");
    setTimeout(initializeServerCheck, 100);
  });
}

// Strategy 2: Also use window load as backup
window.addEventListener('load', () => {
  console.log("[Popup] Window load event fired");
  setTimeout(() => {
    const text = document.getElementById("server-text");
    if (text && text.textContent === "Checking server...") {
      // Still checking, let it finish
      console.log("[Popup] Server check already in progress");
    } else {
      console.log("[Popup] Window load backup: initializing server check");
      initializeServerCheck();
    }
  }, 300);
});

// Retry server check if it fails
let serverCheckRetries = 0;
const MAX_RETRIES = 3;

// Diagnostic function to test server connection
window.testServerConnection = async function() {
  console.log("=== SERVER CONNECTION DIAGNOSTIC ===");
  console.log("API Base URL:", window.API_BASE_URL);
  console.log("Testing basic fetch...");
  
  try {
    // Test 1: Simple fetch
    console.log("Test 1: Fetching root endpoint...");
    const response = await fetch(`${window.API_BASE_URL}/`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      mode: "cors"
    });
    console.log("Response status:", response.status);
    console.log("Response headers:", [...response.headers.entries()]);
    const data = await response.json();
    console.log("Response data:", data);
    console.log("✅ Test 1 PASSED");
    
    // Test 2: Performance endpoint
    console.log("\nTest 2: Fetching /performance/all...");
    const perfResponse = await fetch(`${window.API_BASE_URL}/performance/all?limit=5`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      mode: "cors"
    });
    console.log("Response status:", perfResponse.status);
    const perfData = await perfResponse.json();
    console.log("Response data length:", Array.isArray(perfData) ? perfData.length : "not an array");
    console.log("✅ Test 2 PASSED");
    
    return { success: true, message: "All tests passed" };
  } catch (error) {
    console.error("❌ Test FAILED:", error);
    console.error("Error name:", error.name);
    console.error("Error message:", error.message);
    console.error("Error stack:", error.stack);
    return { success: false, error: error.message };
  }
};

// Model selection handler (for grid buttons)
modelOptions.forEach(option => {
  option.addEventListener("click", () => {
    modelOptions.forEach(opt => opt.classList.remove("active"));
    option.classList.add("active");
    selectedModel = option.dataset.model;
    console.log("Model selected:", selectedModel);
  });
});

// Model list handler (for "More Models" dropdown)
document.querySelectorAll(".model-list-item").forEach(item => {
  item.addEventListener("click", () => {
    // Remove active from grid buttons
    modelOptions.forEach(opt => opt.classList.remove("active"));
    selectedModel = item.dataset.model;
    console.log("Model selected from list:", selectedModel);
    
    // Visual feedback
    item.style.background = "rgba(255, 215, 0, 0.2)";
    item.style.borderColor = "#ffd700";
    setTimeout(() => {
      item.style.background = "";
      item.style.borderColor = "";
    }, 500);
    
    // Show notification
    setStatus("success", `Selected: ${item.textContent.trim()}`);
  });
});

// Helper function to ensure content script is injected
async function ensureContentScript(tabId) {
  try {
    await chrome.tabs.sendMessage(tabId, { action: "ping" });
    return true;
  } catch (error) {
    console.log("Content script not found, injecting...");
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        files: ['content/content.js']
      });
      
      await chrome.scripting.insertCSS({
        target: { tabId: tabId },
        files: ['content/overlay.css']
      });
      
      await new Promise(resolve => setTimeout(resolve, 500));
      return true;
    } catch (injectError) {
      console.error("Failed to inject content script:", injectError);
      return false;
    }
  }
}

// New Conversation - Creates a new session and opens chat
newConversationBtn.addEventListener("click", async () => {
  try {
    setStatus("loading", "Starting new conversation...");
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error("No active tab found");
    
    const contentScriptReady = await ensureContentScript(tab.id);
    if (!contentScriptReady) throw new Error("Failed to initialize");
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Send message to create new session and open chat
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: "newSession"
      });
      
      // Then toggle chat to open it
      await chrome.tabs.sendMessage(tab.id, {
        action: "toggleChat"
      });
    } catch (msgError) {
      console.log("Message sent (channel closed)");
    }
    
    setStatus("success", "New session started!");
    setTimeout(() => window.close(), 1000);
  } catch (error) {
    console.error("New conversation error:", error);
    setStatus("error", `Error: ${error.message}`);
  }
});

// Continue Chat - Opens existing chat panel
toggleChatBtn.addEventListener("click", async () => {
  try {
    setStatus("loading", "Opening chat...");
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error("No active tab found");
    
    const contentScriptReady = await ensureContentScript(tab.id);
    if (!contentScriptReady) throw new Error("Failed to initialize");
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: "toggleChat"
      });
    } catch (msgError) {
      console.log("Message sent (channel closed)");
    }
    
    setStatus("success", "Chat opened!");
    setTimeout(() => window.close(), 800);
  } catch (error) {
    console.error("Toggle chat error:", error);
    setStatus("error", `Error: ${error.message}`);
  }
});

// View Sessions - Opens session manager
viewSessionsBtn.addEventListener("click", async () => {
  try {
    setStatus("loading", "Loading sessions...");
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error("No active tab found");
    
    const contentScriptReady = await ensureContentScript(tab.id);
    if (!contentScriptReady) throw new Error("Failed to initialize");
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    try {
      // First open chat, then session manager
      await chrome.tabs.sendMessage(tab.id, {
        action: "toggleChat"
      });
      
      await new Promise(resolve => setTimeout(resolve, 200));
      
      await chrome.tabs.sendMessage(tab.id, {
        action: "openSessionManager"
      });
    } catch (msgError) {
      console.log("Message sent (channel closed)");
    }
    
    setStatus("success", "Sessions loaded!");
    setTimeout(() => window.close(), 800);
  } catch (error) {
    console.error("View sessions error:", error);
    setStatus("error", `Error: ${error.message}`);
  }
});

// Quick Analyze - Captures chart and analyzes immediately
quickAnalyzeBtn.addEventListener("click", async () => {
  try {
    setStatus("loading", "Capturing chart...");
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error("No active tab found");
    
    const contentScriptReady = await ensureContentScript(tab.id);
    if (!contentScriptReady) throw new Error("Failed to initialize");
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Send analyze message with selected model
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: "quickAnalyze",
        model: selectedModel
      });
    } catch (msgError) {
      console.log("Message sent (channel closed)");
    }
    
    setStatus("success", "Analyzing...");
    setTimeout(() => window.close(), 1000);
  } catch (error) {
    console.error("Quick analyze error:", error);
    setStatus("error", `Error: ${error.message}`);
  }
});

// Server status check
async function checkServerStatus() {
  // Verify DOM elements exist
  if (!serverText || !serverIndicator) {
    console.error("[Popup] Server status elements not found!", {
      serverText: !!serverText,
      serverIndicator: !!serverIndicator
    });
    return false;
  }
  
  try {
    serverText.textContent = "Checking server...";
    serverIndicator.classList.remove("online", "offline");
    
    console.log(`[Popup] Checking server at: ${window.API_BASE_URL}/`);
    console.log(`[Popup] DOM elements found:`, {
      serverText: !!serverText,
      serverIndicator: !!serverIndicator
    });
    
    // Use a timeout wrapper instead of AbortSignal.timeout (not widely supported)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      console.log("[Popup] Fetch timeout triggered, aborting...");
      controller.abort();
    }, 5000); // Increased to 5 seconds
    
    let response;
    try {
      console.log("[Popup] Attempting fetch with options:", {
        url: `${window.API_BASE_URL}/`,
        method: "GET",
        mode: "cors",
        credentials: "omit"
      });
      
      response = await fetch(`${window.API_BASE_URL}/`, {
        method: "GET",
        headers: { 
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        mode: "cors",
        credentials: "omit",
        signal: controller.signal,
        cache: "no-cache"
      });
      clearTimeout(timeoutId);
      console.log("[Popup] Fetch completed successfully");
    } catch (fetchError) {
      clearTimeout(timeoutId);
      console.error("[Popup] Fetch exception caught:", fetchError);
      console.error("[Popup] Fetch error type:", typeof fetchError);
      console.error("[Popup] Fetch error constructor:", fetchError.constructor.name);
      throw fetchError;
    }
    
    console.log(`[Popup] Server response: ${response.status} ${response.statusText}`);
    
    if (response.ok) {
      const data = await response.json();
      console.log("[Popup] Server is online:", data);
      if (serverIndicator) {
        serverIndicator.classList.add("online");
        serverIndicator.classList.remove("offline");
      }
      if (serverText) {
        serverText.textContent = "Server online";
      }
      serverCheckRetries = 0; // Reset retry counter on success
      return true;
    } else {
      throw new Error(`Server returned ${response.status}`);
    }
  } catch (error) {
    console.error("[Popup] Server check failed:", error);
    console.error("[Popup] Error details:", {
      name: error.name,
      message: error.message,
      stack: error.stack,
      toString: String(error)
    });
    
    if (serverIndicator) {
      serverIndicator.classList.add("offline");
      serverIndicator.classList.remove("online");
    }
    
    let errorMsg = "Server offline";
    if (error.name === "AbortError" || error.message.includes("timeout") || error.message.includes("aborted")) {
      errorMsg = "Server timeout (5s)";
    } else if (error.message.includes("Failed to fetch") || error.message.includes("network") || error.message.includes("ERR_") || error.message.includes("Load failed")) {
      errorMsg = "Cannot connect - server may be offline";
    } else if (error.message.includes("CORS") || error.message.includes("cross-origin")) {
      errorMsg = "CORS error";
    } else {
      errorMsg = `Error: ${error.message.substring(0, 30)}`;
    }
    
    if (serverText) {
      serverText.textContent = errorMsg;
    }
    
    // Retry if we haven't exceeded max retries
    if (serverCheckRetries < MAX_RETRIES) {
      serverCheckRetries++;
      console.log(`[Popup] Retrying server check (${serverCheckRetries}/${MAX_RETRIES})...`);
      setTimeout(() => checkServerStatus(), 2000);
    } else {
      console.log("[Popup] Max retries reached, stopping");
    }
    
    return false;
  }
}

// Status helper
function setStatus(type, message) {
  statusDiv.className = `status ${type}`;
  statusDiv.textContent = message;
  
  if (type === "success" || type === "error") {
    setTimeout(() => {
      statusDiv.className = "status";
      statusDiv.textContent = "";
    }, 3000);
  }
}

// ========== Phase 4A: Performance Tracking ==========

// View Performance button handler - now opens as overlay modal (like Log Trade)
viewPerformanceBtn.addEventListener("click", async () => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error("No active tab found");
    
    const contentScriptReady = await ensureContentScript(tab.id);
    if (!contentScriptReady) throw new Error("Failed to initialize");
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: "openPerformanceTab"
      });
    } catch (msgError) {
      console.log("Message sent (channel closed)");
    }
    
    setStatus("success", "Performance tab opened!");
    setTimeout(() => window.close(), 800);
  } catch (error) {
    console.error("Performance tab error:", error);
    setStatus("error", `Error: ${error.message}`);
  }
});

// Phase 4B.1: Open Dashboard in new tab
document.getElementById("openDashboard").addEventListener("click", () => {
  chrome.tabs.create({ url: "http://127.0.0.1:8765/static/dashboard.html" });
});

// Phase 5A: Open Teach Copilot as overlay modal (like Log Trade)
teachCopilotBtn.addEventListener("click", async () => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error("No active tab found");
    
    const contentScriptReady = await ensureContentScript(tab.id);
    if (!contentScriptReady) throw new Error("Failed to initialize");
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: "openTeachCopilot"
      });
    } catch (msgError) {
      console.log("Message sent (channel closed)");
    }
    
    setStatus("success", "Teach Copilot opened!");
    setTimeout(() => window.close(), 800);
  } catch (error) {
    console.error("Teach Copilot error:", error);
    setStatus("error", `Error: ${error.message}`);
  }
});

// Close Performance panel
closePerformanceBtn.addEventListener("click", () => {
  performancePanel.classList.add("hidden");
});

// Close Teach panel
closeTeachBtn.addEventListener("click", () => {
  teachPanel.classList.add("hidden");
});

/**
 * Render Teach Copilot panel UI (Phase 5A)
 */
async function renderTeachPanel() {
  console.log("[Popup] Rendering Teach Copilot panel...");
  
  teachContent.innerHTML = `
    <div id="teach-ui">
      <section id="trade-selection-section">
        <label for="teach-tradeSelect">Select Trade to Teach:</label>
        <select id="teach-tradeSelect">
          <option value="">-- Loading trades... --</option>
        </select>
        <div id="teach-tradeInfo" class="hidden"></div>
      </section>

      <section id="chart-section-teach">
        <div class="chart-label">📊 Chart Preview</div>
        <img id="teach-chartPreview" src="" alt="Chart Preview" style="width:100%; border:1px solid #333; border-radius:4px; display:none;">
      </section>

      <section id="lesson-section-teach">
        <textarea id="teach-lessonInput" placeholder="Explain the BOS and POI here..." style="width:100%; height:100px; margin-top:8px; background:#1e1e1e; color:#fff; border:1px solid #333; padding:8px; border-radius:4px; font-family:inherit;"></textarea>
        <div id="teach-controls" style="display:flex; gap:6px; margin-top:8px;">
          <button id="teach-voiceToggle" style="flex:1; background:#00b0ff; border:none; padding:8px; border-radius:4px; color:white; cursor:pointer;">🎙️ Voice</button>
          <button id="teach-saveLesson" style="flex:1; background:#00b0ff; border:none; padding:8px; border-radius:4px; color:white; cursor:pointer;">💾 Save Lesson</button>
          <button id="teach-getFeedback" style="flex:1; background:#00b0ff; border:none; padding:8px; border-radius:4px; color:white; cursor:pointer;">🧠 Get Feedback</button>
        </div>
      </section>

      <section id="teach-status" style="margin-top:8px; font-size:0.9em; color:#aaa; min-height:20px;">Initializing...</section>
    </div>
  `;
  
  // Wait for DOM to be ready
  await new Promise(resolve => {
    if (document.getElementById("teach-tradeSelect")) {
      resolve();
    } else {
      setTimeout(() => {
        const check = setInterval(() => {
          if (document.getElementById("teach-tradeSelect")) {
            clearInterval(check);
            resolve();
          }
        }, 50);
        setTimeout(() => clearInterval(check), 1000); // Max 1s wait
      }, 100);
    }
  });
  
  // Initialize Teach Copilot functionality
  console.log("[Popup] DOM ready, initializing Teach Copilot...");
  
  // Try both local and window scope
  const initFn = typeof initTeachCopilot !== 'undefined' ? initTeachCopilot : (typeof window !== 'undefined' && window.initTeachCopilot);
  console.log("[Popup] initTeachCopilot function available:", typeof initFn);
  
  if (!initFn) {
    console.error("[Popup] initTeachCopilot is not defined! teach_panel.js may not have loaded.");
    const statusEl = document.getElementById("teach-status");
    if (statusEl) {
      statusEl.textContent = "Error: Teach Copilot module not loaded. Please reload extension.";
      statusEl.className = "error";
    }
    return;
  }
  
  try {
    await initFn();
  } catch (error) {
    console.error("[Popup] Failed to initialize Teach Copilot:", error);
    const statusEl = document.getElementById("teach-status");
    if (statusEl) {
      statusEl.textContent = `Error: ${error.message}`;
      statusEl.className = "error";
    }
  }
}

// Render performance statistics with trade details
function renderPerformanceStats(stats, trades = []) {
  if (stats.total_trades === 0) {
    statsContent.innerHTML = `
      <div class="empty-state">
        <p>📊 No trades logged yet</p>
        <p class="empty-desc">Use the "📊 Log Trade" button in chat to start tracking your trades!</p>
      </div>
    `;
    return;
  }
  
  const winRate = stats.win_rate !== null ? `${stats.win_rate}%` : "N/A";
  const avgR = stats.avg_r !== null ? `${stats.avg_r}R` : "N/A";
  const profitFactor = stats.profit_factor !== null ? stats.profit_factor : "N/A";
  const totalR = stats.total_r !== null ? `${stats.total_r}R` : "N/A";
  
  // Determine win rate color
  let winRateClass = "neutral";
  if (stats.win_rate !== null) {
    if (stats.win_rate >= 60) winRateClass = "good";
    else if (stats.win_rate >= 50) winRateClass = "ok";
    else winRateClass = "bad";
  }
  
  // Determine profit factor color
  let pfClass = "neutral";
  if (stats.profit_factor !== null) {
    if (stats.profit_factor >= 2.0) pfClass = "good";
    else if (stats.profit_factor >= 1.5) pfClass = "ok";
    else pfClass = "bad";
  }
  
  statsContent.innerHTML = `
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Total Trades</div>
        <div class="stat-value">${stats.total_trades}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-label">Win Rate</div>
        <div class="stat-value ${winRateClass}">${winRate}</div>
        <div class="stat-breakdown">${stats.wins}W / ${stats.losses}L / ${stats.breakevens}BE</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-label">Avg R:R</div>
        <div class="stat-value">${avgR}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-label">Profit Factor</div>
        <div class="stat-value ${pfClass}">${profitFactor}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-label">Total R</div>
        <div class="stat-value ${stats.total_r > 0 ? 'good' : 'bad'}">${totalR}</div>
      </div>
    </div>
    
    <div class="stats-footer">
      <p class="stats-hint">💡 Use "📊 Log Trade" button for accurate logging!</p>
    </div>
  `;
  
  // Add trade details if available
  if (trades && trades.length > 0) {
    const tradesHTML = trades.map((trade) => {
      const outcomeClass = trade.outcome === 'win' ? 'good' : trade.outcome === 'loss' ? 'bad' : 'neutral';
      const outcomeIcon = trade.outcome === 'win' ? '✓' : trade.outcome === 'loss' ? '✗' : '⏳';
      const rr = trade.expected_r || trade.r_multiple || '-';
      const timestamp = new Date(trade.timestamp).toLocaleString();
      
      return `
        <div class="trade-item">
          <div class="trade-header">
            <span class="trade-symbol">${trade.symbol}</span>
            <span class="trade-outcome ${outcomeClass}">${outcomeIcon} ${trade.outcome || 'Pending'}</span>
          </div>
          <div class="trade-details-grid">
            <div><span class="label">Entry:</span> <strong>${trade.entry_price || 'N/A'}</strong></div>
            <div><span class="label">SL:</span> <strong>${trade.stop_loss || 'N/A'}</strong></div>
            <div><span class="label">TP:</span> <strong>${trade.take_profit || 'N/A'}</strong></div>
            <div><span class="label">R:R:</span> <strong>${rr}:1</strong></div>
          </div>
          <div class="trade-footer">
            <span class="trade-time">${timestamp}</span>
            <button class="trade-delete-btn" data-session-id="${trade.session_id}">🗑️ Delete</button>
          </div>
        </div>
      `;
    }).join('');
    
    statsContent.innerHTML += `
      <div class="trades-section">
        <h4 style="color: #ffd700; margin: 20px 0 12px 0;">📋 Trade History</h4>
        <div class="trades-list" id="trades-list">
          ${tradesHTML}
        </div>
      </div>
    `;
    
    // Add event delegation for delete buttons
    setTimeout(() => {
      const tradesList = document.getElementById('trades-list');
      if (tradesList) {
        tradesList.onclick = async (e) => {
          if (e.target.classList.contains('trade-delete-btn') || e.target.closest('.trade-delete-btn')) {
            const btn = e.target.closest('.trade-delete-btn') || e.target;
            const sessionId = btn.getAttribute('data-session-id');
            console.log('🗑️ Delete clicked via delegation:', sessionId);
            await deleteTrade(sessionId);
          }
        };
      }
    }, 100);
  }
}

// Delete trade function
async function deleteTrade(sessionId) {
  console.log('🗑️ Delete trade clicked:', sessionId);
  
  if (!confirm('Are you sure you want to delete this trade?')) {
    console.log('🗑️ Delete cancelled by user');
    return;
  }
  
  try {
    console.log('🗑️ Sending DELETE request...');
    const response = await fetch(`${window.API_BASE_URL}/performance/trades/${sessionId}`, {
      method: 'DELETE'
    });
    
    console.log('🗑️ Response status:', response.status);
    
    if (response.ok) {
      console.log('🗑️ Trade deleted successfully, reloading stats...');
      
      // Fetch and display updated stats
      const statsResponse = await fetch(`${window.API_BASE_URL}/performance/stats`);
      const stats = await statsResponse.json();
      
      const tradesResponse = await fetch(`${window.API_BASE_URL}/performance/all?limit=200`);
      const arr = await tradesResponse.json();
      renderPerformanceStats(stats, Array.isArray(arr) ? arr : []);
      
      alert('✅ Trade deleted successfully!');
    } else {
      const errorText = await response.text();
      console.error('🗑️ Delete failed:', errorText);
      alert('Failed to delete trade: ' + errorText);
    }
  } catch (error) {
    console.error('🗑️ Delete error:', error);
    alert('Error deleting trade: ' + error.message);
  }
}
