# arvyn-server/main.py
import os
import uvicorn
import socketio
import asyncio
import uuid
import json
from typing import Dict, Any, Optional

# FastAPI and ASGI dependencies
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Agent Core modules and tools
from core.agent_graph import create_agent_executor, AgentState, graph_status_pusher
from tools.browser import init_browser_connection, ConnectionError as CDPConnectionError, PageContextPlaceholder

# Load environment variables from .env file [cite: 41, 181]
load_dotenv()

# --- Configuration & Initialization ---
# Environment variables are loaded for security and configuration [cite: 44, 183]
SOCKETIO_SERVER_URL = os.getenv("SOCKETIO_SERVER_URL", "http://localhost:8000")
CDP_DEBUG_PORT = os.getenv("CDP_DEBUG_PORT", "9222")
STT_API_KEY = os.getenv("STT_API_KEY") 

# Initialize Socket.IO Server: Using an ASGI mode for integration with FastAPI [cite: 10, 257]
# Cors is restricted in production, open for local dev here [cite: 262]
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*", 
    client_manager=None 
)

# Initialize FastAPI App [cite: 10, 257]
app = FastAPI(title="Arvyn Engine API", version="1.0.0")

# Create the ASGI application with the Socket.IO middleware [cite: 257]
app_asgi = socketio.ASGIApp(sio, app)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the LangGraph executor without passing sio at compile time for newer versions [cite: 263, 343]
graph_executor = create_agent_executor(sio)

# --- Utility Function: Simulated STT ---
async def transcribe_audio(audio_file_content: bytes) -> str:
    """Simulates transcription of the raw audio blob. Returns a critical command for E2E testing."""
    # Simulation: return the critical command for focused testing [cite: 263]
    await asyncio.sleep(0.1) 
    return "Transfer one hundred fifty dollars to Jane Doe, this is critical."

# --- Socket.IO Listener: Resolves Conscious Pause ---
@sio.on('user_decision')
async def handle_user_decision(sid: str, data: Dict[str, Any]):
    """
    Listens for the 'user_decision' event from the Sidecar.
    This external signal resolves the LangGraph's Conscious Pause. [cite: 70, 259]
    """
    session_id: Optional[str] = data.get("session_id")
    decision: Optional[str] = data.get("decision")

    if not session_id or decision not in ["approved", "cancelled"]:
        print(f"Error: Invalid user_decision payload for session {session_id}")
        return

    print(f"Received user decision for Session {session_id}: {decision}")

    # Prepare input to update the LangGraph state flag [cite: 70, 259]
    new_input = {"user_approved": decision == "approved"}

    try:
        # Resume the specific graph thread using the stored thread_id
        # Explicitly pass 'sio' in the config for node access [cite: 117, 265]
        config = {
            "configurable": {"thread_id": session_id},
            "sio": sio 
        }
        
        # ainvoke resumes the graph from the interrupted checkpoint [cite: 266]
        await graph_executor.ainvoke(new_input, config=config)
    except Exception as e:
        print(f"Error resuming graph for session {session_id}: {e}")
        await graph_status_pusher(sio, session_id, "Critical Error during Resume.", 'CRITICAL_HALT')


# --- FastAPI Endpoint: Command Ingress ---
@app.post("/command", status_code=status.HTTP_202_ACCEPTED)
async def handle_command(audio_file: UploadFile = File(...)):
    """
    Handles the raw audio file POST request from the Sidecar.
    Initiates the entire agent execution flow asynchronously. [cite: 67, 258]
    """
    if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be audio.")
    
    audio_content = await audio_file.read()
    
    # 1. Transcribe audio (Simulation) [cite: 268]
    transcribed_text = await transcribe_audio(audio_content)
    
    # 2. Generate unique session ID (used as LangGraph thread_id) [cite: 268]
    session_id = str(uuid.uuid4())
    print(f"Initiating session: {session_id}")

    # 3. Establish Playwright/CDP connection [cite: 81, 268]
    try:
        # Connects to the active Chrome instance via CDP [cite: 82, 275]
        page = init_browser_connection()
        page_context_ref = PageContextPlaceholder(page)
        print(f"CDP connection established for session {session_id}.")
    except CDPConnectionError as e:
        # Mitigation 3.3.A & C: CDP Connection Failure handling [cite: 63, 269]
        error_msg = str(e)
        print(f"CDP connection failed: {error_msg}")
        await graph_status_pusher(sio, session_id, "CDP Connection Lost. Cannot execute.", 'CDP_DISCONNECTED')
        raise HTTPException(status_code=503, detail="Actuation system offline.") from e

    # 4. Initialize LangGraph State [cite: 95, 271]
    initial_state = AgentState(
        input=transcribed_text,
        intent_json={},
        status='RECEIVED',
        user_approved=False,
        error=None,
        page_context=page_context_ref, 
        retries=0,
        session_id=session_id
    )

    # 5. Launch LangGraph execution ASYNCHRONOUSLY [cite: 68, 258]
    config = {
        "configurable": {"thread_id": session_id},
        "sio": sio # Inject sio here for node access
    }

    async def run_graph():
        """Worker function to run the graph executor."""
        try:
            # ainvoke saves the initial state checkpoint and begins execution [cite: 272]
            await graph_executor.ainvoke(initial_state, config=config)
        except Exception as e:
            print(f"Unhandled graph exception in session {session_id}: {e}")
            await graph_status_pusher(sio, session_id, "Internal Execution Error.", 'CRITICAL_HALT')

    # Background task ensures the API endpoint remains non-blocking [cite: 69, 258]
    asyncio.create_task(run_graph())

    return {"message": "Command initiated", "session_id": session_id}

# --- Server Startup ---
if __name__ == "__main__":
    # Optimized for WebSockets with standard timeouts [cite: 273]
    uvicorn.run(
        app_asgi, 
        host="0.0.0.0", 
        port=8000, 
        ws_ping_interval=10, 
        ws_ping_timeout=10 
    )