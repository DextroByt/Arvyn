# arvyn-server/main.py

import os
import uvicorn
import socketio
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncio
import uuid
from typing import Dict, Any

from core.agent_graph import create_agent_executor, AgentState, graph_status_pusher
from tools.browser import init_browser_connection
from tools.browser import ConnectionError as CDPConnectionError
from tools.browser import PageContextPlaceholder 

load_dotenv()

# --- Configuration ---
SOCKETIO_SERVER_URL = os.getenv("SOCKETIO_SERVER_URL", "http://localhost:8000")
STT_API_KEY = os.getenv("STT_API_KEY") 

# --- Initialize FastAPI and Socket.IO ---
# Use the thread_id as the room ID for isolated IPC
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*", client_manager=socketio.AsyncRedisManager if os.getenv("REDIS_URL") else None)
app = FastAPI(title="Arvyn Engine API")
app_asgi = socketio.ASGIApp(sio, app)

# CORS middleware (highly restricted in production, open for local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the LangGraph executor with the SocketIO server reference
graph_executor = create_agent_executor(sio)


# Simulated STT function
async def transcribe_audio(audio_file_content: bytes) -> str:
    # Simulation: return the critical command for focused testing
    await asyncio.sleep(0.1) 
    return "Transfer one hundred fifty dollars to Jane Doe, this is critical."

# --- Socket.IO Listener: Resolves Conscious Pause ---

@sio.on('user_decision')
async def handle_user_decision(sid, data: Dict[str, Any]):
    session_id = data.get("session_id")
    decision = data.get("decision")
    
    if not session_id or decision not in ["approved", "cancelled"]:
        print("Error: Invalid or missing session_id/decision in user_decision payload.")
        return

    print(f"Received user decision for Session {session_id}: {decision}")

    # LangGraph's checkpointer handles loading the state implicitly when using the thread_id
    new_input = {"user_approved": decision == "approved"}

    try:
        # Resume the specific graph thread using the stored thread_id 
        config = {"configurable": {"thread_id": session_id}}
        
        # Ainvoke resumes the graph from the interrupted state
        await graph_executor.ainvoke(new_input, config=config)
        
    except Exception as e:
        print(f"Error resuming graph for session {session_id}: {e}")
        await graph_status_pusher(sio, session_id, "Critical Error during Resume.", 'CRITICAL_HALT')


# --- FastAPI Endpoint: Command Ingress ---

@app.post("/command", status_code=status.HTTP_202_ACCEPTED)
async def handle_command(audio_file: UploadFile = File(...)):
    if not audio_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be audio.")
    
    audio_content = await audio_file.read()

    # 1. Transcribe audio (Simulation)
    transcribed_text = await transcribe_audio(audio_content)
    
    # 2. Generate unique session ID (LangGraph thread_id)
    session_id = str(uuid.uuid4())
    
    # 3. Establish Playwright/CDP connection and acquire Page object
    try:
        page = init_browser_connection()
        page_context_ref = PageContextPlaceholder(page) # Wrap non-serializable object
        print(f"CDP connection established for session {session_id}.")
    except CDPConnectionError as e:
        # Mitigation 3.3.A & C: CDP Connection Failure leads to immediate status push and termination
        error_msg = str(e)
        if "CDP_DISCONNECTED" in error_msg:
            print(f"CDP connection failed: {error_msg}")
            await graph_status_pusher(sio, session_id, "CDP Connection Lost. Cannot execute.", 'CDP_DISCONNECTED')
            raise HTTPException(status_code=503, detail="Actuation system offline.")
        else:
            raise

    # 4. Initialize LangGraph State
    initial_state = AgentState(
        input=transcribed_text,
        intent_json={},
        status='RECEIVED',
        user_approved=False,
        error=None,
        page_context=page_context_ref, # Pass reference
        retries=0,
        session_id=session_id
    )

    # 5. Launch LangGraph execution ASYNCHRONOUSLY
    config = {"configurable": {"thread_id": session_id}}
    
    async def run_graph():
        try:
            # Ainvoke saves the initial state checkpoint and begins execution
            await graph_executor.ainvoke(initial_state, config=config)
        except Exception as e:
            print(f"Unhandled graph exception in session {session_id}: {e}")
            await graph_status_pusher(sio, session_id, "Internal Execution Error.", 'CRITICAL_HALT')

    asyncio.create_task(run_graph())

    # Return the session ID immediately to the client
    return {"message": "Command initiated", "session_id": session_id}


if __name__ == "__main__":
    uvicorn.run(app_asgi, host="0.0.0.0", port=8000, ws_ping_interval=10, ws_ping_timeout=10) # Optimized for WebSockets


