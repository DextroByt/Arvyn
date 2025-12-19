from typing import Annotated, TypedDict, List, Dict, Optional, Any
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    """
    The internal state of Agent Arvyn.
    Optimized for multi-turn direct execution and session persistence.
    """
    # Conversation history: Appends new messages automatically for context
    messages: Annotated[List[Any], add_messages]
    
    # Intent: The direct action, target, and provider extracted from the command
    intent: Dict[str, Any]
    
    # Session Context: Optional data from local storage or previous steps
    user_data: Optional[Dict[str, Any]]
    
    # Internal Tracking: Used for browser state and step validation
    missing_fields: List[str]
    browser_context: Dict[str, Any]
    screenshot: Optional[str]
    
    # HITL Data: Details requiring human confirmation
    transaction_details: Dict[str, Any]
    human_approval: Optional[str]
    
    # UI/Log Status
    current_step: str

class IntentOutput(BaseModel):
    """Structured output for Gemini intent parsing with prototype-ready defaults."""
    action: str = Field(default="QUERY", description="Action: PAY, CHECK_BALANCE, NAVIGATE, etc.")
    target: str = Field(default="UNKNOWN", description="Category: BANKING, UTILITY, etc.")
    provider: str = Field(default="NONE", description="Specific entity name")
    amount: Optional[float] = Field(default=None, description="Monetary value if present")
    urgency: str = Field(default="LOW", description="Priority level")

class VisualGrounding(BaseModel):
    """Structured output for VLM coordinate mapping."""
    element_name: str
    coordinates: List[float] = Field(description="Normalized [ymin, xmin, ymax, xmax]")
    confidence: float