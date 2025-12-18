import asyncio
from typing import Dict, List, Optional
from langgraph.graph import StateGraph, END

from core.state_schema import AgentState
from core.gemini_logic import ArvynBrain, AgentAction
from tools.browser import BrowserManager
from config import logger

class ArvynOrchestrator:
    def __init__(self):
        self.brain = ArvynBrain()
        self.browser = BrowserManager()
        self.builder = StateGraph(AgentState)
        self._setup_graph()
        self.graph = self.builder.compile()

    def _setup_graph(self):
        """Builds the Neuro-Symbolic Graph architecture."""
        self.builder.add_node("perceive", self.node_perceive)
        self.builder.add_node("reason", self.node_reason)
        self.builder.add_node("execute", self.node_execute)
        self.builder.add_node("verify", self.node_verify)

        self.builder.set_entry_point("perceive")
        self.builder.add_edge("perceive", "reason")
        self.builder.add_edge("reason", "execute")
        self.builder.add_edge("execute", "verify")
        
        self.builder.add_conditional_edges(
            "verify",
            self.decide_next_step,
            {"continue": "perceive", "end": END}
        )

    async def node_perceive(self, state: AgentState) -> Dict:
        """Captures the current state of the page (URL + Screenshot)."""
        if not self.browser.is_running:
            await self.browser.start()
        
        browser_data = await self.browser.get_state()
        return {
            "current_screenshot": browser_data["screenshot"],
            "ui_message": f"Analyzing {browser_data['url']}..."
        }

    async def node_reason(self, state: AgentState) -> Dict:
        """Determines next steps based on user intent and visual state."""
        if not state.get("execution_plan") or state.get("last_error"):
            # Re-plan if we have no plan or just hit an error
            context = state.get("user_data", {})
            new_plan = self.brain.parse_intent(state["messages"][-1]["content"], context)
            return {"execution_plan": new_plan, "status": "thinking", "last_error": None}
        return {}

    async def node_execute(self, state: AgentState) -> Dict:
        """Executes the next action with Self-Healing fallback."""
        plan = state["execution_plan"]
        # Find the next step that hasn't been completed
        action = plan[0] # Simplified for this cycle

        try:
            # 1. Attempt Standard Code-Based Interaction
            await self.browser.execute_action(
                action.action_type, 
                selector=action.selector, 
                value=action.value
            )
            return {"status": "acting", "ui_message": f"Executed {action.action_type}"}

        except Exception as e:
            logger.warning(f"Standard action failed: {e}. Attempting Visual Healing...")
            
            # 2. NEURO FALLBACK: Use Gemini to "see" the element and click coordinates
            if state["current_screenshot"] and action.selector:
                coords = self.brain.visual_grounding(state["current_screenshot"], action.selector)
                if coords:
                    await self.browser.click_at_coordinates(coords['x'], coords['y'])
                    return {"status": "healed", "ui_message": "Action recovered via Vision Logic"}
            
            return {"last_error": str(e), "status": "retrying"}

    async def node_verify(self, state: AgentState) -> Dict:
        """Safety check for financial finalization."""
        # Check if the screen looks like a 'Confirm Payment' screen
        if state.get("current_screenshot"):
            is_payment_screen = "PAY" in (state.get("ui_message") or "").upper()
            if is_payment_screen and not state.get("is_approved"):
                return {"ui_message": "Waiting for manual verification..."}
        
        return {"status": "verifying"}

    def decide_next_step(self, state: AgentState) -> str:
        if state.get("status") == "completed" or state.get("last_error"):
            return "end"
        return "continue"

    async def run(self, user_command: str):
        """Streams graph updates for real-time console tracking."""
        initial_state = {
            "messages": [{"role": "user", "content": user_command}],
            "user_data": {},
            "missing_fields": [],
            "execution_plan": [],
            "current_screenshot": None,
            "status": "starting",
            "last_error": None,
            "is_approved": False
        }
        async for output in self.graph.astream(initial_state):
            yield output