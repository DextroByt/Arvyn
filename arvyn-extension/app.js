// arvyn-extension/app.js

const WIDGET_ROOT = document.getElementById('arvyn-omni-widget-root');
const SERVER_HOST = 'http://localhost:8000'; // Redefine for fetch usage
let mediaRecorder;
let audioChunks =;
let isRecording = false;
let currentSessionId = null; 

// Utility function to update the widget UI state based on server pushes
function updateWidgetStatus(message, status_code, details = null) {
    if (!WIDGET_ROOT) return;

    // Clear and redraw base UI
    WIDGET_ROOT.innerHTML = `
        <div class="arvyn-status">${message}</div>
        <button id="arvyn-mic-button" ${status_code === 'AWAITING_APPROVAL'? 'disabled' : ''}>
            ${isRecording? 'Stop Recording' : 'Start Command'}
        </button>
    `;
    
    // Mitigation 3.2.B: Pre-emptive Text Feedback
    if (status_code === 'PARSING_COMPLETE' && details && details.transcribed_text) {
        WIDGET_ROOT.innerHTML += `<div class="arvyn-feedback">Agent interpretation: <em>"I heard: ${details.transcribed_text}"</em></div>`;
    }

    // Handle Critical Status: AWAITING_APPROVAL (Conscious Pause Handshake UI)
    if (status_code === 'AWAITING_APPROVAL' && details) {
        // Mandatory Transaction Bond Display (Mitigation 3.2.A)
        WIDGET_ROOT.innerHTML += `
            <div class="arvyn-card">
                <h4>⚠️ TRANSACTION BOND REQUIRED</h4>
                <p><strong>Action:</strong> ${details.action}</p>
                <p><strong>Amount:</strong> $${details.amount? details.amount.toFixed(2) : 'N/A'}</p>
                <p><strong>Recipient:</strong> ${details.recipient}</p>
                <p class="arvyn-status">Awaiting explicit ratification...</p>
                <button id="arvyn-approve-btn" class="arvyn-button-approve">Approve Transaction</button>
                <button id="arvyn-cancel-btn" class="arvyn-button-cancel">Cancel Execution</button>
            </div>
        `;
        // Attach listeners for the critical handshake signals
        document.getElementById('arvyn-approve-btn').addEventListener('click', () => handleDecision('approved', details.session_id));
        document.getElementById('arvyn-cancel-btn').addEventListener('click', () => handleDecision('cancelled', details.session_id));
    } 
    
    // Rebind the mic button event listener if not paused
    const micButton = document.getElementById('arvyn-mic-button');
    if (micButton &&!micButton.disabled) {
        micButton.addEventListener('click', toggleRecording);
    }
}

// --- Audio Capture Logic ---

async function toggleRecording() {
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            audioChunks =;
            
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                submitCommand(audioBlob);
                stream.getTracks().forEach(track => track.stop()); 
            };

            mediaRecorder.start();
            isRecording = true;
            updateWidgetStatus('Listening for command...', 'RECORDING');
        } catch (err) {
            console.error('Error accessing microphone:', err);
            updateWidgetStatus('Microphone access denied.', 'ERROR_MIC');
        }
    } else {
        mediaRecorder.stop();
        isRecording = false;
        updateWidgetStatus('Processing command...', 'UPLOADING');
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

        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }

        const data = await response.json();
        currentSessionId = data.session_id;
        console.log(`Command received, Session ID: ${currentSessionId}`);

    } catch (error) {
        console.error('Command submission failed:', error);
        updateWidgetStatus(`Error submitting command: ${error.message}`, 'ERROR_SUBMIT');
    }
}

// --- Conscious Pause Handshake Logic ---

function handleDecision(decision, session_id) {
    if (window.arvynSocket && session_id) {
        // Critical Socket.IO emission to resolve the LangGraph interrupt 
        window.arvynSocket.emit('user_decision', { 
            decision: decision, 
            session_id: session_id 
        });
        updateWidgetStatus(`Decision: ${decision.toUpperCase()}. Resuming execution...`, 'RESUMING');
    }
}

// --- Socket.IO Status Listener ---

if (window.arvynSocket) {
    window.arvynSocket.on('status_update', (payload) => {
        const { message, status, session_id, details } = payload;
        
        if (session_id) currentSessionId = session_id;

        updateWidgetStatus(message, status, details);
    });
} else {
    // Initial display status if the socket connection fails
    updateWidgetStatus("Arvyn is Offline. Connect server.", 'OFFLINE');
}


