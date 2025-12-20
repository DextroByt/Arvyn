import os
import json
import logging
import asyncio
import re
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from typing import Optional, Dict, Any, List, Union

from config import GEMINI_API_KEY, GEMINI_MODEL_NAME, logger
from core.state_schema import IntentOutput, VisualGrounding

# Configure SDK
genai.configure(api_key=GEMINI_API_KEY)

class GeminiBrain:
    """
    Superior Visual-Reasoning Engine for Agent Arvyn.
    Features: Chain-of-Thought reasoning, Advanced Visual Grounding, 
    and strict Banking Logic for Rio Finance Bank.
    """
    
    def __init__(self, model_name: str = GEMINI_MODEL_NAME):
        # Uses the model specified in Config (Gemini 2.5 Flash)
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.0, # Zero temperature for precision banking
                "top_p": 0.95,
                "max_output_tokens": 4096,
                "response_mime_type": "application/json"
            }
        )
        logger.info(f"[BRAIN] GeminiBrain initialized with: {self.model_name}")

    def _clean_json_response(self, raw_text: str) -> str:
        """Robust JSON extraction from LLM markdown wrappers."""
        try:
            # Remove markdown code blocks if present
            clean_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
            # Find the first { and last } to isolate the object
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            if start != -1 and end != -1:
                return clean_text[start:end+1]
            return clean_text
        except Exception as e:
            logger.error(f"[ERROR] JSON Cleaning Error: {e}")
            return "{}"

    async def _call_with_retry(self, prompt: str, image_data: Optional[str] = None, retries: int = 3):
        """Standardized API caller with exponential backoff and 404 safety."""
        for attempt in range(retries):
            try:
                content = [prompt]
                if image_data:
                    content.append({"mime_type": "image/png", "data": image_data})
                
                # API Call using the standard SDK
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    content,
                    request_options=RequestOptions(retry=None)
                )
                
                if not response.text:
                    raise ValueError("Empty response from Gemini API.")
                return response.text
                
            except Exception as e:
                # Catching the 404/Quota errors found in your logs
                logger.warning(f"[RETRY] Attempt {attempt+1} failed: {e}")
                if "429" in str(e): # Rate limit
                    await asyncio.sleep(2 ** attempt)
                elif "404" in str(e):
                    logger.critical(f"[FATAL] Model {self.model_name} not found. Check region/API version.")
                    raise e
                elif attempt == retries - 1:
                    raise e
                await asyncio.sleep(1)

    async def parse_intent(self, user_input: str) -> IntentOutput:
        """
        Superior Intent Extraction.
        Anchors the agent to Rio Finance Bank for all banking/gold/bill requests.
        """
        prompt = f"""
        TASK: Parse user command for a High-Precision Autonomous Banking Agent.
        USER COMMAND: "{user_input}"
        
        DOMAIN CONTEXT:
        - Primary Target: Rio Finance Bank (https://roshan-chaudhary13.github.io/rio_finance_bank/)
        - Supported Actions: PAY_BILL, BUY_GOLD, UPDATE_PROFILE, LOGIN, NAVIGATE, SEARCH.

        LOGIC:
        1. Default to "Rio Finance Bank" if "bill", "gold", "login", or "bank" is mentioned.
        2. Set target to "BANKING" for all financial tasks.

        RETURN JSON FORMAT:
        {{
            "action": "PAY_BILL | BUY_GOLD | UPDATE_PROFILE | LOGIN | NAVIGATE | SEARCH | QUERY",
            "target": "BANKING | UTILITY | BROWSER",
            "provider": "Rio Finance Bank",
            "amount": float or null,
            "search_query": "Optimized search string",
            "urgency": "HIGH | MEDIUM | LOW",
            "reasoning": "Brief CoT explanation"
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt)
            data = json.loads(self._clean_json_response(raw_response))
            
            # Post-processing Safety: Force the bank if context implies it
            if data.get("target") == "BANKING" or data.get("action") in ["PAY_BILL", "BUY_GOLD", "LOGIN"]:
                data["provider"] = "Rio Finance Bank"
            
            return IntentOutput(**data)
        except Exception as e:
            logger.error(f"[ERROR] Intent Extraction Failure: {e}")
            return IntentOutput(action="QUERY", provider="Rio Finance Bank", target="BANKING")

    async def analyze_page_for_action(
        self, 
        screenshot_b64: str, 
        goal: str, 
        history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Advanced Visual Execution Planner.
        Maps current UI state to the goal using 1920x1080 normalized coordinates.
        """
        # Increased history buffer to 10 steps for complex sequences
        history_log = "\n".join([f"- Step {i}: {h.get('action')} on {h.get('element')} -> {h.get('thought')}" for i, h in enumerate(history[-10:])])
        
        prompt = f"""
        OBJECTIVE: {goal}
        USER DATA: {json.dumps(user_context)}
        SESSION HISTORY:
        {history_log if history else "Start of session."}

        SCREEN ANALYSIS TASK: 
        1. Analyze the attached screenshot (1920x1080 resolution).
        2. Select the next UI element to interact with.
        3. Provide coordinates [ymin, xmin, ymax, xmax] in 0-1000 normalized space.

        RULES:
        - Buttons: Target the geometric center.
        - Text Fields: Target the clickable input area.
        - ACTION: Use FINISHED once you see a transaction confirmation or success message.

        RETURN JSON ONLY:
        {{
            "thought": "Explain your visual analysis and next logical step.",
            "action_type": "CLICK | TYPE | ASK_USER | FINISHED",
            "element_name": "Label of the element",
            "coordinates": [ymin, xmin, ymax, xmax],
            "input_text": "Text to type (if action is TYPE)",
            "voice_prompt": "Arvyn's spoken update for the user",
            "is_navigation_required": boolean
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64)
            analysis = json.loads(self._clean_json_response(raw_response))
            
            # Coordinate Safety Check
            if analysis.get("action_type") in ["CLICK", "TYPE"]:
                coords = analysis.get("coordinates")
                if not coords or len(coords) != 4:
                    logger.warning("[WARNING] VLM failed coordinates. Reverting to user guidance.")
                    return {"action_type": "ASK_USER", "voice_prompt": "I see the element but need your help to click it precisely."}
            
            return analysis
        except Exception as e:
            logger.error(f"[ERROR] Brain Visual Crash: {e}")
            return {
                "action_type": "ASK_USER", 
                "voice_prompt": "I'm having a visual processing delay. Please guide me manually.",
                "thought": f"Error: {str(e)}"
            }