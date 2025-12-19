import os
import json
import logging
import asyncio
import re
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from typing import Optional, Dict, Any, List, Union

from config import GEMINI_API_KEY, logger
from core.state_schema import IntentOutput, VisualGrounding

# Configure the older SDK
genai.configure(api_key=GEMINI_API_KEY)

class GeminiBrain:
    """
    Advanced Visual-Reasoning Engine for Agent Arvyn.
    Updated: Uses google-generativeai SDK with robust JSON parsing.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        # Note: 'gemini-2.5-flash' requires the updated SDK; 
        # using 'gemini-1.5-flash' if 2.5 is not yet available in your region.
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

    def _clean_json_response(self, raw_text: str) -> str:
        """Removes markdown blocks and fixes common JSON formatting issues."""
        # Remove markdown code blocks
        clean_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
        # Ensure it isolates the first valid JSON object
        start = clean_text.find('{')
        end = clean_text.rfind('}')
        if start != -1 and end != -1:
            return clean_text[start:end+1]
        return clean_text

    async def _call_with_retry(self, prompt: str, image_data: Optional[str] = None):
        """Standardized API caller using the google-generativeai SDK."""
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
        """Sophisticated Entity & Intent Extraction."""
        prompt = f"""
        TASK: Extract intent for a banking assistant.
        USER COMMAND: "{user_input}"
        
        LOGIC & DEFAULTS:
        1. ACTIONS: PAY_BILL, BUY_GOLD, UPDATE_PROFILE, LOGIN, NAVIGATE, SEARCH.
        2. DEFAULT PROVIDER: If task is banking but no bank is named, use "Rio Finance Bank".
        
        RETURN JSON:
        {{
            "action": "PAY_BILL | BUY_GOLD | UPDATE_PROFILE | LOGIN | NAVIGATE | SEARCH | QUERY",
            "target": "BANKING | UTILITY | BROWSER",
            "provider": "Normalized Entity Name",
            "amount": float | null,
            "search_query": "Optimized query",
            "urgency": "HIGH | MEDIUM | LOW"
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt)
            data = json.loads(self._clean_json_response(raw_response))
            
            if not data.get("provider") or data["provider"] == "NONE":
                if data.get("action") in ["PAY_BILL", "BUY_GOLD", "UPDATE_PROFILE", "LOGIN"]:
                    data["provider"] = "Rio Finance Bank"
                else:
                    data["provider"] = "UNKNOWN"
                    
            return IntentOutput(**data)
        except Exception as e:
            logger.error(f"Intent Error: {e}")
            return IntentOutput(action="QUERY", provider="UNKNOWN", target="BROWSER")

    async def analyze_page_for_action(
        self, 
        screenshot_b64: str, 
        goal: str, 
        history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyzes a screenshot to determine the next step."""
        history_summary = "\n".join([f"- {h.get('action')}: {h.get('element')}" for h in history[-5:]])
        
        prompt = f"""
        GOAL: {goal}
        CONTEXT: {json.dumps(user_context)}
        STEPS: {history_summary if history else "None"}

        TASK: Analyze screenshot and return JSON for ONE action.
        ACTION TYPES: CLICK, TYPE, ASK_USER, FINISHED.

        RETURN JSON ONLY:
        {{
            "thought": "Brief explanation",
            "action_type": "CLICK | TYPE | ASK_USER | FINISHED",
            "element_name": "Target name",
            "coordinates": [ymin, xmin, ymax, xmax],
            "input_text": "text to type",
            "voice_prompt": "Natural speech"
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64)
            return json.loads(self._clean_json_response(raw_response))
        except Exception as e:
            logger.error(f"Visual Planning Error: {e}")
            return {"action_type": "ASK_USER", "voice_prompt": "I'm having trouble reading the screen."}