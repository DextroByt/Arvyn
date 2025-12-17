# arvyn-server/core/vision_healer.py
import os
import io
from pydantic import BaseModel, Field, ValidationError
from PIL import Image
from playwright.sync_api import Page
from google import genai
from google.genai import types

# --- Pydantic Schema for VLM Output (Coordinate Validation) ---
class ClickCoordinates(BaseModel):
    """
    Structured schema to enforce VLM output to be a valid pair of X, Y coordinates.
    """
    x: int = Field(description="The X-coordinate of the center point of the target element, relative to the viewport.")
    y: int = Field(description="The Y-coordinate of the center point of the target element, relative to the viewport.")

def visual_self_heal(page: Page, target_description: str) -> tuple[int, int]:
    """
    Captures a screenshot, sends it to the VLM with context (Enhanced Prompt Grounding), 
    and returns precise X, Y coordinates for a visual click.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in environment variables.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # 1. Capture Screenshot
    # Use buffered I/O (BytesIO) to handle the image in memory without writing to disk
    screenshot_bytes = page.screenshot()
    image = Image.open(io.BytesIO(screenshot_bytes))

    # 2. Enhanced Prompt Grounding (Mitigation 3.1.B)
    # The prompt includes detailed context from the agent's state to improve VLM accuracy
    prompt = f"""
    Analyze the provided screenshot of the banking interface. The agent encountered an error trying to locate an element.
    Your task is to perform Visual Grounding. Based on the current page and the failure context: '{target_description}', 
    identify the precise location of the intended interactive element (e.g., a button to submit or continue the transaction).
    Return the X, Y coordinates of the center point of the element as a JSON object, strictly conforming to the schema.
    """
    
    try:
        # Multimodal call to Gemini 2.5 Flash with both text and image input
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
        
        # Return the deterministic X, Y pair
        return coords.x, coords.y
        
    except ValidationError as e:
        # Failure path if the VLM output is not a valid coordinate pair
        raise ValueError(f"VLM visual output failed Coordinate Pydantic validation: {e.errors()}") from e
    except Exception as e:
        # Handle API or connection errors
        raise RuntimeError(f"VLM API or connection error during visual healing: {e}") from e