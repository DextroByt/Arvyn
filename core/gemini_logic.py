import os
import json
import logging
import asyncio
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from typing import Optional, Dict, Any

from config import GEMINI_API_KEY, logger
from core.state_schema import IntentOutput, VisualGrounding

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

class GeminiBrain:
    """
    The cognitive interface for Agent Arvyn.
    Updated to support Gemini 2.5 models.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.95,
                "max_output_tokens": 2048, # Increased for 2.5 capabilities
                "response_mime_type": "application/json"
            }
        )
        logger.info(f"GeminiBrain initialized with model: {self.model_name}")

    async def _call_with_retry(self, prompt: str, image_data: Optional[str] = None, retries: int = 1):
        """Executes API calls. Identifies quota limits for the fallback logic."""
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

    def _local_parse_fallback(self, user_input: str) -> Optional[IntentOutput]:
        """Simple keyword matching to bypass API when quota is hit."""
        lower_input = user_input.lower()
        if "open" in lower_input or "navigate to" in lower_input:
            words = lower_input.split()
            try:
                trigger = "open" if "open" in words else "to"
                idx = words.index(trigger)
                provider = words[idx + 1].upper()
                return IntentOutput(action="NAVIGATE", target="BROWSER", provider=provider)
            except (ValueError, IndexError):
                pass
        return None

    async def parse_intent(self, user_input: str) -> IntentOutput:
        """Translates natural language into action. Uses local fallback on API failure."""
        try:
            prompt = f"""
            TASK: Identify intent from user command: "{user_input}"
            
            RETURN JSON ONLY:
            {{
                "action": "NAVIGATE | SEARCH | CLICK | QUERY",
                "target": "BROWSER | APP",
                "provider": "string (the website name or entity)",
                "amount": float or null,
                "urgency": "HIGH | MEDIUM | LOW"
            }}
            """
            raw_response = await self._call_with_retry(prompt)
            clean_json = raw_response.strip().replace("```json", "").replace("```", "")
            data = json.loads(clean_json)
            
            if "amount" not in data:
                data["amount"] = None
                
            return IntentOutput(**data)

        except Exception as e:
            fallback = self._local_parse_fallback(user_input)
            if fallback:
                logger.info("Gemini Busy: Using local command fallback.")
                return fallback
            
            logger.error(f"Intent Error: {e}")
            if "QUOTA_EXCEEDED" in str(e):
                raise Exception("System Overloaded: I cannot process this request right now.")
            raise Exception("I encountered an error and cannot process this command.")

    async def analyze_visual_element(self, screenshot_b64: str, target_desc: str) -> Optional[VisualGrounding]:
        """Generic visual analysis for element coordinates."""
        prompt = f"Locate '{target_desc}' in the image. Return JSON: {{'element_name': str, 'coordinates': [ymin, xmin, ymax, xmax], 'confidence': float}}"
        try:
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64)
            data = json.loads(raw_response.strip().replace("```json", "").replace("```", ""))
            return VisualGrounding(**data)
        except:
            return None