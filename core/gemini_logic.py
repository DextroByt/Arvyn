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
    Features: Multi-Stage Chain-of-Thought, Fuzzy JSON Recovery, 
    and Domain-Specific Logic for High-Precision Banking.
    """
    
    def __init__(self, model_name: str = GEMINI_MODEL_NAME):
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.0, # Zero temperature for absolute banking precision
                "top_p": 0.95,
                "max_output_tokens": 4096,
                "response_mime_type": "application/json"
            }
        )
        logger.info(f"[BRAIN] Superior Intelligence Engine active: {self.model_name}")

    def _clean_json_response(self, raw_text: Any) -> str:
        """Robust JSON extraction with type-safety to prevent string-mapping errors."""
        try:
            if not isinstance(raw_text, str):
                raw_text = str(raw_text) if raw_text else "{}"

            # Standard cleanup for Gemini markdown blocks
            clean_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
            
            # Isolate the JSON object via brace-matching
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            if start != -1 and end != -1:
                return clean_text[start:end+1]
            return clean_text
        except Exception as e:
            logger.error(f"[ERROR] Logic Layer: JSON Recovery failed: {e}")
            return "{}"

    async def _call_with_retry(self, prompt: str, image_data: Optional[str] = None, retries: int = 4):
        """Advanced API caller with Dynamic Backoff for Quota stability."""
        for attempt in range(retries):
            try:
                content = [prompt]
                if image_data:
                    content.append({"mime_type": "image/png", "data": image_data})
                
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    content,
                    request_options=RequestOptions(retry=None)
                )
                
                if not response or not response.text:
                    raise ValueError("Incomplete response from Gemini API.")
                return response.text
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str:
                    # Exponential backoff tuned for 5 RPM limit
                    wait_time = (2 ** attempt) * 12 
                    logger.warning(f"[QUOTA] Rate limit hit. Cooling down for {wait_time}s...")
                    await asyncio.sleep(wait_time)
                elif "404" in error_str:
                    logger.critical(f"[FATAL] Model {self.model_name} access denied.")
                    raise e
                elif attempt == retries - 1:
                    raise e
                else:
                    await asyncio.sleep(2)

    async def parse_intent(self, user_input: str) -> IntentOutput:
        """
        Superior Intent Extraction.
        Anchors all financial commands to the Rio Finance Bank portal.
        """
        prompt = f"""
        TASK: High-Precision Intent Parsing for Autonomous Banking.
        USER COMMAND: "{user_input}"
        
        CONTEXT:
        - Primary Target: Rio Finance Bank (https://roshan-chaudhary13.github.io/rio_finance_bank/)
        - Priority Keywords: electricity, bill, gold, pay, login, transfer, banking.

        LOGIC RULES:
        1. If user mentions any Priority Keyword, the provider MUST be "Rio Finance Bank".
        2. Map action based on verbs: 'bill' -> PAY_BILL, 'gold' -> BUY_GOLD, 'login' -> LOGIN.
        3. Ensure urgency is 'HIGH' for all bill/payment tasks.

        RETURN JSON:
        {{
            "action": "PAY_BILL | BUY_GOLD | UPDATE_PROFILE | LOGIN | NAVIGATE | SEARCH | QUERY",
            "target": "BANKING",
            "provider": "Rio Finance Bank",
            "amount": float or null,
            "search_query": "Optimized query string",
            "urgency": "HIGH",
            "reasoning": "Explain identifying the banking goal from user input."
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt)
            data = json.loads(self._clean_json_response(raw_response))
            return IntentOutput(**data)
        except Exception as e:
            logger.error(f"[ERROR] Intent Parser Fault: {e}")
            return IntentOutput(action="NAVIGATE", provider="Rio Finance Bank", target="BANKING", reasoning="Error recovery.")

    async def analyze_page_for_action(
        self, 
        screenshot_b64: str, 
        goal: str, 
        history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Advanced Visual Execution Planner.
        UPGRADED: Features High-Precision Grounding for 1080p and State-Transition Verification.
        """
        # Increased history buffer for better context on loop-prevention
        history_log = "\n".join([f"- Step {i}: {h.get('action')} on {h.get('element')} -> {h.get('thought')}" for i, h in enumerate(history[-15:])])
        
        mapping_instruction = """
        IMPORTANT DATA MAPPING & SECURITY:
        - 'login_credentials': Contains 'email' and 'password'. USE THESE ONLY for Login forms.
        - 'security_details': Contains 'upi_pin' or 'card_pin'. USE THESE ONLY for payment/PIN screens.
        - VERIFICATION: Check the page content (titles, input labels) to ensure you are using the right block.
        - WARNING: Never use a PIN for a 'Password' field.
        """

        prompt = f"""
        OBJECTIVE: {goal}
        USER DATA: {json.dumps(user_context)}
        {mapping_instruction}

        HISTORY (Last 15 steps):
        {history_log if history else "Initial state."}

        VISUAL TASK (1920x1080 Resolution):
        1. Identify the target element based on the goal.
        2. COORDINATE ACCURACY: You MUST be precise. Provide [ymin, xmin, ymax, xmax] in 0-1000 scale.
           - Buttons: Target the geometric center of the button text.
           - Inputs: Target the center of the input box.
        3. VERIFICATION: If you previously clicked 'Login' and are still on the Home page, YOUR CLICK FAILED. Try targeting the exact center of the 'Login' text or the button borders.
        4. DATA INJECTION: If typing credentials, use the exact values from 'login_credentials'.

        RETURN JSON:
        {{
            "thought": "CoT: 1. Current page identification. 2. Analysis of why the last step succeeded/failed. 3. Target element choice and coordinate calculation.",
            "action_type": "CLICK | TYPE | ASK_USER | FINISHED",
            "element_name": "Full descriptive name of the UI element",
            "coordinates": [ymin, xmin, ymax, xmax],
            "input_text": "Text to type (from correct credential block)",
            "voice_prompt": "Concise status update for the user.",
            "is_navigation_required": false
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64)
            analysis = json.loads(self._clean_json_response(raw_response))
            
            # Coordination check for kinetic safety
            if analysis.get("action_type") in ["CLICK", "TYPE"]:
                coords = analysis.get("coordinates")
                if not coords or len(coords) != 4:
                    logger.warning("[BRAIN] Coordinate anomaly. Requesting human guidance.")
                    return {"action_type": "ASK_USER", "voice_prompt": "I see the next step but need help clicking it precisely."}
            
            return analysis
        except Exception as e:
            logger.error(f"[ERROR] Visual Logic Fault: {e}")
            return {
                "action_type": "ASK_USER", 
                "voice_prompt": "I'm having trouble reasoning about this page. Please assist.",
                "thought": f"Exception: {str(e)}"
            }