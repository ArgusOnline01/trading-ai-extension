// Visual Trade Copilot - Popup Script (Phase 3B.1: Redesigned UI)
// Handles quick actions and model selection

const API_BASE_URL = "http://127.0.0.1:8765";

// DOM Elements
const newConversationBtn = document.getElementById("newConversation");
const toggleChatBtn = document.getElementById("toggleChat");
const viewSessionsBtn = document.getElementById("viewSessions");
const viewPerformanceBtn = document.getElementById("viewPerformance");
const quickAnalyzeBtn = document.getElementById("quickAnalyze");
const performancePanel = document.getElementById("performancePanel");
const closePerformanceBtn = document.getElementById("closePerformance");
const statsContent = document.getElementById("statsContent");
const statusDiv = document.getElementById("status");
const serverIndicator = document.getElementById("server-indicator");
const serverText = document.getElementById("server-text");
const modelOptions = document.querySelectorAll(".model-option");

// Selected model state
let selectedModel = "fast"; // GPT-5 Chat (native vision)

// Check server status on popup open
checkServerStatus();

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
  try {
    const response = await fetch(`${API_BASE_URL}/`, {
      method: "GET",
      signal: AbortSignal.timeout(3000)
    });
    
    if (response.ok) {
      serverIndicator.classList.add("online");
      serverIndicator.classList.remove("offline");
      serverText.textContent = "Server online";
    } else {
      throw new Error("Server not responding");
    }
  } catch (error) {
    serverIndicator.classList.add("offline");
    serverIndicator.classList.remove("online");
    serverText.textContent = "Server offline";
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

// View Performance button handler
viewPerformanceBtn.addEventListener("click", async () => {
  try {
    performancePanel.classList.remove("hidden");
    statsContent.innerHTML = '<div class="loading">Loading performance stats...</div>';
    
    // Fetch stats and trades from backend
    const [statsRes, tradesRes] = await Promise.all([
      fetch(`${API_BASE_URL}/performance/stats`),
      fetch(`${API_BASE_URL}/performance/trades`)
    ]);
    
    if (!statsRes.ok) throw new Error("Failed to fetch stats");
    
    const stats = await statsRes.json();
    let trades = [];
    
    if (tradesRes.ok) {
      const tradesData = await tradesRes.json();
      trades = tradesData.trades || tradesData || [];
    }
    
    // Render stats with trade details
    renderPerformanceStats(stats, trades);
  } catch (error) {
    console.error("Performance stats error:", error);
    statsContent.innerHTML = `<div class="error">Error loading stats: ${error.message}</div>`;
  }
});

// Phase 4B.1: Open Dashboard in new tab
document.getElementById("openDashboard").addEventListener("click", () => {
  chrome.tabs.create({ url: "http://127.0.0.1:8765/static/dashboard.html" });
});

// Close Performance panel
closePerformanceBtn.addEventListener("click", () => {
  performancePanel.classList.add("hidden");
});

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
    const response = await fetch(`${API_BASE_URL}/performance/trades/${sessionId}`, {
      method: 'DELETE'
    });
    
    console.log('🗑️ Response status:', response.status);
    
    if (response.ok) {
      console.log('🗑️ Trade deleted successfully, reloading stats...');
      
      // Fetch and display updated stats
      const statsResponse = await fetch(`${API_BASE_URL}/performance/stats`);
      const stats = await statsResponse.json();
      
      const tradesResponse = await fetch(`${API_BASE_URL}/performance/trades`);
      const tradesData = await tradesResponse.json();
      
      renderPerformanceStats(stats, tradesData.trades || []);
      
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
