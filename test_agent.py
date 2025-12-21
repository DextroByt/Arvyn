import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from langgraph.checkpoint.memory import MemorySaver

# Import migrated orchestrator and schema
from core.agent_orchestrator import ArvynOrchestrator
from core.state_schema import IntentOutput
from config import logger

class TestArvynWorkflow(unittest.IsolatedAsyncioTestCase):
    """
    Test suite to verify the Agent's Qwen-VL logic and autonomous safety guards.
    Run this with: python -m unittest Arvyn/test_agent.py
    """

    async def asyncSetUp(self):
        # 1. Initialize Orchestrator (Which now utilizes QwenBrain)
        self.orchestrator = ArvynOrchestrator()
        
        # 2. Mock the Brain to prevent API costs during unit tests
        self.orchestrator.brain = MagicMock()
        self.orchestrator.brain.parse_intent = AsyncMock()
        
        # FIX: Explicitly mock analyze_page_for_action as an AsyncMock 
        # that returns a DICTIONARY to prevent AttributeError: 'coroutine' object has no attribute 'get'
        self.orchestrator.brain.analyze_page_for_action = AsyncMock()
        
        # 3. Mock the Browser (ArvynBrowser) to avoid launching Playwright in tests
        self.orchestrator.browser = AsyncMock()
        self.orchestrator.browser.ensure_page = AsyncMock()
        self.orchestrator.browser.get_screenshot_b64 = AsyncMock(return_value="fake_qwen_vlm_base64")
        self.orchestrator.browser.navigate = AsyncMock()
        self.orchestrator.browser.click_at_coordinates = AsyncMock()
        self.orchestrator.browser.type_text = AsyncMock()
        
        # 4. Use a fresh checkpointer for session isolation
        self.checkpointer = MemorySaver()
        await self.orchestrator.init_app(self.checkpointer)
        
        # Updated thread ID to reflect the Qwen-VL session version
        self.config = {"configurable": {"thread_id": "test_qwen_autonomous_v4"}}

    async def test_intent_parsing_and_discovery(self):
        """Verify the agent correctly parses Qwen-VL intent and proceeds to site discovery."""
        print("\n--- Testing Intent Parsing & Discovery ---")
        
        user_input = "Check my Rio Bank gold balance"
        
        # Mocking the parsed intent response
        self.orchestrator.brain.parse_intent.return_value = IntentOutput(
            action="QUERY", 
            target="BANKING", 
            provider="Rio Finance Bank", 
            urgency="MEDIUM",
            reasoning="User specified banking keywords and Rio Finance Bank."
        )

        initial_input = {"messages": [("user", user_input)]}
        steps = []
        
        async for event in self.orchestrator.app.astream(initial_input, config=self.config):
            for node, output in event.items():
                steps.append(node)
                print(f"Executed Node: {node}")

        # ASSERTIONS matching the ArvynOrchestrator node structure
        self.assertIn("intent_parser", steps)
        self.assertIn("site_discovery", steps)
        
        print("RESULT: Agent correctly identified intent and reached Site Discovery.")

    async def test_autonomous_execution_path(self):
        """Verify the agent enters the executor and correctly handles Qwen-VL vision actions."""
        print("\n--- Testing Autonomous Executor Loop ---")
        
        self.orchestrator.brain.parse_intent.return_value = IntentOutput(
            action="PURCHASE", target="E-COMMERCE", provider="Amazon"
        )
        
        # FIX: Ensure the mock returns a dictionary to satisfy .get() calls in the orchestrator
        self.orchestrator.brain.analyze_page_for_action.return_value = {
            "thought": "CoT: Page loaded. I see the search bar. Calculating geometric center.",
            "action_type": "CLICK",
            "element_name": "Amazon Search Input",
            "coordinates": [50, 200, 80, 500],
            "voice_prompt": "Navigating Amazon UI."
        }

        initial_input = {"messages": [("user", "Buy a mechanical keyboard on Amazon")]}
        
        # Run limited steps to verify entry into the autonomous executor
        count = 0
        steps = []
        async for event in self.orchestrator.app.astream(initial_input, config=self.config):
            for node, output in event.items():
                steps.append(node)
                print(f"Executed Node: {node}")
            count += 1
            if count > 2: break 

        self.assertIn("autonomous_executor", steps)
        print("RESULT: Agent successfully engaged the Qwen-VL Autonomous Executor.")

    async def test_human_interaction_on_visual_stuck(self):
        """Verify the agent pauses and triggers the interaction node if the VLM is stuck."""
        print("\n--- Testing Human Interaction Fallback ---")
        
        self.orchestrator.brain.parse_intent.return_value = IntentOutput(
            action="LOGIN", provider="Netflix"
        )
        
        # Simulate a visual failure where the VLM needs human help
        self.orchestrator.brain.analyze_page_for_action.return_value = {
            "thought": "I cannot locate the email field even after visual scan.",
            "action_type": "ASK_USER",
            "voice_prompt": "I can't see the login fields."
        }

        initial_input = {"messages": [("user", "Sign in to my Netflix account")]}
        
        async for event in self.orchestrator.app.astream(initial_input, config=self.config):
            for node, output in event.items():
                print(f"Executed Node: {node}")
                if node == "human_interaction_node":
                    break

        # Check the graph state to ensure it stopped at the correct node
        state = self.orchestrator.app.get_state(self.config)
        self.assertIn("human_interaction_node", state.next)
        print("RESULT: Agent successfully reached Human Interaction Node.")

if __name__ == "__main__":
    unittest.main()