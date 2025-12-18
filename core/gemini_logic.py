import base64
import json
import logging
from typing import List, Optional, Dict, Literal
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from config import GEMINI_API_KEY, logger

# ==========================================
# SCHEMA DEFINITIONS (Structured Output)
# ==========================================
class AgentAction(BaseModel):
    """
    Defines a single atomic action for the automation agent.
    """
    action_type: Literal["CLICK", "INPUT", "WAIT", "SCROLL", "NAVIGATE", "DONE", "FAIL"] = Field(
        ..., description="The type of action to perform."
    )
    selector: Optional[str] = Field(
        None, description="The semantic selector (e.g., 'Submit Button', '#login-id') or instruction."
    )
    input_value: Optional[str] = Field(
        None, description="The text value to type if the action is INPUT."
    )
    reasoning: str = Field(
        ..., description="Brief thought process explaining why this action was chosen."
    )

class ArvynBrain:
    def __init__(self):
        """Initializes the Gemini client with advanced safety and logging."""
        if not GEMINI_API_KEY:
            logger.critical("GEMINI_API_KEY is missing! The Brain cannot function.")
            raise ValueError("GEMINI_API_KEY not found.")
        
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        # using 1.5-flash for speed/efficiency, use 'gemini-1.5-pro' for maximum reasoning
        self.model_id = "gemini-3-pro-preview" 
        logger.info(f"ArvynBrain initialized with model: {self.model_id}")

    def parse_intent(self, user_input: str, user_context: Dict) -> List[AgentAction]:
        """
        Parses raw natural language into a sequence of executable AgentActions.
        Uses context-aware reasoning to disambiguate user requests.
        """
        logger.debug(f"Parsing intent for input: {user_input}")
        
        prompt = f"""
        You are the Brain of Agent Arvyn, a sophisticated financial automation expert.
        
        User Command: "{user_input}"
        User Context (Profile/Memory): {json.dumps(user_context)}

        Task: Convert the user command into a logical sequence of 'AgentAction' steps.
        
        Guidelines:
        1. If the User Context is missing required info (like a bank name), issue a 'WAIT' action to ask the user.
        2. Break complex tasks down. For "Pay my electric bill", start with "NAVIGATE" to the site.
        3. Be decisive. Select the most likely path based on the context.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=list[AgentAction], # Request a LIST of actions
                    temperature=0.2 # Low temperature for deterministic actions
                ),
            )
            
            # The SDK handles serialization often, but we parse explicitly to be safe
            actions_data = json.loads(response.text)
            
            # Validate with Pydantic
            actions = [AgentAction(**item) for item in actions_data]
            
            logger.info(f"Generated {len(actions)} actions successfully.")
            for i, act in enumerate(actions):
                logger.debug(f"Step {i+1}: {act.action_type} - {act.reasoning}")
                
            return actions

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Logic Error in Intent Parsing: {e}")
            # Fallback: Return a WAIT action so the agent doesn't crash
            return [AgentAction(
                action_type="WAIT", 
                reasoning="I encountered a processing error. Please repeat the command.", 
                selector="Error Recovery"
            )]
        except Exception as e:
            logger.critical(f"API Error in parse_intent: {e}")
            return []

    def visual_grounding(self, screenshot_b64: str, target_desc: str) -> Optional[Dict[str, float]]:
        """
        Explorer Mode: Analyzes a screenshot to find pixel coordinates of a UI element.
        This is the 'Self-Healing' mechanism used when DOM selectors fail.
        """
        logger.info(f"Visual Grounding requested for: {target_desc}")
        
        prompt = f"""
        Analyze this UI screenshot. Locate the visual element described as: '{target_desc}'.
        Return the center X and Y coordinates as normalized values (0.0 to 1.0) in JSON format:
        {{"x": 0.5, "y": 0.5}}
        If not found, return null.
        """
        
        try:
            image_part = types.Part.from_bytes(
                data=base64.b64decode(screenshot_b64),
                mime_type="image/png"
            )

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )

            coords = json.loads(response.text)
            logger.info(f"Visual coordinates found: {coords}")
            return coords

        except Exception as e:
            logger.warning(f"Visual Grounding failed: {e}")
            return None

    def analyze_ui_safety(self, screenshot_b64: str, expected_amount: str) -> bool:
        """
        Critical Verification: 'Sees' the final confirmation modal to prevent payment errors.
        """
        logger.info(f"Performing UI Safety Check. Expected: {expected_amount}")
        
        prompt = f"Does this payment confirmation screen show a transaction amount of roughly {expected_amount}? Answer only 'YES' or 'NO'."
        
        try:
            image_part = types.Part.from_bytes(
                data=base64.b64decode(screenshot_b64),
                mime_type="image/png"
            )

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, image_part]
            )
            
            result = "YES" in response.text.upper()
            logger.info(f"Safety Check Result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Safety Check Error: {e}")
            return False