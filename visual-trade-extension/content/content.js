// Visual Trade Copilot - Content Script (Phase 3A: Conversational Memory)
// Persistent chat panel with IndexedDB storage

let chatHistory = [];
let chatContainer = null;

// ========== IndexedDB Helper Functions ==========

/**
 * Open or create the IndexedDB database for chat storage
 */
async function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("vtc_conversations", 1);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains("chats")) {
        db.createObjectStore("chats", { keyPath: "id", autoIncrement: true });
      }
    };
    
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Save a single message to IndexedDB
 */
async function saveMessage(role, content) {
  try {
    const db = await openDB();
    const tx = db.transaction("chats", "readwrite");
    const store = tx.objectStore("chats");
    
    const message = {
      role: role,
      content: content,
      timestamp: Date.now()
    };
    
    store.add(message);
    
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => {
        chatHistory.push(message);
        resolve(message);
      };
      tx.onerror = () => reject(tx.error);
    });
  } catch (error) {
    console.error("Failed to save message:", error);
  }
}

/**
 * Load all messages from IndexedDB
 */
async function loadMessages() {
  try {
    const db = await openDB();
    const tx = db.transaction("chats", "readonly");
    const store = tx.objectStore("chats");
    
    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  } catch (error) {
    console.error("Failed to load messages:", error);
    return [];
  }
}

/**
 * Clear all messages from IndexedDB
 */
async function clearMessages() {
  try {
    const db = await openDB();
    const tx = db.transaction("chats", "readwrite");
    const store = tx.objectStore("chats");
    store.clear();
    
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => {
        chatHistory = [];
        resolve();
      };
      tx.onerror = () => reject(tx.error);
    });
  } catch (error) {
    console.error("Failed to clear messages:", error);
  }
}

/**
 * Export chat history as JSON
 */
function exportChatHistory() {
  const data = JSON.stringify(chatHistory, null, 2);
  const blob = new Blob([data], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `vtc-chat-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
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
    
    chatContainer.innerHTML = `
      <div id="vtc-header" class="vtc-header">
        <div class="vtc-title">
          <span class="vtc-icon" title="Drag to move">🤖</span>
          <h3>Visual Trade Copilot</h3>
        </div>
        <div id="vtc-controls" class="vtc-controls">
          <button id="exportChat" title="Export Chat" class="vtc-control-btn">💾</button>
          <button id="clearChat" title="Clear Chat" class="vtc-control-btn">🗑️</button>
          <button id="minimizeChat" title="Minimize" class="vtc-control-btn">➖</button>
          <button id="closeChat" title="Close" class="vtc-control-btn">✖️</button>
        </div>
      </div>
      <div id="vtc-messages" class="vtc-messages"></div>
      <div id="vtc-input-area" class="vtc-input-area">
        <textarea id="vtc-input" class="vtc-input" placeholder="Ask a follow-up question..." rows="2"></textarea>
        <button id="vtc-send" class="vtc-send-btn" title="Capture new chart and ask">📸</button>
      </div>
      <div id="vtc-footer" class="vtc-footer">
        <span id="vtc-message-count">0 messages</span>
        <span id="vtc-status">Ready</span>
      </div>
    `;
    
    document.body.appendChild(chatContainer);
    
    // Attach event listeners
    document.getElementById("clearChat").onclick = handleClearChat;
    document.getElementById("exportChat").onclick = exportChatHistory;
    document.getElementById("minimizeChat").onclick = toggleMinimize;
    document.getElementById("closeChat").onclick = () => {
      chatContainer.classList.add("vtc-closing");
      setTimeout(() => {
        chatContainer.remove();
        chatContainer = null;
      }, 300);
    };
    
    // Send button functionality
    const sendBtn = document.getElementById("vtc-send");
    const input = document.getElementById("vtc-input");
    
    sendBtn.onclick = async () => {
      const question = input.value.trim();
      if (!question) {
        showNotification("Please enter a question first", "error");
        return;
      }
      
      // Disable button and show loading
      sendBtn.disabled = true;
      sendBtn.textContent = "⏳";
      showNotification("Capturing chart...", "info");
      
      try {
        // Request chart capture from background/popup
        const response = await chrome.runtime.sendMessage({
          action: "captureAndAnalyze",
          question: question
        });
        
        if (response && response.success) {
          // Message will be added via showOverlay action
          input.value = "";
          showNotification("Analysis complete!", "success");
        } else {
          throw new Error(response?.error || "Analysis failed");
        }
      } catch (error) {
        console.error("Send error:", error);
        showNotification("Error: " + error.message, "error");
      } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = "📸";
      }
    };
    
    // Enter key to send (Ctrl+Enter)
    input.onkeydown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        sendBtn.click();
      }
    };
    
    // Make draggable
    makeDraggable(chatContainer, document.getElementById("vtc-header"));
    
    // Animate in
    setTimeout(() => chatContainer.classList.add("vtc-visible"), 10);
  }
  
  return chatContainer;
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
    // Don't drag if clicking on buttons
    if (e.target.tagName === "BUTTON" || e.target.closest(".vtc-controls")) {
      return;
    }
    
    e.preventDefault();
    isDragging = true;
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    document.onmousemove = elementDrag;
    element.style.transition = "none"; // Disable transition while dragging
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
    element.style.right = "auto"; // Override fixed right position
  }
  
  function closeDragElement() {
    isDragging = false;
    document.onmouseup = null;
    document.onmousemove = null;
    element.style.transition = ""; // Re-enable transitions
  }
}

/**
 * Toggle minimize state
 */
function toggleMinimize() {
  chatContainer.classList.toggle("vtc-minimized");
  const btn = document.getElementById("minimizeChat");
  btn.textContent = chatContainer.classList.contains("vtc-minimized") ? "➕" : "➖";
}

/**
 * Handle clear chat with confirmation
 */
async function handleClearChat() {
  if (chatHistory.length === 0) {
    showNotification("Chat is already empty", "info");
    return;
  }
  
  if (confirm("Clear all chat history? This cannot be undone.")) {
    await clearMessages();
    renderMessages();
    showNotification("Chat cleared", "success");
  }
}

/**
 * Show temporary notification
 */
function showNotification(message, type = "info") {
  const statusEl = document.getElementById("vtc-status");
  if (statusEl) {
    statusEl.textContent = message;
    statusEl.className = `vtc-status ${type}`;
    setTimeout(() => {
      statusEl.textContent = "Ready";
      statusEl.className = "vtc-status";
    }, 3000);
  }
}

/**
 * Render all messages in the chat panel
 */
function renderMessages() {
  ensureChatUI();
  
  const msgBox = document.getElementById("vtc-messages");
  const countEl = document.getElementById("vtc-message-count");
  
  if (!msgBox) return;
  
  msgBox.innerHTML = "";
  
  if (chatHistory.length === 0) {
    const emptyMsg = document.createElement("div");
    emptyMsg.className = "vtc-empty-state";
    emptyMsg.innerHTML = `
      <p>📸 No messages yet</p>
      <p>Click the extension icon and analyze a chart to start!</p>
    `;
    msgBox.appendChild(emptyMsg);
  } else {
    chatHistory.forEach((msg, index) => {
      const msgDiv = document.createElement("div");
      msgDiv.className = `vtc-message vtc-${msg.role}`;
      msgDiv.dataset.index = index;
      
      const avatar = document.createElement("div");
      avatar.className = "vtc-avatar";
      avatar.textContent = msg.role === "user" ? "👤" : "🤖";
      
      const content = document.createElement("div");
      content.className = "vtc-message-content";
      
      const bubble = document.createElement("div");
      bubble.className = "vtc-bubble";
      bubble.innerHTML = formatMessageContent(msg.content);
      
      const timestamp = document.createElement("div");
      timestamp.className = "vtc-timestamp";
      timestamp.textContent = formatTimestamp(msg.timestamp);
      
      content.appendChild(bubble);
      content.appendChild(timestamp);
      
      msgDiv.appendChild(avatar);
      msgDiv.appendChild(content);
      
      msgBox.appendChild(msgDiv);
    });
  }
  
  // Update message count
  if (countEl) {
    countEl.textContent = `${chatHistory.length} message${chatHistory.length !== 1 ? 's' : ''}`;
  }
  
  // Scroll to bottom
  msgBox.scrollTop = msgBox.scrollHeight;
}

/**
 * Format message content with markdown-like syntax
 */
function formatMessageContent(text) {
  if (!text) return "<p>No content</p>";
  
  // Escape HTML first
  const escaped = text.replace(/[<>]/g, (m) => m === '<' ? '&lt;' : '&gt;');
  
  // Convert markdown-like formatting
  let formatted = escaped
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")  // Bold
    .replace(/\*(.*?)\*/g, "<em>$1</em>")               // Italic
    .replace(/\n\n/g, "</p><p>")                        // Paragraphs
    .replace(/\n/g, "<br>");                            // Line breaks
  
  return `<p>${formatted}</p>`;
}

/**
 * Format timestamp
 */
function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  // Less than 1 minute
  if (diff < 60000) {
    return "Just now";
  }
  // Less than 1 hour
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000);
    return `${mins} min${mins > 1 ? 's' : ''} ago`;
  }
  // Less than 24 hours
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  }
  // Show date
  return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ========== Message Listener ==========

/**
 * Listen for messages from popup.js and background.js
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Ping check for content script presence
  if (message.action === "ping") {
    sendResponse({ status: "ready" });
    return false; // Synchronous response
  }
  
  // Toggle chat panel visibility
  if (message.action === "toggleChat") {
    try {
      if (chatContainer && document.body.contains(chatContainer)) {
        // If exists and visible, close it
        if (chatContainer.classList.contains("vtc-visible")) {
          chatContainer.classList.add("vtc-closing");
          setTimeout(() => {
            if (chatContainer && chatContainer.parentNode) {
              chatContainer.remove();
            }
            chatContainer = null;
          }, 300);
        } else {
          // Show it
          chatContainer.classList.add("vtc-visible");
        }
      } else {
        // Create and show
        chatContainer = null; // Reset reference
        ensureChatUI();
        renderMessages();
      }
      sendResponse({ status: "toggled" });
    } catch (error) {
      console.error("Toggle chat error:", error);
      sendResponse({ status: "error", message: error.message });
    }
    return false;
  }
  
  if (message.action === "showOverlay") {
    // Handle async operation
    (async () => {
      const { question, response } = message.payload;
      
      // Save user question
      await saveMessage("user", question);
      
      // Save assistant response
      await saveMessage("assistant", response.answer);
      
      // Render updated chat
      renderMessages();
      
      // Show notification
      showNotification("Analysis complete", "success");
      
      sendResponse({ status: "displayed" });
    })();
    return true; // Keep channel open for async response
  }
  
  // Return chat history when requested
  if (message.action === "getChatHistory") {
    sendResponse({ history: chatHistory });
    return false; // Synchronous response
  }
});

// ========== Auto-load on Page Load ==========

(async function initChat() {
  try {
    const savedMessages = await loadMessages();
    if (savedMessages && savedMessages.length > 0) {
      chatHistory = savedMessages;
      // Auto-show panel if there's history
      ensureChatUI();
      renderMessages();
      console.log(`Loaded ${chatHistory.length} messages from IndexedDB`);
    }
  } catch (error) {
    console.error("Failed to initialize chat:", error);
  }
})();

console.log("✅ Visual Trade Copilot content script loaded (Phase 3A)");
