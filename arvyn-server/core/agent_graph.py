# arvyn-server/core/agent_graph.py
import os
import asyncio
from typing import TypedDict, Optional, Dict, Any

# LangGraph dependencies
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

# External dependencies and tools
import socketio
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local imports
from tools.actions import fill_form_field, click_element, visual_click
from tools.browser import PageContextPlaceholder 
from core.intent_parser import parse_financial_intent
from core.vision_healer import visual_self_heal

# --- Constants and Configuration ---
MAX_RETRIES = 3 # Maximum attempts for the Visual Self-Healing cycle [cite: 151, 162, 178]

# --- 1. Defining the Persistent State (TypedDict Schema) ---
class AgentState(TypedDict):
    """
    The state persisted across LangGraph checkpoints, implemented as a TypedDict 
    for consistent data types and schema enforcement[cite: 144, 146].
    """
    input: str                         # Initial transcription from STT [cite: 146]
    intent_json: dict                  # Structured, Pydantic-validated output from VLM parser [cite: 146]
    status: str                        # Current operational state for real-time UI updates (via Socket.IO) [cite: 147]
    user_approved: bool                # Flag updated externally to resolve the Conscious Pause [cite: 147, 405]
    error: Optional[str]               # Stores Playwright exceptions (e.g., TimeoutError) for recovery [cite: 147, 395]
    page_context: object               # Reference to the non-serializable Playwright Page object [cite: 144, 147]
    retries: int                       # Counter limiting recursive visual healing attempts [cite: 147, 395]
    session_id: str                    # Unique identifier (used as LangGraph thread_id and Socket.IO room ID) [cite: 147, 395]

# --- 2. Socket.IO Status Push Utility ---
async def graph_status_pusher(sio: socketio.AsyncServer, session_id: str, message: str, status: str, details: Optional[dict] = None):
    """Pushes real-time status updates back to the client Sidecar for operational transparency[cite: 151, 152]."""
    payload = {
        "message": message,
        "status": status,
        "session_id": session_id,
        "details": details if details is not None else {}
    }
    # Emits to the specific room identified by the session_id
    await sio.emit('status_update', payload, room=session_id)

# --- 3. Graph Node Definitions ---

async def analyze_node(state: AgentState, config: dict):
    """Node 1: Parses raw input into structured intent via VLM (Semantic Intent Parsing)[cite: 153, 398]."""
    session_id = state['session_id']
    sio = config['sio']

    await graph_status_pusher(sio, session_id, "Analyzing command...", 'ANALYZING')

    try:
        # Use Pydantic-enforced VLM call
        intent = parse_financial_intent(state['input'])

        # Pre-emptive Text Feedback (Mitigation 3.2.B)
        await graph_status_pusher(sio, session_id,
            f"Agent interpretation: 'I heard: {state['input']}' - Parsed: {intent['action']} ${intent['amount']} to {intent['recipient']}.",
            'PARSING_COMPLETE', 
            {'transcribed_text': state['input'], 'action': intent['action']}
        )
        
        return {
            "intent_json": intent,
            "status": "INTENT_PARSED",
            "error": None
        }
    except Exception as e:
        await graph_status_pusher(sio, session_id, "Intent parsing failed. Terminating.", 'FAILURE')
        return {"error": f"INTENT_PARSE_ERROR: {e}", "status": "FAILURE"}

async def navigator_node(state: AgentState, config: dict):
    """Node 2: Navigates the browser to the required financial action page[cite: 156, 399]."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']

    await graph_status_pusher(sio, session_id, "NAVIGATING to required page...", 'NAVIGATING')
    
    # In a real system, the target URL would be dynamically determined by intent['action']
    target_url = "https://www.dummy-bank.com/transfer"

    try:
        # Prevents unnecessary navigation if already on the correct page
        if page.url != target_url:
            page.goto(target_url, wait_until="networkidle") 
        return {"status": "NAVIGATED"}
    except PlaywrightTimeoutError as e:
        # Navigation failure is considered unrecoverable by the healing mechanism
        await graph_status_pusher(sio, session_id, "Navigation timeout. Cannot proceed.", 'FAILURE')
        return {"error": f"NAV_TIMEOUT: {e}", "status": "FAILURE"}

async def filler_node(state: AgentState, config: dict):
    """Node 3: Attempts form filling and interaction using deterministic Playwright selectors[cite: 158, 400]."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']
    intent = state['intent_json']
    
    await graph_status_pusher(sio, session_id, "FILLING form fields (Deterministic Attempt)...", 'FILLING_FORM')

    try:
        # Attempt deterministic actions (prone to SelectorTimeout)
        fill_form_field(page, "input[name='amount']", str(intent['amount']))
        fill_form_field(page, "input[name='recipient']", intent['recipient'])
        
        # Attempt to click the next button to advance the transaction flow
        click_element(page, "button#review_button") 
        
        # Success: reset error and retries count
        return {"status": "FORM_FILLED", "error": None, "retries": 0} 
        
    except PlaywrightTimeoutError as e:
        # Structured exception (SYMBOLIC TRIGGER) that initiates the resilience cycle [cite: 132, 386]
        return {"error": str(e), "status": "SELECTOR_FAILED"}
    except Exception as e:
        await graph_status_pusher(sio, session_id, "Unexpected execution error during form filling.", 'FAILURE')
        return {"error": f"EXECUTION_ERROR: {e}", "status": "FAILURE"}

async def visual_heal_node(state: AgentState, config: dict):
    """Node 4: Executes Visual Self-Healing (Neuro Component) if a selector fails[cite: 161, 402]."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']
    
    # Guardrail: Check max retries [cite: 162]
    if state['retries'] >= MAX_RETRIES:
        await graph_status_pusher(sio, session_id,
            "Visual Self-Healing failed after max retries. Halting.", 'FAILURE')
        return {"status": "FAILURE", "error": "MAX_RETRIES_EXCEEDED"}
        
    await graph_status_pusher(sio, session_id,
        f"Selector failed. Initiating Visual Self-Healing (Retry {state['retries'] + 1})...",
        'SELF_HEALING'
    )
    
    try:
        # Enhanced Prompt Grounding (Mitigation 3.1.B) [cite: 198, 356]
        target_description = f"Find the next logical button, typically 'Continue' or 'Review', given the transaction details: {state['intent_json']['action']} to {state['intent_json']['recipient']} for ${state['intent_json']['amount']}."
        
        # Multimodal VLM call returns X, Y coordinates [cite: 199, 402]
        x, y = visual_self_heal(page, target_description)
        
        # Execute VLM-guided click, bypassing the DOM structure [cite: 134, 140]
        visual_click(page, x, y)
        
        # Post-Click Validation (Mitigation 3.1.A): Wait and check if page state advanced [cite: 356, 165]
        await asyncio.sleep(2)
        # Verify the success by checking for an expected subsequent element
        page.wait_for_selector("h2:has-text('Review Transaction')", timeout=5000)
        
        # Success: reset error, increment retry count for safety
        return {"error": None, "status": "HEALED", "retries": state['retries'] + 1} 
        
    except Exception as e:
        # Healing failed, increment retry count and loop back
        await graph_status_pusher(sio, session_id, f"VLM click or post-click validation failed: {e}", 'HEALING_FAILED')
        return {"error": f"VLM_HEAL_FAILED: {e}", "status": "HEALING_FAILED", "retries": state['retries'] + 1}

async def human_approval_node(state: AgentState, config: dict):
    """Node 5: Enforces the Conscious Pause Protocol (Symbolic Safety Layer)[cite: 166, 322]."""
    session_id = state['session_id']
    sio = config['sio']
    intent = state['intent_json']
    
    # Check if the transaction is critical (modifies funds)
    if intent.get('critical', False):
        
        # Check if the external signal has already updated the state (for re-invocation) [cite: 167]
        if state.get('user_approved'):
            return {"status": "APPROVAL_GRANTED"} # Resume Execution

        # Mandate self-freeze and push notification
        details = {
            "action": intent.get('action'),
            "amount": intent.get('amount'), # Will be displayed on the Transaction Bond (Mitigation 3.2.A) [cite: 359]
            "recipient": intent.get('recipient'),
            "session_id": session_id
        }
        
        await graph_status_pusher(sio, session_id,
            "MANDATORY PAUSE: Awaiting explicit user approval.",
            'AWAITING_APPROVAL', details # Triggers the Transaction Bond display on the Sidecar [cite: 169]
        )
        
        # The graph persistence layer saves the complete state snapshot[cite: 170].
        # Execution is halted until external re-invocation via main.py updates state['user_approved'][cite: 171, 324].
        return {"status": "PAUSED_AWAITING_AUTH"}
        
    return {"status": "SKIP_APPROVAL"} # Non-critical command proceeds directly

async def executor_node(state: AgentState, config: dict):
    """Node 6: Executes the final critical action (reached only after approval or if non-critical)[cite: 172, 406]."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']
    
    # Final guardrail check
    if state.get('user_approved', True) == False: 
        # This path should ideally be prevented by conditional edges, but serves as a final safety measure
        await graph_status_pusher(sio, session_id, "User cancelled transaction.", 'FAILURE')
        return {"error": "EXECUTION_DENIED_BY_USER", "status": "FAILURE"}
        
    await graph_status_pusher(sio, session_id, "Executing final transaction...", 'EXECUTING')

    try:
        # Final atomic click action to submit the payment
        click_element(page, "button#final_submit_payment_button")
        
        return {"status": "TRANSACTION_SENT"}
    except PlaywrightTimeoutError as e:
        await graph_status_pusher(sio, session_id, "Final execution failed.", 'EXECUTION_FAILED')
        return {"error": str(e), "status": "EXECUTION_FAILED"}

async def auditor_node(state: AgentState, config: dict):
    """Node 7: Checks for confirmation, logs the final status, and terminates the graph[cite: 174, 407]."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']
    
    # Check for failure states (including CDP disconnect or user cancellation) [cite: 175]
    if state['status'] == "FAILURE" or state['error'] or state.get('user_approved') == False:
        # The auditor node handles all final failure/termination logging
        final_message = f"Execution halted. Reason: {state['error'] if state['error'] else 'User cancelled.'}"
        await graph_status_pusher(sio, session_id, final_message, 'FAILURE')
        return {"status": "TERMINATED_FAILURE"}
        
    # Successful Path Check (In a real system, verify transaction ID/confirmation page)
    if "confirmation" in page.url or "success" in page.title().lower():
        final_message = "Transaction successfully completed. Confirmation logged."
        await graph_status_pusher(sio, session_id, final_message, 'SUCCESS')
    else:
        final_message = "Execution completed, but confirmation page not fully verified."
        await graph_status_pusher(sio, session_id, final_message, 'FAILURE')
        
    return {"status": "TERMINATED_SUCCESS"}

# --- 4. Conditional Edge Logic ---

def decide_next_step(state: AgentState):
    """
    Conditional Edge logic defining the flow control, enforcing resilience and the safety gate[cite: 177, 409].
    """
    # 1. Error Handling and Resilience Cycle
    if state['error']:
        # Selector failure triggers Visual Self-Healing if retries remain [cite: 178, 411]
        if state['retries'] < MAX_RETRIES and ("SELECTOR_TIMEOUT" in state['error'] or "VLM_HEAL_FAILED" in state['error']):
            return "visual_heal"
        # Unrecoverable error (max retries exceeded, nav failure, or CDP disconnect) terminates the graph
        return "auditor" 

    # 2. Main Execution Flow
    if state['status'] == 'FORM_FILLED' or state['status'] == 'HEALED':
        # Check the critical flag from the VLM intent parse [cite: 179]
        if state['intent_json'].get('critical', False):
            return "human_approval" # Mandatory Conscious Pause
        else:
            return "executor" # Skip approval for non-critical (read-only) actions
            
    # 3. Conscious Pause Resolution 
    if state['status'] == 'APPROVAL_GRANTED' or state['status'] == 'SKIP_APPROVAL':
        # Flow resumes after the external user_decision signal is processed
        return "executor" 

    # 4. Final Termination
    if state['status'] in ('TRANSACTION_SENT'):
        return "auditor" 
        
    # Default flow for linear steps (this should only happen if the graph is launched mid-flow)
    return "navigator"

# --- 5. Graph Construction and Compilation ---
def create_agent_executor(sio: socketio.AsyncServer):
    """Initializes and compiles the LangGraph state machine, injecting the Socket.IO server reference."""
    
    # Setup Checkpointer using the secure SQLite URL from .env 
    LANGGRAPH_CHECKPOINTER_URL = os.getenv("LANGGRAPH_CHECKPOINTER_URL", "sqlite:///./arvyn_checkpoints.sqlite")
    # This remains correct
    memory = SqliteSaver.from_conn_string(LANGGRAPH_CHECKPOINTER_URL)
    
    workflow = StateGraph(AgentState)
    
    # Add nodes (Remains the same)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("navigator", navigator_node)
    workflow.add_node("filler", filler_node)
    workflow.add_node("visual_heal", visual_heal_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("auditor", auditor_node)
    
    # Define the starting point of the graph (Remains the same)
    workflow.set_entry_point("analyze") 
    
    # Define edges (Remains the same)
    workflow.add_edge("analyze", "navigator")
    workflow.add_edge("navigator", "filler") 
    workflow.add_conditional_edges("filler", decide_next_step)
    workflow.add_conditional_edges("visual_heal", decide_next_step) 
    workflow.add_conditional_edges("human_approval", decide_next_step) 
    workflow.add_edge("executor", "auditor")
    workflow.add_edge("auditor", END) 
    
    # Compile the graph: REMOVE the 'config' parameter from compile()
    # The 'sio' object will now be passed in main.py via the ainvoke call config
    app = workflow.compile(
        checkpointer=memory
    )
    return app