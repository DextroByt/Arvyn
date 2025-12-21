import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Union, Literal, Optional
from langgraph.graph import StateGraph, END

# Use high-fidelity exports from upgraded config
from config import (
    logger, 
    QWEN_MODEL_NAME, 
    VIEWPORT_WIDTH, 
    VIEWPORT_HEIGHT,
    DASHBOARD_SIZE
)
from core.state_schema import AgentState
from core.qwen_logic import QwenBrain
from tools.browser import ArvynBrowser
from tools.data_store import ProfileManager
from tools.voice import ArvynVoice

class ArvynOrchestrator:
    """
    Superior Autonomous Orchestrator for Agent Arvyn.
    UPGRADED: Full Autonomy Mode - No user authorization required.
    MAINTAINED: Kinetic Anti-Loop logic, Dynamic Offset Scaling, and Persistent Session Logging.
    """

    def __init__(self, model_name: str = QWEN_MODEL_NAME):
        self.brain = QwenBrain(model_name=model_name)
        self.browser = ArvynBrowser(headless=False)
        self.profile = ProfileManager()
        self.voice = ArvynVoice()
        self.app = None
        self.workflow = self._create_workflow()
        
        self.session_log = []
        # Track repeated element interactions for kinetic reliability
        self.interaction_attempts = {} 
        
        logger.info(f"🚀 Arvyn Core v4.0 [Autonomous Edition]: Orchestrator active. HITL Gates deactivated.")

    async def init_app(self, checkpointer):
        """Compiles the LangGraph for Full-Auto execution."""
        if self.app is None:
            # REMOVED: interrupt_before=["human_interaction_node"] to allow non-stop flow
            self.app = self.workflow.compile(
                checkpointer=checkpointer
            )
            logger.info("✅ Arvyn Autonomous Core: Logic layers compiled for non-stop execution.")

    async def cleanup(self):
        """Graceful release of browser and kinetic resources."""
        if self.browser:
            self._add_to_session_log("system", "Deactivating kinetic layer...")
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Cleanup Error: {e}")

    def _create_workflow(self) -> StateGraph:
        """Defines the autonomous interaction loop: Discovery -> Observe -> Reason -> Act."""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("intent_parser", self._node_parse_intent)
        workflow.add_node("site_discovery", self._node_site_discovery)
        workflow.add_node("autonomous_executor", self._node_autonomous_executor)

        workflow.set_entry_point("intent_parser")
        
        workflow.add_edge("intent_parser", "site_discovery")
        workflow.add_edge("site_discovery", "autonomous_executor")
        
        # Continuous loop until the task is marked as FINISHED
        workflow.add_conditional_edges(
            "autonomous_executor",
            self._decide_next_step,
            {
                "continue_loop": "autonomous_executor",
                "finish_task": END 
            }
        )
        
        return workflow

    def _add_to_session_log(self, step: str, status: str):
        """Structured auditing for the Command Center Dashboard."""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{step.upper()}] {status}"
        self.session_log.append(entry)
        logger.info(f"📊 {entry}")

    async def _node_parse_intent(self, state: AgentState) -> Dict[str, Any]:
        self._add_to_session_log("intent_parser", "Processing natural language command...")
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        try:
            intent_obj = await self.brain.parse_intent(content)
            intent_dict = intent_obj.model_dump()
            provider = intent_dict.get('provider', 'Rio Finance Bank')
            self._add_to_session_log("intent_parser", f"Target Locked: {provider}")
            
            return {
                "intent": intent_dict, 
                "task_history": [], 
                "current_step": f"Initiating workflow for {provider}..."
            }
        except Exception as e:
            logger.error(f"Intent Extraction Failure: {e}")
            return {"current_step": "System recovery initiated...", "intent": {"provider": "Rio Finance Bank", "action": "PAY_BILL"}}

    def _resolve_target_url(self, provider_name: str) -> str:
        RIO_URL = "https://roshan-chaudhary13.github.io/rio_finance_bank/"
        if any(key in provider_name.lower() for key in ["rio", "finance", "bank", "gold", "bill"]):
            return RIO_URL
        norm_name = provider_name.upper().replace(" ", "_")
        url = self.profile.get_verified_url(norm_name)
        return url if url else f"https://www.google.com/search?q={provider_name}+official+site"

    async def _node_site_discovery(self, state: AgentState) -> Dict[str, Any]:
        """Navigates and prepares the browser for autonomous action."""
        intent = state.get("intent") or {}
        provider = intent.get("provider", "Rio Finance Bank")
        target_url = self._resolve_target_url(provider)

        try:
            page = await self.browser.ensure_page()
            if target_url not in page.url or page.url == "about:blank":
                self._add_to_session_log("discovery", f"Connecting to secure portal: {target_url}")
                await self.browser.navigate(target_url)
                await asyncio.sleep(4.0) 
            
            self._add_to_session_log("security", "STATUS: Connection secured. Ready for autonomous input.")
            return {"current_step": f"Portal ready. Starting execution sequence..."}
            
        except Exception as e:
            self._add_to_session_log("error", f"Portal connection error: {str(e)}")
            return {"current_step": "Discovery retry required..."}

    async def _node_autonomous_executor(self, state: AgentState) -> Dict[str, Any]:
        """
        Main autonomous loop using Qwen2.5-VL for visual reasoning.
        FIXED: Authorization gates removed. PINs/Credentials handled automatically.
        """
        self._add_to_session_log("executor", "Observing UI state...")
        
        intent = state.get("intent")
        history = state.get("task_history", [])
        
        screenshot = await self.browser.get_screenshot_b64()
        provider_name = intent.get("provider", "Rio Finance Bank")
        
        # Strict objective for the Brain to follow
        goal = (
            f"GOAL: Complete {intent.get('action')} on {provider_name}. "
            f"If login is required, use login_credentials. If a PIN/UPI field is seen, use security_details. "
            f"DO NOT WAIT. DO NOT ASK. PROCEED TO FINISH."
        )
        
        user_context = self.profile.get_provider_details(provider_name)
        user_context.update(self.profile.get_data().get("personal_info", {}))

        self._add_to_session_log("brain", "Analyzing UI (Qwen)...")
        analysis = await self.brain.analyze_page_for_action(screenshot, goal, history, user_context)

        action_type = analysis.get("action_type")
        current_history = history.copy()
        element_name = analysis.get("element_name", "").lower()
        input_text = analysis.get("input_text", "")

        # KINETIC EXECUTION ENGINE
        if action_type in ["CLICK", "TYPE"]:
            coords = analysis.get("coordinates")
            if coords and len(coords) == 4:
                ymin, xmin, ymax, xmax = coords
                cx = int(((xmin + xmax) / 2) * (VIEWPORT_WIDTH / 1000))
                cy = int(((ymin + ymax) / 2) * (VIEWPORT_HEIGHT / 1000))
                
                # --- KINETIC ANTI-LOOP ENGINE ---
                interaction_key = f"{action_type}_{element_name}"
                count = self.interaction_attempts.get(interaction_key, 0)
                
                if count > 0:
                    # Apply spiral offsets to bypass non-responsive UI layers
                    offset = (count * 8) if count % 2 == 0 else -(count * 8)
                    self._add_to_session_log("kinetic", f"BLOCKER DETECTED: Applying {offset}px offset to interaction.")
                    cx += offset
                    cy += offset
                
                self.interaction_attempts[interaction_key] = count + 1

                self._add_to_session_log("kinetic", f"Interacting with {analysis.get('element_name')}...")
                await self.browser.click_at_coordinates(cx, cy)
                
                if action_type == "TYPE":
                    # HALLUCINATION OVERRIDE: Double-check that we are typing real profile data
                    is_security_field = any(k in element_name for k in ["pin", "upi", "password", "cvv", "card"])
                    if is_security_field or "password123" in input_text.lower():
                         # Force lookup from user_profile.json
                         sec_details = user_context.get("security_details", {})
                         log_creds = user_context.get("login_credentials", {})
                         
                         if "pin" in element_name:
                             input_text = sec_details.get("upi_pin") or sec_details.get("card_pin", input_text)
                         elif "password" in element_name:
                             input_text = log_creds.get("password", input_text)

                    self._add_to_session_log("kinetic", f"Injecting secure data...")
                    await self.browser.type_text(input_text)
                
                await asyncio.sleep(3.0) # Unified buffer for React/SPA updates
                
                current_history.append({
                    "action": action_type, 
                    "element": analysis.get("element_name"),
                    "thought": analysis.get("thought")
                })
                
                # Reset attempts if we successfully moved to a new element
                if len(history) > 0 and history[-1].get("element") != analysis.get("element_name"):
                    self.interaction_attempts = {interaction_key: 1}

        elif action_type == "FINISHED":
            self._add_to_session_log("executor", "✅ Task completed autonomously.")

        return {
            "screenshot": await self.browser.get_screenshot_b64(),
            "task_history": current_history,
            "browser_context": analysis,
            "current_step": analysis.get("thought", "Advancing autonomous workflow..."),
            "human_approval": None 
        }

    def _decide_next_step(self, state: AgentState) -> Literal["continue_loop", "finish_task"]:
        analysis = state.get("browser_context", {})
        action_type = analysis.get("action_type")
        
        if action_type == "FINISHED": return "finish_task"
        
        # Hard safety limit for recursion
        if len(state.get("task_history", [])) > 60: 
            self._add_to_session_log("safety", "Limit reached. Terminating session.")
            return "finish_task"
            
        return "continue_loop"