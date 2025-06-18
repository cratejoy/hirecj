"""Simple tool execution monitor that works with CrewAI's step callback."""

import time
from typing import Any, Dict, Optional, Callable, List
from datetime import datetime
from shared.logging_config import get_logger
from app.services.thinking_token_manager import thinking_token_manager

logger = get_logger(__name__)


class ToolExecutionMonitor:
    """Monitors tool execution through CrewAI's step callback mechanism."""
    
    def __init__(self):
        self._tool_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._active_tool_start: Optional[float] = None
        self._last_tool_name: Optional[str] = None
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for tool execution events."""
        self._tool_callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Unregister a callback."""
        if callback in self._tool_callbacks:
            self._tool_callbacks.remove(callback)
    
    def create_step_callback(self, session_id: str):
        """Create a step callback function for CrewAI agent.
        
        This callback is called after each tool execution with the result.
        """
        def step_callback(tool_result: Any):
            """Callback called after tool execution."""
            try:
                # Only process if we have a known tool name from on_tool_start
                if not self._last_tool_name:
                    # Skip unknown tools - these are likely internal CrewAI operations
                    return
                
                # Extract tool information from the result
                tool_name = self._last_tool_name
                result_text = str(tool_result)
                
                # Try to extract more information from the result object
                if hasattr(tool_result, 'result'):
                    result_text = str(tool_result.result)
                    
                # For ToolResult objects
                if hasattr(tool_result, '__class__') and tool_result.__class__.__name__ == 'ToolResult':
                    if hasattr(tool_result, 'output'):
                        result_text = str(tool_result.output)
                
                # Calculate duration if we tracked the start
                duration_ms = None
                if self._active_tool_start:
                    duration_ms = int((time.time() - self._active_tool_start) * 1000)
                    self._active_tool_start = None
                
                # Create tool call completed event
                tool_call_data = {
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "tool_input": {},  # We don't have access to inputs in step callback
                    "timestamp": datetime.now(),
                    "status": "completed",
                    "result": result_text[:500] if result_text else "",  # Truncate long results
                    "duration_ms": duration_ms
                }
                
                
                # Notify callbacks
                for callback in self._tool_callbacks:
                    try:
                        callback(tool_call_data)
                    except Exception as e:
                        logger.error(f"Error in tool callback: {e}")
                
                
                # Clear last tool name after processing
                self._last_tool_name = None
                
            except Exception as e:
                logger.error(f"[TOOL_MONITOR] Error processing tool result: {e}")
        
        return step_callback
    
    def on_tool_start(self, tool_name: str, tool_input: Dict[str, Any]):
        """Manually track tool start (can be called from agent wrapper)."""
        self._active_tool_start = time.time()
        self._last_tool_name = tool_name
        
        # Create tool call started event
        tool_call_data = {
            "type": "tool_call",
            "tool_name": tool_name,
            "tool_input": tool_input,  # Keep as dict
            "timestamp": datetime.now(),
            "status": "started"
        }
        
        
        # Notify callbacks
        for callback in self._tool_callbacks:
            try:
                callback(tool_call_data)
            except Exception as e:
                logger.error(f"Error in tool callback: {e}")
        


# Global instance
tool_execution_monitor = ToolExecutionMonitor()