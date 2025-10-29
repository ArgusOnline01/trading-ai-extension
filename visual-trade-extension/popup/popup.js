// Visual Trade Copilot - Popup Script
// Handles chart capture and AI analysis requests

const API_BASE_URL = "http://127.0.0.1:8765";

// DOM Elements
const analyzeBtn = document.getElementById("analyze");
const toggleChatBtn = document.getElementById("toggleChat");
const modelSelect = document.getElementById("model");
const questionInput = document.getElementById("question");
const statusDiv = document.getElementById("status");
const serverIndicator = document.getElementById("server-indicator");
const serverText = document.getElementById("server-text");

// Check server status on popup open
checkServerStatus();

// Check for pending question from chat panel
(async () => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      const [result] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => sessionStorage.getItem("vtc_pending_question")
      });
      
      if (result && result.result) {
        questionInput.value = result.result;
        questionInput.focus();
        
        // Clear the pending question
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => sessionStorage.removeItem("vtc_pending_question")
        });
      }
    }
  } catch (error) {
    // Silently fail - no pending question
  }
})();

// Helper function to ensure content script is injected
async function ensureContentScript(tabId) {
  try {
    // Try to ping the content script
    await chrome.tabs.sendMessage(tabId, { action: "ping" });
    return true; // Content script already exists
  } catch (error) {
    // Content script not found, inject it
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
      
      // Wait for initialization
      await new Promise(resolve => setTimeout(resolve, 500));
      return true;
    } catch (injectError) {
      console.error("Failed to inject content script:", injectError);
      return false;
    }
  }
}

// Toggle chat button handler
toggleChatBtn.addEventListener("click", async () => {
  try {
    setStatus("loading", "Opening chat panel...");
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      throw new Error("No active tab found");
    }
    
    // Ensure content script is injected
    const contentScriptReady = await ensureContentScript(tab.id);
    
    if (!contentScriptReady) {
      throw new Error("Failed to initialize chat panel");
    }
    
    // Wait a moment for content script to fully initialize
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Toggle chat panel
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: "toggleChat"
      });
    } catch (msgError) {
      // Ignore "receiving end does not exist" - content script might have been re-injected
      if (!msgError.message.includes("Receiving end does not exist")) {
        throw msgError;
      }
    }
    
    setStatus("success", "✅ Chat panel opened!");
    
    // Close popup after short delay
    setTimeout(() => window.close(), 500);
  } catch (error) {
    console.error("Failed to toggle chat:", error);
    setStatus("error", "Failed to open chat panel: " + error.message);
  }
});

// Analyze button click handler
analyzeBtn.addEventListener("click", async () => {
  try {
    // Disable button during analysis
    analyzeBtn.disabled = true;
    setStatus("loading", "📸 Capturing chart...");
    
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab) {
      throw new Error("No active tab found");
    }
    
    // Ensure content script is injected
    setStatus("loading", "🔌 Checking chat panel...");
    const contentScriptReady = await ensureContentScript(tab.id);
    
    if (!contentScriptReady) {
      throw new Error("Failed to initialize chat panel. Please reload the page and try again.");
    }
    
    // Capture visible tab as image
    setStatus("loading", "📸 Capturing chart...");
    const imageDataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { 
      format: "png" 
    });
    
    setStatus("loading", "🔄 Converting image...");
    
    // Convert data URL to Blob
    const blob = await dataURLtoBlob(imageDataUrl);
    
    setStatus("loading", "🧠 Sending to AI...");
    
    // Get chat history from content script
    let chatHistory = [];
    try {
      const historyResponse = await chrome.tabs.sendMessage(tab.id, {
        action: "getChatHistory"
      });
      if (historyResponse && historyResponse.history) {
        chatHistory = historyResponse.history;
      }
    } catch (error) {
      // Silently continue without history - normal for first message
      // Suppress "receiving end does not exist" errors
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append("image", blob, "chart.png");
    
    const question = questionInput.value.trim() || "Analyze this trading chart using Smart Money Concepts. Provide market structure, POIs, and trade recommendations.";
    formData.append("question", question);
    
    const model = modelSelect.value;
    formData.append("model", model);
    
    // Send recent chat history (last 5 messages) for context
    if (chatHistory.length > 0) {
      const recentMessages = chatHistory.slice(-5).map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      formData.append("messages", JSON.stringify(recentMessages));
    }
    
    // Send to backend
    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: "POST",
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `Server returned ${response.status}`);
    }
    
    const data = await response.json();
    
    setStatus("loading", "✨ Displaying results...");
    
    // Send message to content script to show overlay
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: "showOverlay",
        payload: {
          question: question,
          response: data
        }
      });
    } catch (msgError) {
      // Message sent but response channel closed - this is fine
      console.log("Message sent successfully (response channel closed)");
    }
    
    setStatus("success", "✅ Analysis complete!");
    
    // Auto-clear status after 3 seconds
    setTimeout(() => {
      statusDiv.textContent = "";
      statusDiv.className = "status";
    }, 3000);
    
  } catch (error) {
    console.error("Analysis error:", error);
    setStatus("error", `❌ Error: ${error.message}`);
  } finally {
    analyzeBtn.disabled = false;
  }
});

// Helper: Convert data URL to Blob
async function dataURLtoBlob(dataURL) {
  const response = await fetch(dataURL);
  return await response.blob();
}

// Helper: Set status message
function setStatus(type, message) {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
}

// Helper: Check if server is online
async function checkServerStatus() {
  try {
    const response = await fetch(`${API_BASE_URL}/`, {
      method: "GET",
      signal: AbortSignal.timeout(3000)
    });
    
    if (response.ok) {
      serverIndicator.className = "status-indicator online";
      serverText.textContent = "Server online";
    } else {
      throw new Error("Server returned error");
    }
  } catch (error) {
    serverIndicator.className = "status-indicator offline";
    serverText.textContent = "Server offline";
    setStatus("error", "⚠️ Backend server not running. Start server first!");
  }
}

// Keyboard shortcut: Enter to analyze (with Ctrl/Cmd)
questionInput.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    analyzeBtn.click();
  }
});

