from typing import Annotated, TypedDict, List, Dict, Optional, Any
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

# ==========================================
# 1. ACTION SCHEMA
# ==========================================
class AgentAction(BaseModel):
    action_type: str = Field(..., description="NAVIGATE, CLICK, INPUT, WAIT, DONE")
    selector: Optional[str] = Field(None, description="CSS/Playwright selector")
    value: Optional[str] = Field(None, description="Input text or URL")
    thought: str = Field(..., description="Reasoning for this step")

class UIElement(BaseModel):
    tag: str
    attributes: Dict[str, str]
    text: Optional[str] = None
    bounding_box: Optional[Dict[str, float]] = None

# ==========================================
# 2. STATE SCHEMA
# ==========================================
class AgentState(TypedDict):
    """
    Core memory of the Agent. add_messages allows conversation history persistence.
    """
    messages: Annotated[List[Dict[str, Any]], add_messages]
    user_data: Dict[str, Any]
    missing_fields: List[str]
    execution_plan: List[AgentAction]
    current_screenshot: Optional[str]
    status: str
    last_error: Optional[str]
    is_approved: bool