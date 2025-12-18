import base64
import json
from typing import List, Optional, Dict
from google import genai
from google.genai import types
from pydantic import ValidationError

from config import GEMINI_API_KEY
from core.state_schema import AgentAction, UIElement

class ArvynBrain:
    def __init__(self):
        """Initializes the Gemini 1.5 Pro client with strict safety settings."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_id = "gemini-1.5-pro"

    def parse_intent(self, user_input: str, user_context: Dict) -> List[AgentAction]:
        """
        Parses raw natural language into a sequence of executable AgentActions.
        Uses context-aware reasoning to disambiguate user requests.
        """
        prompt = f"""
        You are the Brain of Agent Arvyn, a financial automation expert.
        User Command: "{user_input}"
        User Context: {json.dumps(user_context)}

        Task: Convert the user command into a sequence of 'AgentAction' steps.
        Rules:
        1. If the provider is ambiguous, issue a 'WAIT' action to ask for clarification.
        2. Ensure every 'CLICK' or 'INPUT' has a valid semantic selector.
        3. Output MUST be a valid JSON list matching the AgentAction schema.
        """

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AgentAction,
            ),
        )

        try:
            return [AgentAction(**item) for item in json.loads(response.text)]
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Logic Error in Intent Parsing: {e}")
            return []

    def visual_grounding(self, screenshot_b64: str, target_desc: str) -> Optional[Dict[str, float]]:
        """
        Explorer Mode: Analyzes a screenshot to find pixel coordinates of a UI element.
        This is the 'Self-Healing' mechanism used when DOM selectors fail.
        """
        prompt = f"Locate the '{target_desc}' on this screen. Return the center X and Y coordinates as normalized values (0.0 to 1.0)."
        
        image_part = types.Part.from_bytes(
            data=base64.b64decode(screenshot_b64),
            mime_type="image/png"
        )

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=[prompt, image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                # Expecting format: {"x": 0.5, "y": 0.5}
            ),
        )

        try:
            return json.loads(response.text)
        except Exception:
            return None

    def analyze_ui_safety(self, screenshot_b64: str, expected_amount: str) -> bool:
        """
        Critical Verification: 'Sees' the final confirmation modal to prevent payment errors.
        """
        prompt = f"Does this payment confirmation screen show an amount of {expected_amount}? Answer only 'YES' or 'NO'."
        
        image_part = types.Part.from_bytes(
            data=base64.b64decode(screenshot_b64),
            mime_type="image/png"
        )

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=[prompt, image_part]
        )
        
        return "YES" in response.text.upper()