# arvyn-server/core/intent_parser.py

import os
import json
from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types

# --- Pydantic Schema: The Symbolic Firewall ---

class FinancialIntent(BaseModel):
    """Structured schema for financial command extraction."""
    action: str = Field(description="The primary financial action: 'transfer', 'pay_bill', or 'check_balance'.")
    amount: float = Field(description="The monetary value involved in the action. Must be a positive floating point number.")
    recipient: str = Field(description="The name or identifier of the recipient, e.g., 'Jane Doe' or 'Credit Card'.")
    critical: bool = Field(description="True if the action modifies funds (transfer/pay_bill). False for read-only (check_balance).")

def parse_financial_intent(user_input: str) -> dict:
    """
    Invokes Gemini 2.5 Flash with Pydantic schema enforcement to extract intent.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Tailored prompt engineering for high fidelity extraction 
    prompt = f"""
    You are a high-fidelity semantic parsing engine for a financial agent. 
    Analyze the following user input and strictly extract the structured financial intent according to the provided JSON schema. 
    User Input: "{user_input}"
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FinancialIntent,
            ),
        )
        
        parsed_data = FinancialIntent.model_validate_json(response.text)
        return parsed_data.model_dump()

    except ValidationError as e:
        # Structured failure path for VLM misinterpretation
        raise ValueError(f"VLM output failed Pydantic validation: {e.errors()}")
    except Exception as e:
        raise RuntimeError(f"VLM API or connection error during parsing: {e}")


