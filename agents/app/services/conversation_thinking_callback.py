"""Conversation-aware thinking token callback."""

import asyncio
from typing import Any, Dict, Optional
from litellm.integrations.custom_logger import CustomLogger
from shared.logging_config import get_logger

logger = get_logger(__name__)


class ConversationThinkingCallback(CustomLogger):
    """Callback that sends thinking tokens with conversation context."""
    
    def __init__(self, conversation_id: str):
        super().__init__()
        self.conversation_id = conversation_id
    
    async def async_log_stream_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float) -> None:
        """Capture streaming chunks in real-time."""
        try:
            # Extract content from streaming response
            content = self._extract_content_from_stream(response_obj)
            if not content or not content.strip():
                return
            
            # For now, just log streaming content
            logger.debug(f"[THINKING_STREAM] {content.strip()}")
                
        except Exception as e:
            logger.error(f"[CONV_THINKING_CALLBACK] Error in streaming callback: {e}")
    
    def log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float) -> None:
        """Handle non-streaming responses."""
        try:
            # Extract full content
            content = self._extract_full_content(response_obj)
            if not content:
                return
            
            # Log just the reasoning content in a concise format
            # Remove "Thought:" prefix if present and clean up whitespace
            reasoning = content.strip()
            if reasoning.startswith("Thought:"):
                reasoning = reasoning[8:].strip()
            
            # Only log if there's actual content
            if reasoning:
                # Split into first line for concise logging
                while '\n\n' in reasoning:
                    reasoning = reasoning.replace('\n\n', '\n')
                reasoning = reasoning.replace('\n', ' | ').strip()
                logger.info(f"[THINKING] {reasoning}")
                
        except Exception as e:
            logger.error(f"[CONV_THINKING_CALLBACK] Error in success callback: {e}")
    
    def _extract_content_from_stream(self, response_obj: Any) -> Optional[str]:
        """Extract content from various streaming response formats."""
        if hasattr(response_obj, 'choices') and response_obj.choices:
            choice = response_obj.choices[0]
            
            # Handle delta format (streaming)
            if hasattr(choice, 'delta'):
                if hasattr(choice.delta, 'content'):
                    return choice.delta.content
                elif hasattr(choice.delta, 'text'):
                    return choice.delta.text
            
            # Handle non-delta format
            if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                return choice.message.content
            elif hasattr(choice, 'text'):
                return choice.text
        
        return None
    
    def _extract_full_content(self, response_obj: Any) -> Optional[str]:
        """Extract full content from response object."""
        if hasattr(response_obj, 'choices') and response_obj.choices:
            choice = response_obj.choices[0]
            
            if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                return choice.message.content
            elif hasattr(choice, 'text'):
                return choice.text
        
        return None