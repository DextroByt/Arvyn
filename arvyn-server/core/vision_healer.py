# arvyn-server/core/vision_healer.py

import os
import io
import time
import asyncio
from pydantic import BaseModel, Field, ValidationError
from PIL import Image
# CHANGE: Use Async API
from playwright.async_api import Page
from google import genai
from google.genai import types

# --- Pydantic Schema for VLM Output ---

class ClickCoordinates(BaseModel):
    x: int = Field(description="The X-coordinate of the center point of the target element, relative to the viewport.")
    y: int = Field(description="The Y-coordinate of the center point of the target element, relative to the viewport.")

# CHANGE: Added async keyword
async def visual_self_heal(page: Page, target_description: str) -> tuple[int, int]:
    """
    Captures a screenshot, sends it to the VLM with context, and returns precise X, Y coordinates.
    Includes RETRY logic for 503 Overloaded errors.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=GEMINI_API_KEY)

    # 1. Capture Screenshot (Async)
    # CHANGE: Added await
    screenshot_bytes = await page.screenshot()
    image = Image.open(io.BytesIO(screenshot_bytes))

    # 2. Enhanced Prompt Grounding
    prompt = f"""
    Analyze the provided screenshot of the banking interface. The agent encountered an error trying to locate an element.
    Based on the current page and the context: '{target_description}', identify the precise location of the intended interactive element.
    
    If the user wants to 'Buy Gold', find the 'Amount' or 'Quantity' input field.
    If the user wants to 'Transfer', find the 'Recipient' or 'Amount' field.
    
    Return the X, Y coordinates of the center point of the element as a JSON object, strictly conforming to the schema.
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    # Helper for blocking call
    def _call_gemini():
        return client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClickCoordinates,
            ),
        )

    for attempt in range(MAX_RETRIES):
        try:
            print(f"👁️ VLM Analysis Attempt {attempt + 1}/{MAX_RETRIES}...")
            
            # 3. Offload blocking VLM call
            response = await asyncio.to_thread(_call_gemini)
            
            # 4. Validate and Extract Coordinates
            coords = ClickCoordinates.model_validate_json(response.text)
            return coords.x, coords.y

        except ValidationError as e:
            raise ValueError(f"VLM visual output failed Coordinate Pydantic validation: {e.errors()}")
            
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "overloaded" in error_msg.lower() or "UNAVAILABLE" in error_msg:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    print(f"⚠️ Model Overloaded (503). Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time) # Async sleep
                    continue
            
            raise RuntimeError(f"VLM API failed: {e}")