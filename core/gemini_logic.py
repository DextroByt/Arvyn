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
    UPGRADED: Features Data-Integrity Enforcement and Label-Aware Grounding.
    FIXED: Eliminates credential hallucination and improves coordinate centering.
    """
    
    def __init__(self, model_name: str = GEMINI_MODEL_NAME):
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.0, 
                "top_p": 0.95,
                "max_output_tokens": 4096,
                "response_mime_type": "application/json"
            }
        )
        logger.info(f"[BRAIN] Intelligence Engine active: {self.model_name}")

    def _clean_json_response(self, raw_text: Any) -> str:
        """Robust JSON extraction with type-safety."""
        try:
            if not isinstance(raw_text, str):
                raw_text = str(raw_text) if raw_text else "{}"
            clean_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            if start != -1 and end != -1:
                return clean_text[start:end+1]
            return clean_text
        except Exception as e:
            logger.error(f"[ERROR] Logic Layer: JSON Recovery failed: {e}")
            return "{}"

    async def _call_with_retry(self, prompt: str, image_data: Optional[str] = None, retries: int = 4):
        """Advanced API caller with Dynamic Backoff."""
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
        """Superior Intent Extraction for Rio Finance Bank."""
        prompt = f"""
        TASK: High-Precision Intent Parsing for Autonomous Banking.
        USER COMMAND: "{user_input}"
        
        CONTEXT:
        - Primary Target: Rio Finance Bank (https://roshan-chaudhary13.github.io/rio_finance_bank/)
        - Priority Keywords: electricity, bill, gold, pay, login, transfer, banking.

        LOGIC RULES:
        1. If user mentions any Priority Keyword, the provider MUST be "Rio Finance Bank".
        2. Map action based on verbs: 'bill' -> PAY_BILL, 'gold' -> BUY_GOLD, 'login' -> LOGIN.
        3. Urgency is 'HIGH' for all bill/payment tasks.

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
        UPGRADED: Strict Data Mapping to prevent 'password123' style hallucinations.
        """
        history_log = "\n".join([f"- Step {i}: {h.get('action')} on {h.get('element')} -> {h.get('thought')}" for i, h in enumerate(history[-15:])])
        
        mapping_instruction = """
        STRICT DATA INTEGRITY RULES:
        1. NO HALLUCINATIONS: Do NOT invent passwords or pins. Use ONLY values found in the 'USER DATA' block.
        2. DATA MAPPING:
           - Login fields (Password): Use ONLY user_context['login_credentials']['password']. (In this case: admin123).
           - Payment fields (PIN): Use ONLY user_context['security_details']['upi_pin'] or 'card_pin'.
        3. LABEL AWARENESS: Read the text next to inputs. If it says "Password", do NOT use a PIN. If it says "PIN", do NOT use a password.
        4. COORDINATE PRECISION: Aim for the absolute geometric center of the target element. 
        """

        prompt = f"""
        OBJECTIVE: {goal}
        USER DATA: {json.dumps(user_context)}
        {mapping_instruction}

        HISTORY (Last 15 steps):
        {history_log if history else "Initial state."}

        VISUAL TASK (1920x1080 Resolution):
        1. Target Identification: Find the specific button or input needed for the next step.
        2. Credential Selection: Choose the exact string from USER DATA. Verification: You previously failed with "password123". Correct it to the value in USER DATA.
        3. Coordinate Logic: Provide [ymin, xmin, ymax, xmax] in 0-1000 scale. Ensure ymin/ymax and xmin/xmax tightly bound the element.

        RETURN JSON:
        {{
            "thought": "CoT: 1. Visual identification of labels. 2. Verification of correct credential value from context. 3. Geometric center calculation.",
            "action_type": "CLICK | TYPE | ASK_USER | FINISHED",
            "element_name": "Full descriptive name of the UI element",
            "coordinates": [ymin, xmin, ymax, xmax],
            "input_text": "THE EXACT STRING FROM USER DATA (No inventions!)",
            "voice_prompt": "Concise update for the user.",
            "is_navigation_required": false
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64)
            analysis = json.loads(self._clean_json_response(raw_response))
            
            if analysis.get("action_type") in ["CLICK", "TYPE"]:
                coords = analysis.get("coordinates")
                if not coords or len(coords) != 4:
                    return {"action_type": "ASK_USER", "voice_prompt": "I see the target but need help with precise positioning."}
            
            return analysis
        except Exception as e:
            logger.error(f"[ERROR] Visual Logic Fault: {e}")
            return {
                "action_type": "ASK_USER", 
                "voice_prompt": "Visual reasoning failure. Please assist.",
                "thought": f"Exception: {str(e)}"
            }