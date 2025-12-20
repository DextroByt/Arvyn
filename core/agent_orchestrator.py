import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Union, Literal, Optional
from langgraph.graph import StateGraph, END

# Use high-fidelity exports from config
from config import (
    logger, 
    GEMINI_MODEL_NAME, 
    VIEWPORT_WIDTH, 
    VIEWPORT_HEIGHT
)
from core.state_schema import AgentState
from core.gemini_logic import GeminiBrain
from tools.browser import ArvynBrowser
from tools.data_store import ProfileManager
from tools.voice import ArvynVoice

class ArvynOrchestrator:
    """
    The Superior Autonomous Orchestrator for Agent Arvyn.
    Engineered for precision banking on Rio Finance Bank with 
    Deep Stateful Memory and 1080p Visual Grounding.
    """

    def __init__(self, model_name: str = GEMINI_MODEL_NAME):
        # Initializing with Gemini 2.5 Flash as requested for superior speed/reasoning
        self.brain = GeminiBrain(model_name=model_name)
        self.browser = ArvynBrowser(headless=False)
        self.profile = ProfileManager()
        self.voice = ArvynVoice()
        self.app = None
        self.workflow = self._create_workflow()
        
        # Comprehensive log buffer for the Arvyn Dashboard
        self.session_log = []
        logger.info(f"🚀 Arvyn Core v3.0: Orchestrator initialized with {model_name} at {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT}.")

    async def init_app(self, checkpointer):
        """Compiles the LangGraph with Persistent Checkpointing and HITL Interrupts."""
        if self.app is None:
            self.app = self.workflow.compile(
                checkpointer=checkpointer,
                interrupt_before=["human_interaction_node"]
            )
            logger.info("✅ Arvyn Autonomous Core: Logic Graph compiled with Persistence.")

    async def cleanup(self):
        """Production teardown: Safely releases browser resources and locks."""
        if self.browser:
            self._add_to_session_log("system", "Deactivating kinetic layer and browser engine...")
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Cleanup Error: {e}")

    def _create_workflow(self) -> StateGraph:
        """
        Defines the Advanced Recursive Execution Graph.
        Pattern: Parse -> Resolution -> [Observation -> Reasoning -> Action] Loop
        """
        workflow = StateGraph(AgentState)
        
        # Define core capability nodes
        workflow.add_node("intent_parser", self._node_parse_intent)
        workflow.add_node("site_discovery", self._node_site_discovery)
        workflow.add_node("autonomous_executor", self._node_autonomous_executor)
        workflow.add_node("human_interaction_node", self._node_wait_for_user)

        # Set entry point
        workflow.set_entry_point("intent_parser")
        
        # Define deterministic edges
        workflow.add_edge("intent_parser", "site_discovery")
        workflow.add_edge("site_discovery", "autonomous_executor")
        
        # Define conditional recursive loop
        workflow.add_conditional_edges(
            "autonomous_executor",
            self._decide_next_step,
            {
                "continue_loop": "autonomous_executor",
                "ask_user": "human_interaction_node",
                "finish_task": END 
            }
        )
        
        # Loopback for human guidance
        workflow.add_edge("human_interaction_node", "autonomous_executor")
        
        return workflow

    def _add_to_session_log(self, step: str, status: str):
        """Generates a high-fidelity audit trail for the Dashboard Logs."""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{step.upper()}] {status}"
        self.session_log.append(entry)
        logger.info(f"📊 {entry}")

    async def _node_parse_intent(self, state: AgentState) -> Dict[str, Any]:
        """Step 1: Multi-turn intent extraction and objective anchoring."""
        self._add_to_session_log("intent_parser", "Processing natural language command...")
        
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        try:
            intent_obj = await self.brain.parse_intent(content)
            intent_dict = intent_obj.model_dump()
            
            # Persistent target anchoring for Rio Finance Bank
            provider = intent_dict.get('provider', 'Rio Finance Bank')
            self._add_to_session_log("intent_parser", f"Target Locked: {provider} | Primary Action: {intent_dict.get('action')}")
            
            return {
                "intent": intent_dict, 
                "task_history": [], 
                "current_step": f"Initiating workflow for {provider}..."
            }
        except Exception as e:
            logger.error(f"Intent Failure: {e}")
            self._add_to_session_log("error", "Failed to resolve intent. Escalating to user.")
            return {"current_step": "Awaiting clarification...", "intent": None}

    def _resolve_target_url(self, provider_name: str) -> str:
        """
        Hardened URL Resolution Engine.
        Ensures exact navigation to Rio Finance Bank for all banking/finance keywords.
        """
        RIO_TARGET = "https://roshan-chaudhary13.github.io/rio_finance_bank/"
        
        # Absolute override to prevent blank tabs or search fallbacks for primary targets
        keywords = ["rio", "finance", "bank", "gold", "bill", "electricity"]
        if any(key in provider_name.lower() for key in keywords):
            return RIO_TARGET

        # Secondary resolution via verified memory
        norm_name = provider_name.upper().replace(" ", "_")
        url = self.profile.get_verified_url(norm_name)
        
        return url if url else f"https://www.google.com/search?q={provider_name}+official+site"

    async def _node_site_discovery(self, state: AgentState) -> Dict[str, Any]:
        """Step 2: Navigation layer with state-check verification."""
        intent = state.get("intent") or {}
        provider = intent.get("provider", "Rio Finance Bank")
        
        target_url = self._resolve_target_url(provider)
        self._add_to_session_log("discovery", f"Verifying endpoint for {provider}...")

        try:
            page = await self.browser.ensure_page()
            current_url = page.url
            
            # Prevent redundant reloads and fix blank tab issues
            if target_url not in current_url or current_url == "about:blank":
                self._add_to_session_log("discovery", f"Connecting to secure portal: {target_url}")
                await self.browser.navigate(target_url)
                # Ensure SPA components are hydrated
                await asyncio.sleep(2.5)
            else:
                self._add_to_session_log("discovery", "Target portal active. Commencing task execution.")

            return {"current_step": f"Secured connection to {provider}."}
            
        except Exception as e:
            self._add_to_session_log("error", f"Discovery Fault: {str(e)}")
            return {"current_step": "Portal connection error. Retrying logic..."}

    async def _node_autonomous_executor(self, state: AgentState) -> Dict[str, Any]:
        """Step 3: The Primary Reasoning-Execution Loop."""
        self._add_to_session_log("executor", "Observing UI state and analyzing components...")
        
        # 1. State Acquisition
        screenshot = await self.browser.get_screenshot_b64()
        intent = state.get("intent")
        history = state.get("task_history", [])
        
        if not intent:
            return {"action_type": "ASK_USER", "voice_prompt": "I've lost the task context. Please re-state your goal."}

        # 2. Context Aggregation
        provider_name = intent.get("provider", "Rio Finance Bank")
        goal = f"Action: {intent.get('action')} on {provider_name}. Task: Execute with 100% accuracy."
        
        user_context = self.profile.get_provider_details(provider_name)
        user_context.update(self.profile.get_data().get("personal_info", {}))

        # 3. Vision-Reasoning Phase (The VLM 'Brain')
        self._add_to_session_log("brain", f"Calculating next step... (Action {len(history)+1})")
        analysis = await self.brain.analyze_page_for_action(screenshot, goal, history, user_context)
        
        action_type = analysis.get("action_type")
        current_history = history.copy()
        
        # 4. Kinetic Execution Phase (Pixel Grounding)
        if action_type in ["CLICK", "TYPE"]:
            coords = analysis.get("coordinates")
            if coords and len(coords) == 4:
                # Resolve pixel mapping for high-res 1920x1080 viewport
                ymin, xmin, ymax, xmax = coords
                cx = int(((xmin + xmax) / 2) * (VIEWPORT_WIDTH / 1000))
                cy = int(((ymin + ymax) / 2) * (VIEWPORT_HEIGHT / 1000))
                
                element = analysis.get("element_name", "interface element")
                self._add_to_session_log("kinetic", f"Interacting with {element} at pixel ({cx}, {cy})")
                
                await self.browser.click_at_coordinates(cx, cy)
                
                if action_type == "TYPE":
                    text = analysis.get("input_text", "")
                    # Log security-safe data
                    sensitive_keys = ["pass", "pin", "otp", "cvv", "card"]
                    is_secret = any(s in element.lower() or s in text.lower() for s in sensitive_keys)
                    log_text = "[ENCRYPTED]" if is_secret else text
                    self._add_to_session_log("kinetic", f"Inputting sequence: {log_text}")
                    await self.browser.type_text(text)
                
                # Stabilization wait for banking UI transitions
                await asyncio.sleep(2.0)
                
                current_history.append({
                    "action": action_type, 
                    "element": element,
                    "thought": analysis.get("thought")
                })

        elif action_type == "FINISHED":
            self._add_to_session_log("executor", "🏁 Task verification successful. Objective reached.")
        
        elif action_type == "ASK_USER":
            self._add_to_session_log("executor", "Execution paused. Requesting user input...")

        # 5. Commit state back to the Persistent Graph
        return {
            "screenshot": await self.browser.get_screenshot_b64(),
            "task_history": current_history,
            "browser_context": analysis,
            "current_step": analysis.get("thought", "Advancing autonomous workflow..."),
            "pending_question": analysis.get("voice_prompt") if action_type == "ASK_USER" else None
        }

    async def _node_wait_for_user(self, state: AgentState) -> Dict[str, Any]:
        """Human-in-the-loop synchronization node."""
        return {"current_step": "Standing by for user guidance."}

    def _decide_next_step(self, state: AgentState) -> Literal["continue_loop", "ask_user", "finish_task"]:
        """Recursive Loop Decision Logic."""
        analysis = state.get("browser_context", {})
        action_type = analysis.get("action_type")
        
        if action_type == "FINISHED": return "finish_task"
        if action_type == "ASK_USER": return "ask_user"
        
        # Production Safety: Prevent logic recursion deeper than 35 actions
        if len(state.get("task_history", [])) > 35: 
            self._add_to_session_log("safety", "Maximum recursion limit reached. Shutting down for safety.")
            return "finish_task"
            
        return "continue_loop"