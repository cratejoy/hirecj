"""Conversation persistence."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models import Conversation, Message
from app.services.session_manager import Session
from app.logging_config import get_logger

logger = get_logger(__name__)


class ConversationStorage:
    """Handles conversation persistence."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.conversations_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session: Session) -> Path:
        """Save session to disk."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        merchant = session.conversation.merchant_name.replace(" ", "_").lower()
        scenario = session.conversation.scenario_name.replace(" ", "_").lower()

        filename = f"{merchant}_{scenario}_{timestamp}.json"
        filepath = self.base_dir / filename

        data = {
            "session_id": session.id,
            "created_at": session.created_at.isoformat(),
            "conversation": {
                "id": session.conversation.id,
                "created_at": session.conversation.created_at.isoformat(),
                "scenario_name": session.conversation.scenario_name,
                "merchant_name": session.conversation.merchant_name,
                "workflow": session.conversation.workflow,
                "messages": [
                    {
                        "timestamp": msg.timestamp.isoformat(),
                        "sender": msg.sender,
                        "content": msg.content,
                        "metadata": msg.metadata,
                    }
                    for msg in session.conversation.messages
                ],
            },
            "metrics": session.metrics,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved session to {filepath}")
        return filepath

    def load_conversation(self, filepath: Path) -> Optional[Conversation]:
        """Load conversation from file."""
        try:
            with open(filepath) as f:
                data = json.load(f)

            conv_data = data["conversation"]
            conversation = Conversation(
                id=conv_data["id"],
                created_at=datetime.fromisoformat(conv_data["created_at"]),
                scenario_name=conv_data["scenario_name"],
                merchant_name=conv_data["merchant_name"],
                workflow=conv_data.get("workflow"),
            )

            # Recreate messages
            for msg_data in conv_data["messages"]:
                msg = Message(
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    sender=msg_data["sender"],
                    content=msg_data["content"],
                    metadata=msg_data.get("metadata", {}),
                )
                conversation.messages.append(msg)

            return conversation

        except Exception as e:
            logger.error(f"Failed to load conversation from {filepath}: {e}")
            return None

    def list_conversations(self) -> list[Path]:
        """List all saved conversations."""
        return list(self.base_dir.glob("*.json"))
