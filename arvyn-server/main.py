import os
import uvicorn
import socketio
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncio
import uuid
from typing import Dict, Any
# Use Async API
from playwright.async_api import async_playwright, Page 
from google import genai
from google.genai import types

# Internal imports
# We import ACTIVE_SESSIONS to register the browser connection globally
from core.agent_graph import create_agent_executor, AgentState, graph_status_pusher, ACTIVE_SESSIONS

load_dotenv()

# --- Configuration ---
SOCKETIO_SERVER_URL = os.getenv("SOCKETIO_SERVER_URL", "http://127.0.0.1:8000")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

# --- Connection Container ---
class PageContextPlaceholder:
    """
    Holds references to the Playwright objects to keep the session alive
    in the global ACTIVE_SESSIONS registry.
    """
    def __init__(self, page: Page, browser, playwright):
        self.page = page
        self.browser = browser
        self.playwright = playwright

# --- REAL Speech-to-Text Function (Gemini Powered) ---
async def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    """
    Sends the audio file to Gemini 2.5 Flash for transcription.
    """
    print(f"🎙️ Transcribing audio ({len(audio_bytes)} bytes, type: {mime_type})...")
    
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY is missing in .env")
        return "Error: API Key Missing"

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = "Transcribe the following audio command exactly as spoken. Return ONLY the text, no other commentary."

    # Run blocking API call in a thread to keep server async
    def _call_gemini():
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    prompt,
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                ]
            )
            return response.text.strip()
        except Exception as e:
            print(f"❌ STT API Error: {e}")
            raise

    try:
        text = await asyncio.to_thread(_call_gemini)
        return text
    except Exception:
        return "Error transcribing audio."

# --- Helper: Dynamic Browser Connection (ASYNC) ---
async def get_browser_page():
    """
    Connects to the running Chrome instance using Async Playwright.
    Returns: (page, browser, playwright_instance)
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

        # 2. Connect Playwright (ASYNC)
        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp(ws_url)
        
        # 3. Get the active context and page
        default_context = browser.contexts[0]
        if not default_context.pages:
            # Create a new page if none exist
            page = await default_context.new_page()
        else:
            # Attach to the first open tab
            page = default_context.pages[0]
            
        return page, browser, pw

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
    # Validate content type
    if not audio_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    # 1. Read and Transcribe
    audio_content = await audio_file.read()
    transcribed_text = await transcribe_audio(audio_content, audio_file.content_type)
    
    session_id = str(uuid.uuid4())
    print(f"🎤 New Command: {transcribed_text} (Session: {session_id})")

    try:
        # 2. Establish Async Connection
        page, browser, pw = await get_browser_page()
        
        # 3. STORE IN GLOBAL REGISTRY
        ACTIVE_SESSIONS[session_id] = PageContextPlaceholder(page, browser, pw)
        
        title = await page.title()
        print(f"✅ CDP connection established. Page Title: {title}")
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        await graph_status_pusher(sio, session_id, "Browser Connection Lost.", 'CDP_DISCONNECTED')
        raise HTTPException(status_code=503, detail=str(e))
        
    # 4. Initialize State
    initial_state = AgentState(
        input=transcribed_text,
        intent_json={},
        status='RECEIVED',
        user_approved=False,
        error=None,
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

    # Start the graph execution in the background
    asyncio.create_task(run_graph())
    
    return {"message": "Command initiated", "session_id": session_id}

if __name__ == "__main__":
    uvicorn.run(app_asgi, host="127.0.0.1", port=8000, ws_ping_interval=10, ws_ping_timeout=10)