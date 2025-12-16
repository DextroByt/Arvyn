# arvyn-server/core/vision_healer.py

import os
import io
from pydantic import BaseModel, Field
from PIL import Image
from playwright.sync_api import Page
from google import genai
from google.genai import types

# --- Pydantic Schema for VLM Output (Coordinate Validation) ---

class ClickCoordinates(BaseModel):
    x: int = Field(description="The X-coordinate of the center point of the target element, relative to the viewport.")
    y: int = Field(description="The Y-coordinate of the center point of the target element, relative to the viewport.")

def visual_self_heal(page: Page, target_description: str) -> tuple[int, int]:
    """
    Captures a screenshot, sends it to the VLM with context, and returns precise X, Y coordinates.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=GEMINI_API_KEY)

    # 1. Capture Screenshot
    # Use buffered I/O to handle the image in memory
    screenshot_bytes = page.screenshot()
    image = Image.open(io.BytesIO(screenshot_bytes))

    # 2. Enhanced Prompt Grounding
    prompt = f"""
    Analyze the provided screenshot of the banking interface. The agent encountered an error trying to locate an element.
    Based on the current page and the context: '{target_description}', identify the precise location of the intended interactive element (e.g., a button to submit or continue).
    Return the X, Y coordinates of the center point of the element as a JSON object, strictly conforming to the schema.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClickCoordinates,
            ),
        )
        
        # 3. Validate and Extract Coordinates
        coords = ClickCoordinates.model_validate_json(response.text)
        return coords.x, coords.y

    except ValidationError as e:
        raise ValueError(f"VLM visual output failed Coordinate Pydantic validation: {e.errors()}")
    except Exception as e:
        raise RuntimeError(f"VLM API or connection error during visual healing: {e}")


