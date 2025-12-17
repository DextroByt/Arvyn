// arvyn-extension/socket.js
// Define the global Socket.IO client interface for Inter-Process Communication (IPC)

// Use the URL defined in the .env file and hardcoded in the server's main.py
const SERVER_HOST = 'http://localhost:8000';
let socket; 

try {
    // Check if the 'io' object (from lib/socket.io.min.js) is available globally
    if (typeof io === 'undefined') {
        throw new Error("Socket.IO client library ('io' object) not loaded.");
    }
    
    // Initialize the client connection
    socket = io(SERVER_HOST, {
        reconnection: true, // Attempt to reconnect if connection is lost
        transports: ['websocket'], // Prioritize WebSocket for low latency
        timeout: 10000 
    });

    // --- 1. Connection Success Handler ---
    socket.on('connect', () => {
        console.log('✅ Arvyn Sidecar connected successfully via Socket.IO');
        // Initial status update (This will be overwritten by app.js's initial display)
        if (typeof updateWidgetStatus === 'function') {
             updateWidgetStatus("Arvyn is Online. Ready for command.", 'ONLINE', null);
        }
    });

    // --- 2. Primary Status Listener (The "Nervous System") ---
    // Listens for 'status_update' events emitted by the LangGraph executor
    socket.on('status_update', (data) => {
        console.log("📩 Arvyn Engine Update:", data);
        
        // This is where the Conscious Pause Protocol is triggered
        // If data.status is 'AWAITING_APPROVAL', app.js will render the Transaction Bond
        if (typeof updateWidgetStatus === 'function') {
            updateWidgetStatus(data.message, data.status, data.details);
        }
    });

    // --- 3. Disconnection Handler (Mitigation 3.3.B: Emergency Halt) ---
    socket.on('disconnect', (reason) => {
        console.warn(`⚠️ Arvyn Sidecar disconnected from server. Reason: ${reason}`);
        
        // Explicitly alert the user if the server connection is lost during a transaction
        if (typeof updateWidgetStatus === 'function') {
             // CRITICAL_HALT is a signal to display an unrecoverable error message
             updateWidgetStatus(
                "CRITICAL ERROR: Agent connection lost. Verify transaction manually.", 
                'CRITICAL_HALT', 
                null
            );
        }
    });

    // --- 4. Error Handling ---
    socket.on('connect_error', (error) => {
        console.error("❌ Socket.IO connection error:", error);
    });
    
    // Make socket globally accessible to app.js for sending events like 'user_decision'
    window.arvynSocket = socket;
    
} catch (error) {
    console.error("❌ Socket.IO initialization failed:", error);
    
    // Fallback UI to display if the IPC client failed to load or connect
    const widgetRoot = document.getElementById('arvyn-omni-widget-root');
    if (widgetRoot) {
         widgetRoot.innerHTML = '<div class="arvyn-status" style="color:red; font-weight:bold;">ERROR: IPC Client Failed to Load. Check console.</div>';
    }
}