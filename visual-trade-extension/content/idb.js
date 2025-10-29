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

