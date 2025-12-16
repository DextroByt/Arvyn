# arvyn-server/core/agent_graph.py

import os
import asyncio
import socketio
from langgraph.graph import StateGraph, END

from tools.actions import fill_form_field, click_element, visual_click
from tools.browser import PageContextPlaceholder # Ensure this is imported if used for runtime logic
from core.intent_parser import parse_financial_intent
from core.vision_healer import visual_self_heal

MAX_RETRIES = 3 

# --- Socket.IO Status Push Utility ---
async def graph_status_pusher(sio: socketio.AsyncServer, session_id: str, message: str, status: str, details: Optional[dict] = None):
    """Pushes real-time status updates back to the client Sidecar."""
    payload = {
        "message": message,
        "status": status,
        "session_id": session_id,
        "details": details if details is not None else {}
    }
    await sio.emit('status_update', payload, room=session_id)


# --- Graph Node Definitions ---

async def analyze_node(state: AgentState, config: dict):
    """Node 1: Parses raw input into structured intent via VLM."""
    session_id = state['session_id']
    sio = config['sio']
    
    await graph_status_pusher(sio, session_id, "Analyzing command...", 'ANALYZING')
    
    try:
        intent = parse_financial_intent(state['input'])
        
        # Pre-emptive Text Feedback (Mitigation 3.2.B)
        await graph_status_pusher(sio, session_id, 
            f"Parsed command: {intent['action']} ${intent['amount']} to {intent['recipient']}.", 
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


async def navigator_node(state: AgentState, config: dict):
    """Node 2: Navigates the browser to the required page."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']
    
    await graph_status_pusher(sio, session_id, "NAVIGATING to required page...", 'NAVIGATING')
    
    target_url = "https://www.dummy-bank.com/transfer" 
    
    try:
        if page.url!= target_url:
            page.goto(target_url, wait_until="networkidle") 
        return {"status": "NAVIGATED"}
    except PlaywrightTimeoutError as e:
        # If navigation fails (e.g., page never loads), terminate. Healing is only for element failure.
        await graph_status_pusher(sio, session_id, "Navigation timeout. Cannot proceed.", 'FAILURE')
        return {"error": f"NAV_TIMEOUT: {e}", "status": "FAILURE"}


async def filler_node(state: AgentState, config: dict):
    """Node 3: Attempts form filling and interaction using deterministic selectors."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']
    intent = state['intent_json']

    await graph_status_pusher(sio, session_id, "FILLING form fields (Deterministic Attempt)...", 'FILLING_FORM')
    
    try:
        # Attempt deterministic actions (prone to SelectorTimeout)
        fill_form_field(page, "input[name='amount']", str(intent['amount']))
        fill_form_field(page, "input[name='recipient']", intent['recipient'])
        
        # Attempt to click the next button 
        click_element(page, "button#review_button")
        
        return {"status": "FORM_FILLED", "error": None, "retries": 0} # Reset retries on success
        
    except PlaywrightTimeoutError as e:
        # Selector failure triggers the resilience cycle 
        return {"error": str(e), "status": "SELECTOR_FAILED"}
    except Exception as e:
        await graph_status_pusher(sio, session_id, "Unexpected execution error.", 'FAILURE')
        return {"error": f"EXECUTION_ERROR: {e}", "status": "FAILURE"}


async def visual_heal_node(state: AgentState, config: dict):
    """Node 4: Executes Visual Self-Healing if a selector fails."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']
    
    # Check max retries (Guardrail against infinite loop) 
    if state['retries'] >= MAX_RETRIES:
        await graph_status_pusher(sio, session_id, 
            "Visual Self-Healing failed after max retries. Halting.", 'FAILURE')
        return {"status": "FAILURE", "error": "MAX_RETRIES_EXCEEDED"}

    await graph_status_pusher(sio, session_id, 
        f"Selector failed. Initiating Visual Self-Healing (Retry {state['retries'] + 1})...", 
        'SELF_HEALING'
    )
    
    try:
        # Enhanced Prompt Grounding (Mitigation 3.1.B)
        target_description = f"Find the next logical button, typically 'Continue' or 'Review', given the transaction details: {state['intent_json']['action']} to {state['intent_json']['recipient']}."
        x, y = visual_self_heal(page, target_description)
        
        # Execute VLM-guided click
        visual_click(page, x, y)
        
        # Post-Click Validation (Mitigation 3.1.A): Wait and check if page state advanced
        await asyncio.sleep(2) 
        page.wait_for_selector("h2:has-text('Review Transaction')", timeout=5000)
             
        # Success: reset error, increment retry count for safety
        return {"error": None, "status": "HEALED", "retries": state['retries'] + 1}
        
    except Exception as e:
        # Healing failed, increment retry count and loop back
        await graph_status_pusher(sio, session_id, f"VLM click failed: {e}", 'HEALING_FAILED')
        return {"error": f"VLM_HEAL_FAILED: {e}", "status": "HEALING_FAILED", "retries": state['retries'] + 1}


async def human_approval_node(state: AgentState, config: dict):
    """Node 5: Enforces the Conscious Pause Protocol (Symbolic Safety Layer)."""
    session_id = state['session_id']
    sio = config['sio']
    intent = state['intent_json']
    
    # Check if the transaction is critical (modifies funds)
    if intent.get('critical', False):
        
        # Check if the external signal has already updated the state
        if state.get('user_approved'):
            return {"status": "APPROVAL_GRANTED"} # Resume Execution
        
        # Mandate self-freeze and push notification 
        details = {
            "action": intent.get('action'),
            "amount": intent.get('amount'),
            "recipient": intent.get('recipient'),
            "session_id": session_id
        }
        
        await graph_status_pusher(sio, session_id, 
            "MANDATORY PAUSE: Awaiting explicit user approval.", 
            'AWAITING_APPROVAL', details
        )
        
        # The LangGraph persistence layer saves the current state snapshot.
        # Execution is halted until external re-invocation via main.py updates state['user_approved'].
        return {"status": "PAUSED_AWAITING_AUTH"}
        
    return {"status": "SKIP_APPROVAL"} # Non-critical command proceeds directly


async def executor_node(state: AgentState, config: dict):
    """Node 6: Executes the final critical action."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']
    
    await graph_status_pusher(sio, session_id, "Executing final transaction...", 'EXECUTING')

    if state.get('user_approved', True) == False:
         # Should not happen if conditional edges are correct, but as a final guardrail
         return {"error": "EXECUTION_DENIED_BY_USER", "status": "FAILURE"}

    try:
        # Final atomic click action
        click_element(page, "button#final_submit_payment_button") 
        return {"status": "TRANSACTION_SENT"}
    except PlaywrightTimeoutError as e:
        return {"error": str(e), "status": "EXECUTION_FAILED"}


async def auditor_node(state: AgentState, config: dict):
    """Node 7: Checks for confirmation and terminates the graph."""
    page = state['page_context'].page
    session_id = state['session_id']
    sio = config['sio']
    
    if state['status'] == "FAILURE" or state['error'] or state.get('user_approved') == False:
        # Termination due to failure, CDP disconnect, or user cancellation
        final_message = f"Execution halted. Error: {state['error'] if state['error'] else 'User cancelled.'}"
        await graph_status_pusher(sio, session_id, final_message, 'FAILURE')
        return {"status": "TERMINATED_FAILURE"}

    # Successful Path Check (In a real system, verify transaction ID)
    if "confirmation" in page.url or "success" in page.title().lower():
        final_message = "Transaction successfully completed. Confirmation logged."
        await graph_status_pusher(sio, session_id, final_message, 'SUCCESS')
    else:
        final_message = "Execution completed, but confirmation page not fully verified."
        await graph_status_pusher(sio, session_id, final_message, 'FAILURE')

    return {"status": "TERMINATED_SUCCESS"}


# --- Graph Construction and Compilation ---

def decide_next_step(state: AgentState):
    """Conditional Edge logic defining the flow control."""
    # 1. Error Handling and Resilience Cycle 
    if state['error']:
        if state['retries'] < MAX_RETRIES and "SELECTOR_TIMEOUT" in state['error']:
            return "visual_heal" # Trigger VLM recovery
        else:
            return "auditor" # Max retries exceeded or unrecoverable error

    # 2. Main Execution Flow
    if state['status'] == 'FORM_FILLED' or state['status'] == 'HEALED':
        if state['intent_json'].get('critical', False):
            return "human_approval"
        else:
            return "executor" # Skip approval for non-critical

    # 3. Conscious Pause Resolution 
    if state['status'] == 'APPROVAL_GRANTED' or state['status'] == 'SKIP_APPROVAL':
        return "executor"
        
    # 4. Final Termination
    if state['status'] in ('TRANSACTION_SENT'):
        return "auditor"

    # Default flow for linear steps 
    return "navigator"

def create_agent_executor(sio):
    """Initializes and compiles the LangGraph state machine."""
    
    # Setup Checkpointer using the secure SQLite URL from.env [6]
    memory = SqliteSaver.from_conn_string(os.getenv("LANGGRAPH_CHECKPOINTER_URL"))

    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("navigator", navigator_node)
    workflow.add_node("filler", filler_node)
    workflow.add_node("visual_heal", visual_heal_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("auditor", auditor_node)
    
    workflow.set_entry_point("analyze")
    
    # Define edges
    workflow.add_edge("analyze", "navigator") 
    workflow.add_edge("navigator", "filler") 
    
    # Critical Resilience Cycle: Filler -> Healing or Approval
    workflow.add_conditional_edges("filler", decide_next_step)
    
    # Healing Loop: Visual_Heal -> Filler (to retry the step) or Auditor (if retries exceeded)
    workflow.add_conditional_edges("visual_heal", decide_next_step)

    # Safety Gate Flow: Approval -> Executor (if approved) or Auditor (if cancelled)
    workflow.add_conditional_edges("human_approval", decide_next_step)
    
    # Final steps
    workflow.add_edge("executor", "auditor")
    workflow.add_edge("auditor", END)

    # Compile the graph, passing Socket.IO server reference into the config
    app = workflow.compile(
        checkpointer=memory,
        config={"sio": sio} 
    )
    return app


