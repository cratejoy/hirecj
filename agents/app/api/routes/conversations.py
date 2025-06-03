"""
Conversation and annotation API endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime

from app.constants import HTTPStatus, PaginationDefaults
from app.config import settings

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


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
