"""Tool execution interceptor for real-time streaming of tool calls."""

import time
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from shared.logging_config import get_logger

logger = get_logger(__name__)

# Try to import CrewAI event system
try:
    from crewai.utilities.events.crewai_event_bus import crewai_event_bus
    from crewai.utilities.events.tool_usage_events import (
        ToolUsageStartedEvent,
        ToolUsageFinishedEvent,
        ToolUsageErrorEvent,
    )
    CREWAI_EVENTS_AVAILABLE = True
except ImportError:
    logger.warning("[TOOL_INTERCEPTOR] CrewAI events not available - tool execution tracking disabled")
    CREWAI_EVENTS_AVAILABLE = False
    # Define dummy classes to prevent errors
    class ToolUsageStartedEvent:
        pass
    class ToolUsageFinishedEvent:
        pass
    class ToolUsageErrorEvent:
        pass

from app.services.thinking_token_manager import thinking_token_manager


class ToolExecutionInterceptor:
    """Intercepts CrewAI tool execution events and streams them in real-time."""
    
    def __init__(self):
        self._tool_callbacks: list[Callable[[Dict[str, Any]], None]] = []
        self._active_tools: Dict[str, Dict[str, Any]] = {}
        self._subscribed = False
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for tool execution events."""
        self._tool_callbacks.append(callback)
        
        # Subscribe to CrewAI events if not already subscribed
        if not self._subscribed:
            self._subscribe_to_events()
    
    def unregister_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Unregister a callback."""
        if callback in self._tool_callbacks:
            self._tool_callbacks.remove(callback)
    
    def _subscribe_to_events(self):
        """Subscribe to CrewAI tool usage events."""
        if not CREWAI_EVENTS_AVAILABLE:
            logger.warning("[TOOL_INTERCEPTOR] CrewAI events not available - skipping subscription")
            return
            
        # Register handlers for tool events
        crewai_event_bus.register_handler(
            ToolUsageStartedEvent,
            lambda source, event: self._on_tool_started(event)
        )
        
        crewai_event_bus.register_handler(
            ToolUsageFinishedEvent,
            lambda source, event: self._on_tool_finished(event)
        )
        
        crewai_event_bus.register_handler(
            ToolUsageErrorEvent,
            lambda source, event: self._on_tool_error(event)
        )
        
        self._subscribed = True
        logger.info("[TOOL_INTERCEPTOR] Subscribed to CrewAI tool events")
    
    def _on_tool_started(self, event: ToolUsageStartedEvent):
        """Handle tool usage started event."""
        tool_name = event.tool_name
        tool_args = event.tool_args
        
        # Track active tool
        self._active_tools[tool_name] = {
            "started_at": time.time(),
            "args": tool_args,
        }
        
        # Create tool call data
        tool_call_data = {
            "type": "tool_call",
            "tool_name": tool_name,
            "tool_input": tool_args,
            "timestamp": datetime.now(),
            "status": "started"
        }
        
        # Also add as thinking token
        thinking_token_manager.add_token(
            content=f"Using {tool_name} with inputs: {tool_args}",
            token_type="tool_usage",
            metadata={
                "tool_name": tool_name,
                "tool_input": tool_args,
                "status": "started"
            }
        )
        
        # Notify callbacks
        for callback in self._tool_callbacks:
            try:
                callback(tool_call_data)
            except Exception as e:
                logger.error(f"Error in tool callback: {e}")
        
        logger.info(f"[TOOL_STARTED] {tool_name} with args: {tool_args}")
    
    def _on_tool_finished(self, event: ToolUsageFinishedEvent):
        """Handle tool usage finished event."""
        tool_name = event.tool_name
        # ToolUsageFinishedEvent might not have result attribute
        result = getattr(event, 'result', getattr(event, 'output', 'No result available'))
        from_cache = getattr(event, 'from_cache', False)
        
        # Calculate duration
        duration_ms = None
        if tool_name in self._active_tools:
            started_at = self._active_tools[tool_name]["started_at"]
            duration_ms = int((time.time() - started_at) * 1000)
            del self._active_tools[tool_name]
        
        # Create tool call data
        tool_call_data = {
            "type": "tool_call",
            "tool_name": tool_name,
            "tool_input": getattr(event, 'tool_args', {}),
            "timestamp": datetime.now(),
            "status": "completed",
            "result": str(result)[:500],  # Truncate long results
            "duration_ms": duration_ms,
            "from_cache": from_cache
        }
        
        # Also add as thinking token
        thinking_token_manager.add_token(
            content=f"Tool {tool_name} completed: {str(result)[:200]}...",
            token_type="tool_result",
            metadata={
                "tool_name": tool_name,
                "duration_ms": duration_ms,
                "from_cache": from_cache
            }
        )
        
        # Notify callbacks
        for callback in self._tool_callbacks:
            try:
                callback(tool_call_data)
            except Exception as e:
                logger.error(f"Error in tool callback: {e}")
        
        logger.info(f"[TOOL_FINISHED] {tool_name} in {duration_ms}ms (cache={from_cache})")
    
    def _on_tool_error(self, event: ToolUsageErrorEvent):
        """Handle tool usage error event."""
        tool_name = event.tool_name
        error = event.error
        
        # Calculate duration
        duration_ms = None
        if tool_name in self._active_tools:
            started_at = self._active_tools[tool_name]["started_at"]
            duration_ms = int((time.time() - started_at) * 1000)
            del self._active_tools[tool_name]
        
        # Create tool call data
        tool_call_data = {
            "type": "tool_call",
            "tool_name": tool_name,
            "tool_input": event.tool_args,
            "timestamp": datetime.now(),
            "status": "failed",
            "error": str(error),
            "duration_ms": duration_ms
        }
        
        # Also add as thinking token
        thinking_token_manager.add_token(
            content=f"Tool {tool_name} failed: {str(error)}",
            token_type="tool_error",
            metadata={
                "tool_name": tool_name,
                "error": str(error)
            }
        )
        
        # Notify callbacks
        for callback in self._tool_callbacks:
            try:
                callback(tool_call_data)
            except Exception as e:
                logger.error(f"Error in tool callback: {e}")
        
        logger.error(f"[TOOL_ERROR] {tool_name}: {error}")


# Global instance
tool_execution_interceptor = ToolExecutionInterceptor()