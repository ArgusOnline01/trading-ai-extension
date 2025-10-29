/**
 * IndexedDB Helper for Visual Trade Copilot - Phase 3B
 * Handles multi-session memory with sessions and messages stores
 * 
 * Note: This file is loaded as a regular script (not ES6 module) for Chrome extension compatibility.
 * All functions are attached to the global IDB namespace.
 */

console.log("🔧 idb.js file is being executed...");

// Create global IDB namespace
window.IDB = window.IDB || {};
console.log("📦 window.IDB namespace created:", window.IDB);

const DB_NAME = "vtc_memory";
const DB_VERSION = 2; // Upgraded from v1 (Phase 3A) to v2 (Phase 3B)

console.log("🗄️ DB config:", DB_NAME, "version", DB_VERSION);

/**
 * Open IndexedDB connection with sessions and messages stores
 * @returns {Promise<IDBDatabase>}
 */
window.IDB.openDB = async function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // Create sessions store (if not exists)
      if (!db.objectStoreNames.contains("sessions")) {
        const sessionsStore = db.createObjectStore("sessions", { keyPath: "sessionId" });
        sessionsStore.createIndex("symbol", "symbol", { unique: false });
        sessionsStore.createIndex("last_updated", "last_updated", { unique: false });
      }

      // Create messages store (if not exists)
      if (!db.objectStoreNames.contains("messages")) {
        const messagesStore = db.createObjectStore("messages", { keyPath: "id", autoIncrement: true });
        messagesStore.createIndex("sessionId", "sessionId", { unique: false });
        messagesStore.createIndex("timestamp", "timestamp", { unique: false });
      }

      // Migrate old chat_history to new structure (Phase 3A → 3B migration)
      if (event.oldVersion === 1 && db.objectStoreNames.contains("chat_history")) {
        const transaction = event.target.transaction;
        const oldStore = transaction.objectStore("chat_history");
        const newMessagesStore = transaction.objectStore("messages");
        
        // Create default session for old messages
        const defaultSessionId = `default-${Date.now()}`;
        const sessionsStore = transaction.objectStore("sessions");
        sessionsStore.add({
          sessionId: defaultSessionId,
          title: "Migrated Session",
          symbol: "CHART",
          created_at: Date.now(),
          last_updated: Date.now(),
          context: {}
        });

        // Migrate messages
        oldStore.openCursor().onsuccess = (e) => {
          const cursor = e.target.result;
          if (cursor) {
            const oldMsg = cursor.value;
            newMessagesStore.add({
              sessionId: defaultSessionId,
              role: oldMsg.role,
              content: oldMsg.content,
              timestamp: oldMsg.timestamp || Date.now()
            });
            cursor.continue();
          }
        };
      }
    };
  });
}

/**
 * Create a new session
 * @param {string} symbol - Trading symbol (e.g., "6EZ25", "ES", "BTC")
 * @param {string} [title] - Optional custom title
 * @returns {Promise<Object>} Created session object
 */
window.IDB.createSession = async function createSession(symbol, title = null) {
  const db = await window.IDB.openDB();
  const sessionId = `${symbol}-${Date.now()}`;
  const session = {
    sessionId,
    title: title || `${symbol} Session`,
    symbol: symbol.toUpperCase(),
    created_at: Date.now(),
    last_updated: Date.now(),
    context: {
      latest_price: null,
      bias: null,
      last_poi: null,
      timeframe: null,
      notes: []
    }
  };

  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["sessions"], "readwrite");
    const store = transaction.objectStore("sessions");
    const request = store.add(session);

    request.onsuccess = () => resolve(session);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Get all sessions, sorted by last_updated (newest first)
 * @returns {Promise<Array>}
 */
window.IDB.getAllSessions = async function getAllSessions() {
  const db = await window.IDB.openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["sessions"], "readonly");
    const store = transaction.objectStore("sessions");
    const request = store.getAll();

    request.onsuccess = () => {
      const sessions = request.result;
      // Sort by last_updated descending
      sessions.sort((a, b) => b.last_updated - a.last_updated);
      resolve(sessions);
    };
    request.onerror = () => reject(request.error);
  });
}

/**
 * Get a specific session by ID
 * @param {string} sessionId
 * @returns {Promise<Object|null>}
 */
window.IDB.getSession = async function getSession(sessionId) {
  const db = await window.IDB.openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["sessions"], "readonly");
    const store = transaction.objectStore("sessions");
    const request = store.get(sessionId);

    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Update session metadata (title, context, etc.)
 * @param {string} sessionId
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>}
 */
window.IDB.updateSession = async function updateSession(sessionId, updates) {
  const db = await window.IDB.openDB();
  const session = await window.IDB.getSession(sessionId);
  
  if (!session) {
    throw new Error(`Session ${sessionId} not found`);
  }

  const updatedSession = {
    ...session,
    ...updates,
    last_updated: Date.now()
  };

  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["sessions"], "readwrite");
    const store = transaction.objectStore("sessions");
    const request = store.put(updatedSession);

    request.onsuccess = () => resolve(updatedSession);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Delete a session and all its messages
 * @param {string} sessionId
 * @returns {Promise<void>}
 */
window.IDB.deleteSession = async function deleteSession(sessionId) {
  const db = await window.IDB.openDB();
  
  return new Promise(async (resolve, reject) => {
    const transaction = db.transaction(["sessions", "messages"], "readwrite");
    
    // Delete session
    const sessionsStore = transaction.objectStore("sessions");
    sessionsStore.delete(sessionId);
    
    // Delete all messages for this session
    const messagesStore = transaction.objectStore("messages");
    const index = messagesStore.index("sessionId");
    const request = index.openCursor(IDBKeyRange.only(sessionId));
    
    request.onsuccess = (e) => {
      const cursor = e.target.result;
      if (cursor) {
        messagesStore.delete(cursor.primaryKey);
        cursor.continue();
      }
    };

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
}

/**
 * Save a message to a session
 * @param {string} sessionId
 * @param {string} role - "user" or "assistant"
 * @param {string} content - Message content
 * @returns {Promise<Object>} Saved message
 */
window.IDB.saveMessage = async function saveMessage(sessionId, role, content) {
  const db = await window.IDB.openDB();
  const message = {
    sessionId,
    role,
    content,
    timestamp: Date.now()
  };

  return new Promise(async (resolve, reject) => {
    const transaction = db.transaction(["messages", "sessions"], "readwrite");
    
    // Save message
    const messagesStore = transaction.objectStore("messages");
    const messageRequest = messagesStore.add(message);
    
    messageRequest.onsuccess = () => {
      message.id = messageRequest.result;
    };

    // Update session's last_updated timestamp
    const sessionsStore = transaction.objectStore("sessions");
    const sessionRequest = sessionsStore.get(sessionId);
    
    sessionRequest.onsuccess = () => {
      const session = sessionRequest.result;
      if (session) {
        session.last_updated = Date.now();
        sessionsStore.put(session);
      }
    };

    transaction.oncomplete = () => resolve(message);
    transaction.onerror = () => reject(transaction.error);
  });
}

/**
 * Load messages for a session
 * @param {string} sessionId
 * @param {number} [limit] - Max number of messages to load (default: all)
 * @returns {Promise<Array>}
 */
window.IDB.loadMessages = async function loadMessages(sessionId, limit = null) {
  const db = await window.IDB.openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["messages"], "readonly");
    const store = transaction.objectStore("messages");
    const index = store.index("sessionId");
    const request = index.getAll(IDBKeyRange.only(sessionId));

    request.onsuccess = () => {
      let messages = request.result;
      // Sort by timestamp ascending (oldest first)
      messages.sort((a, b) => a.timestamp - b.timestamp);
      
      // Apply limit if specified (keep most recent)
      if (limit && messages.length > limit) {
        messages = messages.slice(-limit);
      }
      
      resolve(messages);
    };
    request.onerror = () => reject(request.error);
  });
}

/**
 * Clear all messages in a session (but keep the session)
 * @param {string} sessionId
 * @returns {Promise<void>}
 */
window.IDB.clearSessionMessages = async function clearSessionMessages(sessionId) {
  const db = await window.IDB.openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["messages"], "readwrite");
    const store = transaction.objectStore("messages");
    const index = store.index("sessionId");
    const request = index.openCursor(IDBKeyRange.only(sessionId));
    
    request.onsuccess = (e) => {
      const cursor = e.target.result;
      if (cursor) {
        store.delete(cursor.primaryKey);
        cursor.continue();
      }
    };

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
}

/**
 * Export session data (session + messages) as JSON
 * @param {string} sessionId
 * @returns {Promise<Object>}
 */
window.IDB.exportSession = async function exportSession(sessionId) {
  const session = await window.IDB.getSession(sessionId);
  const messages = await window.IDB.loadMessages(sessionId);
  
  if (!session) {
    throw new Error(`Session ${sessionId} not found`);
  }

  return {
    session,
    messages,
    exported_at: Date.now(),
    version: "3B"
  };
}

/**
 * Get the most recent active session (or create default if none exist)
 * @returns {Promise<Object>}
 */
window.IDB.getActiveSession = async function getActiveSession() {
  const sessions = await window.IDB.getAllSessions();
  
  if (sessions.length === 0) {
    // Create default session
    return await window.IDB.createSession("CHART", "Default Session");
  }
  
  return sessions[0]; // Most recently updated
}

/**
 * Delete all sessions and messages (nuclear option)
 * @returns {Promise<void>}
 */
window.IDB.deleteAllData = async function deleteAllData() {
  const db = await window.IDB.openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["sessions", "messages"], "readwrite");
    
    transaction.objectStore("sessions").clear();
    transaction.objectStore("messages").clear();
    
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
}

/**
 * Get session statistics
 * @param {string} sessionId
 * @returns {Promise<Object>}
 */
window.IDB.getSessionStats = async function getSessionStats(sessionId) {
  const messages = await window.IDB.loadMessages(sessionId);
  const session = await window.IDB.getSession(sessionId);
  
  return {
    total_messages: messages.length,
    user_messages: messages.filter(m => m.role === "user").length,
    assistant_messages: messages.filter(m => m.role === "assistant").length,
    created_at: session?.created_at,
    last_updated: session?.last_updated,
    duration_hours: session ? (Date.now() - session.created_at) / (1000 * 60 * 60) : 0
  };
}

console.log("✅ IndexedDB helpers loaded (Phase 3B)");

// Visual Trade Copilot - Content Script (Phase 3B: Multi-Session Memory)
// Persistent chat panel with multi-session support and context tracking

// Wait for IDB to be loaded
let idbReadyPromise = new Promise((resolve) => {
  if (window.IDB) {
    console.log("✅ IDB already loaded");
    resolve();
  } else {
    console.log("⏳ Waiting for IDB to load...");
    const checkIDB = setInterval(() => {
      if (window.IDB) {
        console.log("✅ IDB loaded after wait");
        clearInterval(checkIDB);
        resolve();
      }
    }, 100);
    
    // Timeout after 5 seconds
    setTimeout(() => {
      clearInterval(checkIDB);
      if (!window.IDB) {
        console.error("❌ IDB failed to load after 5 seconds");
      }
      resolve();
    }, 5000);
  }
});

let chatHistory = [];
let chatContainer = null;
let currentSession = null;
let sessionManagerModal = null;
let selectedModel = "balanced"; // Phase 3B.2: Default GPT-5 model

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
                   <option value="fast">⚡ Fast (GPT-5 Chat) 👁️</option>
                   <option value="balanced" selected>⚖️ Balanced (GPT-5 Search) 🧠</option>
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
        </div>
      </div>
      <div id="vtc-footer" class="vtc-footer">
        <span id="vtc-message-count">0 messages</span>
        <span id="vtc-status">Ready</span>
      </div>
    `;
    
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
          context: contextToSend
        });
        
        if (response && response.success) {
          // Message will be added via showOverlay action
          input.value = "";
          showNotification("Analysis complete!", "success");
          
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
