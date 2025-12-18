from typing import Literal, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from core.state_schema import AgentState, AgentAction
from core.gemini_logic import ArvynBrain
from tools.browser import ArvynBrowser
from tools.voice import ArvynVoice
from tools.data_store import ArvynDataStore

class ArvynOrchestrator:
    def __init__(self):
        """Initializes the Brain, Hands, and Senses."""
        self.brain = ArvynBrain()
        self.browser = ArvynBrowser()
        self.voice = ArvynVoice()
        self.store = ArvynDataStore()
        self.memory = MemorySaver()
        
        self.workflow = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Constructs the Neuro-Symbolic Graph with cycles."""
        builder = StateGraph(AgentState)

        # Define Nodes (The "Work" units)
        builder.add_node("intent_parser", self.node_intent_parser)
        builder.add_node("data_validator", self.node_data_validator)
        builder.add_node("browser_executor", self.node_browser_executor)
        builder.add_node("human_approval", self.node_human_approval)
        builder.add_node("ask_user_missing", self.node_ask_user_missing)

        # Define Logic (The "Pathways")
        builder.add_edge(START, "intent_parser")
        builder.add_edge("intent_parser", "data_validator")
        
        # Conditional Edge: Check if data is complete
        builder.add_conditional_edges(
            "data_validator",
            self.check_data_completion,
            {
                "ready": "browser_executor",
                "missing": "ask_user_missing"
            }
        )

        # Loop back from asking user to validation
        builder.add_edge("ask_user_missing", "data_validator")
        
        # Guardrail: Approval before final submission
        builder.add_edge("browser_executor", "human_approval")
        builder.add_edge("human_approval", END)

        return builder.compile(checkpointer=self.memory)

    # ==========================================
    # NODE IMPLEMENTATIONS
    # ==========================================

    def node_intent_parser(self, state: AgentState):
        """Brain analyzes text to plan action."""
        last_message = state["messages"][-1]["content"]
        user_profile = self.store.get_profile()
        
        plan = self.brain.parse_intent(last_message, user_profile)
        return {"execution_plan": plan, "status": "planning"}

    def node_data_validator(self, state: AgentState):
        """Symbolic check for missing financial fields."""
        # Logic to extract provider from plan and check against store
        # Simplified: Check for 'consumer_id' as a baseline
        required = ["consumer_id", "mobile_number"]
        missing = self.store.get_missing_fields("default", required)
        
        return {"missing_fields": missing, "user_data": self.store.get_profile()}

    def check_data_completion(self, state: AgentState) -> Literal["ready", "missing"]:
        """Router: Determines the next logical step."""
        return "missing" if state["missing_fields"] else "ready"

    def node_ask_user_missing(self, state: AgentState):
        """HITL: Pauses to ask user for data via Voice/UI."""
        field = state["missing_fields"][0]
        prompt = f"I need your {field.replace('_', ' ')} to proceed."
        
        self.voice.speak(prompt)
        # CONSCIOUS PAUSE: Graph state is saved; execution stops
        user_response = interrupt(f"INPUT_REQUESTED:{field}")
        
        # Save received data back to symbolic store
        self.store.update_field("personal_info", field, user_response)
        return {"status": "data_updated"}

    async def node_browser_executor(self, state: AgentState):
        """Kinetic Layer: Playwright executes the plan."""
        await self.browser.start()
        
        for step in state["execution_plan"]:
            if step.action_type == "NAVIGATE":
                await self.browser.navigate(step.value)
            elif step.action_type == "CLICK":
                success = await self.browser.smart_click(step.selector)
                # FALLBACK: If DOM click fails, trigger Explorer Mode
                if not success:
                    screenshot = await self.browser.get_screenshot_b64()
                    coords = self.brain.visual_grounding(screenshot, step.thought)
                    if coords:
                        await self.browser.click_at_coordinates(coords['x'], coords['y'])
        
        return {"status": "awaiting_approval"}

    def node_human_approval(self, state: AgentState):
        """Final Security Guardrail: Requires Dashboard Approval."""
        self.voice.speak("I am ready to process the payment. Please approve it on your dashboard.")
        
        # CONSCIOUS PAUSE for HITL
        decision = interrupt("FINAL_APPROVAL")
        
        if decision == "APPROVE":
            return {"is_approved": True, "status": "completed"}
        else:
            return {"is_approved": False, "status": "cancelled"}