"""Patch for CrewAI's LLM class to preserve LiteLLM callbacks.

CrewAI's LLM class replaces the entire litellm.callbacks list when initializing,
which breaks our debug callback functionality. This patch makes it append instead.
"""

import litellm
from crewai.llm import LLM
from shared.logging_config import get_logger

logger = get_logger(__name__)


def patch_crewai_llm():
    """Monkey patch CrewAI's LLM to preserve existing callbacks."""
    
    # Store the original __init__ method
    original_init = LLM.__init__
    
    def patched_init(self, *args, **kwargs):
        # Extract callbacks if provided
        callbacks = kwargs.get('callbacks', [])
        
        # Store existing callbacks before they get replaced
        existing_callbacks = list(litellm.callbacks) if hasattr(litellm, 'callbacks') else []
        existing_success = list(litellm.success_callback) if hasattr(litellm, 'success_callback') else []
        existing_input = list(litellm.input_callback) if hasattr(litellm, 'input_callback') else []
        
        logger.debug(f"[LLM_PATCH] Before init - callbacks: {len(existing_callbacks)}, success: {len(existing_success)}, input: {len(existing_input)}")
        
        # Call original init
        original_init(self, *args, **kwargs)
        
        # The original init sets litellm.callbacks = callbacks (replacing everything)
        # But we need to preserve success_callback and input_callback which are separate lists!
        
        # Restore input callbacks
        if existing_input and hasattr(litellm, 'input_callback'):
            for cb in existing_input:
                if cb not in litellm.input_callback:
                    litellm.input_callback.append(cb)
                    logger.debug(f"[LLM_PATCH] Restored input callback: {type(cb).__name__}")
        
        # Restore success callbacks
        if existing_success and hasattr(litellm, 'success_callback'):
            for cb in existing_success:
                if cb not in litellm.success_callback:
                    litellm.success_callback.append(cb)
                    logger.debug(f"[LLM_PATCH] Restored success callback: {type(cb).__name__}")
        
        # Restore general callbacks
        if existing_callbacks:
            for cb in existing_callbacks:
                if cb not in litellm.callbacks:
                    litellm.callbacks.append(cb)
            
        logger.debug(f"[LLM_PATCH] After init - callbacks: {len(litellm.callbacks)}, success: {len(litellm.success_callback)}, input: {len(litellm.input_callback)}")
    
    # Store the original call method
    original_call = LLM.call
    
    def patched_call(self, messages, callbacks=[]):
        # Store existing callbacks
        existing_callbacks = list(litellm.callbacks) if hasattr(litellm, 'callbacks') else []
        
        # Call original method
        result = original_call(self, messages, callbacks)
        
        # The original call method sets litellm.callbacks = callbacks if callbacks are provided
        # We need to restore any callbacks that were removed
        if callbacks and existing_callbacks:
            for cb in existing_callbacks:
                if cb not in litellm.callbacks:
                    litellm.callbacks.append(cb)
        
        return result
    
    # Replace the methods
    LLM.__init__ = patched_init
    LLM.call = patched_call
    
    logger.info("[LLM_PATCH] Successfully patched CrewAI LLM class to preserve callbacks")