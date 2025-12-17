// arvyn-extension/content.js

(function () {
    // Prevent duplicate injection
    if (document.getElementById('arvyn-widget-container')) return;

    console.log("🚀 Arvyn Omni-Widget Initializing (Glassmorphism Mode)...");

    // --- Configuration ---
    const BACKEND_URL = "http://127.0.0.1:8000";
    let socket = null;
    let mediaRecorder = null;
    let audioChunks = [];
    let currentSessionId = null; // Track active session for Halting

    // --- 1. Inject Widget UI ---
    function injectWidget() {
        const widgetHTML = `
            <div id="arvyn-widget-container">
                <div id="arvyn-header">
                    <span id="arvyn-title">
                        <div id="arvyn-status-dot"></div> Arvyn
                    </span>
                    <div class="arvyn-header-controls">
                        <button id="arvyn-halt-btn" class="arvyn-icon-btn" title="Emergency Stop">⏹</button>
                        <button id="arvyn-minimize-btn" class="arvyn-icon-btn" title="Minimize">_</button>
                    </div>
                </div>
                
                <div id="arvyn-chat-area">
                    <div class="arvyn-msg arvyn-msg-system">
                        👋 I'm online. Click 🎤 to speak.
                    </div>
                </div>
                
                <div id="arvyn-input-area">
                    <button id="arvyn-mic-btn">🎤</button>
                    <input type="text" id="arvyn-text-input" placeholder="Type or speak..." />
                </div>
            </div>
        `;

        const div = document.createElement('div');
        div.innerHTML = widgetHTML;
        document.body.appendChild(div);

        // --- Bind Window Events ---
        setupWindowControls();
        setupVoiceControls();
    }

    // --- 2. Window Control Logic (Minimize/Halt) ---
    function setupWindowControls() {
        const container = document.getElementById('arvyn-widget-container');
        const minBtn = document.getElementById('arvyn-minimize-btn');
        const haltBtn = document.getElementById('arvyn-halt-btn');

        // Minimize Handler
        minBtn.onclick = (e) => {
            e.stopPropagation(); // Prevent bubbling to container click
            container.classList.add('arvyn-minimized');
        };

        // Maximize Handler (Clicking the bubble)
        container.onclick = (e) => {
            // Only maximize if clicking the container itself (bubble mode)
            // and NOT if clicking inside the chat/input when fully open
            if (container.classList.contains('arvyn-minimized')) {
                container.classList.remove('arvyn-minimized');
            }
        };

        // Emergency Halt Handler
        haltBtn.onclick = (e) => {
            e.stopPropagation();
            if (currentSessionId) {
                console.log(`🛑 Halting Session: ${currentSessionId}`);
                socket.emit('halt_session', { session_id: currentSessionId });
                addSystemMessage("🛑 Emergency Halt Requested...", "FAILURE");
            } else {
                addSystemMessage("⚠️ No active session to halt.", "INFO");
            }
        };
    }

    // --- 3. Initialize Socket.IO ---
    try {
        // Ensure io is loaded (Manifest handles this, but safety check)
        if (typeof io === 'undefined') {
            console.error("Socket.io library not loaded!");
        } else {
            socket = io(BACKEND_URL, {
                transports: ['websocket'],
                upgrade: false
            });

            socket.on('connect', () => {
                document.getElementById('arvyn-status-dot').style.backgroundColor = "#00ff88";
            });

            socket.on('disconnect', () => {
                document.getElementById('arvyn-status-dot').style.backgroundColor = "#ff4444";
            });

            // --- Handle Status Updates ---
            socket.on('status_update', (data) => {
                const { status, message, session_id, details } = data;
                
                // Track ID for Halt functionality
                if (session_id) currentSessionId = session_id;

                if (status === 'AWAITING_APPROVAL') {
                    renderApprovalCard(session_id, details);
                    // Auto-maximize if minimized when approval is needed
                    document.getElementById('arvyn-widget-container').classList.remove('arvyn-minimized');
                } else {
                    addSystemMessage(message, status);
                }
            });
        }

    } catch (e) {
        console.error("Socket Init Failed:", e);
    }

    // --- 4. UI Helper Functions ---

    function scrollToBottom() {
        const chat = document.getElementById('arvyn-chat-area');
        chat.scrollTop = chat.scrollHeight;
    }

    function addSystemMessage(text, type = 'INFO') {
        const chat = document.getElementById('arvyn-chat-area');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'arvyn-msg arvyn-msg-system';
        
        if (type === 'FAILURE' || type === 'CRITICAL_HALT') {
            msgDiv.classList.add('arvyn-msg-error');
        }

        // Icons
        let icon = "";
        if (type === 'NAVIGATING') icon = "🧭";
        if (type === 'FILLING_FORM') icon = "✍️";
        if (type === 'EXECUTING') icon = "⚡";
        if (type === 'SUCCESS') icon = "🎉";
        if (type === 'FAILURE') icon = "⚠️";
        if (type === 'CRITICAL_HALT') icon = "🛑";

        msgDiv.innerHTML = `<strong>${icon}</strong> ${text}`;
        chat.appendChild(msgDiv);
        scrollToBottom();
    }

    function addUserMessage(text) {
        const chat = document.getElementById('arvyn-chat-area');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'arvyn-msg arvyn-msg-user';
        msgDiv.textContent = text;
        chat.appendChild(msgDiv);
        scrollToBottom();
    }

    function renderApprovalCard(sessionId, details) {
        const chat = document.getElementById('arvyn-chat-area');
        const card = document.createElement('div');
        card.className = 'arvyn-action-card';
        
        card.innerHTML = `
            <div style="font-weight:700; color:#b45309; margin-bottom:8px;">⚠️ Approval Required</div>
            <div style="font-size:13px; color:#444; margin-bottom:12px;">
                <strong>Action:</strong> ${details.action}<br>
                <strong>Value:</strong> $${details.amount}<br>
                <strong>To:</strong> ${details.recipient}
            </div>
            <div style="display:flex; gap:10px;">
                <button id="btn-approve-${sessionId}" style="flex:1; background:#10b981; color:white; border:none; padding:8px; border-radius:6px; cursor:pointer;">Approve</button>
                <button id="btn-reject-${sessionId}" style="flex:1; background:#ef4444; color:white; border:none; padding:8px; border-radius:6px; cursor:pointer;">Reject</button>
            </div>
        `;

        chat.appendChild(card);
        scrollToBottom();

        // Bind Events
        document.getElementById(`btn-approve-${sessionId}`).onclick = () => {
            socket.emit('user_decision', { session_id: sessionId, decision: 'approved' });
            card.remove();
            addSystemMessage("✅ Approved. Proceeding...", "SUCCESS");
        };

        document.getElementById(`btn-reject-${sessionId}`).onclick = () => {
            socket.emit('user_decision', { session_id: sessionId, decision: 'cancelled' });
            card.remove();
            addSystemMessage("🚫 Rejected by user.", "FAILURE");
        };
    }

    // --- 5. Voice Logic ---
    function setupVoiceControls() {
        const micBtn = document.getElementById('arvyn-mic-btn');
        const textInput = document.getElementById('arvyn-text-input');

        // Mic Click
        micBtn.onclick = async () => {
            if (!mediaRecorder || mediaRecorder.state === "inactive") {
                startRecording();
            } else {
                stopRecording();
            }
        };

        // Text Input (Enter Key)
        textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                // For now, text input isn't wired to backend in this snippet, 
                // but you can add a fetch similar to sendAudioCommand here.
                addUserMessage(textInput.value);
                textInput.value = '';
            }
        });
    }

    async function startRecording() {
        const micBtn = document.getElementById('arvyn-mic-btn');
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
            mediaRecorder.onstop = sendAudioCommand;

            mediaRecorder.start();
            micBtn.classList.add('recording');
            micBtn.textContent = "⏹";
            addSystemMessage("Listening...", "INFO");
        } catch (err) {
            console.error("Mic Error:", err);
            addSystemMessage("Mic Access Denied.", "FAILURE");
        }
    }

    function stopRecording() {
        const micBtn = document.getElementById('arvyn-mic-btn');
        if (mediaRecorder) {
            mediaRecorder.stop();
            micBtn.classList.remove('recording');
            micBtn.textContent = "🎤";
        }
    }

    async function sendAudioCommand() {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append("audio_file", audioBlob, "command.webm");

        addUserMessage("🎤 (Processing...)");

        try {
            await fetch(`${BACKEND_URL}/command`, { method: "POST", body: formData });
        } catch (err) {
            addSystemMessage("Server unreachable.", "FAILURE");
        }
    }

    // Run injection
    injectWidget();

})();