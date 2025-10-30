// Visual Trade Copilot - Content Script (Phase 3B: Multi-Session Memory)
// Persistent chat panel with multi-session support and context tracking

// Wait for IDB to be loaded
let idbReadyPromise = new Promise((resolve) => {
  // Phase 4A: Check for both session AND performance functions
  const checkFullyLoaded = () => {
    return window.IDB && 
           window.IDB.openDB && 
           window.IDB.savePerformanceLog && 
           window.IDB.getPerformanceLogs;
  };
  
  if (checkFullyLoaded()) {
    console.log("✅ IDB already loaded (including Phase 4A performance functions)");
    resolve();
  } else {
    console.log("⏳ Waiting for IDB to load (including Phase 4A)...");
    const checkIDB = setInterval(() => {
      if (checkFullyLoaded()) {
        console.log("✅ IDB fully loaded (Phase 3B + 4A)");
        clearInterval(checkIDB);
        resolve();
      }
    }, 100);
    
    // Timeout after 5 seconds
    setTimeout(() => {
      clearInterval(checkIDB);
      if (!checkFullyLoaded()) {
        console.error("❌ IDB failed to fully load after 5 seconds. Available:", Object.keys(window.IDB || {}));
      }
      resolve();
    }, 5000);
  }
});

let chatHistory = [];
let chatContainer = null;
let currentSession = null;
let sessionManagerModal = null;
let selectedModel = "fast"; // Phase 4A.1: Default GPT-5 Chat (native vision)

// ========== Session Management ==========

/**
 * Initialize or load the active session
 */
async function initializeSession() {
  try {
    // Wait for IDB to be ready
    await idbReadyPromise;
    
    // Make sure IDB is available
    if (!window.IDB) {
      throw new Error("IndexedDB helper not loaded");
    }
    
    currentSession = await window.IDB.getActiveSession();
    
    if (!currentSession) {
      console.error("❌ Failed to get session, creating default...");
      currentSession = await window.IDB.createSession("CHART", "Default Session");
    }
    
    console.log("🧠 Active session loaded:", currentSession.sessionId);
    
    // Load messages for this session
    chatHistory = await window.IDB.loadMessages(currentSession.sessionId);
    console.log("📚 Loaded", chatHistory.length, "messages from IndexedDB");
    
    // Update UI
    renderMessages();
    updateSessionStatus();
    
    return currentSession;
  } catch (error) {
    console.error("Failed to initialize session:", error);
    showNotification("Error loading session: " + error.message, "error");
    
    // Fallback: create minimal session object
    currentSession = {
      sessionId: `FALLBACK-${Date.now()}`,
      symbol: "CHART",
      title: "Fallback Session",
      created_at: Date.now(),
      last_updated: Date.now(),
      context: {}
    };
    chatHistory = [];
    return currentSession;
  }
}

/**
 * Switch to a different session
 */
async function switchSession(sessionId) {
  try {
    const session = await window.IDB.getSession(sessionId);
    if (!session) {
      throw new Error("Session not found");
    }
    
    currentSession = session;
    chatHistory = await window.IDB.loadMessages(sessionId);
    
    renderMessages();
    updateSessionStatus();
    
    showNotification(`🧠 Loaded ${session.symbol} session`, "success");
    
    // Close session manager if open
    if (sessionManagerModal) {
      closeSessionManager();
    }
  } catch (error) {
    console.error("Failed to switch session:", error);
    showNotification("Error switching session", "error");
  }
}

/**
 * Create a new session
 */
async function createNewSession() {
  const symbol = prompt("Enter symbol (e.g., 6EZ25, ES, BTC):");
  if (!symbol || !symbol.trim()) {
    return;
  }
  
  try {
    const session = await window.IDB.createSession(symbol.trim());
    await switchSession(session.sessionId);
    showNotification(`✅ Created ${session.symbol} session`, "success");
  } catch (error) {
    console.error("Failed to create session:", error);
    showNotification("Error creating session", "error");
  }
}

/**
 * Delete a session with confirmation
 */
async function deleteSessionWithConfirm(sessionId) {
  const session = await window.IDB.getSession(sessionId);
  if (!session) return;
  
  const confirmed = confirm(`Delete "${session.title}" (${session.symbol})?\n\nThis will permanently remove all messages in this session.`);
  if (!confirmed) return;
  
  try {
    await window.IDB.deleteSession(sessionId);
    
    // If deleting current session, switch to another or create new
    if (currentSession && currentSession.sessionId === sessionId) {
      const sessions = await window.IDB.getAllSessions();
      if (sessions.length > 0) {
        await switchSession(sessions[0].sessionId);
      } else {
        // Create default session
        const newSession = await window.IDB.createSession("CHART", "Default Session");
        await switchSession(newSession.sessionId);
      }
    }
    
    showNotification("✅ Session deleted", "success");
    
    // Refresh session manager if open
    if (sessionManagerModal) {
      await renderSessionManager();
    }
  } catch (error) {
    console.error("Failed to delete session:", error);
    showNotification("Error deleting session", "error");
  }
}

/**
 * Export current session
 */
async function exportCurrentSession() {
  if (!currentSession) {
    showNotification("No active session", "error");
    return;
  }
  
  try {
    const data = await window.IDB.exportSession(currentSession.sessionId);
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vtc-${currentSession.symbol}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    showNotification("💾 Session exported", "success");
  } catch (error) {
    console.error("Failed to export session:", error);
    showNotification("Error exporting session", "error");
  }
}

/**
 * Clear messages in current session
 */
async function clearCurrentSession() {
  if (!currentSession) return;
  
  const confirmed = confirm(`Clear all messages in "${currentSession.title}"?\n\nThe session will remain but all conversation history will be deleted.`);
  if (!confirmed) return;
  
  try {
    await window.IDB.clearSessionMessages(currentSession.sessionId);
    chatHistory = [];
    renderMessages();
    showNotification("✅ Messages cleared", "success");
  } catch (error) {
    console.error("Failed to clear messages:", error);
    showNotification("Error clearing messages", "error");
  }
}

/**
 * Update context for current session
 * Extracts trading context from messages automatically
 */
async function updateSessionContext() {
  if (!currentSession || chatHistory.length === 0) return;
  
  try {
    // Extract context from recent messages
    const recentMessages = chatHistory.slice(-10);
    const context = { ...currentSession.context };
    
    // Look for price mentions, bias, POIs in assistant messages
    for (const msg of recentMessages) {
      if (msg.role === "assistant") {
        const content = msg.content.toLowerCase();
        
        // Extract bias
        if (content.includes("bullish")) context.bias = "bullish";
        else if (content.includes("bearish")) context.bias = "bearish";
        
        // Extract price patterns (e.g., "1.1674", "$50,000")
        const priceMatch = content.match(/(\$?[\d,]+\.?\d*)/);
        if (priceMatch) {
          context.latest_price = priceMatch[1];
        }
        
        // Extract POI mentions
        if (content.includes("poi") || content.includes("point of interest")) {
          const poiMatch = content.match(/(\d+\.?\d*[\s–-]+\d+\.?\d*)/);
          if (poiMatch) {
            context.last_poi = poiMatch[1];
          }
        }
      }
    }
    
    // Update session with new context
    await window.IDB.updateSession(currentSession.sessionId, { context });
    currentSession.context = context;
    
  } catch (error) {
    console.error("Failed to update context:", error);
  }
}

// ========== Session Manager UI ==========

/**
 * Show session manager modal
 */
async function showSessionManager() {
  if (sessionManagerModal) {
    sessionManagerModal.classList.add("vtc-modal-visible");
    return;
  }
  
  await renderSessionManager();
}

/**
 * Render the session manager modal
 */
async function renderSessionManager() {
  const sessions = await window.IDB.getAllSessions();
  console.log(`[Session Manager] Found ${sessions.length} sessions:`, sessions.map(s => s.title));
  
  if (!sessionManagerModal) {
    sessionManagerModal = document.createElement("div");
    sessionManagerModal.id = "vtc-session-manager";
    sessionManagerModal.className = "vtc-modal";
    document.body.appendChild(sessionManagerModal);
  }
  
  sessionManagerModal.innerHTML = `
    <div class="vtc-modal-content">
      <div class="vtc-modal-header">
        <h3>🗂️ Session Manager</h3>
        <button class="vtc-close-modal" title="Close">✖️</button>
      </div>
      <div class="vtc-modal-body">
        <button id="vtc-new-session" class="vtc-btn-primary">➕ New Session</button>
        <div class="vtc-sessions-list">
          ${sessions.map(session => `
            <div class="vtc-session-item ${currentSession && currentSession.sessionId === session.sessionId ? 'active' : ''}" data-session-id="${session.sessionId}">
              <div class="vtc-session-info">
                <div class="vtc-session-symbol">${session.symbol}</div>
                <div class="vtc-session-title">${session.title}</div>
                <div class="vtc-session-meta">
                  ${formatTimestamp(session.last_updated)} • 
                  <span class="vtc-session-stats" data-session-id="${session.sessionId}">...</span>
                </div>
              </div>
              <div class="vtc-session-actions">
                <button class="vtc-session-load" data-session-id="${session.sessionId}" title="Load">📂</button>
                <button class="vtc-session-export" data-session-id="${session.sessionId}" title="Export">💾</button>
                <button class="vtc-session-delete" data-session-id="${session.sessionId}" title="Delete">🗑️</button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  `;
  
  // Attach event listeners
  sessionManagerModal.querySelector(".vtc-close-modal").onclick = closeSessionManager;
  sessionManagerModal.querySelector("#vtc-new-session").onclick = createNewSession;
  
  // Load session stats asynchronously
  sessions.forEach(async (session) => {
    const stats = await window.IDB.getSessionStats(session.sessionId);
    const statsEl = sessionManagerModal.querySelector(`.vtc-session-stats[data-session-id="${session.sessionId}"]`);
    if (statsEl) {
      statsEl.textContent = `${stats.total_messages} messages`;
    }
  });
  
  // Session action buttons
  sessionManagerModal.querySelectorAll(".vtc-session-load").forEach(btn => {
    btn.onclick = () => switchSession(btn.dataset.sessionId);
  });
  
  sessionManagerModal.querySelectorAll(".vtc-session-export").forEach(btn => {
    btn.onclick = async () => {
      try {
        const data = await window.IDB.exportSession(btn.dataset.sessionId);
        const session = await window.IDB.getSession(btn.dataset.sessionId);
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `vtc-${session.symbol}-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showNotification("💾 Session exported", "success");
      } catch (error) {
        showNotification("Export failed", "error");
      }
    };
  });
  
  sessionManagerModal.querySelectorAll(".vtc-session-delete").forEach(btn => {
    btn.onclick = () => deleteSessionWithConfirm(btn.dataset.sessionId);
  });
  
  // Show modal
  sessionManagerModal.classList.add("vtc-modal-visible");
}

/**
 * Close session manager modal
 */
function closeSessionManager() {
  if (sessionManagerModal) {
    sessionManagerModal.classList.remove("vtc-modal-visible");
  }
}

/**
 * Update session status display in chat header
 */
function updateSessionStatus() {
  const statusEl = document.getElementById("vtc-session-status");
  if (!statusEl) {
    console.log("⏳ Session status element not ready yet");
    return;
  }
  
  if (!currentSession) {
    statusEl.textContent = "🧠 Loading...";
    statusEl.title = "Initializing session";
    statusEl.style.cursor = "default";
    return;
  }
  
  const sessionTitle = currentSession.title || currentSession.symbol;
  statusEl.textContent = `🧠 ${sessionTitle}`;
  statusEl.title = "Click to rename session";
  statusEl.style.cursor = "pointer";
  
  // Add click handler for renaming (only add once)
  if (!statusEl.hasRenameHandler) {
    statusEl.onclick = () => renameSession();
    statusEl.hasRenameHandler = true;
  }
}

/**
 * Rename the current session
 */
async function renameSession() {
  if (!currentSession) return;
  
  const newTitle = prompt(`Rename session "${currentSession.title || currentSession.symbol}":`, currentSession.title || currentSession.symbol);
  
  if (newTitle && newTitle.trim() && newTitle !== currentSession.title) {
    try {
      // Update in IndexedDB
      await window.IDB.updateSession(currentSession.sessionId, { title: newTitle.trim() });
      
      // Update local state
      currentSession.title = newTitle.trim();
      
      // Update UI
      updateSessionStatus();
      
      showNotification(`Renamed to "${newTitle.trim()}"`, "success");
    } catch (error) {
      console.error("Failed to rename session:", error);
      showNotification("Error renaming session: " + error.message, "error");
    }
  }
}

// ========== Chat UI Functions ==========

/**
 * Create or get the chat panel
 */
function ensureChatUI() {
  if (!chatContainer) {
    chatContainer = document.createElement("div");
    chatContainer.id = "vtc-chat";
    chatContainer.className = "vtc-chat-panel";
    
    // Phase 3C: Set default width (balanced size to avoid covering chart prices)
    chatContainer.style.width = "620px";
    
    chatContainer.innerHTML = `
      <div class="vtc-resize-handle vtc-resize-top"></div>
      <div class="vtc-resize-handle vtc-resize-bottom"></div>
      <div class="vtc-resize-handle vtc-resize-left"></div>
      <div class="vtc-resize-handle vtc-resize-right"></div>
      <div class="vtc-resize-handle vtc-resize-topleft"></div>
      <div class="vtc-resize-handle vtc-resize-topright"></div>
      <div class="vtc-resize-handle vtc-resize-bottomleft"></div>
      <div class="vtc-resize-handle vtc-resize-bottomright"></div>
      
      <div id="vtc-header" class="vtc-header">
        <div class="vtc-title">
          <span class="vtc-icon" title="Drag to move">🤖</span>
          <h3>Visual Trade Copilot</h3>
          <span id="vtc-session-status" class="vtc-session-badge">🧠 Loading...</span>
              <select id="vtc-model-selector" class="vtc-model-selector" title="Select AI Model">
                <optgroup label="Recommended Models">
                  <option value="fast" selected>⚡ Fast (GPT-5 Chat) 👁️</option>
                  <option value="balanced">⚖️ Balanced (GPT-5 Search) 🧠</option>
                  <option value="advanced">🔷 Advanced (GPT-4o) 👁️</option>
                </optgroup>
                 <optgroup label="Alternative Models">
                   <option value="gpt4o-mini">💎 GPT-4o Mini (Budget)</option>
                   <option value="gpt5-mini">⚠️ GPT-5 Mini (Limited)</option>
                 </optgroup>
                 <optgroup label="All Available Models">
                   <option value="gpt-5-chat-latest">GPT-5 Chat Latest (Vision)</option>
                   <option value="gpt-5-search-api-2025-10-14">GPT-5 Search API (Hybrid)</option>
                   <option value="gpt-5-mini">GPT-5 Mini (Has Issues)</option>
                   <option value="gpt-4o">GPT-4o (Vision)</option>
                   <option value="gpt-4o-mini">GPT-4o Mini (Vision)</option>
                 </optgroup>
               </select>
        </div>
        <div id="vtc-controls" class="vtc-controls">
          <button id="sessionManager" title="Session Manager" class="vtc-control-btn">🗂️</button>
          <button id="exportChat" title="Export Session" class="vtc-control-btn">💾</button>
          <button id="clearChat" title="Clear Messages" class="vtc-control-btn">🗑️</button>
          <button id="resetSize" title="Reset Size" class="vtc-control-btn">⬜</button>
          <button id="minimizeChat" title="Minimize" class="vtc-control-btn">➖</button>
          <button id="closeChat" title="Close" class="vtc-control-btn">✖️</button>
        </div>
      </div>
      <div id="vtc-messages" class="vtc-messages"></div>
      <div id="vtc-input-area" class="vtc-input-area">
        <textarea id="vtc-input" class="vtc-input" placeholder="Ask a follow-up question..." rows="2"></textarea>
        <div class="vtc-send-controls">
          <button id="vtc-send-text" class="vtc-btn-text" title="Send text-only (fast, cheaper)">📝 Text</button>
          <button id="vtc-send-image" class="vtc-btn-image" title="Analyze chart with image (slower, more expensive)">📸 Chart</button>
          <button id="vtc-upload-image" class="vtc-btn-upload" title="Upload saved screenshot">📤 Upload</button>
          <button id="vtc-log-trade" class="vtc-btn-log" title="Smart trade logging with AI extraction">📊 Log Trade</button>
        </div>
        <input type="file" id="vtc-file-input" accept="image/*" style="display: none;" />
      </div>
      <div id="vtc-footer" class="vtc-footer">
        <span id="vtc-message-count">0 messages</span>
        <span id="vtc-status">Ready</span>
      </div>
    `;
    
    // Phase 4A.1: Trade logging confirmation modal
    const tradeLogModal = document.createElement('div');
    tradeLogModal.id = 'vtc-trade-log-modal';
    tradeLogModal.className = 'vtc-modal';
    tradeLogModal.style.display = 'none';
    tradeLogModal.innerHTML = `
      <div class="vtc-modal-content vtc-trade-log-content">
        <div class="vtc-modal-header">
          <h3>📊 Log Trade</h3>
          <button class="vtc-close-modal" id="vtc-close-trade-log">✕</button>
        </div>
        <div class="vtc-modal-body">
          <p class="vtc-log-hint">Review and edit the extracted values:</p>
          <form id="vtc-trade-log-form" class="vtc-trade-form">
            <div class="vtc-form-row">
              <label>Symbol:</label>
              <input type="text" id="log-symbol" placeholder="e.g., EURUSD, GC" required />
            </div>
            <div class="vtc-form-row">
              <label>Entry Price:</label>
              <input type="number" id="log-entry" step="0.00001" placeholder="e.g., 1.0850" required />
            </div>
            <div class="vtc-form-row">
              <label>Stop Loss:</label>
              <input type="number" id="log-stop" step="0.00001" placeholder="e.g., 1.0800" required />
            </div>
            <div class="vtc-form-row">
              <label>Take Profit:</label>
              <input type="number" id="log-tp" step="0.00001" placeholder="e.g., 1.0950" required />
            </div>
            <div class="vtc-form-row">
              <label>Bias:</label>
              <select id="log-bias" required>
                <option value="bullish">Bullish (Long)</option>
                <option value="bearish">Bearish (Short)</option>
              </select>
            </div>
            <div class="vtc-form-row">
              <label>Setup Type:</label>
              <input type="text" id="log-setup" placeholder="e.g., FVG, Liquidity Grab, BOS" />
            </div>
            <div class="vtc-form-row">
              <label>Timeframe:</label>
              <select id="log-timeframe">
                <option value="1m">1 Minute</option>
                <option value="5m" selected>5 Minutes</option>
                <option value="15m">15 Minutes</option>
                <option value="1h">1 Hour</option>
                <option value="4h">4 Hours</option>
                <option value="1d">1 Day</option>
              </select>
            </div>
            <div class="vtc-form-row vtc-form-full">
              <label>AI Analysis:</label>
              <textarea id="log-ai-verdict" rows="3" readonly style="background: #1a1a1a; color: #00ff99;"></textarea>
            </div>
            <div class="vtc-form-stats">
              <div class="vtc-stat-item">
                <span class="vtc-stat-label">Risk:</span>
                <span class="vtc-stat-value" id="log-risk">-</span>
              </div>
              <div class="vtc-stat-item">
                <span class="vtc-stat-label">Reward:</span>
                <span class="vtc-stat-value" id="log-reward">-</span>
              </div>
              <div class="vtc-stat-item">
                <span class="vtc-stat-label">Expected R:R:</span>
                <span class="vtc-stat-value" id="log-rr">-</span>
              </div>
            </div>
            <div class="vtc-form-divider" style="border-top: 1px solid #333; margin: 16px 0; padding-top: 16px;">
              <p style="color: #ffd700; font-size: 14px; margin-bottom: 12px;">📈 Trade Outcome (Optional - can update later)</p>
            </div>
            <div class="vtc-form-row">
              <label>Outcome:</label>
              <select id="log-outcome">
                <option value="pending">⏳ Pending (Still Open)</option>
                <option value="win">✓ Win</option>
                <option value="loss">✗ Loss</option>
                <option value="breakeven">≈ Breakeven</option>
              </select>
            </div>
            <div class="vtc-form-row" id="log-actual-r-row" style="display: none;">
              <label>Actual R-Multiple:</label>
              <input type="number" id="log-actual-r" step="0.1" placeholder="e.g., 2.5 (if win) or -1.0 (if loss)" />
            </div>
            <div class="vtc-form-actions">
              <button type="button" class="vtc-btn-secondary" id="vtc-cancel-log">Cancel</button>
              <button type="submit" class="vtc-btn-primary">✓ Save Trade</button>
            </div>
          </form>
        </div>
      </div>
    `;
    document.body.appendChild(tradeLogModal);
    
    document.body.appendChild(chatContainer);
    
    // Attach event listeners
    document.getElementById("sessionManager").onclick = showSessionManager;
    document.getElementById("clearChat").onclick = clearCurrentSession;
    document.getElementById("exportChat").onclick = exportCurrentSession;
    document.getElementById("resetSize").onclick = resetChatSize;
    document.getElementById("minimizeChat").onclick = toggleMinimize;
    document.getElementById("closeChat").onclick = () => {
      chatContainer.classList.add("vtc-closing");
      setTimeout(() => {
        chatContainer.remove();
        chatContainer = null;
      }, 300);
    };
    
    // Phase 3B.2: Model selector event listener
    document.getElementById("vtc-model-selector").onchange = (e) => {
      selectedModel = e.target.value;
      const modelText = e.target.options[e.target.selectedIndex].text.trim();
      console.log(`[MODEL SWITCH] Selected: ${selectedModel} (${modelText})`);
      showNotification(`Model: ${modelText}`, "success");
    };
    
    // Phase 3B.1: Dual-send functionality (text-only vs. image)
    const sendTextBtn = document.getElementById("vtc-send-text");
    const sendImageBtn = document.getElementById("vtc-send-image");
    const input = document.getElementById("vtc-input");
    
    /**
     * Universal send function for both text and image modes
     * @param {boolean} includeImage - Whether to capture and include chart image
     */
    async function sendMessage(includeImage) {
      const question = input.value.trim();
      if (!question) {
        showNotification("Please enter a question first", "error");
        return;
      }
      
      // NEW: Copilot intent intercept
      const localCopilotReply = await handleCopilotIntent(question);
      if (localCopilotReply) {
        // Mimic assistant reply - save and render
        await window.IDB.saveMessage(currentSession.sessionId, "user", question);
        await window.IDB.saveMessage(currentSession.sessionId, "assistant", localCopilotReply);
        chatHistory = await window.IDB.loadMessages(currentSession.sessionId);
        renderMessages();
        input.value = "";
        showNotification("Answered instantly from Copilot Bridge!", "success");
        return;
      }
      
      // Disable both buttons and show loading
      sendTextBtn.disabled = true;
      sendImageBtn.disabled = true;
      const activeBtn = includeImage ? sendImageBtn : sendTextBtn;
      const originalText = activeBtn.textContent;
      activeBtn.textContent = "⏳";
      
      const notificationMsg = includeImage ? "Capturing chart..." : "Sending...";
      showNotification(notificationMsg, "info");
      
      try {
        // Apply context summarization if needed (Phase 3B.1)
        let contextToSend = chatHistory.map(msg => ({ role: msg.role, content: msg.content }));
        const estimatedTokens = estimateTokens(contextToSend);
        
        if (estimatedTokens > 7000) {
          console.log(`[Token Optimization] ${estimatedTokens} tokens, applying summarization`);
          contextToSend = summarizeContext(contextToSend);
          console.log(`[Token Optimization] Reduced to ${estimateTokens(contextToSend)} tokens`);
        }
        
        // Request chart capture from background/popup (Phase 3B.2: with model selection)
        const response = await chrome.runtime.sendMessage({
          action: "captureAndAnalyze",
          question: question,
          sessionId: currentSession.sessionId,
          includeImage: includeImage,  // Phase 3B.1: text-only mode flag
          model: selectedModel,  // Phase 3B.2: Send selected model
          context: contextToSend,
          uploadedImage: uploadedImageData  // Phase 4A.1: Pre-uploaded image data
        });
        
        if (response && response.success) {
          // Message will be added via showOverlay action
          input.value = "";
          showNotification("Analysis complete!", "success");
          
          // Phase 4A.1: Clear uploaded image and reset button
          if (uploadedImageData) {
            uploadedImageData = null;
            uploadBtn.textContent = "📤 Upload";
            uploadBtn.style.background = "";
            fileInput.value = "";
          }
          
          // Phase 3C: Detect hybrid mode
          // Note: "balanced" is now GPT-5 Search (hybrid), "advanced" is GPT-4o (native vision)
          const textOnlyModels = ["balanced", "gpt5-mini", "gpt-5-mini", "gpt-5-mini-2025-08-07", "gpt-5-search-api", "gpt-5-search-api-2025-10-14"];
          const hybridMode = includeImage && textOnlyModels.includes(selectedModel);
          
          // Update debug overlay (Phase 3C: with hybrid mode support)
          updateDebugOverlay({ includeImage, tokens: estimateTokens(contextToSend), hybridMode });
        } else {
          throw new Error(response?.error || "Analysis failed");
        }
      } catch (error) {
        console.error("Send error:", error);
        showNotification("Error: " + error.message, "error");
      } finally {
        sendTextBtn.disabled = false;
        sendImageBtn.disabled = false;
        activeBtn.textContent = originalText;
      }
    }
    
    // Text-only send button (Phase 3B.1)
    sendTextBtn.onclick = () => sendMessage(false);
    
    // Image send button (Phase 3B.1)
    sendImageBtn.onclick = () => sendMessage(true);
    
    // Phase 4A.1: Upload image button
    const uploadBtn = document.getElementById("vtc-upload-image");
    const fileInput = document.getElementById("vtc-file-input");
    let uploadedImageData = null;
    
    uploadBtn.onclick = () => {
      fileInput.click();
    };
    
    fileInput.onchange = (e) => {
      const file = e.target.files[0];
      if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          uploadedImageData = event.target.result.split(',')[1]; // Base64 without prefix
          showNotification(`📤 Image loaded: ${file.name}`, "success");
          uploadBtn.textContent = "✅ Ready";
          uploadBtn.style.background = "linear-gradient(135deg, #10b981 0%, #059669 100%)";
        };
        reader.readAsDataURL(file);
      }
    };
    
    // Phase 4A.1: Log Trade button - smart extraction with confirmation
    const logTradeBtn = document.getElementById("vtc-log-trade");
    
    logTradeBtn.onclick = async () => {
      console.log("📊 [Log Trade] Button clicked");
      
      // Check if image is uploaded
      if (!uploadedImageData) {
        console.warn("📊 [Log Trade] No image uploaded");
        showNotification("📤 Please upload a chart image first", "error");
        return;
      }
      
      console.log("📊 [Log Trade] Image found, starting extraction...");
      logTradeBtn.disabled = true;
      logTradeBtn.textContent = "⏳ Extracting...";
      
      try {
        // Send structured extraction prompt to GPT
        const extractionPrompt = `IMPORTANT: Respond with ONLY a JSON object, nothing else. No markdown, no explanation.

Extract these values from the chart:
{
  "symbol": "ticker symbol (e.g., CL, GC, EURUSD, NQ)",
  "entry_price": 12345.67,
  "stop_loss": 12300.00,
  "take_profit": 12450.00,
  "bias": "bullish",
  "setup_type": "Supply/Demand",
  "timeframe": "5m",
  "analysis": "Brief analysis"
}

Extract visible price levels. Response must be ONLY the JSON object above with your values.`;
        
        const response = await chrome.runtime.sendMessage({
          action: "captureAndAnalyze",
          question: extractionPrompt,
          sessionId: currentSession.sessionId,
          includeImage: true,
          model: "fast", // Use GPT-5 Chat for fast extraction
          uploadedImage: uploadedImageData,
          forLogTrade: true // Phase 4A.2: Get direct response, not via showOverlay
        });
        
        if (response && response.success) {
          console.log("📊 [Log Trade] ✅ Got AI response");
          
          // Parse JSON from AI response
          const aiAnswer = response.answer || "";
          console.log("📊 [Log Trade] Full AI Answer Length:", aiAnswer.length);
          console.log("📊 [Log Trade] AI Answer Preview:", aiAnswer.substring(0, 500));
          console.log("📊 [Log Trade] Response object keys:", Object.keys(response));
          
          let extractedData = null;
          
          // Try to parse the entire response as JSON first
          try {
            extractedData = JSON.parse(aiAnswer);
            console.log("📊 [Log Trade] ✅ Parsed entire response as JSON:", extractedData);
          } catch (e) {
            console.log("📊 [Log Trade] Not pure JSON, trying pattern matching...");
            
            // Try multiple JSON extraction methods
            // Method 1: Find JSON object with proper keys (greedy match)
            let jsonMatch = aiAnswer.match(/\{[\s\S]*"symbol"[\s\S]*"entry_price"[\s\S]*\}/);
            
            if (!jsonMatch) {
              // Method 2: Find any JSON object
              jsonMatch = aiAnswer.match(/\{[^{}]*"entry_price"[^{}]*\}/);
            }
            
            if (!jsonMatch) {
              // Method 3: Get everything between first { and last }
              const firstBrace = aiAnswer.indexOf('{');
              const lastBrace = aiAnswer.lastIndexOf('}');
              if (firstBrace !== -1 && lastBrace !== -1) {
                jsonMatch = [aiAnswer.substring(firstBrace, lastBrace + 1)];
              }
            }
            
            if (jsonMatch) {
              try {
                // Clean the JSON string (remove markdown code blocks if any)
                let jsonStr = jsonMatch[0].replace(/```json|```/g, '').trim();
                console.log("📊 [Log Trade] Trying to parse:", jsonStr.substring(0, 200));
                extractedData = JSON.parse(jsonStr);
                console.log("📊 [Log Trade] ✅ Extracted JSON:", extractedData);
              } catch (parseError) {
                console.warn("📊 [Log Trade] ⚠️ Failed to parse JSON:", parseError);
                console.warn("📊 [Log Trade] JSON string was:", jsonMatch[0]);
              }
            } else {
              console.warn("📊 [Log Trade] ⚠️ No JSON found in response");
              console.warn("📊 [Log Trade] Full response:", aiAnswer);
            }
          }
          
          // Open modal with extracted or default values
          console.log("📊 [Log Trade] Opening modal...");
          openTradeLogModal(extractedData, aiAnswer);
        } else {
          throw new Error(response?.error || "Extraction failed");
        }
      } catch (error) {
        console.error("Log trade error:", error);
        showNotification("⚠️ Extraction failed: " + error.message, "error");
      } finally {
        logTradeBtn.disabled = false;
        logTradeBtn.textContent = "📊 Log Trade";
      }
    };
    
    // Phase 4A.1: Open trade log modal with extracted data
    function openTradeLogModal(extractedData, aiAnalysis) {
      console.log("📊 [Modal] Opening modal with data:", extractedData);
      
      const modal = document.getElementById("vtc-trade-log-modal");
      const form = document.getElementById("vtc-trade-log-form");
      
      if (!modal) {
        console.error("📊 [Modal] ❌ Modal element not found!");
        showNotification("⚠️ Modal not found - please reload extension", "error");
        return;
      }
      
      console.log("📊 [Modal] Pre-filling form...");
      
      // Pre-fill form with extracted or session data
      document.getElementById("log-symbol").value = extractedData?.symbol || currentSession?.symbol || "";
      document.getElementById("log-entry").value = extractedData?.entry_price || "";
      document.getElementById("log-stop").value = extractedData?.stop_loss || "";
      document.getElementById("log-tp").value = extractedData?.take_profit || "";
      document.getElementById("log-bias").value = extractedData?.bias || "bullish";
      document.getElementById("log-setup").value = extractedData?.setup_type || "";
      document.getElementById("log-timeframe").value = extractedData?.timeframe || currentSession?.context?.timeframe || "5m";
      document.getElementById("log-ai-verdict").value = extractedData?.analysis || aiAnalysis.substring(0, 200) || "";
      
      // Calculate R:R in real-time
      const updateRR = () => {
        const entry = parseFloat(document.getElementById("log-entry").value);
        const stop = parseFloat(document.getElementById("log-stop").value);
        const tp = parseFloat(document.getElementById("log-tp").value);
        
        if (entry && stop && tp) {
          const risk = Math.abs(entry - stop);
          const reward = Math.abs(tp - entry);
          const rr = risk > 0 ? (reward / risk).toFixed(2) : 0;
          
          document.getElementById("log-risk").textContent = risk.toFixed(5);
          document.getElementById("log-reward").textContent = reward.toFixed(5);
          document.getElementById("log-rr").textContent = rr + ":1";
          document.getElementById("log-rr").style.color = rr >= 2 ? "#00ff99" : rr >= 1 ? "#ffd700" : "#ff4444";
        }
      };
      
      // Update R:R on input change
      ["log-entry", "log-stop", "log-tp"].forEach(id => {
        document.getElementById(id).oninput = updateRR;
      });
      
      // Show/hide actual R field based on outcome
      document.getElementById("log-outcome").onchange = (e) => {
        const actualRRow = document.getElementById("log-actual-r-row");
        if (e.target.value !== "pending") {
          actualRRow.style.display = "flex";
        } else {
          actualRRow.style.display = "none";
        }
      };
      
      updateRR(); // Initial calculation
      
      console.log("📊 [Modal] ✅ Showing modal!");
      modal.style.display = "flex";
      modal.style.opacity = "1";
      modal.style.pointerEvents = "all";
    }
    
    // Close modal handlers
    document.getElementById("vtc-close-trade-log").onclick = () => {
      document.getElementById("vtc-trade-log-modal").style.display = "none";
    };
    
    document.getElementById("vtc-cancel-log").onclick = () => {
      document.getElementById("vtc-trade-log-modal").style.display = "none";
    };
    
    // Form submission
    document.getElementById("vtc-trade-log-form").onsubmit = async (e) => {
      e.preventDefault();
      
      const entry = parseFloat(document.getElementById("log-entry").value);
      const stop = parseFloat(document.getElementById("log-stop").value);
      const tp = parseFloat(document.getElementById("log-tp").value);
      const risk = Math.abs(entry - stop);
      const reward = Math.abs(tp - entry);
      const expectedR = risk > 0 ? parseFloat((reward / risk).toFixed(2)) : null;
      
      // Get outcome fields
      const outcome = document.getElementById("log-outcome").value;
      let actualR = null;
      
      if (outcome !== "pending") {
        const actualRInput = document.getElementById("log-actual-r").value;
        if (actualRInput) {
          actualR = parseFloat(actualRInput);
        } else {
          // Auto-calculate based on outcome
          if (outcome === "win") actualR = expectedR;
          else if (outcome === "loss") actualR = -1.0;
          else if (outcome === "breakeven") actualR = 0;
        }
      }
      
      const tradeData = {
        session_id: `trade-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`, // Unique ID for each trade
        timestamp: new Date().toISOString(),
        symbol: document.getElementById("log-symbol").value,
        timeframe: document.getElementById("log-timeframe").value,
        bias: document.getElementById("log-bias").value,
        setup_type: document.getElementById("log-setup").value,
        ai_verdict: document.getElementById("log-ai-verdict").value,
        user_action: "entered",
        outcome: outcome === "pending" ? null : outcome,
        r_multiple: actualR,
        comments: outcome === "pending" ? "Logged via Smart Log Trade - Trade Open" : `Logged via Smart Log Trade - ${outcome}`,
        entry_price: entry,
        stop_loss: stop,
        take_profit: tp,
        expected_r: expectedR
      };
      
      try {
        // Save to IndexedDB
        await idbReadyPromise;
        if (window.IDB && window.IDB.savePerformanceLog) {
          await window.IDB.savePerformanceLog(tradeData);
          console.log("📊 [Smart Log] ✅ Saved to IndexedDB");
        }
        
        // Sync to backend
        const response = await fetch("http://127.0.0.1:8765/performance/log", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(tradeData)
        });
        
        if (response.ok) {
          console.log("📊 [Smart Log] ✅ Synced to backend");
          showNotification(`📊 Trade logged! R:R: ${expectedR}:1`, "success");
          document.getElementById("vtc-trade-log-modal").style.display = "none";
          
          // Clear uploaded image
          uploadedImageData = null;
          uploadBtn.textContent = "📤 Upload";
          uploadBtn.style.background = "";
          fileInput.value = "";
        } else {
          throw new Error("Backend sync failed");
        }
      } catch (error) {
        console.error("📊 [Smart Log] ❌ Error:", error);
        showNotification("⚠️ Failed to log trade: " + error.message, "error");
      }
    };
    
    // Enter key to send text-only (Ctrl+Enter for image)
    input.onkeydown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        sendMessage(true); // Image mode on Ctrl+Enter
      } else if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(false); // Text mode on Enter
      }
    };
    
    // Make draggable
    makeDraggable(chatContainer, document.getElementById("vtc-header"));
    
    // Make resizable (Phase 3B.1: Multi-directional resize)
    makeResizable(chatContainer);
    
    // Animate in
    setTimeout(() => chatContainer.classList.add("vtc-visible"), 10);
  }
  
  return chatContainer;
}

/**
 * Render all messages in the chat
 */
function renderMessages() {
  const messagesEl = document.getElementById("vtc-messages");
  if (!messagesEl) {
    console.log("⏳ Messages element not ready yet, skipping render");
    return;
  }
  
  if (chatHistory.length === 0) {
    messagesEl.innerHTML = `
      <div class="vtc-empty-state">
        <div class="vtc-empty-icon">💬</div>
        <h4>Start a Conversation</h4>
        <p>Capture a chart and ask me anything about:<br/>
        • Market structure & bias<br/>
        • Entry/exit points<br/>
        • Risk management<br/>
        • Smart Money Concepts</p>
      </div>
    `;
    updateFooter(0);
    return;
  }
  
  messagesEl.innerHTML = chatHistory.map(msg => {
    const isUser = msg.role === "user";
    const time = formatTimestamp(msg.timestamp);
    const avatar = isUser ? "👤" : "🤖";
    
    return `
      <div class="vtc-message ${msg.role}">
        <div class="vtc-message-avatar">${avatar}</div>
        <div class="vtc-message-content">
          <div class="vtc-message-text">${formatMessage(msg.content)}</div>
          <div class="vtc-message-time">${time}</div>
        </div>
      </div>
    `;
  }).join('');
  
  // Auto-scroll to bottom
  messagesEl.scrollTop = messagesEl.scrollHeight;
  
  // Update footer
  updateFooter(chatHistory.length);
}

/**
 * Make chat panel draggable
 */
function makeDraggable(element, handle) {
  let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
  let isDragging = false;
  
  handle.onmousedown = dragMouseDown;
  handle.style.cursor = "move";
  
  function dragMouseDown(e) {
    // Don't drag if clicking on buttons, session badge, or model selector
    if (e.target.tagName === "BUTTON" || 
        e.target.tagName === "SELECT" || 
        e.target.closest(".vtc-controls") || 
        e.target.closest(".vtc-session-badge") ||
        e.target.closest(".vtc-model-selector")) {
      return;
    }
    
    e.preventDefault();
    isDragging = true;
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    document.onmousemove = elementDrag;
    element.style.transition = "none";
  }
  
  function elementDrag(e) {
    if (!isDragging) return;
    e.preventDefault();
    
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    
    // Calculate new position
    let newTop = element.offsetTop - pos2;
    let newLeft = element.offsetLeft - pos1;
    
    // Keep within viewport
    const maxX = window.innerWidth - element.offsetWidth;
    const maxY = window.innerHeight - element.offsetHeight;
    
    newTop = Math.max(0, Math.min(newTop, maxY));
    newLeft = Math.max(0, Math.min(newLeft, maxX));
    
    element.style.top = newTop + "px";
    element.style.left = newLeft + "px";
    element.style.right = "auto";
  }
  
  function closeDragElement() {
    isDragging = false;
    document.onmouseup = null;
    document.onmousemove = null;
    element.style.transition = "";
  }
}

/**
 * Make chat panel resizable from all sides (Phase 3B.1)
 */
function makeResizable(element) {
  const handles = {
    top: element.querySelector('.vtc-resize-top'),
    bottom: element.querySelector('.vtc-resize-bottom'),
    left: element.querySelector('.vtc-resize-left'),
    right: element.querySelector('.vtc-resize-right'),
    topleft: element.querySelector('.vtc-resize-topleft'),
    topright: element.querySelector('.vtc-resize-topright'),
    bottomleft: element.querySelector('.vtc-resize-bottomleft'),
    bottomright: element.querySelector('.vtc-resize-bottomright')
  };
  
  let isResizing = false;
  let currentHandle = null;
  let startX, startY, startWidth, startHeight, startTop, startLeft;
  
  Object.entries(handles).forEach(([direction, handle]) => {
    if (!handle) return;
    
    handle.addEventListener('mousedown', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      isResizing = true;
      currentHandle = direction;
      startX = e.clientX;
      startY = e.clientY;
      startWidth = element.offsetWidth;
      startHeight = element.offsetHeight;
      startTop = element.offsetTop;
      startLeft = element.offsetLeft;
      
      document.addEventListener('mousemove', handleResize);
      document.addEventListener('mouseup', stopResize);
      element.style.transition = 'none';
    });
  });
  
  function handleResize(e) {
    if (!isResizing) return;
    
    const deltaX = e.clientX - startX;
    const deltaY = e.clientY - startY;
    
    const minWidth = 320;
    const minHeight = 400;
    const maxWidth = window.innerWidth * 0.9;
    const maxHeight = window.innerHeight;
    
    // Handle horizontal resizing
    if (currentHandle.includes('left')) {
      let newWidth = startWidth - deltaX;
      let newLeft = startLeft + deltaX;
      
      if (newWidth >= minWidth && newWidth <= maxWidth && newLeft >= 0) {
        element.style.width = newWidth + 'px';
        element.style.left = newLeft + 'px';
        element.style.right = 'auto';
      }
    } else if (currentHandle.includes('right')) {
      let newWidth = startWidth + deltaX;
      if (newWidth >= minWidth && newWidth <= maxWidth) {
        element.style.width = newWidth + 'px';
      }
    }
    
    // Handle vertical resizing
    if (currentHandle.includes('top')) {
      let newHeight = startHeight - deltaY;
      let newTop = startTop + deltaY;
      
      if (newHeight >= minHeight && newHeight <= maxHeight && newTop >= 0) {
        element.style.height = newHeight + 'px';
        element.style.top = newTop + 'px';
      }
    } else if (currentHandle.includes('bottom')) {
      let newHeight = startHeight + deltaY;
      if (newHeight >= minHeight && newHeight <= maxHeight) {
        element.style.height = newHeight + 'px';
      }
    }
  }
  
  function stopResize() {
    if (!isResizing) return;
    isResizing = false;
    currentHandle = null;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
    element.style.transition = '';
  }
}

/**
 * Reset chat panel to default size and position
 */
function resetChatSize() {
  if (!chatContainer) return;
  
  // Default dimensions (Phase 3C: Balanced size to avoid covering chart)
  chatContainer.style.width = "620px";
  chatContainer.style.height = "100vh";
  chatContainer.style.top = "0";
  chatContainer.style.right = "0";
  chatContainer.style.left = "auto";
  chatContainer.style.bottom = "auto";
  
  showNotification("Chat size reset", "success");
}

/**
 * Toggle minimize state
 */
function toggleMinimize() {
  if (chatContainer) {
    chatContainer.classList.toggle("vtc-minimized");
  }
}

/**
 * Update footer with message count and status
 */
function updateFooter(count) {
  const countEl = document.getElementById("vtc-message-count");
  const statusEl = document.getElementById("vtc-status");
  
  if (countEl) countEl.textContent = `${count} message${count !== 1 ? 's' : ''}`;
  if (statusEl) statusEl.textContent = currentSession ? `${currentSession.symbol}` : "Ready";
}

/**
 * Format message content (support bold, italic, paragraphs)
 */
function formatMessage(text) {
  return text
    .split('\n\n').map(p => `<p>${p}</p>`).join('')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>');
}

/**
 * Format timestamp (smart relative time)
 */
function formatTimestamp(timestamp) {
  const now = Date.now();
  const diff = now - timestamp;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (seconds < 60) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  
  return new Date(timestamp).toLocaleDateString();
}

/**
 * Show notification toast
 */
function showNotification(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `vtc-toast vtc-toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => toast.classList.add("vtc-toast-visible"), 10);
  setTimeout(() => {
    toast.classList.remove("vtc-toast-visible");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ========== Phase 4A: Performance Tracking ==========

/**
 * Phase 4A.1: Extract trade details from AI response
 * Parses structured data like entry, stop loss, take profit from AI analysis
 * @param {string} aiResponse - The AI's response text
 * @returns {Object} Extracted trade details
 */
function extractTradeDetailsFromAI(aiResponse) {
  const details = {
    entry_price: null,
    stop_loss: null,
    take_profit: null,
    expected_r: null
  };
  
  // Enhanced extraction patterns to catch more variations
  // Remove markdown formatting first (**, __, etc.)
  const cleanResponse = aiResponse.replace(/[*_~`]/g, '');
  
  // Matches: "entry: 1.1625", "entered at 1.1625", "shorted around 1.1625", "bought at 1.1625"
  const entryPatterns = [
    /(?:entry|entered|shorted|bought|longed|went (?:long|short))(?:\s+at|\s+around|\s+near|\s+off|:|\s+@)?\s+(?:that\s+)?(?:red\s+)?(?:supply\s+)?(?:zone\s+)?(?:near\s+)?(\d+(?:[,\s]\d+)?(?:\.\d+)?)/i,
    /(?:entry|filled)(?:\s+price)?[:\s]+(\d+(?:[,\s]\d+)?(?:\.\d+)?)/i,
    /(?:current|sitting at|price)[:\s]+(\d+(?:\.\d+)?)/i,
    /(?:zone|area|level)(?:\s+at|\s+around|\s+near)?[:\s]+(\d+(?:[,\s-]\d+)?(?:\.\d+)?)/i
  ];
  
  // Matches: "stop: 1.1580", "SL at 1.1580", "stop loss: 1.1580", "break-even at 1.1580"
  const slPatterns = [
    /(?:stop|sl|stop loss|stoploss)(?:\s+at|\s+around|:|\s+@)?\s+(\d+\.?\d*)/i,
    /break(?:-|\s)?even(?:\s+at|:|\s+@)?\s+(\d+\.?\d*)/i,
    /trail(?:ing)?\s+stop[:\s]+(\d+\.?\d*)/i
  ];
  
  // Matches: "target: 1.1565", "TP at 1.1565", "take profit around 1.1565", "profit around 1.1565"
  const tpPatterns = [
    /(?:target|tp|take profit|takeprofit)(?:\s+at|\s+around|:|\s+@)?\s+(\d+\.?\d*)/i,
    /(?:profit|pnl)(?:\s+at|\s+around|:|\s+@)?\s+(\d+\.?\d*)/i,
    /(?:next|first|second)\s+(?:target|liquidity|poi)(?:\s+at|:|\s+@)?\s+(\d+\.?\d*)/i
  ];
  
  // Helper to parse price (handles ranges like "3562-3565" -> 3563.5)
  const parsePrice = (str) => {
    str = str.replace(/[,\s]/g, ''); // Remove commas/spaces
    if (str.includes('-')) {
      // Handle range: take midpoint
      const [low, high] = str.split('-').map(parseFloat);
      return (low + high) / 2;
    }
    return parseFloat(str);
  };
  
  // Try all entry patterns
  for (const pattern of entryPatterns) {
    const match = cleanResponse.match(pattern);
    if (match) {
      details.entry_price = parsePrice(match[1]);
      break;
    }
  }
  
  // Try all stop loss patterns
  for (const pattern of slPatterns) {
    const match = cleanResponse.match(pattern);
    if (match) {
      details.stop_loss = parsePrice(match[1]);
      break;
    }
  }
  
  // Try all take profit patterns
  for (const pattern of tpPatterns) {
    const match = cleanResponse.match(pattern);
    if (match) {
      details.take_profit = parsePrice(match[1]);
      break;
    }
  }
  
  // Calculate R:R if we have all levels
  if (details.entry_price && details.stop_loss && details.take_profit) {
    const risk = Math.abs(details.entry_price - details.stop_loss);
    const reward = Math.abs(details.take_profit - details.entry_price);
    details.expected_r = risk > 0 ? parseFloat((reward / risk).toFixed(2)) : null;
  }
  
  return details;
}

/**
 * Auto-detect trade events from user messages
 * Looks for keywords indicating trade entry/exit
 * @param {string} userMessage - The user's message
 * @param {string} aiResponse - The AI's response
 * @param {Object} sessionContext - Current session context
 * @returns {Promise<boolean>} True if trade was logged
 */
async function detectAndLogTrade(userMessage, aiResponse, sessionContext) {
  const lower = userMessage.toLowerCase();
  
  // Trade entry keywords (expanded for Phase 4A.1)
  const entryKeywords = [
    "entered", "took trade", "took this trade", "took the trade",
    "went long", "went short", "bought", "sold", 
    "entry at", "filled at", "got filled", "execution",
    "opened", "shorted", "longed", "entered long", "entered short",
    "i entered", "entered here"
  ];
  const isEntry = entryKeywords.some(keyword => lower.includes(keyword));
  
  if (isEntry) {
    // Phase 4A.1: Extract trade details from AI's vision analysis
    const extractedDetails = extractTradeDetailsFromAI(aiResponse);
    
    // Log extraction results
    console.log("📊 [Price Extraction] Results:", {
      entry: extractedDetails.entry_price || "❌ Not found",
      stop_loss: extractedDetails.stop_loss || "❌ Not found",
      take_profit: extractedDetails.take_profit || "❌ Not found",
      expected_r: extractedDetails.expected_r || "❌ Not calculated"
    });
    
    const tradeData = {
      session_id: `trade-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`, // Unique ID for each trade
      timestamp: new Date().toISOString(),
      symbol: sessionContext.symbol || currentSession?.symbol || "Unknown",
      timeframe: sessionContext.timeframe || currentSession?.context?.timeframe || "5m",
      bias: sessionContext.bias || currentSession?.context?.bias || "neutral",
      setup_type: sessionContext.setup || currentSession?.context?.setup || "manual",
      ai_verdict: aiResponse.substring(0, 200), // First 200 chars of AI response
      user_action: "entered",
      outcome: null, // To be updated later
      r_multiple: null,
      comments: userMessage,
      // Phase 4A.1: Add extracted price levels
      entry_price: extractedDetails.entry_price,
      stop_loss: extractedDetails.stop_loss,
      take_profit: extractedDetails.take_profit,
      expected_r: extractedDetails.expected_r
    };
    
    try {
      console.log("📊 [Trade Detection] ENTRY DETECTED! Starting log process...", tradeData);
      
      // Wait for IDB to be ready
      await idbReadyPromise;
      
      // Phase 4A.1: Fallback - define savePerformanceLog if it doesn't exist
      if (!window.IDB.savePerformanceLog) {
        console.warn("⚠️ savePerformanceLog not found, defining fallback...");
        window.IDB.savePerformanceLog = async function(data) {
          const db = await window.IDB.openDB();
          
          // Check if performance_logs store exists
          if (!db.objectStoreNames.contains("performance_logs")) {
            throw new Error("Database needs upgrade. Please run: indexedDB.deleteDatabase('vtc_memory') in console, then reload.");
          }
          
          return new Promise((resolve, reject) => {
            const tx = db.transaction(["performance_logs"], "readwrite");
            const store = tx.objectStore("performance_logs");
            const record = { ...data, timestamp: data.timestamp || new Date().toISOString(), created_at: Date.now() };
            const request = store.add(record);
            request.onsuccess = () => { console.log("📊 Saved trade #" + request.result); resolve(request.result); };
            request.onerror = () => reject(request.error);
          });
        };
      }
      
      console.log("📊 [Trade Detection] IDB ready, saving to IndexedDB...");
      
      // Save to IndexedDB
      await window.IDB.savePerformanceLog(tradeData);
      console.log("📊 [Trade Detection] ✅ Saved to IndexedDB");
      
      // Sync to backend
      const response = await fetch("http://127.0.0.1:8765/performance/log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(tradeData)
      });
      
      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }
      
      const result = await response.json();
      console.log("📊 [Trade Detection] ✅ Synced to backend:", result);
      
      // Phase 4A.1: Enhanced notification with R:R if available
      const notification = extractedDetails.expected_r 
        ? `📊 Trade logged! Expected R:R: ${extractedDetails.expected_r}:1`
        : "📊 Trade logged!";
      
      console.log("📊 [Trade Detection] ✅ Trade entry logged successfully:", tradeData);
      showNotification(notification, "success");
      return true;
    } catch (error) {
      console.error("📊 [Trade Detection] ❌ Error logging trade:", error);
      showNotification("⚠️ Trade logging failed: " + error.message, "error");
      return false;
    }
  }
  
  // Trade exit keywords
  const exitKeywords = ["closed", "exited", "took profit", "hit stop", "stopped out", "tp hit", "sl hit"];
  const isExit = exitKeywords.some(keyword => lower.includes(keyword));
  
  if (isExit) {
    // Try to extract outcome and R multiple from message
    let outcome = "win"; // default
    let rMultiple = null;
    
    if (lower.includes("stop") || lower.includes("loss") || lower.includes("sl hit")) {
      outcome = "loss";
      rMultiple = -1.0; // default loss
    } else if (lower.includes("breakeven") || lower.includes("be")) {
      outcome = "breakeven";
      rMultiple = 0.0;
    } else {
      // Try to extract R multiple from message (e.g., "2r", "1.5r", "3:1")
      const rMatch = lower.match(/(\d+(?:\.\d+)?)\s*r\b|(\d+(?:\.\d+)?)\s*:\s*1/);
      if (rMatch) {
        rMultiple = parseFloat(rMatch[1] || rMatch[2]);
      } else {
        rMultiple = 1.0; // default win
      }
    }
    
    try {
      const updates = { outcome, r_multiple: rMultiple, comments: userMessage };
      
      // Update in IndexedDB
      await window.IDB.updatePerformanceLog(currentSession?.sessionId, updates);
      
      // Update in backend
      const formData = new FormData();
      formData.append("session_id", currentSession?.sessionId);
      formData.append("outcome", outcome);
      formData.append("r_multiple", rMultiple);
      formData.append("comments", userMessage);
      
      await fetch("http://127.0.0.1:8765/performance/update", {
        method: "POST",
        body: formData
      });
      
      console.log(`📊 [Trade Detection] Updated trade exit: ${outcome} at ${rMultiple}R`);
      showNotification(`📊 Trade closed: ${outcome} (${rMultiple}R)`, "success");
      return true;
    } catch (error) {
      console.error("📊 [Trade Detection] Error updating trade:", error);
      return false;
    }
  }
  
  return false;
}

// ========== Phase 3B.1: Token Efficiency ==========

/**
 * Estimate token count from messages (rough approximation: 1 token ≈ 4 chars)
 * @param {Array} messages - Array of message objects
 * @returns {number} Estimated token count
 */
function estimateTokens(messages) {
  if (!messages || messages.length === 0) return 0;
  return messages.reduce((total, msg) => {
    const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);
    return total + Math.ceil(content.length / 4);
  }, 0);
}

/**
 * Summarize context to reduce token usage (Phase 3B.1)
 * Keeps recent messages intact, summarizes older messages
 * @param {Array} messages - Full message history
 * @returns {Array} Summarized message array
 */
function summarizeContext(messages) {
  if (messages.length <= 40) {
    // Under 40 messages, no need to summarize
    return messages;
  }
  
  // Keep last 20 messages (most recent context)
  const recent = messages.slice(-20);
  
  // Summarize older messages
  const older = messages.slice(0, -20);
  const joined = older.map(m => `${m.role}: ${m.content}`).join(" ");
  const summary = `Summary of previous discussion: ${joined.slice(0, 600)}...`;
  
  // Return summary + recent messages
  return [
    { role: "system", content: summary },
    ...recent
  ];
}

/**
 * Create or update debug overlay showing tokens and cost
 * @param {Object} options - Options for overlay update
 * @param {boolean} options.includeImage - Whether image was included
 * @param {number} options.tokens - Estimated token count
 * @param {boolean} options.hybridMode - Whether hybrid mode was used (Phase 3C)
 */
function updateDebugOverlay({ includeImage = false, tokens = null, hybridMode = false } = {}) {
  let overlay = document.getElementById("vtc-debug-overlay");
  
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "vtc-debug-overlay";
    document.body.appendChild(overlay);
  }
  
  // Calculate tokens if not provided
  if (tokens === null) {
    tokens = estimateTokens(chatHistory);
  }
  
  // Phase 3C: Hybrid mode pricing (GPT-4o vision + GPT-5 reasoning)
  let costPer1k, mode, modeColor;
  
  if (hybridMode) {
    // Hybrid: GPT-4o vision (~$0.005/1k) + GPT-5 Mini reasoning (~$0.004/1k)
    costPer1k = 0.006;
    mode = "🧠 Hybrid (4o→5)";
    modeColor = "#ff66cc";
  } else if (includeImage) {
    // GPT-5 Chat or GPT-4o Vision
    costPer1k = 0.005;
    mode = "👁️ Vision ON";
    modeColor = "#ffd700";
  } else {
    // Text-only mode
    costPer1k = 0.002;
    mode = "📝 Text Only";
    modeColor = "#00ff99";
  }
  
  const estimatedCost = ((tokens / 1000) * costPer1k).toFixed(4);
  
  overlay.innerHTML = `
    <div style="color: ${modeColor}">
      🧮 Tokens: ${tokens} | ≈ $${estimatedCost}<br/>
      ${hybridMode ? '🧠' : '💰'} ${mode}
    </div>
  `;
  overlay.style.color = modeColor;
  overlay.style.opacity = "1";
  overlay.style.visibility = "visible";
  
  // Position to the left of chat panel
  if (chatContainer && document.body.contains(chatContainer)) {
    const chatRect = chatContainer.getBoundingClientRect();
    overlay.style.left = `${chatRect.left - overlay.offsetWidth - 16}px`;
  }
  
  // Phase 3B.1: Auto-fade after 6 seconds
  clearTimeout(overlay.fadeTimeout);
  overlay.fadeTimeout = setTimeout(() => {
    overlay.style.opacity = "0";
    setTimeout(() => {
      overlay.style.visibility = "hidden";
    }, 500);
  }, 6000);
}

// ==== Copilot Bridge Intent Handler ====
async function handleCopilotIntent(userInput) {
  const lower = userInput.toLowerCase();
  // Broader intent detection for common phrasing
  const asksForStats =
    lower.includes('show my stats') ||
    lower.includes('my performance') ||
    lower.includes('how am i doing') ||
    /\b(show|see|check|review)\b[\s\S]*\b(stats|performance|win\s?rate|summary)\b/i.test(userInput);

  if (asksForStats) {
    const res = await fetch('http://127.0.0.1:8765/copilot/performance').then(r=>r.json());
    const d = res.data;
    return `📊 **Performance Summary**  \n• Total Trades: ${d.total}\n• Wins: ${d.wins} | Losses: ${d.losses} | BE: ${d.breakeven}\n• Win Rate: ${d.win_rate}%\n• Avg R:R: ${d.avg_rr}R\n• Best Setup: ${d.best_setup}`;
  }
  const asksForRecent =
    lower.includes('review my last') ||
    lower.includes('show last trades') ||
    lower.includes('recent trades') ||
    lower.includes('recently added') ||
    lower.includes('new trades') ||
    /\b(review|show|see|list|check)\b[\s\S]*\b(last|recent|new|recently added)\b[\s\S]*\b(trades|entries|examples|metadata)\b/i.test(userInput);

  if (asksForRecent) {
    const limit = 5;
    const res = await fetch(`http://127.0.0.1:8765/copilot/teach/examples?limit=${limit}`).then(r=>r.json());
    const list = res.examples.map((e,i)=>`#${i+1} ${e.symbol} (${e.outcome||'unlabeled'}) – ${e.chart_path}`).join("\n");
    return `🧾 Here are your last ${limit} teaching examples:\n${list}`;
  }
  const tradeIdMatch = userInput.match(/trade\s*(\d+)/i) || userInput.match(/#?(\d{6,})/);
  if (lower.includes('what was trade') || tradeIdMatch) {
    const id = tradeIdMatch ? tradeIdMatch[1] || tradeIdMatch[0] : lower.match(/\d+/)[0];
    const res = await fetch(`http://127.0.0.1:8765/copilot/teach/example/${id}`).then(r=>r.json());
    if (!res.success) return res.message;
    const e = res.example;
    return `📈 Trade ${id}: ${e.symbol} (${e.direction}) → ${e.outcome||'unlabeled'}  \nPOI: ${e.poi_range||'N/A'}  BOS: ${e.bos_range||'N/A'}  \nExplanation: ${e.explanation||'Not set yet.'}`;
  }
  return null;
}

// ========== Message Listener ==========

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Ping check for content script presence
  if (message.action === "ping") {
    sendResponse({ status: "ready" });
    return false;
  }
  
  // Toggle chat panel visibility
  if (message.action === "toggleChat") {
    try {
      if (chatContainer && document.body.contains(chatContainer)) {
        if (chatContainer.classList.contains("vtc-visible")) {
          chatContainer.classList.add("vtc-closing");
          setTimeout(() => {
            if (chatContainer && chatContainer.parentNode) {
              chatContainer.remove();
            }
            chatContainer = null;
          }, 300);
        } else {
          chatContainer.classList.add("vtc-visible");
        }
      } else {
        chatContainer = null;
        ensureChatUI();
        initializeSession();
      }
      sendResponse({ status: "toggled" });
    } catch (error) {
      console.error("Toggle chat error:", error);
      sendResponse({ status: "error", message: error.message });
    }
    return false;
  }
  
  // Show overlay with new message
  if (message.action === "showOverlay") {
    (async () => {
      try {
        const { question, response, hybrid_mode } = message.payload;
        
        if (!currentSession) {
          await initializeSession();
        }
        
        // Save user question
        await window.IDB.saveMessage(currentSession.sessionId, "user", question);
        
        // Save assistant response
        await window.IDB.saveMessage(currentSession.sessionId, "assistant", response.answer);
        
        // Phase 4A: Auto-detect trade logging (DISABLED - use "📊 Log Trade" button instead)
        // await detectAndLogTrade(question, response.answer, currentSession.context || {});
        
        // Reload messages and render
        chatHistory = await window.IDB.loadMessages(currentSession.sessionId);
        renderMessages();
        
        // Update context
        await updateSessionContext();
        
        // Phase 3C: Show hybrid mode notification if applicable
        if (hybrid_mode) {
          showNotification("🧠 Hybrid: GPT-4o Vision → GPT-5 Reasoning", "success");
        } else {
          showNotification("Analysis complete", "success");
        }
        
        sendResponse({ status: "displayed" });
      } catch (error) {
        console.error("Show overlay error:", error);
        sendResponse({ status: "error", message: error.message });
      }
    })();
    return true; // Keep channel open for async response
  }
  
  // Return chat history when requested
  if (message.action === "getChatHistory") {
    (async () => {
      try {
        if (!currentSession) {
          await initializeSession();
        }
        
        // Get last 50 messages for context (Phase 3B: full session memory)
        const messages = await window.IDB.loadMessages(currentSession.sessionId, 50);
        const formattedHistory = messages.map(msg => ({
          role: msg.role,
          content: msg.content
        }));
        
        console.log("📤 Sending chat history:", formattedHistory.length, "messages");
        
        sendResponse({ 
          history: formattedHistory,
          sessionId: currentSession.sessionId,
          context: currentSession.context
        });
      } catch (error) {
        console.error("Get history error:", error);
        sendResponse({ history: [], context: {} });
      }
    })();
    return true;
  }
  
  // Phase 3B.1: New popup actions
  if (message.action === "newSession") {
    (async () => {
      try {
        // Create a new session
        const symbol = "CHART";
        const newSession = await window.IDB.createSession(symbol);
        
        // Switch to new session
        currentSession = newSession;
        chatHistory = [];
        
        console.log("✨ Created new session:", newSession.sessionId);
        sendResponse({ status: "created", sessionId: newSession.sessionId });
      } catch (error) {
        console.error("New session error:", error);
        sendResponse({ status: "error", message: error.message });
      }
    })();
    return true;
  }
  
  if (message.action === "openSessionManager") {
    showSessionManager();
    sendResponse({ status: "opened" });
    return false;
  }
  
  if (message.action === "quickAnalyze") {
    (async () => {
      try {
        if (!currentSession) {
          await initializeSession();
        }
        
        // Ensure chat UI is visible
        if (!chatContainer || !document.body.contains(chatContainer)) {
          ensureChatUI();
        }
        
        // Open chat and trigger quick analysis
        if (chatContainer) {
          chatContainer.classList.add("vtc-visible");
          showNotification("Quick analysis starting...", "info");
        }
        
        sendResponse({ status: "analyzing" });
      } catch (error) {
        console.error("Quick analyze error:", error);
        sendResponse({ status: "error", message: error.message });
      }
    })();
    return true;
  }
});

// ========== Auto-load on Page Load ==========
(async function initChat() {
  try {
    console.log("🚀 Initializing Visual Trade Copilot...");
    await idbReadyPromise;
    console.log("✅ IDB ready, initializing session...");
    await initializeSession();
    console.log("✅ Visual Trade Copilot initialized (Phase 3B)");
  } catch (error) {
    console.error("❌ Failed to initialize chat:", error);
  }
})();

console.log("✅ Visual Trade Copilot content script loaded (Phase 3B: Multi-Session Memory)");
