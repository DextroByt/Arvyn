# arvyn-server/core/intent_parser.py
import os
import json
from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types

# --- Pydantic Schema: The Symbolic Firewall ---
class FinancialIntent(BaseModel):
    """
    Structured schema for financial command extraction. 
    Enforces deterministic output for the VLM (Structured Output Mandate).
    """
    action: str = Field(
        description="The primary financial action: 'transfer', 'pay_bill', or 'check_balance'."
    )
    amount: float = Field(
        description="The monetary value involved in the action. Must be a positive floating point number."
    )
    recipient: str = Field(
        description="The name or identifier of the recipient, e.g., 'Jane Doe' or 'Credit Card'."
    )
    critical: bool = Field(
        description="True if the action modifies funds (transfer/pay_bill). False for read-only (check_balance). This flag triggers the Conscious Pause Protocol."
    )

def parse_financial_intent(user_input: str) -> dict:
    """
    Invokes Gemini 2.5 Flash with Pydantic schema enforcement to extract 
    and validate the structured financial intent from the raw user input.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in environment variables.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Tailored prompt engineering for high fidelity extraction [cite: 191]
    prompt = f"""
    You are a high-fidelity semantic parsing engine for a financial agent.
    Analyze the following user input and strictly extract the structured financial intent according to the provided JSON schema.
    Ensure the 'critical' field is set to True if the action modifies or moves money, and False otherwise.

    User Input: "{user_input}"
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                # Mandates JSON output conforming to the schema
                response_mime_type="application/json",
                response_schema=FinancialIntent,
            ),
        )
        
        # 3. Validate and Extract Data
        # Pydantic validation guarantees the integrity of the returned structure
        parsed_data = FinancialIntent.model_validate_json(response.text)
        
        # Convert the Pydantic model to a standard dictionary for LangGraph state persistence
        return parsed_data.model_dump()
        
    except ValidationError as e:
        # Structured failure path for VLM misinterpretation or incorrect output format [cite: 194]
        raise ValueError(f"VLM output failed Pydantic validation. The structured output was incorrect. Errors: {e.errors()}") from e
    except Exception as e:
        # Handle API or connection errors [cite: 195]
        raise RuntimeError(f"VLM API or connection error during intent parsing: {e}") from e