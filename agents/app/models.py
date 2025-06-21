"""Simplified data models for the synthetic conversation generator."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.config import settings


class Message(BaseModel):
    """A single message in a conversation."""

    timestamp: datetime
    sender: str  # "merchant" or "cj"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationState(BaseModel):
    """Lightweight conversation state for tracking context."""

    workflow: Optional[str] = None
    workflow_details: Optional[str] = None
    context_window: List[Message] = Field(default_factory=list)

    def to_prompt_context(self) -> Dict[str, Any]:
        """Convert state to context for prompt."""
        return {
            "workflow_name": self.workflow or "None",
            "workflow_details": self.workflow_details
            or "No specific workflow - be responsive to merchant needs",
            "recent_context": (
                "\n".join(
                    [
                        f"{msg.sender}: {msg.content}"
                        for msg in self.context_window[-settings.recent_history_limit :]
                    ]
                )
                if self.context_window
                else "No previous messages"
            ),
        }

    def add_message(self, message: Message):
        """Add a message and update state."""
        self.context_window.append(message)
        # Keep only last N messages in context
        if len(self.context_window) > settings.context_window_size:
            self.context_window = self.context_window[-settings.context_window_size :]


class Conversation(BaseModel):
    """A simple conversation between merchant and CJ."""

    id: str
    created_at: datetime
    scenario_name: str
    merchant_name: str
    cj_version: str = settings.default_cj_version
    workflow: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    state: ConversationState = Field(default_factory=ConversationState)

    def add_message(self, message: Message):
        """Add a message to the conversation."""
        self.messages.append(message)
        self.state.add_message(message)


# API Request/Response Models


class ConversationRequest(BaseModel):
    """Request to generate a conversation."""

    merchant_name: str
    scenario_name: str
    cj_version: str = settings.default_cj_version  # Default from settings
    workflow: Optional[str] = None  # Optional workflow
    max_turns: int = Field(
        settings.max_conversation_turns_display,
        description="Maximum conversation turns",
    )
    merchant_opens: Optional[str] = None  # Let merchant start the conversation


class ConversationResponse(BaseModel):
    """Response containing generated conversation."""

    conversation_id: str
    created_at: datetime
    workflow: Optional[str]
    messages: List[Message]


class EvalChatRequest(BaseModel):
    """Request for eval chat endpoint to generate CJ response."""
    
    messages: List[Dict[str, str]]  # [{"role": "user", "content": "..."}, ...]
    workflow: str = Field(default="ad_hoc_support")
    persona: Optional[str] = Field(default="jessica")
    trust_level: int = Field(default=3)
    
    class Config:
        schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "sup guy"}
                ],
                "workflow": "ad_hoc_support",
                "persona": "jessica"
            }
        }


class EvalChatResponse(BaseModel):
    """Response from eval chat endpoint."""
    
    response: str
