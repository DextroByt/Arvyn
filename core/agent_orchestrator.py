import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Union, Literal, Optional
from langgraph.graph import StateGraph, END

# Use high-fidelity exports from upgraded config
from config import (
    logger, 
    GEMINI_MODEL_NAME, 
    VIEWPORT_WIDTH, 
    VIEWPORT_HEIGHT,
    DASHBOARD_SIZE
)
from core.state_schema import AgentState
from core.gemini_logic import GeminiBrain
from tools.browser import ArvynBrowser
from tools.data_store import ProfileManager
from tools.voice import ArvynVoice

class ArvynOrchestrator:
    """
    Superior Autonomous Orchestrator for Agent Arvyn.
    UPGRADED: Features Stateful Action Caching, Sensitive Interception,
    and Pixel-Perfect Grounding with UI Deadlock Prevention.
    """

    def __init__(self, model_name: str = GEMINI_MODEL_NAME):
        # Initializing with Gemini 2.5 Flash for high-speed banking loops
        self.brain = GeminiBrain(model_name=model_name)
        self.browser = ArvynBrowser(headless=False)
        self.profile = ProfileManager()
        self.voice = ArvynVoice()
        self.app = None
        self.workflow = self._create_workflow()
        
        # Comprehensive log buffer for the Arvyn Dashboard
        self.session_log = []
        logger.info(f"🚀 Arvyn Core v3.4: Orchestrator ready. UI: {DASHBOARD_SIZE[0]}x{DASHBOARD_SIZE[1]} | Engine: {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT}.")

    async def init_app(self, checkpointer):
        """Compiles the LangGraph with Persistent Checkpointing and HITL support."""
        if self.app is None:
            self.app = self.workflow.compile(
                checkpointer=checkpointer,
                interrupt_before=["human_interaction_node"]
            )
            logger.info("✅ Arvyn Autonomous Core: Persistence logic compiled.")

    async def cleanup(self):
        """Graceful release of all kinetic layers and browser instances."""
        if self.browser:
            self._add_to_session_log("system", "Deactivating kinetic layer and releasing resources...")
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Cleanup Error: {e}")

    def _create_workflow(self) -> StateGraph:
        """Defines the recursive interaction loop: Discovery -> Observe -> Reason -> Act."""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("intent_parser", self._node_parse_intent)
        workflow.add_node("site_discovery", self._node_site_discovery)
        workflow.add_node("autonomous_executor", self._node_autonomous_executor)
        workflow.add_node("human_interaction_node", self._node_wait_for_user)

        workflow.set_entry_point("intent_parser")
        
        workflow.add_edge("intent_parser", "site_discovery")
        workflow.add_edge("site_discovery", "autonomous_executor")
        
        workflow.add_conditional_edges(
            "autonomous_executor",
            self._decide_next_step,
            {
                "continue_loop": "autonomous_executor",
                "ask_user": "human_interaction_node",
                "finish_task": END 
            }
        )
        
        workflow.add_edge("human_interaction_node", "autonomous_executor")
        
        return workflow

    def _add_to_session_log(self, step: str, status: str):
        """Structured auditing for the Command Center Dashboard."""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{step.upper()}] {status}"
        self.session_log.append(entry)
        logger.info(f"📊 {entry}")

    async def _node_parse_intent(self, state: AgentState) -> Dict[str, Any]:
        """Multi-turn intent resolution and banking target anchoring."""
        self._add_to_session_log("intent_parser", "Processing natural language command...")
        
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        try:
            intent_obj = await self.brain.parse_intent(content)
            intent_dict = intent_obj.model_dump()
            
            provider = intent_dict.get('provider', 'Rio Finance Bank')
            self._add_to_session_log("intent_parser", f"Target Locked: {provider} | Action: {intent_dict.get('action')}")
            
            return {
                "intent": intent_dict, 
                "task_history": [], 
                "current_step": f"Initiating workflow for {provider}..."
            }
        except Exception as e:
            logger.error(f"Intent Extraction Failure: {e}")
            return {"current_step": "Clarification required.", "intent": None}

    def _resolve_target_url(self, provider_name: str) -> str:
        """Ensures exact navigation to Rio Finance for all finance-related keywords."""
        RIO_URL = "https://roshan-chaudhary13.github.io/rio_finance_bank/"
        
        if any(key in provider_name.lower() for key in ["rio", "finance", "bank", "gold", "bill", "electricity"]):
            return RIO_URL

        norm_name = provider_name.upper().replace(" ", "_")
        url = self.profile.get_verified_url(norm_name)
        
        return url if url else f"https://www.google.com/search?q={provider_name}+official+site"

    async def _node_site_discovery(self, state: AgentState) -> Dict[str, Any]:
        """Navigation node with browser state verification."""
        intent = state.get("intent") or {}
        provider = intent.get("provider", "Rio Finance Bank")
        
        target_url = self._resolve_target_url(provider)
        self._add_to_session_log("discovery", f"Verifying endpoint for {provider}...")

        try:
            page = await self.browser.ensure_page()
            current_url = page.url
            
            if target_url not in current_url or current_url == "about:blank":
                self._add_to_session_log("discovery", f"Connecting to secure portal: {target_url}")
                await self.browser.navigate(target_url)
                await asyncio.sleep(3.0) # Extended hydration buffer
            else:
                self._add_to_session_log("discovery", "Target portal active. Commencing execution.")

            return {"current_step": f"Secured portal connection."}
            
        except Exception as e:
            self._add_to_session_log("error", f"Portal connection error: {str(e)}")
            return {"current_step": "Discovery retry required..."}

    async def _node_autonomous_executor(self, state: AgentState) -> Dict[str, Any]:
        """
        Main autonomous loop for visual reasoning and kinetic execution.
        UPGRADED: Features Action Caching and Repetitive Click Logic.
        """
        self._add_to_session_log("executor", "Observing UI state and analyzing components...")
        
        intent = state.get("intent")
        history = state.get("task_history", [])
        approval = state.get("human_approval")
        cached_analysis = state.get("browser_context", {})

        if not intent:
            return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "I've lost the objective. Please re-state."}

        # ACTION CACHING: If resuming from authorization, execute the cached action directly
        if approval == "approved" and cached_analysis.get("action_type") in ["CLICK", "TYPE"]:
            self._add_to_session_log("human_interaction", "Authorization received. Executing sensitive action...")
            analysis = cached_analysis
        else:
            # Standard Vision-Reasoning Phase
            screenshot = await self.browser.get_screenshot_b64()
            provider_name = intent.get("provider", "Rio Finance Bank")
            goal = f"Goal: {intent.get('action')} on {provider_name}. Task progress: Step {len(history)+1}."
            
            user_context = self.profile.get_provider_details(provider_name)
            user_context.update(self.profile.get_data().get("personal_info", {}))

            self._add_to_session_log("brain", f"Calculating next step... (Action {len(history)+1})")
            analysis = await self.brain.analyze_page_for_action(screenshot, goal, history, user_context)

        action_type = analysis.get("action_type")
        current_history = history.copy()
        element_name = analysis.get("element_name", "").lower()
        input_text = analysis.get("input_text", "")

        # SENSITIVE ACTION INTERCEPTION
        is_confidential = any(k in element_name for k in ["password", "pin", "otp", "cvv", "card"])
        if action_type == "TYPE" and is_confidential and approval != "approved":
            self._add_to_session_log("security", f"LOCKED: Detected confidential field '{element_name}'.")
            return {
                "browser_context": analysis, # Cache for resumption
                "pending_question": f"Authorization Required: I need to enter your {element_name}. Please verify the credentials on the dashboard and click Authorize.",
                "current_step": f"LOCKED: Awaiting permission for {element_name}."
            }

        # KINETIC EXECUTION
        if action_type in ["CLICK", "TYPE"]:
            coords = analysis.get("coordinates")
            if coords and len(coords) == 4:
                ymin, xmin, ymax, xmax = coords
                cx = int(((xmin + xmax) / 2) * (VIEWPORT_WIDTH / 1000))
                cy = int(((ymin + ymax) / 2) * (VIEWPORT_HEIGHT / 1000))
                
                # REPETITIVE CLICK LOGIC: Apply slight offset to break UI deadlocks on Rio Bank
                if len(history) > 0 and history[-1].get("element") == analysis.get("element_name"):
                    self._add_to_session_log("kinetic", "Repeating action: Applying precision offset to bypass overlay.")
                    cx += 5; cy += 5

                self._add_to_session_log("kinetic", f"Interacting with {analysis.get('element_name')} at pixel ({cx}, {cy})")
                await self.browser.click_at_coordinates(cx, cy)
                
                if action_type == "TYPE":
                    # Displaying sequence as requested by user
                    self._add_to_session_log("kinetic", f"Inputting sequence: {input_text}")
                    await self.browser.type_text(input_text)
                
                await asyncio.sleep(2.5) # Stabilization buffer for SPA transitions
                
                current_history.append({
                    "action": action_type, 
                    "element": analysis.get("element_name"),
                    "thought": analysis.get("thought")
                })

        elif action_type == "FINISHED":
            self._add_to_session_log("executor", "✅ Task verification successful. Objective reached.")

        return {
            "screenshot": await self.browser.get_screenshot_b64(),
            "task_history": current_history,
            "browser_context": analysis,
            "current_step": analysis.get("thought", "Advancing autonomous workflow..."),
            "pending_question": analysis.get("voice_prompt") if action_type == "ASK_USER" else None,
            "human_approval": None 
        }

    async def _node_wait_for_user(self, state: AgentState) -> Dict[str, Any]:
        """Human-In-The-Loop sync node."""
        approval = state.get("human_approval")
        if approval == "approved":
            self._add_to_session_log("human_interaction", "Authorization confirmed. Passing control to executor node.")
        elif approval == "rejected":
            self._add_to_session_log("human_interaction", "Action rejected. Resuming standby state.")
            return {"current_step": "REJECTED: Task paused."}
        
        return {"current_step": "Awaiting user decision..."}

    def _decide_next_step(self, state: AgentState) -> Literal["continue_loop", "ask_user", "finish_task"]:
        """Recursive loop decision logic with limit handling."""
        analysis = state.get("browser_context", {})
        action_type = analysis.get("action_type")
        
        if action_type == "FINISHED": return "finish_task"
        if action_type == "ASK_USER" or state.get("pending_question"): return "ask_user"
        
        if len(state.get("task_history", [])) > 35: 
            self._add_to_session_log("safety", "Maximum recursion limit reached. Terminating.")
            return "finish_task"
            
        return "continue_loop"