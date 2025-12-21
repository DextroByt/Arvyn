import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Union, Literal, Optional
from langgraph.graph import StateGraph, END

# Use high-fidelity exports from upgraded config
from config import (
    logger, 
    QUBRID_MODEL_NAME, 
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
    v4.6 UPGRADE: Features Precision Kinetic Routing and Visual Marker Deployment.
    FIXED: Position-argument evaluation errors via updated tool interface.
    IMPROVED: Coordinate normalization logic for high-accuracy hit registration.
    PRESERVED: All Qubrid Vision-Reasoning and LangGraph state-aware guards.
    """

    def __init__(self, model_name: str = QUBRID_MODEL_NAME):
        self.brain = QwenBrain(model_name=model_name)
        self.browser = ArvynBrowser(headless=False)
        self.profile = ProfileManager()
        self.voice = ArvynVoice()
        self.app = None
        self.workflow = self._create_workflow()
        
        self.session_log = []
        # Track repeated element interactions to apply scaling offsets
        self.interaction_attempts = {}
        # Safety guard for ASK_USER loops
        self.consecutive_ask_count = 0
        
        logger.info(f"🚀 Arvyn Core v4.6: Autonomous Orchestrator (Precision Kinetic Engine) active.")

    async def init_app(self, checkpointer):
        """Compiles the LangGraph for Full Autonomy (No Interrupts)."""
        if self.app is None:
            self.app = self.workflow.compile(
                checkpointer=checkpointer
            )
            logger.info("✅ Arvyn Autonomous Core: Logic layers compiled for Zero-Authorization flow.")

    async def cleanup(self):
        """Graceful release of browser and kinetic resources."""
        if self.browser:
            self._add_to_session_log("system", "Deactivating kinetic layer...")
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Cleanup Error: {e}")

    def _create_workflow(self) -> StateGraph:
        """Defines the interaction loop: Discovery -> Observe -> Reason -> Act."""
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
            return {"current_step": "Clarification required.", "intent": None}

    def _resolve_target_url(self, provider_name: str) -> str:
        """Improved resolution logic to prevent unwanted redirection."""
        norm_name = provider_name.upper().replace(" ", "_")
        url = self.profile.get_verified_url(norm_name)
        if url:
            return url
        
        RIO_URL = "https://roshan-chaudhary13.github.io/rio_finance_bank/"
        rio_keywords = ["rio finance", "rio bank", "dummy bank", "rio gold"]
        if any(key in provider_name.lower() for key in rio_keywords):
            return RIO_URL
            
        return f"https://www.google.com/search?q={provider_name}+official+site"

    async def _node_site_discovery(self, state: AgentState) -> Dict[str, Any]:
        """Navigates and prepares for the Auto-Login Check."""
        intent = state.get("intent") or {}
        provider = intent.get("provider", "Rio Finance Bank")
        target_url = self._resolve_target_url(provider)

        try:
            page = await self.browser.ensure_page()
            if target_url not in page.url or page.url == "about:blank":
                self._add_to_session_log("discovery", f"Connecting to secure portal: {target_url}")
                await self.browser.navigate(target_url)
                await asyncio.sleep(4.0)
            
            self._add_to_session_log("security", "STATUS: Verifying Login/Session state...")
            return {"current_step": f"Connection secured. Checking login status..."}
            
        except Exception as e:
            self._add_to_session_log("error", f"Portal connection error: {str(e)}")
            return {"current_step": "Discovery retry required..."}

    async def _node_autonomous_executor(self, state: AgentState) -> Dict[str, Any]:
        """
        Main autonomous loop using Qubrid/Qwen-VL.
        ENHANCED: Coordinate normalization and deployment of visual click markers.
        """
        self._add_to_session_log("executor", "Observing UI state...")
        
        intent = state.get("intent")
        history = state.get("task_history", [])
        
        if not intent:
            return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "I've lost the objective."}

        screenshot = await self.browser.get_screenshot_b64()
        provider_name = intent.get("provider", "Rio Finance Bank")
        
        goal = (
            f"GOAL: Execute {intent.get('action')} on {provider_name}. "
            f"Aim for the GEOMETRIC CENTER of interactive elements. Accuracy is paramount. "
            f"Use ONLY data in 'USER DATA'. DO NOT ask for permission."
        )
        
        user_context = self.profile.get_provider_details(provider_name)
        user_context.update(self.profile.get_data().get("personal_info", {}))

        self._add_to_session_log("brain", f"Qubrid Engine: Analyzing page for {intent.get('action')}...")
        analysis = await self.brain.analyze_page_for_action(screenshot, goal, history, user_context)

        if not isinstance(analysis, dict):
            logger.warning("[SYSTEM] AI analysis returned non-dict format. Recovery mode active.")
            analysis = {"action_type": "ASK_USER", "thought": "Invalid analysis format."}

        action_type = str(analysis.get("action_type", "ASK_USER"))
        current_history = history.copy()
        element_name = str(analysis.get("element_name", "")).lower()
        input_text = str(analysis.get("input_text", ""))

        if action_type in ["CLICK", "TYPE"]:
            self.consecutive_ask_count = 0
            coords = analysis.get("coordinates")
            if coords and len(coords) == 4:
                # 0-1000 Normalized Coordinate Translation
                ymin, xmin, ymax, xmax = coords
                cx = round(((xmin + xmax) / 2) * (VIEWPORT_WIDTH / 1000))
                cy = round(((ymin + ymax) / 2) * (VIEWPORT_HEIGHT / 1000))
                
                interaction_key = f"{action_type}_{element_name}"
                count = self.interaction_attempts.get(interaction_key, 0)
                
                # Apply Dynamic Drift Correction Offsets
                if count > 0:
                    offset = (count * 8) if count % 2 == 0 else -(count * 8)
                    self._add_to_session_log("kinetic", f"RETRY: Precision offset applied: {offset}px.")
                    cx += offset
                    cy += offset
                
                self.interaction_attempts[interaction_key] = count + 1
                self._add_to_session_log("kinetic", f"Interacting with {analysis.get('element_name')} [Marker Deployed]")
                
                success = await self.browser.click_at_coordinates(cx, cy)
                
                if success:
                    if action_type == "TYPE":
                        self._add_to_session_log("kinetic", f"Typing secured data sequence...")
                        await self.browser.type_text(input_text)
                    
                    await asyncio.sleep(2.5)
                    current_history.append({
                        "action": action_type, 
                        "element": analysis.get("element_name"),
                        "thought": analysis.get("thought")
                    })
                    
                    # Reset context for new elements to prevent offset carryover
                    if len(history) > 0 and history[-1].get("element") != analysis.get("element_name"):
                        self.interaction_attempts = {interaction_key: 1}
                else:
                    self._add_to_session_log("kinetic", "ERROR: Kinetic registration failed. Recalibrating...")

        elif action_type == "FINISHED":
            self.consecutive_ask_count = 0
            self._add_to_session_log("executor", "✅ Task completed successfully.")
        
        elif action_type == "ASK_USER":
            self.consecutive_ask_count += 1

        return {
            "screenshot": await self.browser.get_screenshot_b64(),
            "task_history": current_history,
            "browser_context": analysis,
            "current_step": str(analysis.get("thought", "Advancing autonomous workflow...")),
            "pending_question": analysis.get("voice_prompt") if action_type == "ASK_USER" else None,
            "human_approval": "approved"
        }

    async def _node_wait_for_user(self, state: AgentState) -> Dict[str, Any]:
        """Breakpoint node for manual intervention."""
        return {"current_step": "Resuming autonomous execution...", "human_approval": "approved"}

    def _decide_next_step(self, state: AgentState) -> Literal["continue_loop", "ask_user", "finish_task"]:
        analysis = state.get("browser_context", {})
        action_type = analysis.get("action_type")
        
        if action_type == "FINISHED": return "finish_task"
        
        # RECURSION GUARD: Stop if we are stuck in ASK_USER mode without progress
        if action_type == "ASK_USER":
            if self.consecutive_ask_count > 5:
                self._add_to_session_log("safety", "Stuck detected. Session terminated to ensure safety.")
                return "finish_task"
            return "ask_user"
        
        if len(state.get("task_history", [])) > 60:
            self._add_to_session_log("safety", "Task history limit reached (60 steps).")
            return "finish_task"
            
        return "continue_loop"