import os
import uvicorn
import socketio
import requests # Added for dynamic WS URL fetching
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncio
import uuid
from typing import Dict, Any
from playwright.sync_api import sync_playwright # Keep sync to match agent_graph

# Internal imports
from core.agent_graph import create_agent_executor, AgentState, graph_status_pusher
# We still import PageContextPlaceholder, but we will handle connection locally
from tools.browser import PageContextPlaceholder, ConnectionError as CDPConnectionError

load_dotenv()

# --- Configuration ---
SOCKETIO_SERVER_URL = os.getenv("SOCKETIO_SERVER_URL", "http://127.0.0.1:8000")

# --- Initialize FastAPI and Socket.IO ---
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI(title="Arvyn Engine API")
app_asgi = socketio.ASGIApp(sio, app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LangGraph
graph_executor = create_agent_executor(sio)

# Simulated STT function
async def transcribe_audio(audio_file_content: bytes) -> str:
    # Simulation: return a critical command for testing
    await asyncio.sleep(0.1)
    return "Transfer one hundred fifty dollars to Jane Doe, this is critical."

# --- Helper: Dynamic Browser Connection ---
def get_browser_page():
    """
    Connects to the running Chrome instance using the dynamic WebSocket URL.
    """
    try:
        # 1. Get the dynamic WebSocket URL from Chrome
        response = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
        if response.status_code != 200:
            raise Exception(f"Chrome Debugger API returned status {response.status_code}")
        
        data = response.json()
        ws_url = data.get("webSocketDebuggerUrl")
        
        if not ws_url:
            raise Exception("No webSocketDebuggerUrl found. Is Chrome running with --remote-debugging-port=9222?")
            
        print(f"🔗 Connecting to Chrome at: {ws_url}")

        # 2. Connect Playwright
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(ws_url)
        
        # 3. Get the active context and page
        default_context = browser.contexts[0]
        if not default_context.pages:
            # Create a new page if none exist
            page = default_context.new_page()
        else:
            # Attach to the first open tab
            page = default_context.pages[0]
            
        return page

    except requests.exceptions.ConnectionError:
        raise Exception("Could not reach http://127.0.0.1:9222. Please start Chrome with --remote-debugging-port=9222")
    except Exception as e:
        raise Exception(f"Browser Connection Failed: {str(e)}")


# --- Socket.IO Listener: Resolves Conscious Pause ---
@sio.on('user_decision')
async def handle_user_decision(sid, data: Dict[str, Any]):
    session_id = data.get("session_id")
    decision = data.get("decision")
    
    if not session_id or decision not in ["approved", "cancelled"]:
        print("Error: Invalid payload.")
        return

    print(f"Received user decision for Session {session_id}: {decision}")
    
    # Update state to resolve interrupt
    new_input = {"user_approved": decision == "approved"}
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        await graph_executor.ainvoke(new_input, config=config)
    except Exception as e:
        print(f"Error resuming graph: {e}")
        await graph_status_pusher(sio, session_id, "Critical Error during Resume.", 'CRITICAL_HALT')

# --- FastAPI Endpoint: Command Ingress ---
@app.post("/command", status_code=status.HTTP_202_ACCEPTED)
async def handle_command(audio_file: UploadFile = File(...)):
    if not audio_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    audio_content = await audio_file.read()
    transcribed_text = await transcribe_audio(audio_content)
    session_id = str(uuid.uuid4())
    
    print(f"🎤 New Command: {transcribed_text} (Session: {session_id})")

    try:
        # Use our new robust connection helper
        page = get_browser_page()
        
        # Wrap it in the placeholder for the graph state
        page_context_ref = PageContextPlaceholder(page)
        print(f"✅ CDP connection established. Page Title: {page.title()}")
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        await graph_status_pusher(sio, session_id, "Browser Connection Lost.", 'CDP_DISCONNECTED')
        raise HTTPException(status_code=503, detail=str(e))
        
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
    
    config = {"configurable": {"thread_id": session_id}}
    
    async def run_graph():
        try:
            await graph_executor.ainvoke(initial_state, config=config)
        except Exception as e:
            print(f"Graph exception: {e}")
            await graph_status_pusher(sio, session_id, "Internal Execution Error.", 'CRITICAL_HALT')

    asyncio.create_task(run_graph())
    return {"message": "Command initiated", "session_id": session_id}

if __name__ == "__main__":
    # STRICT HOST SETTING
    uvicorn.run(app_asgi, host="127.0.0.1", port=8000, ws_ping_interval=10, ws_ping_timeout=10)