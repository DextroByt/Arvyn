import json
import logging
import asyncio
from typing import Dict, List, Any, Union, Literal
from langgraph.graph import StateGraph, END

from config import logger
from core.state_schema import AgentState
from core.gemini_logic import GeminiBrain
from tools.browser import ArvynBrowser
from tools.data_store import ProfileManager
from tools.voice import ArvynVoice

class ArvynOrchestrator:
    """
    The Advanced Autonomous Controller for Agent Arvyn.
    Fixed: Uses safe kinetic methods and defensive state access to prevent attribute errors.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.brain = GeminiBrain(model_name=model_name)
        self.browser = ArvynBrowser(headless=False)
        self.profile = ProfileManager()
        self.voice = ArvynVoice()
        self.app = None
        self.workflow = self._create_workflow()
        logger.info(f"Persistent Orchestrator ready with {model_name}.")

    async def init_app(self, checkpointer):
        """Compiles the LangGraph with Persistence and Interruption support."""
        if self.app is None:
            self.app = self.workflow.compile(
                checkpointer=checkpointer,
                # Interrupt for voice interaction or final approval
                interrupt_before=["human_interaction_node"]
            )
            logger.info("Arvyn Autonomous Core compiled.")

    async def cleanup(self):
        """Shutdown the browser session safely."""
        if self.browser:
            logger.info("Orchestrator: Terminating browser session.")
            await self.browser.close()

    def _create_workflow(self) -> StateGraph:
        """
        Defines the Recursive Loop: 
        Parse -> Navigate to Site -> [Analyze -> Act -> Repeat] -> Finish
        """
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

    async def _node_parse_intent(self, state: AgentState) -> Dict[str, Any]:
        """Step 1: Extract intent and initialize session history."""
        logger.info("Node: Parsing Intent...")
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        try:
            intent_obj = await self.brain.parse_intent(content)
            intent_dict = intent_obj.model_dump()
            return {
                "intent": intent_dict, 
                "task_history": [], 
                "current_step": f"Target: {intent_dict.get('provider')}"
            }
        except Exception as e:
            logger.error(f"Intent Error: {e}")
            return {"current_step": "I couldn't clarify the intent.", "intent": None}

    async def _node_site_discovery(self, state: AgentState) -> Dict[str, Any]:
        """Step 2: Navigate to the target banking or official site."""
        intent = state.get("intent") or {}
        provider = intent.get("provider", "UNKNOWN")
        verified_url = self.profile.get_verified_url(provider)
        
        if verified_url:
            current_url = self.browser.page.url if self.browser.page else ""
            if verified_url not in current_url:
                await self.browser.navigate(verified_url)
        
        return {"current_step": f"Accessing {provider}"}

    async def _node_autonomous_executor(self, state: AgentState) -> Dict[str, Any]:
        """
        Step 3: Visual Execution Loop.
        Uses safe browser methods to prevent NoneType attribute errors.
        """
        logger.info("Node: Autonomous Executor reasoning...")
        
        # Ensure browser page is initialized for screenshot
        screenshot = await self.browser.get_screenshot_b64()
        
        intent = state.get("intent")
        if not intent:
            return {"browser_context": {"action_type": "ASK_USER", "voice_prompt": "I'm lost. What is the goal?"}}

        provider_name = intent.get("provider", "GENERAL")
        goal = f"Action: {intent.get('action')} on {provider_name}. Context: {intent}"
        history = state.get("task_history", [])
        
        # Pull user data for the specific bank
        user_context = self.profile.get_provider_details(provider_name)
        user_context.update(self.profile.get_data().get("personal_info", {}))

        # 2. Brain Analysis
        analysis = await self.brain.analyze_page_for_action(screenshot, goal, history, user_context)
        
        # 3. Safe Kinetic Execution
        action_type = analysis.get("action_type")
        current_history = history.copy()
        
        if action_type in ["CLICK", "TYPE"]:
            coords = analysis.get("coordinates")
            if coords and len(coords) == 4:
                dims = await self.browser.get_dimensions()
                ymin, xmin, ymax, xmax = coords
                cx = int(((xmin + xmax) / 2) * (dims['width'] / 1000))
                cy = int(((ymin + ymax) / 2) * (dims['height'] / 1000))
                
                # Execute safe coordinate click
                await self.browser.click_at_coordinates(cx, cy)
                
                if action_type == "TYPE":
                    # FIX: Use safe type_text instead of direct keyboard access
                    await self.browser.type_text(analysis.get("input_text", ""))
                
                await asyncio.sleep(1.5)
                
                current_history.append({
                    "action": action_type, 
                    "element": analysis.get("element_name"),
                    "thought": analysis.get("thought")
                })

        return {
            "screenshot": await self.browser.get_screenshot_b64(),
            "task_history": current_history,
            "browser_context": analysis,
            "current_step": analysis.get("thought", "Advancing..."),
            "pending_question": analysis.get("voice_prompt") if action_type == "ASK_USER" else None
        }

    async def _node_wait_for_user(self, state: AgentState) -> Dict[str, Any]:
        return {"current_step": "Waiting for your answer..."}

    def _decide_next_step(self, state: AgentState) -> Literal["continue_loop", "ask_user", "finish_task"]:
        analysis = state.get("browser_context", {})
        action_type = analysis.get("action_type")
        
        if action_type == "FINISHED": return "finish_task"
        if action_type == "ASK_USER": return "ask_user"
        if len(state.get("task_history", [])) > 20: return "finish_task"
            
        return "continue_loop"