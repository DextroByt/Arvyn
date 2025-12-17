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

# --- CRITICAL: Use Async API to prevent Event Loop Crashes ---
from playwright.async_api import async_playwright, Page 
from google import genai
from google.genai import types

# Internal imports
from core.agent_graph import create_agent_executor, AgentState, graph_status_pusher, ACTIVE_SESSIONS

load_dotenv()

# --- Configuration ---
SOCKETIO_SERVER_URL = os.getenv("SOCKETIO_SERVER_URL", "http://127.0.0.1:8000")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Global Task Registry (For Emergency Halt) ---
# Maps session_id -> asyncio.Task
RUNNING_TASKS: Dict[str, asyncio.Task] = {}

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

# --- Connection Placeholder ---
class PageContextPlaceholder:
    def __init__(self, page: Page, browser, playwright):
        self.page = page
        self.browser = browser
        self.playwright = playwright

# --- REAL Speech-to-Text (Gemini) ---
async def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    print(f"🎙️ Transcribing audio ({len(audio_bytes)} bytes)...")
    if not GEMINI_API_KEY:
        return "Error: API Key Missing"

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = "Transcribe the following audio command exactly as spoken. Return ONLY the text."

    def _call_gemini():
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)]
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
    try:
        # 1. Fetch WebSocket URL
        response = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
        if response.status_code != 200:
            raise Exception(f"Chrome Debugger API Error: {response.status_code}")
        
        ws_url = response.json().get("webSocketDebuggerUrl")
        if not ws_url:
            raise Exception("No webSocketDebuggerUrl found.")

        print(f"🔗 Connecting to Chrome at: {ws_url}")

        # 2. Connect Playwright (Async)
        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp(ws_url)
        
        # 3. Get Page
        default_context = browser.contexts[0]
        page = await default_context.new_page() if not default_context.pages else default_context.pages[0]
            
        return page, browser, pw

    except Exception as e:
        raise Exception(f"Browser Connection Failed: {str(e)}")

# --- Socket Listener: User Decisions ---
@sio.on('user_decision')
async def handle_user_decision(sid, data: Dict[str, Any]):
    session_id = data.get("session_id")
    decision = data.get("decision")
    print(f"🔔 User Decision for {session_id}: {decision}")
    
    # Resume graph execution
    new_input = {"user_approved": decision == "approved"}
    config = {"configurable": {"thread_id": session_id}}
    
    # We wrap resume in a task too, so it can be halted if it hangs
    task = asyncio.create_task(graph_executor.ainvoke(new_input, config=config))
    RUNNING_TASKS[session_id] = task
    
    try:
        await task
    except asyncio.CancelledError:
        print(f"🚫 Task {session_id} cancelled during resume.")
    except Exception as e:
        print(f"❌ Error resuming graph: {e}")
    finally:
        RUNNING_TASKS.pop(session_id, None)

# --- CRITICAL: Emergency Halt Listener ---
@sio.on('halt_session')
async def handle_halt_session(sid, data: Dict[str, Any]):
    session_id = data.get("session_id")
    print(f"🛑 Emergency Halt Requested for Session: {session_id}")
    
    # 1. Cancel the asyncio Task
    task = RUNNING_TASKS.get(session_id)
    if task:
        task.cancel()
        print(f"✅ Task {session_id} cancelled.")
    
    # 2. Close Browser Resources
    if session_id in ACTIVE_SESSIONS:
        ctx = ACTIVE_SESSIONS[session_id]
        try:
            # We don't close the whole browser (it kills Chrome), just cleanup refs
            # If you want to close the TAB, uncomment below:
            # await ctx.page.close() 
            pass
        except Exception as e:
            print(f"⚠️ cleanup error: {e}")
        del ACTIVE_SESSIONS[session_id]

    # 3. Notify Frontend
    await graph_status_pusher(sio, session_id, "Process terminated by user.", 'CRITICAL_HALT')

# --- FastAPI Endpoint ---
@app.post("/command", status_code=status.HTTP_202_ACCEPTED)
async def handle_command(audio_file: UploadFile = File(...)):
    if not audio_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    # 1. Transcribe
    audio_content = await audio_file.read()
    transcribed_text = await transcribe_audio(audio_content, audio_file.content_type)
    session_id = str(uuid.uuid4())
    
    print(f"🎤 New Command: {transcribed_text} (Session: {session_id})")

    # 2. Connect Browser
    try:
        page, browser, pw = await get_browser_page()
        # Register in Active Sessions
        ACTIVE_SESSIONS[session_id] = PageContextPlaceholder(page, browser, pw)
        print(f"✅ Connection Active. Title: {await page.title()}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        await graph_status_pusher(sio, session_id, "Browser Connection Failed.", 'CDP_DISCONNECTED')
        raise HTTPException(status_code=503, detail=str(e))

    # 3. Start Agent
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
        except asyncio.CancelledError:
            print(f"🚫 Session {session_id} execution cancelled.")
        except Exception as e:
            print(f"❌ Graph Error: {e}")
            await graph_status_pusher(sio, session_id, "Internal Error.", 'FAILURE')
        finally:
            # Clean up task registry
            RUNNING_TASKS.pop(session_id, None)

    # Track the task globally so we can Halt it
    task = asyncio.create_task(run_graph())
    RUNNING_TASKS[session_id] = task
    
    return {"message": "Command initiated", "session_id": session_id}

if __name__ == "__main__":
    uvicorn.run(app_asgi, host="127.0.0.1", port=8000, ws_ping_interval=10, ws_ping_timeout=10)