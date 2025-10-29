// Visual Trade Copilot - Popup Script (Phase 3B.1: Redesigned UI)
// Handles quick actions and model selection

const API_BASE_URL = "http://127.0.0.1:8765";

// DOM Elements
const newConversationBtn = document.getElementById("newConversation");
const toggleChatBtn = document.getElementById("toggleChat");
const viewSessionsBtn = document.getElementById("viewSessions");
const quickAnalyzeBtn = document.getElementById("quickAnalyze");
const statusDiv = document.getElementById("status");
const serverIndicator = document.getElementById("server-indicator");
const serverText = document.getElementById("server-text");
const modelOptions = document.querySelectorAll(".model-option");

// Selected model state
let selectedModel = "balanced";

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
