import os
import json
import logging
import asyncio
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from typing import Optional, Dict, Any, List, Union

from config import GEMINI_API_KEY, logger
from core.state_schema import IntentOutput, VisualGrounding

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

class GeminiBrain:
    """
    Advanced Visual-Reasoning Engine for Agent Arvyn.
    Features: Recursive Planning, Visual Grounding, and Default Provider Mapping.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.95,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json"
            }
        )
        logger.info(f"GeminiBrain initialized with model: {self.model_name}")

    async def _call_with_retry(self, prompt: str, image_data: Optional[str] = None):
        """Standardized API caller with quota handling."""
        try:
            content = [prompt]
            if image_data:
                content.append({"mime_type": "image/png", "data": image_data})
            
            response = await asyncio.to_thread(
                self.model.generate_content, 
                content,
                request_options=RequestOptions(retry=None)
            )
            return response.text
        except Exception as e:
            if "429" in str(e):
                raise Exception("QUOTA_EXCEEDED")
            raise e

    async def parse_intent(self, user_input: str) -> IntentOutput:
        """
        Sophisticated Entity & Intent Extraction.
        Fixed: Includes Default Mapping for Rio Finance Bank to prevent validation errors.
        """
        prompt = f"""
        TASK: Extract intent for a banking and browsing assistant.
        USER COMMAND: "{user_input}"
        
        LOGIC & DEFAULTS:
        1. ACTIONS: Map to PAY_BILL, BUY_GOLD, UPDATE_PROFILE, LOGIN, NAVIGATE, or SEARCH.
        2. DEFAULT PROVIDER: If the user mentions 'bill', 'gold', or 'bank' WITHOUT naming a specific bank, 
           ALWAYS set "provider" to "Rio Finance Bank".
        3. DATA: Extract amounts or specific values if mentioned.
        
        RETURN JSON:
        {{
            "action": "PAY_BILL | BUY_GOLD | UPDATE_PROFILE | LOGIN | NAVIGATE | SEARCH | QUERY",
            "target": "BANKING | UTILITY | BROWSER",
            "provider": "Normalized Entity Name (Default: 'Rio Finance Bank' for banking tasks)",
            "amount": float | null,
            "search_query": "Optimized query if navigation is needed",
            "urgency": "HIGH | MEDIUM | LOW"
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt)
            data = json.loads(raw_response.strip().replace("```json", "").replace("```", ""))
            
            # Post-processing to ensure provider is NEVER None (Safety against AI hallucinations)
            if not data.get("provider") or data["provider"] == "NONE":
                if data.get("action") in ["PAY_BILL", "BUY_GOLD", "UPDATE_PROFILE", "LOGIN"]:
                    data["provider"] = "Rio Finance Bank"
                else:
                    data["provider"] = "UNKNOWN"
                    
            return IntentOutput(**data)
        except Exception as e:
            logger.error(f"Intent Error: {e}")
            # Fallback to a safe object to prevent downstream crashes
            return IntentOutput(action="QUERY", provider="UNKNOWN", target="BROWSER")

    async def analyze_page_for_action(
        self, 
        screenshot_b64: str, 
        goal: str, 
        history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        THE CORE ENGINE: Visual Observation + Reasoning.
        Analyzes a screenshot to determine the next kinetic step.
        """
        history_summary = "\n".join([f"- {h.get('action')}: {h.get('element')}" for h in history[-5:]])
        
        prompt = f"""
        GOAL: {goal}
        CURRENT CONTEXT (User Data): {json.dumps(user_context)}
        RECENT STEPS TAKEN:
        {history_summary if history else "No actions taken yet."}

        TASK: Analyze the screenshot and determine the SINGLE NEXT STEP to move closer to the goal.

        STRATEGY:
        1. LOGIN: If you see login fields and aren't logged in, use credentials from CURRENT CONTEXT.
        2. DISCOVERY: On the Dashboard, identify 'Digital Gold', 'Bill Payments', or 'Profile' links.
        3. FORM FILLING: Use CONTEXT (Consumer ID, Address, PIN) to fill specific fields.
        4. INTERACTION: If a choice is required (e.g., 'Select Bank' or 'Enter PIN'), use ASK_USER.
        
        ACTION TYPES:
        - CLICK: [ymin, xmin, ymax, xmax]
        - TYPE: {{ "coordinates": [ymin, xmin, ymax, xmax], "text": "value" }}
        - ASK_USER: "Voice prompt for the user"
        - FINISHED: "Completion message"

        RETURN JSON ONLY:
        {{
            "thought": "Brief explanation of visual reasoning",
            "action_type": "CLICK | TYPE | ASK_USER | FINISHED",
            "element_name": "Name of target element",
            "coordinates": [ymin, xmin, ymax, xmax],
            "input_text": "text to type if action is TYPE",
            "voice_prompt": "Natural speech for ASK_USER or FINISHED"
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64)
            clean_json = raw_response.strip().replace("```json", "").replace("```", "")
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Visual Planning Error: {e}")
            return {"action_type": "ASK_USER", "voice_prompt": "I'm having trouble analyzing the screen. Could you guide me?"}

    async def locate_element(self, screenshot_b64: str, description: str) -> Optional[VisualGrounding]:
        """Precise coordinate mapping for a specific element description."""
        prompt = f"""
        Find the [ymin, xmin, ymax, xmax] coordinates for: "{description}"
        Return normalized coordinates [0-1000].
        
        RETURN JSON:
        {{
            "element_name": "{description}",
            "coordinates": [ymin, xmin, ymax, xmax],
            "confidence": 0.9
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64)
            data = json.loads(raw_response.strip().replace("```json", "").replace("```", ""))
            return VisualGrounding(**data)
        except Exception as e:
            logger.error(f"Locator Error: {e}")
            return None