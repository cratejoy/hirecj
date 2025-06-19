import logging
import json
import time
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
    def log_tool_call(cls, tool_name: str, tool_input: Dict[str, Any], tool_output: Any = None, 
                     error: Optional[str] = None, start_time: Optional[float] = None,
                     end_time: Optional[float] = None, duration: Optional[float] = None):
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
                error=error,
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )

def log_tool_execution(func):
    """Enhanced decorator for CrewAI tools with timing and better argument parsing."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = func.__name__
        
        # Better argument parsing for CrewAI tools
        tool_input = {}
        
        # For @tool decorated functions, first arg is usually the actual input
        if args and len(args) > 0:
            first_arg = args[0]
            if isinstance(first_arg, str):
                tool_input = {"input": first_arg}
            elif isinstance(first_arg, dict):
                tool_input = first_arg.copy()
            else:
                # For other types, convert to string representation
                tool_input = {"input": str(first_arg)}
            
            # Add remaining positional args if any
            if len(args) > 1:
                tool_input["additional_args"] = args[1:]
        
        # Add any keyword arguments
        if kwargs:
            tool_input.update(kwargs)
        
        try:
            # Log the call with start time
            ToolLogger.log_tool_call(tool_name, tool_input, start_time=start_time)
            
            # Execute the tool
            result = func(*args, **kwargs)
            
            # Calculate duration
            end_time = time.time()
            duration = end_time - start_time
            
            # Log the result with timing
            ToolLogger.log_tool_call(
                tool_name, 
                tool_input, 
                tool_output=result,
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )
            
            logger.info(f"[TOOL TIMING] {tool_name} executed in {duration:.3f}s")
            
            return result
            
        except Exception as e:
            # Log the error with timing
            end_time = time.time()
            duration = end_time - start_time
            
            ToolLogger.log_tool_call(
                tool_name, 
                tool_input, 
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )
            logger.error(f"[TOOL ERROR] {tool_name} failed after {duration:.3f}s: {str(e)}")
            raise
    
    return wrapper