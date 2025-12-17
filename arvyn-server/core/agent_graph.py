import os
import asyncio
import socketio
from typing import TypedDict, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver 
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from langchain_core.runnables import RunnableConfig

# Internal imports
from tools.actions import fill_form_field, click_element, visual_click
from core.intent_parser import parse_financial_intent
from core.vision_healer import visual_self_heal

MAX_RETRIES = 3

# --- GLOBAL REGISTRY FOR NON-SERIALIZABLE OBJECTS ---
ACTIVE_SESSIONS: Dict[str, Any] = {}

# Global reference to Socket.IO server
SERVER_SIO = None

# --- Socket.IO Status Push Utility (With Console Logging) ---
async def graph_status_pusher(sio: socketio.AsyncServer, session_id: str, message: str, status: str, details: Optional[dict] = None):
    """Pushes real-time status updates back to the client Sidecar AND prints to Console."""
    
    print(f"🚀 [Graph Status] {status}: {message}")

    if sio is None:
        return

    payload = {
        "message": message,
        "status": status,
        "session_id": session_id,
        "details": details if details is not None else {}
    }
    await sio.emit('status_update', payload, room=session_id)

class AgentState(TypedDict):
    """The state persisted across LangGraph checkpoints."""
    input: str
    intent_json: dict
    status: str
    user_approved: bool
    error: Optional[str]
    retries: int
    session_id: str

# --- Helper to get Page ---
def get_page_from_session(session_id: str):
    context = ACTIVE_SESSIONS.get(session_id)
    if not context or not hasattr(context, 'page'):
        raise ValueError(f"No active browser context found for session {session_id}")
    return context.page

# --- Graph Node Definitions ---

async def analyze_node(state: AgentState, config: RunnableConfig):
    session_id = state['session_id']
    sio = SERVER_SIO
    await graph_status_pusher(sio, session_id, "Analyzing command...", 'ANALYZING')

    try:
        intent = parse_financial_intent(state['input'])
        
        # Determine display string based on action
        if intent['action'] == 'login':
            action_desc = f"Login as {intent.get('username')}"
        else:
            action_desc = f"{intent['action']} ${intent.get('amount')} to {intent.get('recipient')}"

        await graph_status_pusher(sio, session_id, 
            f"Parsed command: {action_desc}", 
            'PARSING_COMPLETE', {'transcribed_text': state['input']}
        )

        return {
            "intent_json": intent,
            "status": "INTENT_PARSED",
            "error": None
        }
    except Exception as e:
        await graph_status_pusher(sio, session_id, "Intent parsing failed. Terminating.", 'FAILURE')
        return {"error": f"INTENT_PARSE_ERROR: {e}", "status": "FAILURE"}

async def navigator_node(state: AgentState, config: RunnableConfig):
    session_id = state['session_id']
    sio = SERVER_SIO
    
    try:
        page = get_page_from_session(session_id)
        
        await graph_status_pusher(sio, session_id, "NAVIGATING to required page...", 'NAVIGATING')
        
        target_url = "https://roshan-chaudhary13.github.io/rio_finance_bank/" 
        
        if target_url not in page.url:
             await page.goto(target_url, wait_until="networkidle")
        return {"status": "NAVIGATED"}
        
    except ValueError as ve:
        return {"error": str(ve), "status": "FAILURE"}
    except PlaywrightTimeoutError as e:
        await graph_status_pusher(sio, session_id, "Navigation timeout. Cannot proceed.", 'FAILURE')
        return {"error": f"NAV_TIMEOUT: {e}", "status": "FAILURE"}
    except Exception as e:
         return {"error": f"NAV_ERROR: {e}", "status": "FAILURE"}

async def filler_node(state: AgentState, config: RunnableConfig):
    session_id = state['session_id']
    sio = SERVER_SIO
    intent = state['intent_json']
    action = intent.get('action')
    
    if state.get("status") == "FAILURE":
        return {"status": "FAILURE"}

    await graph_status_pusher(sio, session_id, "FILLING form fields...", 'FILLING_FORM')
    
    try:
        page = get_page_from_session(session_id)
        
        # --- LOGIC BRANCHING BASED ON INTENT ---
        if action == 'login':
            # Try generic selectors for Login
            # Note: We attempt these. If they fail, Visual Healer catches the exception.
            await fill_form_field(page, "input[type='email'], input[name='username'], #username", intent.get('username', ''))
            await fill_form_field(page, "input[type='password'], #password", intent.get('password', ''))
        
        elif action in ['transfer', 'pay_bill']:
            # Try generic selectors for Transfer
            await fill_form_field(page, "#recipient-input, input[name='recipient']", intent.get('recipient', ''))
            await fill_form_field(page, "#amount-input, input[name='amount']", str(intent.get('amount', '')))

        return {"status": "FORM_FILLED", "error": None, "retries": 0} 

    except PlaywrightTimeoutError as e:
        return {"error": str(e), "status": "SELECTOR_FAILED"}
    except Exception as e:
        await graph_status_pusher(sio, session_id, f"Execution error: {e}", 'FAILURE')
        return {"error": f"EXECUTION_ERROR: {e}", "status": "FAILURE"}

async def visual_heal_node(state: AgentState, config: RunnableConfig):
    session_id = state['session_id']
    sio = SERVER_SIO
    intent = state['intent_json']
    
    if state['retries'] >= MAX_RETRIES:
        await graph_status_pusher(sio, session_id, "Visual Self-Healing failed after max retries. Halting.", 'FAILURE')
        return {"status": "FAILURE", "error": "MAX_RETRIES_EXCEEDED"}

    await graph_status_pusher(sio, session_id, f"Selector failed. Initiating Visual Self-Healing (Retry {state['retries'] + 1})...", 'SELF_HEALING')

    try:
        page = get_page_from_session(session_id)
        
        # Dynamic description based on action
        if intent.get('action') == 'login':
             target_description = "Find the username or password input field."
        else:
             target_description = f"Find the input field for {intent.get('action', 'transaction')} details."
        
        x, y = await visual_self_heal(page, target_description)
        await visual_click(page, x, y)
        await asyncio.sleep(2) 
        
        return {"error": None, "status": "HEALED", "retries": state['retries'] + 1}
    except Exception as e:
        await graph_status_pusher(sio, session_id, f"VLM click failed: {e}", 'HEALING_FAILED')
        return {"error": f"VLM_HEAL_FAILED: {e}", "status": "HEALING_FAILED", "retries": state['retries'] + 1}

async def human_approval_node(state: AgentState, config: RunnableConfig):
    session_id = state['session_id']
    sio = SERVER_SIO
    intent = state['intent_json']
    
    if state.get("status") == "FAILURE":
        return {"status": "FAILURE"}

    is_critical = intent.get('critical', True)
    action = intent.get('action')

    # SKIP approval for Login commands to make flow smoother
    if action == 'login':
        return {"status": "SKIP_APPROVAL"}

    if is_critical:
        if state.get('user_approved'):
            return {"status": "APPROVAL_GRANTED"}
        
        details = {
            "action": intent.get('action'),
            "amount": intent.get('amount'),
            "recipient": intent.get('recipient'),
            "session_id": session_id
        }
        await graph_status_pusher(sio, session_id, "MANDATORY PAUSE: Awaiting explicit user approval.", 'AWAITING_APPROVAL', details)
        
        return {"status": "PAUSED_AWAITING_AUTH"}

    return {"status": "SKIP_APPROVAL"}

async def executor_node(state: AgentState, config: RunnableConfig):
    session_id = state['session_id']
    sio = SERVER_SIO
    
    if state.get("status") == "FAILURE":
        return {"status": "FAILURE"}

    await graph_status_pusher(sio, session_id, "Executing final transaction...", 'EXECUTING')
    
    if state.get('user_approved', True) == False:
         return {"error": "EXECUTION_DENIED_BY_USER", "status": "FAILURE"}

    try:
        page = get_page_from_session(session_id)
        
        # Generic submit button selector that works for Login or Transfer forms
        await click_element(page, "button[type='submit'], input[type='submit'], #submit-btn, #login-btn")
        
        return {"status": "TRANSACTION_SENT"}
    except PlaywrightTimeoutError as e:
        return {"error": str(e), "status": "EXECUTION_FAILED"}

async def auditor_node(state: AgentState, config: RunnableConfig):
    session_id = state['session_id']
    sio = SERVER_SIO
    
    status = state.get('status')
    if status in ["FAILURE", "EXECUTION_FAILED", "TERMINATED_FAILURE"]:
        msg = f"Execution halted. Error: {state.get('error')}"
        await graph_status_pusher(sio, session_id, msg, 'FAILURE')
    elif status == "TRANSACTION_SENT":
        await graph_status_pusher(sio, session_id, "Action successfully completed.", 'SUCCESS')
    
    if session_id in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_id]

    return {"status": "TERMINATED"}

# --- Graph Construction ---

def decide_next_step(state: AgentState):
    status = state.get('status')
    
    # 1. Success Paths
    if status == "FORM_FILLED":
        return "human_approval"
    
    if status in ["APPROVAL_GRANTED", "SKIP_APPROVAL"]:
        return "executor"
        
    # 2. Interrupts
    if status == 'PAUSED_AWAITING_AUTH':
        return END 
    
    # 3. Error/Retry Paths
    if status == 'SELECTOR_FAILED':
        return "visual_heal"
        
    if status == 'HEALED':
        return "filler" 
        
    if status == 'HEALING_FAILED' or status == 'FAILURE':
        return "auditor"
    
    return "navigator" 

def create_agent_executor(sio):
    global SERVER_SIO
    SERVER_SIO = sio

    memory = MemorySaver()
    workflow = StateGraph(AgentState)
    
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("navigator", navigator_node)
    workflow.add_node("filler", filler_node)
    workflow.add_node("visual_heal", visual_heal_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("auditor", auditor_node)

    workflow.set_entry_point("analyze")
    
    workflow.add_edge("analyze", "navigator")
    workflow.add_edge("navigator", "filler")
    
    workflow.add_conditional_edges("filler", decide_next_step)
    workflow.add_conditional_edges("visual_heal", decide_next_step)
    workflow.add_conditional_edges("human_approval", decide_next_step)
    
    workflow.add_edge("executor", "auditor")
    workflow.add_edge("auditor", END)

    return workflow.compile(checkpointer=memory)