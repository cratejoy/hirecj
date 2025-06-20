"""
Conversation and annotation API endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Literal
from pathlib import Path
import json
from datetime import datetime
import os
import logging

from app.constants import HTTPStatus, PaginationDefaults
from app.config import settings

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)


class AnnotationRequest(BaseModel):
    """Request model for annotations."""

    sentiment: str  # "like" or "dislike"
    text: Optional[str] = ""

    def validate_sentiment(self):
        if self.sentiment not in ["like", "dislike"]:
            raise ValueError("Sentiment must be 'like' or 'dislike'")


def get_conversation_path(conversation_id: str) -> Optional[Path]:
    """Find conversation file by ID."""
    data_dir = Path("data/conversations")

    # First try exact match
    exact_path = data_dir / f"{conversation_id}.json"
    if exact_path.exists():
        return exact_path

    # Then search for files containing the ID
    pattern = f"*{conversation_id}*.json"
    matches = list(data_dir.glob(pattern))

    if matches:
        return matches[0]  # Return first match

    return None


def load_conversation(conversation_id: str) -> Dict[str, Any]:
    """Load conversation from disk."""
    path = get_conversation_path(conversation_id)
    if not path:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Conversation not found"
        )

    with open(path) as f:
        return json.load(f)


def save_conversation(conversation_id: str, data: Dict[str, Any]):
    """Save conversation to disk."""
    path = get_conversation_path(conversation_id)
    if not path:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Conversation not found"
        )

    # Update the updated_at timestamp
    data["updated_at"] = datetime.utcnow().isoformat() + "Z"

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a conversation including all messages and annotations."""
    conversation = load_conversation(conversation_id)

    # Ensure annotations field exists
    if "annotations" not in conversation:
        conversation["annotations"] = {}

    return conversation


@router.get("/")
async def list_conversations(
    annotated: Optional[bool] = Query(
        None, description="Filter to only annotated conversations"
    ),
    merchant: Optional[str] = Query(None, description="Filter by merchant ID"),
    scenario: Optional[str] = Query(None, description="Filter by scenario ID"),
    limit: int = Query(
        settings.default_pagination_limit,
        ge=PaginationDefaults.MIN_LIMIT,
        le=settings.max_pagination_limit,
        description="Maximum number to return",
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """List all saved conversations with optional filtering."""
    data_dir = Path("data/conversations")
    all_files = sorted(
        data_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    conversations = []
    for file_path in all_files:
        try:
            with open(file_path) as f:
                data = json.load(f)

            # Apply filters
            if merchant and data.get("merchant", {}).get("id") != merchant:
                continue

            if scenario and data.get("scenario", {}).get("id") != scenario:
                continue

            annotation_count = len(data.get("annotations", {}))

            if annotated is not None:
                if annotated and annotation_count == 0:
                    continue
                elif not annotated and annotation_count > 0:
                    continue

            conversations.append(
                {
                    "conversation_id": data.get(
                        "conversation_id", data.get("id", file_path.stem)
                    ),
                    "merchant_id": data.get("merchant", {}).get("id")
                    or data.get("merchant_name"),
                    "scenario_id": data.get("scenario", {}).get("id")
                    or data.get("scenario_name"),
                    "message_count": len(data.get("messages", [])),
                    "annotation_count": annotation_count,
                    "created_at": data.get("created_at", file_path.stat().st_ctime),
                }
            )

        except Exception:
            # Skip files that can't be parsed
            continue

    # Apply pagination
    total = len(conversations)
    conversations = conversations[offset : offset + limit]

    return {
        "conversations": conversations,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{conversation_id}/annotations/{message_index}")
async def add_annotation(
    conversation_id: str, message_index: int, annotation: AnnotationRequest
):
    """Add or update an annotation for a specific message."""
    # Validate sentiment
    try:
        annotation.validate_sentiment()
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))

    # Load conversation
    conversation = load_conversation(conversation_id)

    # Validate message index
    message_count = len(conversation.get("messages", []))
    if message_index < 0 or message_index >= message_count:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Invalid message index: {message_index} (conversation has {message_count} messages)",
        )

    # Ensure annotations field exists
    if "annotations" not in conversation:
        conversation["annotations"] = {}

    # Add/update annotation
    conversation["annotations"][str(message_index)] = {
        "sentiment": annotation.sentiment,
        "text": annotation.text or "",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Save conversation
    save_conversation(conversation_id, conversation)

    return {
        "message": "Annotation added successfully",
        "annotation": conversation["annotations"][str(message_index)],
    }


@router.delete("/{conversation_id}/annotations/{message_index}")
async def delete_annotation(conversation_id: str, message_index: int):
    """Remove an annotation from a message."""
    # Load conversation
    conversation = load_conversation(conversation_id)

    # Check if annotation exists
    annotations = conversation.get("annotations", {})
    if str(message_index) not in annotations:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"No annotation found for message {message_index}",
        )

    # Remove annotation
    del annotations[str(message_index)]

    # Save conversation
    save_conversation(conversation_id, conversation)

    return {"message": "Annotation deleted successfully"}


# Eval Conversation Capture Models
class WorkflowConfig(BaseModel):
    """Workflow configuration for eval capture."""
    name: str
    description: str
    behavior: Optional[Dict[str, Any]] = None
    requirements: Optional[Dict[str, Any]] = None
    workflow: Optional[str] = None
    data_requirements: Optional[List[Any]] = None
    available_tools: Optional[List[str]] = None


class Persona(BaseModel):
    """Persona configuration for eval capture."""
    id: str
    name: str
    business: str
    role: str
    industry: str
    communicationStyle: List[str]
    traits: List[str]


class Scenario(BaseModel):
    """Scenario configuration for eval capture."""
    id: str
    name: str
    description: str


class ToolDefinition(BaseModel):
    """Tool definition for eval capture."""
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None


class ToolCall(BaseModel):
    """Tool call record for eval capture."""
    tool: str
    args: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class GroundingQuery(BaseModel):
    """Grounding query record for eval capture."""
    query: str
    response: str
    sources: Optional[List[str]] = None


class TokenMetrics(BaseModel):
    """Token usage metrics."""
    prompt: int
    completion: int
    thinking: int


class MessageMetrics(BaseModel):
    """Message performance metrics."""
    latency_ms: int
    tokens: TokenMetrics


class AgentProcessing(BaseModel):
    """Agent processing details for a message."""
    thinking: str
    intermediate_responses: List[str]
    tool_calls: List[ToolCall]
    grounding_queries: List[GroundingQuery]
    final_response: str


class CapturedMessage(BaseModel):
    """Captured message with full agent processing."""
    turn: int
    user_input: str
    agent_processing: AgentProcessing
    metrics: MessageMetrics


class ConversationContext(BaseModel):
    """Full conversation context."""
    workflow: WorkflowConfig
    persona: Persona
    scenario: Scenario
    trustLevel: int
    model: str
    temperature: float


class ConversationPrompts(BaseModel):
    """System prompts at time of execution."""
    cj_prompt: str
    workflow_prompt: str
    tool_definitions: List[ToolDefinition]


class ConversationCapture(BaseModel):
    """Complete conversation capture for eval."""
    id: str
    timestamp: str
    context: ConversationContext
    prompts: ConversationPrompts
    messages: List[CapturedMessage]


class CaptureRequest(BaseModel):
    """Request to capture a conversation."""
    conversation: ConversationCapture
    source: Literal["playground", "production", "synthetic"] = "playground"


@router.post("/capture")
async def capture_conversation(request: CaptureRequest):
    """Capture a conversation for evaluation purposes."""
    conversation = request.conversation
    source = request.source
    
    # Create date-based directory structure
    date_path = datetime.now().strftime("%Y-%m-%d")
    dir_path = f"hirecj_evals/conversations/{source}/{date_path}"
    
    try:
        # Ensure directory exists
        os.makedirs(dir_path, exist_ok=True)
        
        # Write conversation as formatted JSON
        file_path = f"{dir_path}/{conversation.id}.json"
        with open(file_path, 'w') as f:
            json.dump(conversation.dict(), f, indent=2, default=str)
        
        # Log capture for tracking
        logger.info(f"Captured conversation {conversation.id} to {file_path}")
        
        return {
            "id": conversation.id, 
            "path": file_path,
            "message": "Conversation captured successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to capture conversation {conversation.id}: {str(e)}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to capture conversation: {str(e)}"
        )
