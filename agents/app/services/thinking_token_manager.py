"""Thinking token manager for sending thinking tokens to connected clients."""

import asyncio
from contextlib import contextmanager
from typing import Optional, Dict, Any
from shared.logging_config import get_logger
from shared.protocol.models import CJThinkingMsg

logger = get_logger(__name__)


class ThinkingTokenManager:
    """Manages thinking token streaming to connected clients."""
    
    def __init__(self):
        """Initialize the thinking token manager."""
        self._web_platform: Optional[Any] = None
        self._current_conversation_id: Optional[str] = None
    
    def set_web_platform(self, platform: Any) -> None:
        """Set the web platform instance for sending messages."""
        self._web_platform = platform
        logger.debug("[THINKING_MANAGER] Web platform set")
    
    def set_current_conversation(self, conversation_id: str) -> None:
        """Set the current conversation ID for thinking token routing."""
        self._current_conversation_id = conversation_id
        logger.debug(f"[THINKING_MANAGER] Current conversation set: {conversation_id}")
    
    async def send_thinking_token(self, content: str) -> None:
        """Send a thinking token to the current conversation."""
        if not self._web_platform:
            logger.warning("[THINKING_MANAGER] No web platform set - cannot send thinking token")
            return
        
        if not self._current_conversation_id:
            logger.warning("[THINKING_MANAGER] No current conversation - cannot send thinking token")
            return
        
        # Get the websocket for the current conversation
        websocket = self._web_platform.connections.get(self._current_conversation_id)
        if not websocket:
            logger.warning(f"[THINKING_MANAGER] No websocket found for conversation {self._current_conversation_id}")
            return
        
        try:
            # Create a validated thinking message
            thinking_msg = CJThinkingMsg(content=content)
            
            # Send via the platform's validated message method
            await self._web_platform.send_validated_message(websocket, thinking_msg)
            
            logger.debug(f"[THINKING_MANAGER] Sent thinking token ({len(content)} chars) to {self._current_conversation_id}")
            
        except Exception as e:
            logger.error(f"[THINKING_MANAGER] Error sending thinking token: {e}")


# Global singleton instance
thinking_token_manager = ThinkingTokenManager()