"""
Simple Conversation Context Manager

This module provides a centralized, consistent way to manage conversation
context across all entry points in HireCJ. One pattern, everywhere.
"""

import yaml
from pathlib import Path
from typing import Optional

from app.models import Conversation, ConversationState
from shared.logging_config import get_logger

logger = get_logger(__name__)


class ConversationContextManager:
    """Manages conversation context with a simple, consistent approach."""

    _instance: Optional["ConversationContextManager"] = None
    _config_path: str = "config/context.yaml"

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self._config_path = config_path
        self.config = self._load_config(self._config_path)
        # Simple config: just window_size for now
        from app.config import settings

        self.window_size = self.config.get("window_size", settings.context_window_size)
        logger.info(
            f"ConversationContextManager initialized with window_size={self.window_size}"
        )

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            from app.config import settings

            logger.warning(
                f"Config file {config_path} not found, using default window_size={settings.context_window_size}"
            )
            return {"window_size": settings.context_window_size}

        with open(path, "r") as f:
            config = yaml.safe_load(f)
            logger.info(f"Loaded context config from {config_path}: {config}")
            return config

    def get_context_for_cj(self, conversation: Conversation) -> str:
        """Get formatted context string for CJ's prompt."""
        if not conversation.messages:
            return "No previous messages."

        # Get last N messages
        recent_messages = conversation.messages[-self.window_size :]

        # Format as simple history
        history = []
        for msg in recent_messages:
            history.append(f"{msg.sender.upper()}: {msg.content}")

        context = "\n".join(history)
        logger.debug(
            f"Built context with {len(recent_messages)} messages, {len(context)} chars"
        )
        return context

    def get_conversation_state(self, conversation: Conversation) -> ConversationState:
        """Get conversation state with context window."""
        state = ConversationState()
        state.context_window = (
            conversation.messages[-self.window_size :] if conversation.messages else []
        )

        logger.info(
            f"Created conversation state with {len(state.context_window)} messages in context window"
        )
        return state

    @classmethod
    def get_instance(
        cls, config_path: Optional[str] = None
    ) -> "ConversationContextManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance


def get_context_manager(
    config_path: Optional[str] = None,
) -> ConversationContextManager:
    """Get or create the context manager instance."""
    return ConversationContextManager.get_instance(config_path)
