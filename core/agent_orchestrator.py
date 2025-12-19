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
    The 'Heart' of Agent Arvyn (Production Grade).
    Updated for Session Persistence: Keeps the browser open after navigation.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.brain = GeminiBrain(model_name=model_name)
        self.browser = ArvynBrowser(headless=False)
        self.profile = ProfileManager()
        self.voice = ArvynVoice()
        self.app = None
        self.workflow = self._create_workflow()
        logger.info(f"Intelligent Orchestrator ready with {model_name}.")

    async def init_app(self, checkpointer):
        """Compiles the LangGraph with Persistence support."""
        if self.app is None:
            self.app = self.workflow.compile(
                checkpointer=checkpointer,
                # This ensures the graph pauses and waits, keeping the browser thread alive
                interrupt_before=["human_approval_node"]
            )
            logger.info("Advanced Agent Arvyn Core compiled with Persistence.")

    async def cleanup(self):
        """Safe shutdown called only on app exit or manual stop."""
        if self.browser:
            logger.info("Orchestrator: Closing browser session.")
            await self.browser.close()

    def _create_workflow(self) -> StateGraph:
        """Defines the flow without an auto-terminating END edge."""
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
        
        # After navigation, move to approval node and HALT.
        # REMOVED: workflow.add_edge("human_approval_node", END)
        # This prevents the thread from finishing and calling cleanup()
        workflow.add_edge("browser_navigator", "human_approval_node")
        
        return workflow

    async def _node_parse_intent(self, state: AgentState) -> Dict[str, Any]:
        """Step 1: Parse intent and check semantic cache."""
        logger.info("Node: Parsing & Normalizing Intent...")
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        try:
            intent = await self.brain.parse_intent(content)
            target_entity = intent.provider
            cached_url = self.profile.get_verified_url(target_entity)
            if cached_url:
                logger.info(f"Memory Hit: {cached_url}")
                intent.search_query = cached_url 
            
            return {"intent": intent.model_dump(), "current_step": f"Target: {target_entity}"}
        except Exception as e:
            logger.error(f"Intent Error: {e}")
            return {"current_step": "Understanding Failed", "missing_fields": ["intent"]}

    async def _node_validate_data(self, state: AgentState) -> Dict[str, Any]:
        intent = state.get("intent", {})
        if not intent.get("provider") or intent.get("provider") == "NONE":
            return {"missing_fields": ["provider"], "current_step": "Task Invalid"}
        return {"missing_fields": [], "current_step": "Task Verified"}

    async def _node_navigate_and_fill(self, state: AgentState) -> Dict[str, Any]:
        """Step 3: Intelligent Navigation with dynamic scaling."""
        logger.info("Node: Discovery & Navigation...")
        intent = state.get("intent", {})
        target_entity = intent.get("provider", "")
        query_or_url = intent.get("search_query") or f"{target_entity} official website"

        try:
            # 1. Navigation
            if query_or_url.startswith("http") and "google.com" not in query_or_url:
                await self.browser.navigate(query_or_url)
                current_step = f"Arrived at {target_entity}"
            else:
                await self.browser.navigate("https://www.google.com")
                await self.browser.page.fill('textarea[name="q"]', f"{target_entity} official website")
                await self.browser.page.press('textarea[name="q"]', "Enter")
                await self.browser.page.wait_for_load_state("networkidle")
                await asyncio.sleep(2) 

                screenshot_b64 = await self.browser.get_screenshot_b64()
                grounding = await self.brain.locate_official_link_on_page(screenshot_b64, target_entity)

                if grounding and grounding.coordinates:
                    dims = await self.browser.get_dimensions()
                    ymin, xmin, ymax, xmax = grounding.coordinates
                    center_x = int(((xmin + xmax) / 2) * (dims['width'] / 1000))
                    center_y = int(((ymin + ymax) / 2) * (dims['height'] / 1000))
                    
                    await self.browser.click_at_coordinates(center_x, center_y)
                    await self.browser.page.wait_for_load_state("load")
                    await asyncio.sleep(2) 
                    
                    final_url = self.browser.page.url
                    if "google.com" not in final_url:
                        self.profile.save_verified_site(target_entity, final_url)
                        current_step = f"Verified & Stayed: {target_entity}"
                    else:
                        current_step = "Navigation Stuck"
                else:
                    await self.browser.find_and_click("h3")
                    current_step = "Using Fallback"

            screenshot = await self.browser.get_screenshot_b64()
            return {"screenshot": screenshot, "current_step": current_step}

        except Exception as e:
            logger.error(f"Navigation Error: {e}")
            return {"current_step": "Discovery Failed"}

    async def _node_wait_for_approval(self, state: AgentState) -> Dict[str, Any]:
        """Halt node: This stops the graph and prevents the browser from closing."""
        logger.info("Session Paused: Browser will remain open.")
        return {"current_step": "Ready"}

    def _should_proceed_to_browser(self, state: AgentState) -> Literal["continue", "stop"]:
        if state.get("missing_fields"):
            return "stop"
        return "continue"