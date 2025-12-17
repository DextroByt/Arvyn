// arvyn-extension/app.js
// Core UI Logic, Audio Capture, and Conscious Pause Handshake

const WIDGET_ROOT = document.getElementById('arvyn-omni-widget-root');
const SERVER_HOST = 'http://localhost:8000'; // Server API gateway endpoint

let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let currentSessionId = null; 

/**
 * Dynamically updates the Omni-Widget's view state and content.
 * This is the primary handler for status_update events from the server.
 */
function updateWidgetStatus(message, status_code, details = null) {
    if (!WIDGET_ROOT) return;

    // 1. Clear and redraw the base UI
    // Disable mic during the mandatory Conscious Pause or Critical Halts
    const isPaused = status_code === 'AWAITING_APPROVAL' || status_code === 'CRITICAL_HALT';
    
    WIDGET_ROOT.innerHTML = `
        <div class="arvyn-status ${isPaused ? 'arvyn-status-pause' : ''}">${message}</div>
        <button id="arvyn-mic-button" ${isPaused ? 'disabled' : ''}>
            ${isRecording ? 'Stop Recording' : 'Start Command'}
        </button>
    `;

    // 2. Mitigation 3.2.B: Pre-emptive Text Feedback (Interpretation validation)
    if (status_code === 'PARSING_COMPLETE' && details && details.transcribed_text) {
        const feedback = document.createElement('div');
        feedback.className = 'arvyn-feedback';
        feedback.innerHTML = `Interpretation: <em>"${details.transcribed_text}"</em>`;
        WIDGET_ROOT.appendChild(feedback);
    }

    // 3. Handle Critical Status: AWAITING_APPROVAL (Conscious Pause Handshake)
    if (status_code === 'AWAITING_APPROVAL' && details) {
        const card = document.createElement('div');
        card.className = 'arvyn-card';
        card.innerHTML = `
            <h4>🛡️ TRANSACTION BOND</h4>
            <p><strong>Action:</strong> ${details.action || 'N/A'}</p>
            <p><strong>Amount:</strong> $${details.amount !== undefined ? parseFloat(details.amount).toFixed(2) : 'N/A'}</p>
            <p><strong>To:</strong> ${details.recipient || 'N/A'}</p>
            <div style="margin-top: 15px; display: flex; gap: 10px;">
                <button id="arvyn-approve-btn" class="arvyn-button-approve">Approve</button>
                <button id="arvyn-cancel-btn" class="arvyn-button-cancel">Cancel</button>
            </div>
        `;
        WIDGET_ROOT.appendChild(card);

        // Attach listeners for the ratification signals
        document.getElementById('arvyn-approve-btn').addEventListener('click', () => handleDecision('approved', details.session_id));
        document.getElementById('arvyn-cancel-btn').addEventListener('click', () => handleDecision('cancelled', details.session_id));
    }
    
    // 4. Rebind the mic button listener
    const micButton = document.getElementById('arvyn-mic-button');
    if (micButton && !micButton.disabled) {
        micButton.addEventListener('click', toggleRecording);
    }
}

// --- Audio Capture Logic (MediaRecorder API) ---

async function toggleRecording() {
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                submitCommand(audioBlob);
                stream.getTracks().forEach(track => track.stop()); // Release mic
            };

            mediaRecorder.start();
            isRecording = true;
            updateWidgetStatus('Listening...', 'RECORDING');
        } catch (err) {
            console.error('Mic Access Denied:', err);
            updateWidgetStatus('Microphone Error', 'ERROR_MIC');
        }
    } else {
        mediaRecorder.stop();
        isRecording = false;
        updateWidgetStatus('Processing...', 'UPLOADING');
    }
}

async function submitCommand(audioBlob) {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'command.webm');
    
    try {
        const response = await fetch(`${SERVER_HOST}/command`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Server Ingress Failed');
        
        const data = await response.json();
        currentSessionId = data.session_id;
        console.log(`Session Started: ${currentSessionId}`);
    } catch (error) {
        updateWidgetStatus('Submission Failed', 'ERROR_SUBMIT');
    }
}

// --- Handshake Logic ---

function handleDecision(decision, session_id) {
    if (window.arvynSocket && session_id) {
        window.arvynSocket.emit('user_decision', {
            decision: decision,
            session_id: session_id
        });
        updateWidgetStatus('Decision Sent. Resuming...', 'RESUMING');
    }
}

// --- Initialize / Status Listener ---

if (window.arvynSocket) {
    window.arvynSocket.on('status_update', (payload) => {
        updateWidgetStatus(payload.message, payload.status, payload.details);
    });
} else {
    // Initial UI state
    updateWidgetStatus("Arvyn: Ready", 'ONLINE', null);
}