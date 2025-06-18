"""Monitored database tools that report execution to the tool monitor."""

from typing import Any, Dict, List
from app.agents.database_tools import create_database_tools
from app.services.tool_execution_monitor import tool_execution_monitor
from app.services.thinking_token_manager import thinking_token_manager
from shared.logging_config import get_logger
import time
from datetime import datetime

logger = get_logger(__name__)


class MonitoredToolWrapper:
    """Wraps a CrewAI tool to add monitoring capabilities."""
    
    def __init__(self, tool):
        self.tool = tool
        self.name = tool.name
        self.description = tool.description
        # Store original _run method (Tool class uses _run, not invoke)
        self._original_run = tool._run
        # Replace _run with monitored version
        tool._run = self._monitored_run
    
    def _monitored_run(self, *args, **kwargs) -> Any:
        """Monitored version of tool execution."""
        # Track tool start
        start_time = time.time()
        tool_input = kwargs if kwargs else {"args": args} if args else {}
        tool_execution_monitor.on_tool_start(self.name, tool_input)
        
        try:
            # Call the original tool
            result = self._original_run(*args, **kwargs)
            
            # Track tool completion
            duration_ms = int((time.time() - start_time) * 1000)
            return result
            
        except Exception as e:
            # Track tool error
            duration_ms = int((time.time() - start_time) * 1000)
            
            
            logger.error(f"[MONITORED_TOOL] {self.name} failed: {e}")
            raise


def create_monitored_database_tools(merchant_name: str) -> List[Any]:
    """Create database tools with execution monitoring."""
    # Get the original tools
    original_tools = create_database_tools(merchant_name)
    
    # Wrap each tool with monitoring
    monitored_tools = []
    for tool in original_tools:
        # Create wrapper to add monitoring
        wrapper = MonitoredToolWrapper(tool)
        monitored_tools.append(tool)  # Return the modified original tool
    return monitored_tools