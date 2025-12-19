import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from langgraph.checkpoint.memory import MemorySaver

# Import your actual logic
from core.agent_orchestrator import ArvynOrchestrator
from core.state_schema import IntentOutput

class TestArvynWorkflow(unittest.IsolatedAsyncioTestCase):
    """
    Test suite to verify the Agent's linear logic and safety guards.
    Run this with: python -m unittest Arvyn/test_agent.py
    """

    async def asyncSetUp(self):
        # 1. Initialize Orchestrator
        self.orchestrator = ArvynOrchestrator()
        
        # 2. Mock the Brain so we don't spend API credits
        self.orchestrator.brain = MagicMock()
        self.orchestrator.brain.parse_intent = AsyncMock()
        
        # 3. Mock the Browser so it doesn't actually open
        self.orchestrator.browser = AsyncMock()
        self.orchestrator.browser.get_screenshot_b64 = AsyncMock(return_value="fake_base64_data")
        
        # 4. Use a fresh checkpointer for each test
        self.checkpointer = MemorySaver()
        await self.orchestrator.init_app(self.checkpointer)
        
        self.config = {"configurable": {"thread_id": "test_session"}}

    async def test_missing_data_stops_loop(self):
        """Verify that the agent stops if consumer_id is missing, instead of looping."""
        print("\n--- Testing Missing Data Stop ---")
        
        # Simulate user asking to pay a bill
        user_input = "Pay my water bill"
        
        # Mock Brain returning a valid intent
        self.orchestrator.brain.parse_intent.return_value = IntentOutput(
            action="PAY", 
            target="UTILITY", 
            provider="SUEZ", 
            urgency="HIGH"
        )
        
        # Mock Profile Manager to return MISSING data
        self.orchestrator.profile.get_provider_details = MagicMock(return_value={})

        # Run the graph
        initial_input = {"messages": [("user", user_input)]}
        steps = []
        
        async for event in self.orchestrator.app.astream(initial_input, config=self.config):
            for node, output in event.items():
                steps.append(node)
                print(f"Executed Node: {node}")

        # ASSERTIONS
        self.assertIn("intent_parser", steps)
        self.assertIn("data_validator", steps)
        self.assertNotIn("browser_navigator", steps, "Should NOT proceed to browser if data is missing!")
        
        print("RESULT: Agent stopped safely at validation. No infinite loops detected.")

    async def test_full_workflow_to_approval(self):
        """Verify the agent reaches the approval node when data is present."""
        print("\n--- Testing Full Successful Workflow ---")
        
        self.orchestrator.brain.parse_intent.return_value = IntentOutput(
            action="PAY", target="UTILITY", provider="SUEZ", urgency="HIGH"
        )
        
        # Mock Profile Manager returning VALID data
        self.orchestrator.profile.get_provider_details = MagicMock(
            return_value={"consumer_id": "12345"}
        )

        initial_input = {"messages": [("user", "Pay SUEZ")]}
        steps = []
        
        async for event in self.orchestrator.app.astream(initial_input, config=self.config):
            for node, output in event.items():
                steps.append(node)
                print(f"Executed Node: {node}")

        self.assertIn("browser_navigator", steps)
        
        # Check if the next step is indeed the interrupt
        state = self.orchestrator.app.get_state(self.config)
        self.assertIn("human_approval_node", state.next)
        print("RESULT: Agent successfully paused for Human Approval.")

if __name__ == "__main__":
    unittest.main()