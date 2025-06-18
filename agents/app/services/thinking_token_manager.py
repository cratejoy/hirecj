import threading
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime
from shared.protocol.models import ThinkingToken
import logging

logger = logging.getLogger(__name__)


class ThinkingTokenManager:
    """Manages thinking tokens during LLM execution.
    
    Uses thread-local storage to capture thinking tokens during execution
    and provides callbacks for streaming them in real-time.
    """
    
    def __init__(self):
        self._local = threading.local()
        self._callbacks: List[Callable[[ThinkingToken], None]] = []
    
    def start_capture(self):
        """Start capturing thinking tokens for the current thread."""
        if not hasattr(self._local, 'tokens'):
            self._local.tokens = []
        self._local.capturing = True
    
    def stop_capture(self) -> List[ThinkingToken]:
        """Stop capturing and return all captured tokens."""
        self._local.capturing = False
        tokens = getattr(self._local, 'tokens', [])
        self._local.tokens = []
        return tokens
    
    def add_token(self, content: str, token_type: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a thinking token and notify callbacks."""
        if not getattr(self._local, 'capturing', False):
            return
        
        token = ThinkingToken(
            timestamp=datetime.now(),
            content=content,
            token_type=token_type,
            metadata=metadata or {}
        )
        
        # Store locally
        if not hasattr(self._local, 'tokens'):
            self._local.tokens = []
        self._local.tokens.append(token)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(token)
            except Exception as e:
                logger.error(f"Error in thinking token callback: {e}")
    
    def register_callback(self, callback: Callable[[ThinkingToken], None]):
        """Register a callback to be notified when thinking tokens are added."""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[ThinkingToken], None]):
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_current_tokens(self) -> List[ThinkingToken]:
        """Get current tokens without stopping capture."""
        return getattr(self._local, 'tokens', []).copy()
    
    def is_capturing(self) -> bool:
        """Check if currently capturing tokens."""
        return getattr(self._local, 'capturing', False)


# Global instance
thinking_token_manager = ThinkingTokenManager()