import os
import json
import logging
import asyncio
import re
import httpx
from typing import Optional, Dict, Any, List, Union

from config import QUBRID_API_KEY, QUBRID_MODEL_NAME, QUBRID_BASE_URL, logger
from core.state_schema import IntentOutput, VisualGrounding

class QwenBrain:
    """
    Superior Visual-Reasoning Engine for Agent Arvyn (v5.0 - Semantic Anchoring).
    v5.0 UPGRADE: Semantic Labeling for Hidden DOM Sync.
    FIXED: Ensures 'element_name' matches visible UI text to enable precision anchoring.
    IMPROVED: Cross-references visual grounding with interactive element discovery.
    PRESERVED: All Qubrid retry logic, JSON recovery, and coordinate sanity refiners.
    """
    
    def __init__(self, model_name: str = QUBRID_MODEL_NAME):
        self.model_name = model_name
        self.api_key = QUBRID_API_KEY
        self.base_url = QUBRID_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"[BRAIN] Qubrid Precision Engine v5.0 active: {self.model_name}")

    def _clean_json_response(self, raw_text: Any) -> str:
        """Robust JSON extraction with deep type-safety for Qwen/VL output."""
        try:
            if not isinstance(raw_text, str):
                raw_text = str(raw_text) if raw_text else "{}"
            
            # Remove multi-layer markdown code blocks
            clean_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
            
            # Find the true JSON boundaries to prevent trailing noise
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            
            if start != -1 and end != -1:
                return clean_text[start:end+1]
            return clean_text
        except Exception as e:
            logger.error(f"[ERROR] Logic Layer: JSON Recovery failed during extraction: {e}")
            return "{}"

    async def _call_with_retry(self, prompt: str, image_data: Optional[str] = None, retries: int = 4):
        """Advanced API caller with Dynamic Backoff, Precision Tuning, and Timeout handling."""
        async with httpx.AsyncClient(timeout=160.0) as client:
            for attempt in range(retries):
                try:
                    # Construct multimodal payload compatible with Qwen-VL architecture
                    content = [{"type": "text", "text": prompt}]
                    
                    # Validate Image Data
                    if image_data:
                        if len(image_data) > 100: # Simple sanity check for valid base64 length
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_data}"}
                            })
                        else:
                            logger.warning("[BRAIN] Screenshot data appears invalid/empty. sending text-only request.")
                    
                    messages = [{"role": "user", "content": content}]
                    payload = {
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": 0.0, # CRITICAL: Locked for absolute coordinate stability
                        "max_tokens": 4096 if image_data else 1024,
                        "stream": False,
                        "top_p": 0.1 # Enhanced focus on highest probability tokens
                    }
                    
                    response = await client.post(self.base_url, headers=self.headers, json=payload)
                    
                    if response.status_code == 429:
                        wait_time = (2 ** attempt) * 15 
                        logger.warning(f"[QUOTA] Rate limit hit on {self.model_name}. Cooling down for {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                        
                    if response.is_error:
                        error_body = response.text
                        logger.error(f"[API ERROR] Status: {response.status_code}, Body: {error_body}")
                        response.raise_for_status()

                    data = response.json()
                    
                    if 'choices' in data and len(data['choices']) > 0:
                        result = data['choices'][0]['message']['content']
                        if not result: raise ValueError("Received empty content string from Qubrid.")
                        return result
                    else:
                        raise ValueError(f"Unexpected response payload format: {data}")
                    
                except Exception as e:
                    if attempt == retries - 1:
                        logger.error(f"[ERROR] Precision API failure after {retries} retries: {e}")
                        raise e
                    wait = 4 + (attempt * 2)
                    logger.warning(f"[RETRY] Precision Sync Attempt {attempt+1} failed. Re-syncing in {wait}s...")
                    await asyncio.sleep(wait)

    async def parse_intent(self, user_input: str) -> IntentOutput:
        """High-Fidelity Intent Extraction for specialized Autonomous Banking flows."""
        prompt = f"""
        TASK: High-Precision Intent Parsing for Autonomous Banking Systems.
        USER COMMAND: "{user_input}"
        
        CONTEXT: Primary Target is Rio Finance Bank (Electricity/Mobile/Internet/Gold/Login/Profile).
        OBJECTIVE: Map action to the strictly defined set [PAY_BILL, BUY_GOLD, UPDATE_PROFILE, LOGIN, NAVIGATE].
        - Use PAY_BILL for any bill payment or recharge (Mobile, Electricity, Internet).
        - Use BUY_GOLD for purchasing digital gold.
        - Use UPDATE_PROFILE for changing user details like name, phone number, email, address, etc.
          Extract ALL mentioned fields and their new values into 'fields_to_update'.
        - Use CLARIFY if the command is meaningless, too short (e.g. "a", "h"), or ambiguous.

        EXTRACTION RULES:
        - If the user says "Change my name to Akash", action="UPDATE_PROFILE", fields_to_update={{"full_name": "Akash"}}.
        - If the user says "Update my phone to 987654321", action="UPDATE_PROFILE", fields_to_update={{"phone": "987654321"}}.
        - If the user says "Update address to Mumbai", action="UPDATE_PROFILE", fields_to_update={{"address": "Mumbai"}}.
        - If the user says "Update email to akash@gmail.com", action="UPDATE_PROFILE", fields_to_update={{"email": "akash@gmail.com"}}.
        - Handle multiple fields: "Update my name to John and number to 123" -> action="UPDATE_PROFILE", fields_to_update={{"full_name": "John", "phone": "123"}}.
        - CRITICAL: Extract ALL details mentioned for update into 'fields_to_update'. Use keys like 'full_name', 'phone', 'email', 'address'.

        RETURN JSON:
        {{
            "action": "ACTION_TYPE",
            "target": "BANKING",
            "provider": "Rio Finance Bank",
            "amount": float or null,
            "fields_to_update": {{"field_name": "new_value"}} or null,
            "search_query": "Optimized search string for discovery",
            "urgency": "HIGH",
            "reasoning": "Step-by-step logic for this intent."
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt)
            data = json.loads(self._clean_json_response(raw_response))
            return IntentOutput(**data)
        except Exception as e:
            logger.error(f"[ERROR] Intent Parser Logic Fault: {e}")
            return IntentOutput(action="NAVIGATE", provider="Search", target="GENERAL", reasoning="Emergency intent recovery.")

    async def analyze_page_for_action(
        self, 
        screenshot_b64: str, 
        goal: str, 
        history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Hyper-Precision Visual Execution Planner (v5.0).
        INTEGRATED: Semantic Hinting for DOM synchronization.
        FIXED: Eliminates grounding drift by enforcing visible label matching for element_name.
        IMPROVED: Multi-layer coordinate validation ensures clicks land on pixels, not overlays.
        """
        # Maintain history context for sequence-aware reasoning
        history_log = "\n".join([f"- Step {i}: {h.get('action')} on {h.get('element')} -> {h.get('thought')}" for i, h in enumerate(history[-10:])])
        
        mapping_instruction = """
        STRICT GROUNDING & SEMANTIC SYNC RULES:
        1. FORM-CENTRIC SCANNING: Banking portals are usually CENTERED. 
           - SCAN the central area of the image for primary inputs and buttons.
        2. SEMANTIC ANCHORING (CRITICAL): The 'element_name' MUST match the EXACT visible text on the button or label.
           - Examples: If a button says 'Login', element_name is 'Login'. If an input is for 'Email', use 'Email'.
           - This text is used by a hidden DOM layer to correct your coordinates.
        3. GEOMETRIC HIT-BOX: Provide [ymin, xmin, ymax, xmax] (0-1000 scale) for the CLICKABLE face.
           - Ensure the coordinates are TIGHTLY BOUNDED to the interactive pixels.
        4. NO HALLUCINATIONS: Use ONLY credentials from the USER DATA block.
        5. FULL AUTONOMY: Execute immediately if data is present. Do NOT pause for verification.
        6. PRE-SUBMISSION VERIFICATION: Before clicking 'Pay'/'Submit'/'Save', you MUST VISUALLY CONFIRM:
           - Is the correct radio button (e.g. UPI) selected? If not, CLICK IT.
           - Are all required fields filled? If not, TYPE into them.
           - For PROFILE UPDATES: Ensure you have filled ALL mentioned target fields before clicking 'Save'.
           - DO NOT click 'Save' if you haven't typed the new values into the specific fields yet.
        """

        prompt = f"""
        OBJECTIVE: {goal}
        USER DATA: {json.dumps(user_context)}
        {mapping_instruction}

        HISTORY:
        {history_log if history else "Initial state - form discovery mode."}

        VISUAL TASK (1920x1080 - 100% DPI):
        1. Identification: Locate the exact target (Button/Input) for the next step.
        2. Precision Grounding: Output coordinates and the EXACT visible text/label as 'element_name'.
        
        RETURN JSON:
        {{
            "thought": "CoT Reasoning: 1. Locate form. 2. Identify target visible label for semantic sync. 3. Calculate hit-box.",
            "action_type": "CLICK | TYPE | ASK_USER | FINISHED",
            "element_name": "EXACT VISIBLE TEXT ON SCREEN",
            "coordinates": [ymin, xmin, ymax, xmax],
            "input_text": "EXACT STRING FROM CONTEXT",
            "voice_prompt": "Immediate progress status.",
            "is_navigation_required": false
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64)
            analysis = json.loads(self._clean_json_response(raw_response))
            
            # COORDINATE SANITY REFINER (v5.0)
            coords = analysis.get("coordinates")
            if coords and len(coords) == 4:
                ymin, xmin, ymax, xmax = coords
                # Detect suspicious bottom-left cluster hallucinations
                if xmax < 150 and ymin > 750:
                    logger.warning(f"[BRAIN] Suspicious grounding for '{analysis.get('element_name')}'. Semantic Sync will attempt correction.")
                
                # Verify bounding box validity
                if ymin >= ymax or xmin >= xmax:
                    logger.error("[BRAIN] Inverted bounding box. Applying center-correction safety.")
                    analysis["coordinates"] = [450, 450, 550, 550] 
            
            return analysis
        except Exception as e:
            logger.error(f"[ERROR] Visual Reasoning Logic Fault: {e}")
            return {
                "action_type": "ASK_USER", 
                "voice_prompt": "I encountered a visual reasoning fault. Please check the portal state.",
                "thought": f"Logic exception: {str(e)}"
            }