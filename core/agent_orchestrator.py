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
    Updated for Sequential Sub-Tasks and Session Persistence.
    Allows for complex interactions like logins with human checkpoints.
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
                # Interrupt BEFORE this node to wait for user 'Approve' or 'Next'
                interrupt_before=["human_approval_node"]
            )
            logger.info("Arvyn Core compiled with Interactive Sub-Task support.")

    async def cleanup(self):
        """Shutdown the browser session. Called only on manual stop or app exit."""
        if self.browser:
            logger.info("Orchestrator: Terminating browser session.")
            await self.browser.close()

    def _create_workflow(self) -> StateGraph:
        """
        Defines a circular or iterative flow for sub-tasks.
        The browser stays open while the graph moves between nodes.
        """
        workflow = StateGraph(AgentState)
        
        # Define Nodes
        workflow.add_node("intent_parser", self._node_parse_intent)
        workflow.add_node("data_validator", self._node_validate_data)
        workflow.add_node("browser_navigator", self._node_navigate_and_fill)
        workflow.add_node("human_approval_node", self._node_wait_for_approval)

        # Set Entry Point
        workflow.set_entry_point("intent_parser")
        
        # Define Edges
        workflow.add_edge("intent_parser", "data_validator")
        
        workflow.add_conditional_edges(
            "data_validator",
            self._should_proceed_to_browser,
            {
                "continue": "browser_navigator",
                "stop": END 
            }
        )
        
        # After a browser action, go to the approval node to pause for the human.
        workflow.add_edge("browser_navigator", "human_approval_node")
        
        # After the human clicks 'Approve/Next', loop back or finish.
        # This allows multi-step tasks to continue using the same session.
        workflow.add_conditional_edges(
            "human_approval_node",
            self._should_continue_task,
            {
                "next_step": "intent_parser", # Loop back for next sub-command if needed
                "stay_ready": END              # Finish current command but keep browser open
            }
        )
        
        return workflow

    async def _node_parse_intent(self, state: AgentState) -> Dict[str, Any]:
        """Step 1: Extract intent and check memory for verified URLs."""
        logger.info("Node: Parsing Intent...")
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        try:
            intent = await self.brain.parse_intent(content)
            target_entity = intent.provider
            
            # Check if we already have a verified URL for this entity
            cached_url = self.profile.get_verified_url(target_entity)
            if cached_url:
                logger.info(f"Memory Hit: Navigating directly to {cached_url}")
                intent.search_query = cached_url 
            
            return {"intent": intent.model_dump(), "current_step": f"Task: {target_entity}"}
        except Exception as e:
            logger.error(f"Intent Parsing Error: {e}")
            return {"current_step": "I didn't quite catch that.", "missing_fields": ["intent"]}

    async def _node_validate_data(self, state: AgentState) -> Dict[str, Any]:
        """Step 2: Ensure we have enough data to perform a browser action."""
        intent = state.get("intent", {})
        if not intent.get("provider") or intent.get("provider") == "NONE":
            return {"missing_fields": ["provider"], "current_step": "Need more info."}
        return {"missing_fields": [], "current_step": "Task Validated"}

    async def _node_navigate_and_fill(self, state: AgentState) -> Dict[str, Any]:
        """
        Step 3: Execute the kinetic action (Navigation, Scoping, or Filling).
        This node keeps the browser alive and updates the visual context.
        """
        logger.info("Node: Executing Browser Action...")
        intent = state.get("intent", {})
        target_entity = intent.get("provider", "")
        query_or_url = intent.get("search_query") or f"{target_entity} official website"

        try:
            # Check if we are already on the target page to avoid redundant loading
            current_url = self.browser.page.url if self.browser.page else ""
            
            if query_or_url.startswith("http") and query_or_url not in current_url:
                await self.browser.navigate(query_or_url)
                current_step = f"Arrived at {target_entity}"
            elif "google.com" in current_url or not current_url:
                # Perform Intelligent Search Discovery
                await self.browser.navigate("https://www.google.com")
                await self.browser.page.fill('textarea[name="q"]', f"{target_entity} official website")
                await self.browser.page.press('textarea[name="q"]', "Enter")
                await self.browser.page.wait_for_load_state("networkidle")
                await asyncio.sleep(1) 

                screenshot_b64 = await self.browser.get_screenshot_b64()
                grounding = await self.brain.locate_official_link_on_page(screenshot_b64, target_entity)

                if grounding and grounding.coordinates:
                    dims = await self.browser.get_dimensions()
                    ymin, xmin, ymax, xmax = grounding.coordinates
                    center_x = int(((xmin + xmax) / 2) * (dims['width'] / 1000))
                    center_y = int(((ymin + ymax) / 2) * (dims['height'] / 1000))
                    
                    await self.browser.click_at_coordinates(center_x, center_y)
                    await self.browser.page.wait_for_load_state("load")
                    
                    final_url = self.browser.page.url
                    if "google.com" not in final_url:
                        self.profile.save_verified_site(target_entity, final_url)
                        current_step = f"Verified: {target_entity}"
                    else:
                        current_step = "Navigation Error"
                else:
                    await self.browser.find_and_click("h3")
                    current_step = "Using Fallback Link"
            else:
                current_step = f"Staying on {target_entity}"

            # Capture visual state for the Dashboard
            screenshot = await self.browser.get_screenshot_b64()
            return {"screenshot": screenshot, "current_step": current_step}

        except Exception as e:
            logger.error(f"Navigation Node Error: {e}")
            return {"current_step": "Action Failed"}

    async def _node_wait_for_approval(self, state: AgentState) -> Dict[str, Any]:
        """
        Checkpoint Node: This is where the Graph pauses.
        The thread remains alive, and the browser remains open.
        """
        logger.info("Sub-task complete. Waiting for user interaction or next command.")
        return {"current_step": "Ready for Next Step"}

    def _should_proceed_to_browser(self, state: AgentState) -> Literal["continue", "stop"]:
        if state.get("missing_fields"):
            return "stop"
        return "continue"

    def _should_continue_task(self, state: AgentState) -> Literal["next_step", "stay_ready"]:
        """
        Determines if the agent should immediately loop for another action
        or stay idle in the current browser state.
        """
        approval = state.get("human_approval")
        if approval == "approved":
            # If the user approved, we could potentially loop back if there's a sub-task queue
            return "stay_ready" 
        return "stay_ready"