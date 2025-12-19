import json
import logging
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
    The 'Heart' of Agent Arvyn.
    Modified for dynamic execution and active search capabilities using Gemini 2.5.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        # Initialize Gemini 2.5 Brain
        self.brain = GeminiBrain(model_name=model_name)
        self.browser = ArvynBrowser(headless=False)
        self.profile = ProfileManager()
        self.voice = ArvynVoice()
        self.app = None
        self.workflow = self._create_workflow()
        logger.info(f"Orchestrator ready with {model_name} for dynamic commands.")

    async def init_app(self, checkpointer):
        """Initializes the graph with persistence for multi-turn commands."""
        if self.app is None:
            self.app = self.workflow.compile(
                checkpointer=checkpointer,
                interrupt_before=["human_approval_node"]
            )
            logger.info("Agent Arvyn Core compiled with LangGraph.")

    async def cleanup(self):
        """Clean shutdown of browser resources."""
        if self.browser:
            await self.browser.close()

    def _create_workflow(self) -> StateGraph:
        """Defines the linear flow: Parse -> Validate -> Navigate -> HITL."""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("intent_parser", self._node_parse_intent)
        workflow.add_node("data_validator", self._node_validate_data)
        workflow.add_node("browser_navigator", self._node_navigate_and_fill)
        workflow.add_node("human_approval_node", self._node_wait_for_approval)

        workflow.set_entry_point("intent_parser")
        workflow.add_edge("intent_parser", "data_validator")
        
        workflow.add_conditional_edges(
            "data_validator",
            self._should_proceed_to_browser,
            {
                "continue": "browser_navigator",
                "stop": END 
            }
        )
        
        workflow.add_edge("browser_navigator", "human_approval_node")
        workflow.add_edge("human_approval_node", END)
        return workflow

    async def _node_parse_intent(self, state: AgentState) -> Dict[str, Any]:
        """Extracts intent using Gemini 2.5 with local rule fallback."""
        logger.info("Node: Parsing Intent...")
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        try:
            intent = await self.brain.parse_intent(content)
            return {"intent": intent.model_dump(), "current_step": "Intent Identified"}
        except Exception as e:
            msg = str(e)
            self.voice.speak(msg)
            return {
                "messages": [("assistant", msg)], 
                "missing_fields": ["intent"],
                "current_step": "Execution Failed"
            }

    async def _node_validate_data(self, state: AgentState) -> Dict[str, Any]:
        """Validates that a clear target exists."""
        logger.info("Node: Validating Task...")
        intent = state.get("intent", {})
        provider = intent.get("provider")
        
        if state.get("current_step") == "Execution Failed":
            return {"current_step": "Halted"}

        if not provider or provider.upper() == "NONE":
            msg = "I can't do this; the command or target is unclear."
            self.voice.speak(msg)
            return {
                "missing_fields": ["provider"], 
                "messages": [("assistant", msg)],
                "current_step": "Task Invalid"
            }
            
        return {"missing_fields": [], "current_step": "Task Verified"}

    async def _node_navigate_and_fill(self, state: AgentState) -> Dict[str, Any]:
        """Navigates and performs actions like Searching or Form Filling."""
        logger.info("Node: Browser Execution...")
        intent = state.get("intent", {})
        action = intent.get("action", "NAVIGATE")
        provider = intent.get("provider", "").lower()
        
        # Get the original user command for context (e.g., "best anime")
        last_message = state["messages"][-1]
        raw_command = last_message.content if hasattr(last_message, 'content') else str(last_message)

        try:
            # 1. Determine the URL
            if action == "SEARCH":
                url = "https://www.google.com"
            else:
                url = provider if "." in provider else f"https://www.{provider}.com"

            # 2. Navigate
            await self.browser.navigate(url)

            # 3. If Search intent, actually perform the search
            if action == "SEARCH":
                logger.info(f"Performing Search for: {raw_command}")
                # Google search input selectors (textarea[name="q"] is standard)
                await self.browser.page.fill('textarea[name="q"]', raw_command)
                await self.browser.page.press('textarea[name="q"]', "Enter")
                await self.browser.page.wait_for_load_state("networkidle")
                current_step = f"Search Results for: {raw_command}"
            else:
                current_step = f"Site Loaded: {provider}"

            # 4. Capture state for UI
            screenshot = await self.browser.get_screenshot_b64()
            return {"screenshot": screenshot, "current_step": current_step}

        except Exception as e:
            logger.error(f"Browser Execution Error: {e}")
            msg = "I encountered an error while browsing the page."
            self.voice.speak(msg)
            return {
                "messages": [("assistant", msg)], 
                "missing_fields": ["execution"],
                "current_step": "Execution Failed"
            }

    async def _node_wait_for_approval(self, state: AgentState) -> Dict[str, Any]:
        """Awaits user interaction."""
        return {"current_step": "Ready"}

    def _should_proceed_to_browser(self, state: AgentState) -> Literal["continue", "stop"]:
        """Ends the workflow if errors occurred."""
        if state.get("missing_fields"):
            return "stop"
        return "continue"