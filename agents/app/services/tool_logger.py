import logging
import json
from typing import Any, Dict, Optional
from functools import wraps
from shared.logging_config import get_logger

logger = get_logger(__name__)

class ToolLogger:
    """Central tool execution logger that integrates with debug callback."""
    
    _instance = None
    _debug_callback = None
    
    @classmethod
    def set_debug_callback(cls, callback):
        """Set the debug callback for capturing tool calls."""
        cls._debug_callback = callback
    
    @classmethod
    def log_tool_call(cls, tool_name: str, tool_input: Dict[str, Any], tool_output: Any = None, error: Optional[str] = None):
        """Log a tool call and capture in debug callback if available."""
        # Standard logging
        if error:
            logger.info(f"[TOOL ERROR] {tool_name}() - {error}")
        elif tool_output is not None:
            logger.info(f"[TOOL RESULT] {tool_name}() - {str(tool_output)[:200]}...")
        else:
            input_str = json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input)
            logger.info(f"[TOOL CALL] {tool_name}({input_str[:100]}...) - Executing")
        
        # Capture in debug callback if available
        if cls._debug_callback:
            cls._debug_callback.capture_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                error=error
            )

def log_tool_execution(func):
    """Decorator for CrewAI tools to automatically log execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        # Extract inputs - this is simplified, real implementation would parse better
        tool_input = {"args": args, "kwargs": kwargs} if args or kwargs else {}
        
        try:
            # Log the call
            ToolLogger.log_tool_call(tool_name, tool_input)
            
            # Execute
            result = func(*args, **kwargs)
            
            # Log the result
            ToolLogger.log_tool_call(tool_name, tool_input, tool_output=result)
            
            return result
            
        except Exception as e:
            # Log the error
            ToolLogger.log_tool_call(tool_name, tool_input, error=str(e))
            raise
    
    return wrapper