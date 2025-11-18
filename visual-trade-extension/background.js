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
  
  // Handle screenshot capture request
  if (message.action === "captureScreenshot") {
    (async () => {
      try {
        // Use null to capture the current window's visible tab
        // activeTab permission should cover this when user interacts with extension
        const dataUrl = await new Promise((resolve, reject) => {
          chrome.tabs.captureVisibleTab(null, { format: 'png' }, (dataUrl) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else if (!dataUrl) {
              reject(new Error("Screenshot capture returned empty data"));
            } else {
              resolve(dataUrl);
            }
          });
        });
        
        sendResponse({ success: true, dataUrl: dataUrl });
      } catch (error) {
        console.error("Screenshot capture error:", error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true; // Keep channel open for async response
  }
  
  // Handle chat: pure AI (no command execution, no trade management)
  if (message.action === "captureAndAnalyze") {
    (async () => {
      try {
        const tabId = sender.tab.id;
        const question = message.question;
        const model = message.model || "balanced";
        const includeImage = message.includeImage || false;
        const uploadedImage = message.uploadedImage || null;
        
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
        
        // Handle image: either uploaded or capture screenshot
        if (uploadedImage) {
          // Use uploaded image (base64 string)
          const base64Data = uploadedImage.includes(',') ? uploadedImage.split(',')[1] : uploadedImage;
          const byteCharacters = atob(base64Data);
          const byteNumbers = new Array(byteCharacters.length);
          for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
          }
          const byteArray = new Uint8Array(byteNumbers);
          const blob = new Blob([byteArray], { type: 'image/png' });
          formData.append("image", blob, 'chart.png');
          console.log("📤 Using uploaded image");
        } else if (includeImage) {
          // Capture screenshot
          try {
            const dataUrl = await new Promise((resolve, reject) => {
              chrome.tabs.captureVisibleTab(null, { format: 'png' }, (dataUrl) => {
                if (chrome.runtime.lastError) {
                  reject(new Error(chrome.runtime.lastError.message));
                } else if (!dataUrl) {
                  reject(new Error("Screenshot capture returned empty data"));
                } else {
                  resolve(dataUrl);
                }
              });
            });
            
            // Convert data URL to blob
            const response = await fetch(dataUrl);
            const blob = await response.blob();
            formData.append("image", blob, 'chart.png');
            console.log("📷 Captured screenshot");
          } catch (captureError) {
            console.error("Screenshot capture failed:", captureError);
            throw new Error(`Failed to capture screenshot: ${captureError.message}`);
          }
        }
        
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

