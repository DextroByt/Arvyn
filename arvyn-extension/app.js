// arvyn-extension/app.js

(function() {
    const WIDGET_ROOT = document.getElementById('arvyn-omni-widget-root');
    const SERVER_HOST = window.ARVYN_CONFIG ? window.ARVYN_CONFIG.SERVER_HOST : 'http://127.0.0.1:8000';
    
    let mediaRecorder;
    let audioChunks = []; 
    let isRecording = false;
    let currentSessionId = null; 

    // Helper: Check for Mixed Content issues
    function checkSecurityContext() {
        if (window.location.protocol === 'https:' && SERVER_HOST.startsWith('http:')) {
            console.warn("⚠️ MIXED CONTENT WARNING: You are on HTTPS but connecting to HTTP. The browser might block this.");
        }
    }

    function updateWidgetStatus(message, status_code, details = null) {
        if (!WIDGET_ROOT) return;

        let html = `
            <div class="arvyn-status" data-status="${status_code}">${message}</div>
            <button id="arvyn-mic-button" ${status_code === 'AWAITING_APPROVAL' ? 'disabled' : ''}>
                ${isRecording ? 'Stop Recording' : 'Start Command'}
            </button>
        `;
        
        if (status_code === 'PARSING_COMPLETE' && details && details.transcribed_text) {
            html += `<div class="arvyn-feedback">Agent interpretation: <em>"I heard: ${details.transcribed_text}"</em></div>`;
        }

        if (status_code === 'AWAITING_APPROVAL' && details) {
            html += `
                <div class="arvyn-card">
                    <h4>⚠️ TRANSACTION BOND REQUIRED</h4>
                    <p><strong>Action:</strong> ${details.action}</p>
                    <p><strong>Amount:</strong> $${details.amount ? details.amount.toFixed(2) : 'N/A'}</p>
                    <p><strong>Recipient:</strong> ${details.recipient}</p>
                    <p class="arvyn-status">Awaiting explicit ratification...</p>
                    <button id="arvyn-approve-btn" class="arvyn-button-approve">Approve Transaction</button>
                    <button id="arvyn-cancel-btn" class="arvyn-button-cancel">Cancel Execution</button>
                </div>
            `;
        }

        if (status_code === 'ERROR_SUBMIT') {
            html += `<div style="font-size:10px; color: #ff9999; margin-top:5px;">Check console for Mixed Content errors.</div>`;
        }

        WIDGET_ROOT.innerHTML = html;

        if (status_code === 'AWAITING_APPROVAL' && details) {
            document.getElementById('arvyn-approve-btn').addEventListener('click', () => handleDecision('approved', details.session_id));
            document.getElementById('arvyn-cancel-btn').addEventListener('click', () => handleDecision('cancelled', details.session_id));
        }

        const micButton = document.getElementById('arvyn-mic-button');
        if (micButton && !micButton.disabled) {
            micButton.addEventListener('click', toggleRecording);
        }
    }

    async function toggleRecording() {
        if (!isRecording) {
            checkSecurityContext(); // Warn if likely to fail
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                audioChunks = []; 
                
                mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);

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
            console.log(`Sending audio to ${SERVER_HOST}/command ...`);
            const response = await fetch(`${SERVER_HOST}/command`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error(`Server status: ${response.status}`);

            const data = await response.json();
            currentSessionId = data.session_id;
            console.log(`Command received, Session ID: ${currentSessionId}`);

        } catch (error) {
            console.error('Command submission failed:', error);
            updateWidgetStatus(`Error: ${error.message}`, 'ERROR_SUBMIT');
        }
    }

    function handleDecision(decision, session_id) {
        if (window.arvynSocket && session_id) {
            window.arvynSocket.emit('user_decision', { 
                decision: decision, 
                session_id: session_id 
            });
            updateWidgetStatus(`Decision: ${decision.toUpperCase()}. Resuming...`, 'RESUMING');
        }
    }

    // Initialization
    setTimeout(() => {
        if (window.arvynSocket) {
            window.arvynSocket.on('status_update', (payload) => {
                updateWidgetStatus(payload.message, payload.status, payload.details);
            });
            window.arvynSocket.on('disconnect', () => {
                updateWidgetStatus("ERROR: Agent connection lost.", 'CRITICAL_HALT');
            });
            updateWidgetStatus("Arvyn Online. Ready.", 'IDLE');
        } else {
            updateWidgetStatus("Connecting to Agent...", 'OFFLINE');
        }
    }, 1000); // Increased timeout slightly to ensure socket loads

})();