// arvyn-extension/socket.js

(function() {
    // 1. Define Config: Use 127.0.0.1 to avoid IPv6/localhost resolution issues
    window.ARVYN_CONFIG = {
        SERVER_HOST: 'http://127.0.0.1:8000' 
    };

    console.log("Arvyn: Initializing Socket Connection to", window.ARVYN_CONFIG.SERVER_HOST);

    try {
        if (typeof io === 'undefined') {
            throw new Error("Socket.IO library not loaded. Check lib/socket.io.min.js");
        }

        const socket = io(window.ARVYN_CONFIG.SERVER_HOST, {
            reconnection: true,
            reconnectionAttempts: 5,
            transports: ['websocket', 'polling'] 
        });

        socket.on('connect', () => {
            console.log('✅ Arvyn Sidecar connected via Socket.IO');
            const statusEl = document.querySelector('.arvyn-status');
            if(statusEl) statusEl.innerText = "Arvyn Online. Ready.";
        });

        socket.on('disconnect', () => {
            console.warn('⚠️ Arvyn Sidecar disconnected.');
        });

        socket.on('connect_error', (err) => {
            console.error('❌ Socket Connection Error:', err);
            // This usually happens due to Mixed Content (HTTPS page -> HTTP server)
        });

        window.arvynSocket = socket;

    } catch (error) {
        console.error("CRITICAL: Socket.IO initialization failed:", error);
        const root = document.getElementById('arvyn-omni-widget-root');
        if (root) {
            root.innerHTML = `<div class="arvyn-status" style="background:red; color:white;">Connection Error: ${error.message}</div>`;
        }
    }
})();