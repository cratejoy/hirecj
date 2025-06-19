"""Extended Agent with additional functionality."""

from typing import List, Any, Optional
from crewai import Agent, LLM, Task
from crewai.tools import BaseTool
from litellm.integrations.custom_logger import CustomLogger
from shared.logging_config import get_logger

logger = get_logger(__name__)


class CompositeCallback(CustomLogger):
    """Forwards callback events to multiple handlers."""
    
    def __init__(self, callbacks):
        super().__init__()
        self.callbacks = callbacks
        logger.info(f"[COMPOSITE_CALLBACK] Created with {len(callbacks)} callbacks: {[type(cb).__name__ for cb in callbacks]}")
    
    def log_pre_api_call(self, *args, **kwargs):
        """Forward pre-API call to all callbacks."""
        for cb in self.callbacks:
            if hasattr(cb, 'log_pre_api_call'):
                try:
                    cb.log_pre_api_call(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[COMPOSITE_CALLBACK] Error in {type(cb).__name__}.log_pre_api_call: {e}")
    
    def log_success_event(self, *args, **kwargs):
        """Forward success event to all callbacks."""
        logger.info(f"[COMPOSITE_CALLBACK] log_success_event called, forwarding to {len(self.callbacks)} callbacks")
        for cb in self.callbacks:
            if hasattr(cb, 'log_success_event'):
                try:
                    logger.info(f"[COMPOSITE_CALLBACK] Calling {type(cb).__name__}.log_success_event")
                    cb.log_success_event(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[COMPOSITE_CALLBACK] Error in {type(cb).__name__}.log_success_event: {e}")
    
    def log_failure_event(self, *args, **kwargs):
        """Forward failure event to all callbacks."""
        for cb in self.callbacks:
            if hasattr(cb, 'log_failure_event'):
                try:
                    cb.log_failure_event(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[COMPOSITE_CALLBACK] Error in {type(cb).__name__}.log_failure_event: {e}")
    
    def log_stream_event(self, *args, **kwargs):
        """Forward stream event to all callbacks."""
        for cb in self.callbacks:
            if hasattr(cb, 'log_stream_event'):
                try:
                    cb.log_stream_event(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[COMPOSITE_CALLBACK] Error in {type(cb).__name__}.log_stream_event: {e}")


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
            
            # Add our callback
            logger.info(f"[EXTENDED_AGENT] Before adding thinking callback - success: {len(litellm.success_callback)}")
            if thinking_callback not in litellm.success_callback:
                litellm.success_callback.append(thinking_callback)
            if thinking_callback not in litellm._async_success_callback:
                litellm._async_success_callback.append(thinking_callback)
            logger.info(f"[EXTENDED_AGENT] After adding thinking callback - success: {len(litellm.success_callback)}")
            
            try:
                # Call parent execute_task
                logger.info(f"[EXTENDED_AGENT] Before parent execute_task - success callbacks: {[type(cb).__name__ for cb in litellm.success_callback]}")
                result = super().execute_task(task, context, tools)
                logger.info(f"[EXTENDED_AGENT] After parent execute_task - success callbacks: {[type(cb).__name__ for cb in litellm.success_callback]}")
                return result
            finally:
                # Only remove our specific callback, preserve others (like DebugCallback)
                logger.info(f"[EXTENDED_AGENT] Cleanup - removing thinking callback")
                if thinking_callback in litellm.success_callback:
                    litellm.success_callback.remove(thinking_callback)
                if thinking_callback in litellm._async_success_callback:
                    litellm._async_success_callback.remove(thinking_callback)
                logger.info(f"[EXTENDED_AGENT] After cleanup - success callbacks: {[type(cb).__name__ for cb in litellm.success_callback]}")
        else:
            # No callback, just execute normally
            return super().execute_task(task, context, tools)
    
    def create_agent_executor(self, tools=None, task=None) -> None:
        """Override to preserve our callbacks when creating executor."""
        import litellm
        
        # Capture existing callbacks before parent creates executor
        existing_input_callbacks = list(litellm.input_callback) if hasattr(litellm, 'input_callback') else []
        existing_success_callbacks = list(litellm.success_callback) if hasattr(litellm, 'success_callback') else []
        
        logger.info(f"[EXTENDED_AGENT] Before create_agent_executor - input: {len(existing_input_callbacks)}, success: {len(existing_success_callbacks)}")
        logger.info(f"[EXTENDED_AGENT] Existing callbacks: input={[type(cb).__name__ for cb in existing_input_callbacks]}, success={[type(cb).__name__ for cb in existing_success_callbacks]}")
        
        # Call parent to create executor normally
        super().create_agent_executor(tools, task)
        
        # The parent sets callbacks=[TokenCalcHandler(...)] on the executor
        # We need to merge our callbacks with theirs
        if hasattr(self.agent_executor, 'callbacks') and self.agent_executor.callbacks:
            crew_callbacks = list(self.agent_executor.callbacks)
            logger.info(f"[EXTENDED_AGENT] CrewAI callbacks: {[type(cb).__name__ for cb in crew_callbacks]}")
            
            # Collect all callbacks that should receive events
            all_callbacks = []
            
            # Add CrewAI's callbacks
            all_callbacks.extend(crew_callbacks)
            
            # Add our callbacks that implement the right methods
            for cb in existing_input_callbacks + existing_success_callbacks:
                if cb not in all_callbacks:  # Avoid duplicates
                    all_callbacks.append(cb)
            
            # Create composite callback
            composite = CompositeCallback(all_callbacks)
            
            # Replace executor's callbacks with our composite
            self.agent_executor.callbacks = [composite]
            
            logger.info(f"[EXTENDED_AGENT] Replaced executor callbacks with CompositeCallback containing {len(all_callbacks)} callbacks")