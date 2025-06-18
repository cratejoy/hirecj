"""Thinking token streaming callback for litellm."""

import re
from typing import Any, Dict, Optional
from litellm.integrations.custom_logger import CustomLogger
from shared.logging_config import get_logger

logger = get_logger(__name__)


class ThinkingTokenStreamingCallback(CustomLogger):
    """Callback that captures thinking tokens from LLM streaming responses."""
    
    def __init__(self):
        super().__init__()
    
    async def async_log_stream_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float) -> None:
        """Capture streaming chunks in real-time."""
        try:
            # Extract content from streaming response
            content = self._extract_content_from_stream(response_obj)
            if not content:
                return
            
            # Send all content as thinking tokens
            from app.services.thinking_token_manager import thinking_token_manager
            await thinking_token_manager.send_thinking_token(content)
            logger.debug(f"[THINKING_CALLBACK] Sent thinking token: {content[:50]}...")
                
        except Exception as e:
            logger.error(f"[THINKING_CALLBACK] Error in streaming callback: {e}")
    
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
    
    
    def log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float) -> None:
        """Handle non-streaming responses."""
        try:
            # Extract full content
            content = self._extract_full_content(response_obj)
            if not content:
                return
            
            # Send entire content as thinking token
            if content and content.strip():
                from app.services.thinking_token_manager import thinking_token_manager
                # Send synchronously (we're in a sync context)
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # No event loop in this thread, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                try:
                    if loop.is_running():
                        # Schedule the coroutine
                        asyncio.create_task(thinking_token_manager.send_thinking_token(content))
                    else:
                        # Run in new event loop
                        loop.run_until_complete(thinking_token_manager.send_thinking_token(content))
                except Exception as e:
                    logger.warning(f"[THINKING_CALLBACK] Could not send thinking token: {e}")
                
                logger.debug(f"[THINKING_CALLBACK] Sent entire response as thinking token")
                
        except Exception as e:
            logger.error(f"[THINKING_CALLBACK] Error in success callback: {e}")
    
    def _extract_full_content(self, response_obj: Any) -> Optional[str]:
        """Extract full content from response object."""
        if hasattr(response_obj, 'choices') and response_obj.choices:
            choice = response_obj.choices[0]
            
            if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                return choice.message.content
            elif hasattr(choice, 'text'):
                return choice.text
        
        return None
    


# Create singleton instance
thinking_token_streaming_callback = ThinkingTokenStreamingCallback()