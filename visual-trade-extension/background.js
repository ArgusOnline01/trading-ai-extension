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
  
  // Handle chart capture and analysis from chat panel
  if (message.action === "captureAndAnalyze") {
    (async () => {
      try {
        const tabId = sender.tab.id;
        const question = message.question;
        const includeImage = message.includeImage !== false; // Default to true for backward compatibility
        
        // Phase 3B.2: Get model from message or use default
        const model = message.model || "balanced";
        const reasonedCommands = !!message.reasonedCommands;
        
        // Phase 3C: Auto-route to /hybrid for text-only models with images
        // Note: "balanced" (GPT-5 Search) uses hybrid with caching
        //       "fast" (GPT-5 Chat) has native vision - no caching needed
        //       "advanced" (GPT-4o) has native vision
        const textOnlyModels = ["balanced", "gpt5-mini", "gpt-5-mini", "gpt-5-mini-2025-08-07", "gpt-5-search-api", "gpt-5-search-api-2025-10-14"];
        const useHybrid = includeImage && textOnlyModels.includes(model);
        
        // Phase 3B.1 & 4A.1: Capture or use uploaded image
        let blob = null;
        if (includeImage) {
          // Phase 4A.1: Use uploaded image if provided, otherwise capture
          if (message.uploadedImage) {
            // Convert base64 to blob
            const base64Data = message.uploadedImage;
            const byteCharacters = atob(base64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
              byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            blob = new Blob([byteArray], { type: 'image/png' });
            console.log("📤 Using uploaded image");
          } else {
            // Capture the visible tab
            const imageDataUrl = await chrome.tabs.captureVisibleTab(sender.tab.windowId, {
              format: "png"
            });
            
            // Convert to blob
            const response = await fetch(imageDataUrl);
            blob = await response.blob();
            console.log("📸 Captured visible tab");
          }
        }
        
        // Get chat history and session context (Phase 3B)
        let chatHistory = [];
        let sessionContext = {};
        try {
          const historyResponse = await chrome.tabs.sendMessage(tabId, {
            action: "getChatHistory"
          });
          if (historyResponse && historyResponse.history) {
            chatHistory = historyResponse.history;
          }
          if (historyResponse && historyResponse.context) {
            sessionContext = historyResponse.context;
          }
        } catch (error) {
          console.log("No history available");
        }
        
        // Prepare form data
        const formData = new FormData();
        // Phase 3B.1: Only append image if captured
        if (blob) {
          formData.append("image", blob, "chart.png");
        }
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
        } else {
          console.log("⚠️ No chat history found - first message in session");
        }
        
        // Phase 4D.3: Attach last 10 trades from backend to system context
        try {
          const recentTrades = await fetch(`http://127.0.0.1:8765/performance/all?limit=10`).then(r => r.json());
          if (recentTrades && Array.isArray(recentTrades)) {
            sessionContext = sessionContext || {};
            sessionContext.recent_trades = recentTrades;
          }
        } catch (e) {
          console.warn("Failed to fetch recent trades for context:", e);
        }
        
        // Phase 4D.4: Ensure sessions data is preserved (from content.js getChatHistory)
        // all_sessions should already be in sessionContext from content.js, but ensure it exists

        // Phase 4D.3.2: If reasoned commands are enabled, execute commands BEFORE AI call
        let commandResult = null;
        if (reasonedCommands) {
          try {
            // Execute command (or detect if no command) - include session context
            const cmdContext = {
              current_model: model,
              all_sessions: sessionContext?.all_sessions || [],
              current_session_id: sessionContext?.current_session_id
            };
            const cmdRes = await fetch('http://127.0.0.1:8765/memory/system/command', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ command: question, context: cmdContext })
            }).then(r=>r.json());
            
            // If a command was detected and executed, inject result into context
            if (cmdRes && cmdRes.detected_command) {
              commandResult = cmdRes;
              // Inject command result into session context so AI knows what happened
              sessionContext = sessionContext || {};
              sessionContext.last_command_result = {
                command: cmdRes.command,
                success: cmdRes.success,
                message: cmdRes.message,
                data: cmdRes.data
              };
              console.log(`[COMMAND] Executed: ${cmdRes.command}, success: ${cmdRes.success}`);
            }
          } catch (e) {
            console.warn('Reasoned command execution failed:', e);
          }
        }

        // Add session context (Phase 3B + 4D.3 + command result)
        if (Object.keys(sessionContext).length > 0) {
          formData.append("context", JSON.stringify(sessionContext));
        }
        
        // Phase 3C: Add session ID for caching
        const sessionId = message.sessionId || "default";
        formData.append("session_id", sessionId);
        
        // Phase 3C: Determine endpoint (hybrid for text-only models with images)
        const endpoint = useHybrid ? "/hybrid" : "/ask";
        console.log(`[ROUTE] Using ${endpoint} endpoint for model: ${model}${useHybrid ? " (HYBRID MODE)" : ""}`);
        
        // Send to backend
        const apiResponse = await fetch(`http://127.0.0.1:8765${endpoint}`, {
          method: "POST",
          body: formData
        });
        
        if (!apiResponse.ok) {
          throw new Error(`Server returned ${apiResponse.status}`);
        }
        
        let data = await apiResponse.json();

        // Phase 4D.3.2: If command was executed, append result to AI response
        if (commandResult && commandResult.success && commandResult.message) {
          const joined = (data.answer || data.response || '') + "\n\n" + commandResult.message;
          if (data.answer !== undefined) data.answer = joined; else data.response = joined;
        }
        
        // Phase 3C: Include hybrid mode info in response
        if (useHybrid) {
          data.hybrid_mode = true;
          data.vision_model = data.vision_model || "gpt-4o";
          data.reasoning_model = data.reasoning_model || model;
        }
        
        // Phase 4A.2: For Log Trade, return data directly
        if (message.forLogTrade) {
          sendResponse({ 
            success: true, 
            answer: data.answer || data.response || "",
            model: data.model,
            tokens: data.tokens
          });
        } else {
          // Send result back to content script via showOverlay
          await chrome.tabs.sendMessage(tabId, {
            action: "showOverlay",
            payload: {
              question: question,
              response: data,
              hybrid_mode: useHybrid
            }
          });
          
          sendResponse({ success: true });
        }
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

