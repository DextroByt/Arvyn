from typing import Annotated, TypedDict, List, Dict, Optional, Any
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    """
    The internal state of Agent Arvyn.
    Optimized for multi-turn direct execution and session persistence.
    Updated for banking tasks and voice interaction loops with error-protection.
    """
    # Conversation history: Appends new messages automatically for context
    messages: Annotated[List[Any], add_messages]
    
    # Intent: Optional to prevent 'KeyError' during initialization or failed parsing
    intent: Optional[Dict[str, Any]]
    
    # Session Context: Optional data from local storage or previous steps
    user_data: Optional[Dict[str, Any]]

    # --- NEW FOR BANKING AUTOMATION ---
    # Temporary Memory: Tracks the sequence of actions taken
    task_history: List[Dict[str, Any]]
    
    # Interaction State: If Arvyn asks a question, this tracks it
    pending_question: Optional[str]
    # ----------------------------------
    
    # Internal Tracking: Used for browser state and step validation
    missing_fields: List[str]
    browser_context: Dict[str, Any]
    screenshot: Optional[str]
    
    # HITL Data: Details requiring human confirmation (PINs, Payment Approval)
    transaction_details: Dict[str, Any]
    human_approval: Optional[str]
    
    # UI/Log Status
    current_step: str

class IntentOutput(BaseModel):
    """Structured output for Gemini intent parsing with advanced discovery support."""
    # Using Optional[str] prevents pydantic.ValidationError if Gemini returns null
    action: Optional[str] = Field(
        default="QUERY", 
        description="Action: PAY_BILL, BUY_GOLD, UPDATE_PROFILE, LOGIN, NAVIGATE, SEARCH, QUERY"
    )
    target: Optional[str] = Field(
        default="BANKING", 
        description="Category: BANKING, UTILITY, BROWSER, etc."
    )
    provider: Optional[str] = Field(
        default="UNKNOWN", 
        description="Normalized entity name or specific site"
    )
    
    # Added to support the Intelligent Search Agent's discovery loop
    search_query: Optional[str] = Field(default=None, description="Optimized query for search engines")
    
    amount: Optional[float] = Field(default=None, description="Monetary value if present")
    
    # Made optional to prevent validation crashes if Gemini returns null
    urgency: Optional[str] = Field(default="LOW", description="Priority level: HIGH | MEDIUM | LOW")

class VisualGrounding(BaseModel):
    """
    Structured output for VLM coordinate mapping.
    Updated to be robust against missing VLM detections.
    """
    element_name: str = Field(default="Target Element")
    
    # Made Optional to prevent 'input should be a valid list' errors when VLM fails
    coordinates: Optional[List[float]] = Field(default=None, description="Normalized [ymin, xmin, ymax, xmax]")
    
    confidence: float = Field(default=0.0)