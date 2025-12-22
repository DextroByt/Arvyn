from typing import Annotated, TypedDict, List, Dict, Optional, Any, Union
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    """
    The internal state of Agent Arvyn (v5.0 - Semantic Sync).
    UPGRADED: Optimized for VLM-Guided Kinetic execution with Hidden DOM Sync.
    FEATURES: Recursive task history, multi-modal context, and secure credential handling.
    """
    # --- CONVERSATION & CONTEXT ---
    messages: Annotated[List[Any], add_messages]
    
    # Intent: Parsed objective with high-fidelity CoT reasoning
    intent: Optional[Dict[str, Any]]
    
    # User Context: Secure metadata pulled from user_profile.json
    user_data: Optional[Dict[str, Any]]

    # --- PERSISTENT TASK MEMORY ---
    # High-fidelity history of every action taken in the current session
    task_history: List[Dict[str, Any]]
    
    # Real-time status update for the Command Center Dashboard
    current_step: str
    
    # --- KINETIC & VISUAL STATE ---
    # Analysis from the VLM regarding the current viewport state
    browser_context: Dict[str, Any]
    screenshot: Optional[str] # Base64 capture for visual reasoning
    
    # Tracks questions for the user (Minimized in Full Autonomy mode)
    pending_question: Optional[str]
    
    # --- AUTONOMY & SECURITY ---
    # Details for transactions; used for logging even in autonomous mode
    transaction_details: Dict[str, Any]
    
    # Decision state: Forced to "approved" in Zero-Auth mode unless a failure occurs
    human_approval: Optional[str]
    
    # Prevents infinite recursion on complex UI roadblocks
    error_count: int

    # Concise Pause Metadata
    is_security_pause: Optional[bool]

class IntentOutput(BaseModel):
    """
    Structured reasoning for Arvyn's Intent Parser (v5.0).
    FIXED: Neutral defaults to prevent bias toward Rio Finance Bank.
    IMPROVED: Universal action mapping for E-Commerce, Utilities, and Banking.
    """
    action: str = Field(
        default="QUERY", 
        description="Core action: PAY_BILL | BUY_GOLD | PURCHASE | LOGIN | NAVIGATE | SEARCH | QUERY"
    )
    target: str = Field(
        default="GENERAL", 
        description="Domain category: E-COMMERCE | BANKING | UTILITY | ENTERTAINMENT | GENERAL"
    )
    provider: str = Field(
        default="Search", 
        description="The specific target entity (e.g., Flipkart, Amazon, Rio Finance Bank)."
    )
    
    # Chain-of-Thought (CoT) Reasoning
    reasoning: Optional[str] = Field(
        default=None, 
        description="Logical justification for the identified action and provider."
    )
    
    # Metadata for specialized tasks
    amount: Optional[float] = Field(default=None, description="Monetary value for purchases or bills")
    search_query: Optional[str] = Field(default=None, description="Query string for site-specific search bars")
    
    # Fields for profile update
    fields_to_update: Optional[Dict[str, str]] = Field(
        default=None, 
        description="Key-value pairs for profile updates (e.g., {'full_name': 'John', 'phone': '1234567890'})"
    )

    # Urgency level for execution prioritization
    urgency: Optional[str] = Field(
        default="MEDIUM", 
        description="Priority: HIGH | MEDIUM | LOW"
    )

class VisualGrounding(BaseModel):
    """
    Structured output for VLM coordinate mapping (v5.0 - Semantic Anchoring).
    UPGRADED: Features 'Semantic Anchor' support for Hidden DOM Correction.
    """
    # Requires the AI to explain its geometric choice before execution
    thought: str = Field(description="Visual analysis and geometric center calculation logic.")
    
    # CRITICAL: This text is used as the 'hook' for the browser's hidden DOM search
    element_name: str = Field(
        default="Target UI Element",
        description="EXACT visible text on the element (Semantic Anchor)."
    )
    
    # Coordinates in 0-1000 normalized space: [ymin, xmin, ymax, xmax]
    coordinates: Optional[List[float]] = Field(
        default=None, 
        description="VLM-estimated bounding box for the target element."
    )
    
    action_type: str = Field(
        default="CLICK", 
        description="Kinetic action: CLICK | TYPE | SCROLL | HOVER | FINISHED | ASK_USER"
    )
    
    input_text: Optional[str] = Field(
        default=None, 
        description="Target string for TYPE actions (e.g., credentials from user context)."
    )
    
    confidence: float = Field(
        default=0.0, 
        ge=0.0, le=1.0, 
        description="Visual grounding confidence threshold."
    )

class TransactionSummary(BaseModel):
    """
    Autonomous task verification and summary for v5.0 auditing.
    """
    status: str = Field(description="SUCCESS | FAILED | PENDING")
    transaction_id: Optional[str] = Field(default=None)
    summary: str = Field(description="Narrative verification of the completed task.")