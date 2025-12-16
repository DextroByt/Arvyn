// arvyn-extension/socket.js

// Define the global Socket.IO client interface 
const SERVER_HOST = 'http://localhost:8000'; 
let socket;

try {
    // 'io' object is available globally due to previous script injection
    socket = io(SERVER_HOST, {
        reconnection: true,
        transports: ['websocket']
    });

    socket.on('connect', () => {
        console.log('Arvyn Sidecar connected via Socket.IO');
    });

    socket.on('disconnect', () => {
        console.warn('Arvyn Sidecar disconnected from server.');
        // Mitigation 3.3.B: Explicitly alert the user if the server connection is lost
        if (typeof updateWidgetStatus === 'function') {
            updateWidgetStatus("ERROR: Agent connection lost. Please verify your bank account manually.", 'CRITICAL_HALT', null);
        }
    });

    // Make socket globally accessible to app.js
    window.arvynSocket = socket;

} catch (error) {
    console.error("Socket.IO initialization failed:", error);
    // Ensure offline status is displayed if the client failed to load the library
    if (document.getElementById('arvyn-omni-widget-root')) {
        document.getElementById('arvyn-omni-widget-root').innerHTML = '<div class="arvyn-status">ERROR: IPC Client Failed to Load.</div>';
    }
}


