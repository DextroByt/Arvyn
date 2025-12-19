import os
import json
import logging
import asyncio
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from typing import Optional, Dict, Any, List

from config import GEMINI_API_KEY, logger
from core.state_schema import IntentOutput, VisualGrounding

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

class GeminiBrain:
    """
    Advanced Reasoning Engine for Agent Arvyn (Production Grade).
    Updated for robust Visual Grounding and coordinate-based site selection.
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
        """Normalized Entity Extraction with fuzzy correction logic."""
        prompt = f"""
        TASK: Extract intent and normalize the target entity.
        USER COMMAND: "{user_input}"
        
        LOGIC:
        1. Correct misspellings (e.g., "jio finance" -> "Jio Financial Services").
        2. Format search queries specifically for finding "Official" sites.
        
        RETURN JSON:
        {{
            "action": "NAVIGATE | SEARCH | CLICK | QUERY",
            "target": "BROWSER | APP",
            "provider": "Normalized Entity Name",
            "search_query": "Optimized search query (e.g. 'Amazon official website')",
            "urgency": "LOW"
        }}
        """
        try:
            raw_response = await self._call_with_retry(prompt)
            data = json.loads(raw_response.strip().replace("```json", "").replace("```", ""))
            return IntentOutput(**data)
        except Exception as e:
            logger.error(f"Intent Error: {e}")
            raise Exception("I couldn't process that command intelligently.")

    async def locate_official_link_on_page(self, screenshot_b64: str, target_entity: str) -> Optional[VisualGrounding]:
        """
        VLM Task: Identify the official website link in the screenshot.
        Uses visual cues to distinguish official results from ads.
        """
        # IMPROVED PROMPT: Provides more context on what an "Official Link" looks like visually
        prompt = f"""
        Analyze this Google Search results page for '{target_entity}'.
        
        TASK: Find the bounding box for the TITLE of the FIRST organic (non-ad) official website result.
        
        VISUAL CLUES:
        - Organic results usually have a large blue/purple title.
        - Look for a URL that clearly belongs to {target_entity} (e.g., {target_entity.lower()}.com).
        - IGNORE results marked as 'Sponsored' or 'Ad'.
        - Provide coordinates for the clickable text area.
        
        RETURN JSON ONLY:
        {{
            "element_name": "Official Link for {target_entity}",
            "coordinates": [ymin, xmin, ymax, xmax],
            "confidence": float (0.0 to 1.0)
        }}
        
        Note: coordinates must be in [0-1000] scale.
        """
        try:
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64)
            # Clean JSON from potential markdown markers
            clean_json = raw_response.strip().replace("```json", "").replace("```", "")
            data = json.loads(clean_json)
            
            # Robustness check: Ensure coordinates are a valid list before creating the object
            if not data.get("coordinates") or not isinstance(data["coordinates"], list):
                logger.warning("VLM returned empty or invalid coordinates.")
                return None
                
            return VisualGrounding(**data)
        except Exception as e:
            logger.error(f"Visual Grounding Logic Error: {e}")
            return None