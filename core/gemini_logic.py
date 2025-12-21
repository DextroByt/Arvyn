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
    IMPROVED: Intelligent intent routing with proper provider detection.
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
        """Superior Intent Extraction with Intelligent Provider Routing."""
        prompt = f"""
        TASK: High-Precision Intent Parsing for Multi-Platform Automation.
        USER COMMAND: "{user_input}"
        
        CONTEXT:
        - Primary Banking Target: Rio Finance Bank (https://roshan-chaudhary13.github.io/rio_finance_bank/)
        - Available Platforms: Flipkart, Amazon, Netflix, GitHub, Jio Financial Services, BSNL
        - Banking Keywords: electricity, bill, gold, pay, transfer, login (when context is BANKING)
        - Shopping Keywords: flipkart, amazon, product, buy (when context is SHOPPING)
        - Entertainment Keywords: netflix, watch, movie (when context is ENTERTAINMENT)

        CRITICAL LOGIC RULES:
        1. IDENTIFY THE DOMAIN FIRST:
           - If user says "open [site]", "go to [site]", "search [site]" -> NAVIGATION mode (use that specific site)
           - If user mentions bills, payments, gold, transfer -> BANKING mode (Rio Finance Bank ONLY)
           - If user mentions shopping, products without a specific site -> SHOPPING mode (use appropriate site)
           - If user mentions entertainment -> ENTERTAINMENT mode
        
        2. PROVIDER SELECTION (CRITICAL):
           - "open flipkart" / "go to flipkart" / "visit flipkart" -> provider = "Flipkart", action = NAVIGATE, target = SHOPPING
           - "open amazon" -> provider = "Amazon", action = NAVIGATE, target = SHOPPING
           - "open netflix" -> provider = "Netflix", action = NAVIGATE, target = ENTERTAINMENT
           - "open github" -> provider = "GitHub", action = NAVIGATE, target = BROWSER
           - "pay electricity bill" / "pay my bill" -> provider = "Rio Finance Bank", action = PAY_BILL, target = BANKING
           - "buy gold" / "purchase gold" -> provider = "Rio Finance Bank", action = BUY_GOLD, target = BANKING
           - "login to rio" / "login to bank" -> provider = "Rio Finance Bank", action = LOGIN, target = BANKING
           - "transfer money" -> provider = "Rio Finance Bank", action = TRANSFER (or PAY_BILL), target = BANKING
           - Any OTHER site-specific request -> use THAT site, NOT Rio
           - General query without specific site -> SEARCH
        
        3. ACTION MAPPING:
           - Navigation requests (open, go to, visit): NAVIGATE
           - Payment/Bill requests: PAY_BILL (provider = Rio Finance Bank)
           - Gold purchase: BUY_GOLD (provider = Rio Finance Bank)
           - Money transfer: TRANSFER or PAY_BILL (provider = Rio Finance Bank)
           - Login: LOGIN
           - Profile updates: UPDATE_PROFILE
           - General queries: SEARCH or QUERY

        4. URGENCY MAPPING:
           - Bill payments, transfers, urgent actions: HIGH
           - Navigation requests: LOW
           - General queries: LOW or MEDIUM

        RETURN JSON:
        {{
            "action": "PAY_BILL | BUY_GOLD | TRANSFER | UPDATE_PROFILE | LOGIN | NAVIGATE | SEARCH | QUERY",
            "target": "BANKING | SHOPPING | ENTERTAINMENT | BROWSER",
            "provider": "Rio Finance Bank | Flipkart | Amazon | Netflix | GitHub | Jio Financial Services | BSNL",
            "amount": float or null,
            "search_query": "Optimized query string or site name",
            "urgency": "HIGH | MEDIUM | LOW",
            "reasoning": "Explain why this provider and action were chosen based on user intent."
        }}
        
        EXAMPLES:
        - Input: "open flipkart"
          Output: {{"action": "NAVIGATE", "provider": "Flipkart", "target": "SHOPPING", "search_query": "flipkart", "urgency": "LOW", "reasoning": "User explicitly requested to navigate to Flipkart shopping site."}}
        
        - Input: "pay my electricity bill"
          Output: {{"action": "PAY_BILL", "provider": "Rio Finance Bank", "target": "BANKING", "amount": null, "urgency": "HIGH", "reasoning": "Electricity bill payment requires banking transaction on Rio Finance Bank."}}
        
        - Input: "buy gold from rio"
          Output: {{"action": "BUY_GOLD", "provider": "Rio Finance Bank", "target": "BANKING", "urgency": "HIGH", "reasoning": "Gold purchase requested from Rio Finance Bank banking platform."}}
        
        - Input: "search amazon for shoes"
          Output: {{"action": "SEARCH", "provider": "Amazon", "target": "SHOPPING", "search_query": "shoes", "urgency": "LOW", "reasoning": "User wants to search for shoes on Amazon shopping platform."}}
        
        - Input: "transfer 5000 rupees"
          Output: {{"action": "TRANSFER", "provider": "Rio Finance Bank", "target": "BANKING", "amount": 5000, "urgency": "HIGH", "reasoning": "Money transfer is a banking operation on Rio Finance Bank."}}
        
        - Input: "open netflix"
          Output: {{"action": "NAVIGATE", "provider": "Netflix", "target": "ENTERTAINMENT", "search_query": "netflix", "urgency": "LOW", "reasoning": "User explicitly requested Netflix entertainment platform."}}
        """
        try:
            raw_response = await self._call_with_retry(prompt)
            data = json.loads(self._clean_json_response(raw_response))
            
            # Validation: Ensure provider makes sense for the action
            action = data.get("action", "QUERY")
            provider = data.get("provider", "Rio Finance Bank")
            
            # Banking actions MUST use Rio Finance Bank
            if action in ["PAY_BILL", "BUY_GOLD", "TRANSFER"]:
                if provider != "Rio Finance Bank":
                    logger.warning(f"[VALIDATION] Banking action '{action}' detected with provider '{provider}'. Forcing Rio Finance Bank.")
                    data["provider"] = "Rio Finance Bank"
                    data["target"] = "BANKING"
            
            return IntentOutput(**data)
        except Exception as e:
            logger.error(f"[ERROR] Intent Parser Fault: {e}")
            # Fallback: default to safe NAVIGATE mode for unknown inputs
            return IntentOutput(
                action="NAVIGATE", 
                provider="Flipkart",
                target="BROWSER", 
                urgency="LOW",
                reasoning="Error recovery - defaulting to navigation mode."
            )

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
        PRESERVED: All credential handling, coordinate centering, and safety features.
        """
        history_log = "\n".join([f"- Step {i}: {h.get('action')} on {h.get('element')} -> {h.get('thought')}" for i, h in enumerate(history[-15:])])
        
        mapping_instruction = """
        STRICT DATA INTEGRITY RULES:
        1. NO HALLUCINATIONS: Do NOT invent passwords or pins. Use ONLY values found in the 'USER DATA' block.
        2. DATA MAPPING:
           - Login fields (Email): Use ONLY user_context['login_credentials']['email'].
           - Login fields (Password): Use ONLY user_context['login_credentials']['password']. (In this case: admin123).
           - Payment fields (PIN): Use ONLY user_context['security_details']['upi_pin'] or 'card_pin'.
           - Account/ID fields: Use ONLY user_context['login_credentials']['consumer_id'] or similar official IDs.
        3. LABEL AWARENESS: Read the text next to inputs. If it says "Password", do NOT use a PIN. If it says "PIN", do NOT use a password.
        4. COORDINATE PRECISION: Aim for the absolute geometric center of the target element. 
        5. VALIDATION: Before returning input_text, verify it exists in USER DATA. Never use placeholder values like 'password123', 'pin123', '0000'.
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
        4. Safety Check: If you don't have the exact data, ask the user instead of guessing.

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
            
            # Safety validation: Check for hallucinated credentials
            input_text = analysis.get("input_text", "").lower()
            if any(hal in input_text for hal in ["password123", "pin123", "0000", "1234", "test123"]):
                logger.error(f"[SECURITY] Brain attempted hallucinated credential: {input_text}. Asking user instead.")
                return {
                    "action_type": "ASK_USER", 
                    "voice_prompt": "I need sensitive data to proceed. Please provide it via the authorization button.",
                    "thought": "Credential validation failed - requesting user confirmation."
                }
            
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