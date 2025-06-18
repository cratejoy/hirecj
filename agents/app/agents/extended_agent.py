"""Extended Agent with additional functionality."""

from typing import List, Any, Optional
from crewai import Agent, LLM, Task
from crewai.tools import BaseTool
from shared.logging_config import get_logger

logger = get_logger(__name__)


class ExtendedAgent(Agent):
    """Extended Agent that adds callbacks and other enhancements."""
    
    # Store thinking callback as instance variable, not Pydantic field
    _thinking_callback: Optional[Any] = None
    
    def model_post_init(self, __context):
        """Initialize after Pydantic validation."""
        super().model_post_init(__context)
        # Initialize our custom attribute after Pydantic is done
        object.__setattr__(self, '_thinking_callback', None)
    
    def set_thinking_callback(self, callback):
        """Set a callback to receive thinking tokens during execution."""
        object.__setattr__(self, '_thinking_callback', callback)
    
    def execute_task(
        self,
        task: Task,
        context: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
    ) -> str:
        """Execute a task with thinking token callbacks."""
        thinking_callback = getattr(self, '_thinking_callback', None)
        
        if thinking_callback:
            # Add to global litellm callbacks for this execution
            import litellm
            
            # Store original callbacks
            original_success = litellm.success_callback.copy() if hasattr(litellm, 'success_callback') else []
            original_async_success = litellm._async_success_callback.copy() if hasattr(litellm, '_async_success_callback') else []
            
            # Add our callback
            if thinking_callback not in litellm.success_callback:
                litellm.success_callback.append(thinking_callback)
            if thinking_callback not in litellm._async_success_callback:
                litellm._async_success_callback.append(thinking_callback)
            
            try:
                # Call parent execute_task
                result = super().execute_task(task, context, tools)
                return result
            finally:
                # Restore original callbacks
                litellm.success_callback = original_success
                litellm._async_success_callback = original_async_success
        else:
            # No callback, just execute normally
            return super().execute_task(task, context, tools)