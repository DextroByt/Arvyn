from typing import Annotated, TypedDict, List, Dict, Optional, Any, Union
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    """
    The internal state of Agent Arvyn (Production Grade).
    Optimized for multi-turn autonomous execution and recursive reasoning.
    """
    # --- CONVERSATION & CONTEXT ---
    messages: Annotated[List[Any], add_messages]
    
    # Intent: Parsed objective with CoT reasoning
    intent: Optional[Dict[str, Any]]
    
    # User Context: Secure storage for PII (Personal Identifiable Information)
    user_data: Optional[Dict[str, Any]]

    # --- PERSISTENT TASK MEMORY ---
    # High-fidelity history of every click, type, and thought
    task_history: List[Dict[str, Any]]
    
    # The current 'mental' status shown on the Dashboard
    current_step: str
    
    # --- BANKING & KINETIC STATE ---
    # Tracks the visual state of the browser and grounding coordinates
    browser_context: Dict[str, Any]
    screenshot: Optional[str] # Base64 viewport capture
    
    # Interaction Flow: Tracks questions asked to the user
    pending_question: Optional[str]
    
    # --- HITL & SECURITY (Human-In-The-Loop) ---
    # Details of a pending transaction requiring manual confirmation
    transaction_details: Dict[str, Any]
    
    # Stores the user's decision: "approved" | "rejected" | None
    human_approval: Optional[str]
    
    # Internal error counter to prevent infinite loops on specific nodes
    error_count: int

class IntentOutput(BaseModel):
    """
    Structured reasoning for Arvyn's Intent Parser.
    Forces domain-specific logic for banking tasks.
    """
    action: str = Field(
        default="QUERY", 
        description="Core action: PAY_BILL | BUY_GOLD | UPDATE_PROFILE | LOGIN | NAVIGATE | SEARCH | QUERY"
    )
    target: str = Field(
        default="BANKING", 
        description="Domain category: BANKING | UTILITY | SHOPPING | BROWSER"
    )
    provider: str = Field(
        default="Rio Finance Bank", 
        description="The specific site or entity being targeted."
    )
    
    # Chain-of-Thought (CoT) Reasoning
    reasoning: Optional[str] = Field(
        default=None, 
        description="The logic behind why this specific action/provider was chosen."
    )
    
    # Metadata for financial/search tasks
    amount: Optional[float] = Field(default=None, description="Monetary value for transactions")
    search_query: Optional[str] = Field(default=None, description="Optimized string for discovery")
    
    urgency: str = Field(
        default="LOW", 
        description="Priority level for task execution: HIGH | MEDIUM | LOW"
    )

class VisualGrounding(BaseModel):
    """
    Structured output for VLM (Vision Language Model) coordinate mapping.
    Maps pixel-space elements to normalized coordinates for kinetic execution.
    """
    thought: str = Field(description="Visual analysis of the current element and its role.")
    
    element_name: str = Field(default="Target UI Element")
    
    # Coordinates in 0-1000 normalized space: [ymin, xmin, ymax, xmax]
    coordinates: Optional[List[float]] = Field(
        default=None, 
        description="Normalized bounding box for the target element."
    )
    
    action_type: str = Field(
        default="CLICK", 
        description="The physical action to perform: CLICK | TYPE | SCROLL | HOVER"
    )
    
    input_text: Optional[str] = Field(
        default=None, 
        description="Text to be entered if the action_type is TYPE."
    )
    
    confidence: float = Field(
        default=0.0, 
        ge=0.0, le=1.0, 
        description="Model confidence in visual detection."
    )

class TransactionSummary(BaseModel):
    """
    Final output for banking task verification.
    """
    status: str = Field(description="SUCCESS | FAILED | PENDING")
    transaction_id: Optional[str] = Field(default=None)
    summary: str = Field(description="Narrative summary of the completed task.")