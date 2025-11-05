// Visual Trade Copilot - Background Service Worker
// Handles extension lifecycle and keeps service worker alive

// Extension installed/updated
chrome.runtime.onInstalled.addListener((details) => {
  console.log("🚀 Visual Trade Copilot installed/updated");
  
  if (details.reason === "install") {
    console.log("First time installation - welcome!");
    // Could open welcome page or setup instructions
  } else if (details.reason === "update") {
    console.log(`Updated from version ${details.previousVersion}`);
  }
});

// Extension startup
chrome.runtime.onStartup.addListener(() => {
  console.log("🔄 Visual Trade Copilot service worker started");
});

// Handle messages from content scripts or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log("Message received:", message);
  
  // Handle chat: pure AI (no command execution, no trade management)
  if (message.action === "captureAndAnalyze") {
    (async () => {
      try {
        const tabId = sender.tab.id;
        const question = message.question;
        const model = message.model || "balanced";
        
        // Get chat history (kept for context)
        let chatHistory = [];
        try {
          const historyResponse = await chrome.tabs.sendMessage(tabId, {
            action: "getChatHistory"
          });
          if (historyResponse && historyResponse.history) {
            chatHistory = historyResponse.history;
          }
        } catch (error) {
          console.log("No history available");
        }
        
        // Prepare form data
        const formData = new FormData();
        formData.append("question", question);
        formData.append("model", model);
        
        // Add recent messages for context (Phase 3B: up to 50 messages)
        if (chatHistory.length > 0) {
          const recentMessages = chatHistory.slice(-50).map(msg => ({
            role: msg.role,
            content: msg.content
          }));
          console.log("📚 Sending", recentMessages.length, "messages to backend for context");
          formData.append("messages", JSON.stringify(recentMessages));
        }
        
        // Pure AI chat endpoint
        const requestUrl = `http://127.0.0.1:8765/ask`;
        
        // Send to backend
        const apiResponse = await fetch(requestUrl, {
            method: "POST",
            body: formData
        });
        
        if (!apiResponse.ok) {
          throw new Error(`Server returned ${apiResponse.status}`);
        }
        
        let data = await apiResponse.json();
        
        // Send result back to content script via showOverlay
        await chrome.tabs.sendMessage(tabId, {
          action: "showOverlay",
          payload: {
            question: question,
            response: data
          }
        });
        
        sendResponse({ success: true });
      } catch (error) {
        console.error("Capture and analyze error:", error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true; // Keep channel open for async response
  }
  
  // Handle any other background tasks
  sendResponse({ status: "received" });
  return true;
});

// Keep service worker alive (Chrome may put it to sleep)
// This is a lightweight keepalive mechanism
let keepAliveInterval;

function startKeepAlive() {
  if (keepAliveInterval) return;
  
  keepAliveInterval = setInterval(() => {
    // Send a simple message to keep alive
    chrome.runtime.getPlatformInfo(() => {
      // Just a no-op to keep the service worker active
    });
  }, 20000); // Every 20 seconds
}

function stopKeepAlive() {
  if (keepAliveInterval) {
    clearInterval(keepAliveInterval);
    keepAliveInterval = null;
  }
}

// Start keepalive
startKeepAlive();

// Clean up on suspend
chrome.runtime.onSuspend.addListener(() => {
  console.log("⏸️ Service worker suspending");
  stopKeepAlive();
});

console.log("✅ Visual Trade Copilot background service worker ready");

