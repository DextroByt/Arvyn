# arvyn-server/core/intent_parser.py

import os
import json
from typing import Optional
from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types

# --- Pydantic Schema: Updated for Login Support ---

class FinancialIntent(BaseModel):
    """Structured schema for financial command extraction."""
    
    action: str = Field(description="The primary action: 'transfer', 'pay_bill', 'check_balance', or 'login'.")
    
    # Made Optional for Login commands
    amount: Optional[float] = Field(default=None, description="The monetary value. Required for transfers/bills.")
    recipient: Optional[str] = Field(default=None, description="The recipient. Required for transfers.")
    
    # New Fields for Authentication
    username: Optional[str] = Field(default=None, description="Username or email for login actions.")
    password: Optional[str] = Field(default=None, description="Password for login actions.")
    
    critical: bool = Field(description="True if the action modifies funds or access (transfer/login). False for read-only.")

def parse_financial_intent(user_input: str) -> dict:
    """
    Invokes Gemini 2.5 Flash with Pydantic schema enforcement to extract intent.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are a high-fidelity semantic parsing engine for a financial agent. 
    Analyze the following user input and strictly extract the structured financial intent according to the provided JSON schema. 
    
    If the user wants to log in, map it to 'login' and extract credentials.
    
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
        raise ValueError(f"VLM output failed Pydantic validation: {e.errors()}")
    except Exception as e:
        raise RuntimeError(f"VLM API or connection error during parsing: {e}")