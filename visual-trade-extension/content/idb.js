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
const DB_VERSION = 3; // Upgraded to v3 (Phase 4A: Performance Tracking)

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

      // Phase 4A: Create performance_logs store (if not exists)
      if (!db.objectStoreNames.contains("performance_logs")) {
        const perfStore = db.createObjectStore("performance_logs", { keyPath: "id", autoIncrement: true });
        perfStore.createIndex("session_id", "session_id", { unique: false });
        perfStore.createIndex("symbol", "symbol", { unique: false });
        perfStore.createIndex("timestamp", "timestamp", { unique: false });
        perfStore.createIndex("outcome", "outcome", { unique: false });
        console.log("📊 Created performance_logs store");
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

// ========== Phase 4A: Performance Tracking Functions ==========

/**
 * Save a performance log entry
 * @param {Object} tradeData - Trade record data
 * @returns {Promise<number>} The new trade's ID
 */
window.IDB.savePerformanceLog = async function savePerformanceLog(tradeData) {
  const db = await window.IDB.openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["performance_logs"], "readwrite");
    const store = transaction.objectStore("performance_logs");
    
    const record = {
      ...tradeData,
      timestamp: tradeData.timestamp || new Date().toISOString(),
      created_at: Date.now()
    };
    
    const request = store.add(record);
    
    request.onsuccess = () => {
      console.log(`📊 [Performance] Saved trade log #${request.result}`);
      resolve(request.result);
    };
    request.onerror = () => {
      console.error("📊 [Performance] Error saving trade log:", request.error);
      reject(request.error);
    };
  });
}

/**
 * Get all performance logs
 * @param {Object} filters - Optional filters (symbol, outcome)
 * @returns {Promise<Array>}
 */
window.IDB.getPerformanceLogs = async function getPerformanceLogs(filters = {}) {
  const db = await window.IDB.openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["performance_logs"], "readonly");
    const store = transaction.objectStore("performance_logs");
    const request = store.getAll();
    
    request.onsuccess = () => {
      let logs = request.result;
      
      // Apply filters
      if (filters.symbol) {
        logs = logs.filter(log => log.symbol === filters.symbol);
      }
      if (filters.outcome) {
        logs = logs.filter(log => log.outcome === filters.outcome);
      }
      
      // Sort by timestamp (newest first)
      logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      
      resolve(logs);
    };
    request.onerror = () => reject(request.error);
  });
}

/**
 * Update a performance log entry
 * @param {string} sessionId - Session ID
 * @param {Object} updates - Fields to update
 * @returns {Promise<void>}
 */
window.IDB.updatePerformanceLog = async function updatePerformanceLog(sessionId, updates) {
  const db = await window.IDB.openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(["performance_logs"], "readwrite");
    const store = transaction.objectStore("performance_logs");
    const index = store.index("session_id");
    const request = index.openCursor(IDBKeyRange.only(sessionId));
    
    request.onsuccess = (e) => {
      const cursor = e.target.result;
      if (cursor) {
        const record = cursor.value;
        const updated = { ...record, ...updates, updated_at: Date.now() };
        cursor.update(updated);
        console.log(`📊 [Performance] Updated trade log for session ${sessionId}`);
        resolve();
      } else {
        reject(new Error(`Trade log not found for session ${sessionId}`));
      }
    };
    request.onerror = () => reject(request.error);
  });
}

/**
 * Calculate performance statistics from local logs
 * @param {Object} filters - Optional filters
 * @returns {Promise<Object>}
 */
window.IDB.calculatePerformanceStats = async function calculatePerformanceStats(filters = {}) {
  const logs = await window.IDB.getPerformanceLogs(filters);
  
  if (logs.length === 0) {
    return {
      total_trades: 0,
      win_rate: null,
      avg_r: null,
      profit_factor: null,
      total_r: null,
      wins: 0,
      losses: 0,
      breakevens: 0
    };
  }
  
  const wins = logs.filter(log => log.outcome === "win");
  const losses = logs.filter(log => log.outcome === "loss");
  const breakevens = logs.filter(log => log.outcome === "breakeven");
  
  const rValues = logs.filter(log => log.r_multiple != null).map(log => log.r_multiple);
  const winningR = wins.filter(log => log.r_multiple != null).map(log => log.r_multiple);
  const losingR = losses.filter(log => log.r_multiple != null).map(log => Math.abs(log.r_multiple));
  
  const totalTrades = logs.length;
  const completedTrades = wins.length + losses.length + breakevens.length;
  const winRate = completedTrades > 0 ? (wins.length / completedTrades) * 100 : null;
  const avgR = rValues.length > 0 ? rValues.reduce((a, b) => a + b, 0) / rValues.length : null;
  const totalR = rValues.length > 0 ? rValues.reduce((a, b) => a + b, 0) : null;
  
  let profitFactor = null;
  if (winningR.length > 0 && losingR.length > 0) {
    const totalWins = winningR.reduce((a, b) => a + b, 0);
    const totalLosses = losingR.reduce((a, b) => a + b, 0);
    profitFactor = totalLosses > 0 ? totalWins / totalLosses : null;
  }
  
  return {
    total_trades: totalTrades,
    win_rate: winRate != null ? Math.round(winRate * 10) / 10 : null,
    avg_r: avgR != null ? Math.round(avgR * 100) / 100 : null,
    profit_factor: profitFactor != null ? Math.round(profitFactor * 100) / 100 : null,
    total_r: totalR != null ? Math.round(totalR * 100) / 100 : null,
    wins: wins.length,
    losses: losses.length,
    breakevens: breakevens.length
  };
}

console.log("✅ IndexedDB helpers loaded (Phase 3B + 4A)");

