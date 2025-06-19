from litellm.integrations.custom_logger import CustomLogger
from typing import Dict, Any, Optional, List
import json
from datetime import datetime
from shared.logging_config import get_logger
from dataclasses import dataclass, asdict
import re
import traceback

logger = get_logger(__name__)

@dataclass
class ToolCallCapture:
    """Captures a tool call during execution."""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Any = None
    error: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

class DebugCallback(CustomLogger):
    """Comprehensive debug callback that captures all LLM and tool interactions."""
    
    def __init__(self, session_id: str, debug_storage: Dict[str, Any]):
        super().__init__()
        self.session_id = session_id
        self.debug_storage = debug_storage
        self.current_message_id = None
        self.crew_output_buffer = []
        self.pending_tool_calls = {}  # Track tool calls in progress
        
    def set_message_id(self, message_id: str):
        """Set the current message ID for associating debug data."""
        self.current_message_id = message_id
        # Clear buffers for new message
        self.crew_output_buffer = []
        self.pending_tool_calls = {}
    
    def log_pre_api_call(self, model: str, messages: list, kwargs: Dict[str, Any]) -> None:
        """Capture the raw API request before it's sent."""
        logger.info(f"[DEBUG_CALLBACK] log_pre_api_call called for message {self.current_message_id}")
        try:
            # Extract the full prompt with all details
            prompt_data = {
                "message_id": self.current_message_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens"),
                "tools": kwargs.get("tools", []),
                "tool_choice": kwargs.get("tool_choice"),
                "stream": kwargs.get("stream", False),
                "metadata": {
                    "provider": kwargs.get("custom_llm_provider", "unknown"),
                    "api_base": kwargs.get("api_base"),
                    "api_version": kwargs.get("api_version"),
                    # Sanitize headers
                    "headers": {k: "***" if k.lower() in ["authorization", "x-api-key", "api-key"] else v 
                               for k, v in kwargs.get("extra_headers", {}).items()},
                }
            }
            
            # Store in debug storage
            self.debug_storage["llm_prompts"].append(prompt_data)
            
            # Keep only last 10 prompts
            if len(self.debug_storage["llm_prompts"]) > 10:
                self.debug_storage["llm_prompts"].pop(0)
                
            logger.info(f"[DEBUG_CALLBACK] Captured prompt for message {self.current_message_id} - {len(messages)} messages, model: {model}")
            
        except Exception as e:
            logger.error(f"[DEBUG_CALLBACK] Error capturing prompt: {e}", exc_info=True)
    
    def log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float) -> None:
        """Capture the raw API response including tool calls."""
        logger.info(f"[DEBUG_CALLBACK] log_success_event called for message {self.current_message_id}")
        logger.info(f"[DEBUG_CALLBACK] Response object type: {type(response_obj)}")
        try:
            # Extract tool calls if present
            tool_calls = []
            if hasattr(response_obj, 'choices') and response_obj.choices:
                choice = response_obj.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls'):
                    for tc in (choice.message.tool_calls or []):
                        tool_calls.append({
                            "id": tc.id if hasattr(tc, 'id') else None,
                            "type": tc.type if hasattr(tc, 'type') else "function",
                            "function": {
                                "name": tc.function.name if hasattr(tc, 'function') else None,
                                "arguments": tc.function.arguments if hasattr(tc, 'function') else None,
                            }
                        })
            
            response_data = {
                "message_id": self.current_message_id,
                "timestamp": datetime.utcnow().isoformat(),
                "duration": end_time - start_time,
                "model": response_obj.model if hasattr(response_obj, 'model') else kwargs.get('model'),
                "usage": response_obj.usage.dict() if hasattr(response_obj, 'usage') else None,
                "choices": [
                    {
                        "message": {
                            "role": choice.message.role if hasattr(choice, 'message') else None,
                            "content": choice.message.content if hasattr(choice, 'message') else None,
                            "tool_calls": tool_calls
                        },
                        "finish_reason": choice.finish_reason if hasattr(choice, 'finish_reason') else None,
                    }
                    for choice in (response_obj.choices if hasattr(response_obj, 'choices') else [])
                ],
                "system_fingerprint": response_obj.system_fingerprint if hasattr(response_obj, 'system_fingerprint') else None,
                "created": response_obj.created if hasattr(response_obj, 'created') else None,
            }
            
            # Store in debug storage
            self.debug_storage["llm_responses"].append(response_data)
            
            # Keep only last 10 responses
            if len(self.debug_storage["llm_responses"]) > 10:
                self.debug_storage["llm_responses"].pop(0)
            
            # Update timing
            if "last_response_time" not in self.debug_storage["timing"]:
                self.debug_storage["timing"]["last_response_time"] = end_time - start_time
            else:
                # Calculate running average
                prev_avg = self.debug_storage["timing"].get("avg_response_time", end_time - start_time)
                count = self.debug_storage["timing"].get("response_count", 1)
                new_avg = (prev_avg * count + (end_time - start_time)) / (count + 1)
                self.debug_storage["timing"]["avg_response_time"] = new_avg
                self.debug_storage["timing"]["response_count"] = count + 1
                self.debug_storage["timing"]["last_response_time"] = end_time - start_time
                
            logger.info(f"[DEBUG_CALLBACK] Captured response for message {self.current_message_id} - {len(tool_calls)} tool calls, duration: {end_time - start_time:.2f}s")
            
        except Exception as e:
            logger.error(f"[DEBUG_CALLBACK] Error capturing response: {e}", exc_info=True)
    
    def capture_tool_call(self, tool_name: str, tool_input: Dict[str, Any], tool_output: Any = None, error: Optional[str] = None):
        """Manually capture tool calls from tool execution logs."""
        try:
            tool_capture = ToolCallCapture(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                error=error
            )
            
            # Add to debug storage
            tool_data = asdict(tool_capture)
            tool_data["message_id"] = self.current_message_id
            
            self.debug_storage["tool_calls"].append(tool_data)
            
            # Keep only last 20 tool calls
            if len(self.debug_storage["tool_calls"]) > 20:
                self.debug_storage["tool_calls"].pop(0)
                
            logger.info(f"[DEBUG_CALLBACK] Captured tool call: {tool_name}")
            
        except Exception as e:
            logger.error(f"[DEBUG_CALLBACK] Error capturing tool call: {e}", exc_info=True)
    
    def capture_crew_output(self, output: str):
        """Capture CrewAI execution output."""
        try:
            if output and output.strip():
                self.crew_output_buffer.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "output": output,
                    "message_id": self.current_message_id
                })
                
                # Parse for tool calls
                self._parse_tool_output(output)
                
        except Exception as e:
            logger.error(f"[DEBUG_CALLBACK] Error capturing crew output: {e}", exc_info=True)
    
    def _parse_tool_output(self, output: str):
        """Parse crew output for tool calls and results."""
        # Pattern: [TOOL CALL] tool_name(args) - Description
        tool_call_pattern = r'\[TOOL CALL\] (\w+)\((.*?)\) - (.*)'
        tool_result_pattern = r'\[TOOL RESULT\] (\w+)\(\) - (.*)'
        tool_error_pattern = r'\[TOOL ERROR\] (\w+)\(\) - (.*)'
        
        for match in re.finditer(tool_call_pattern, output):
            tool_name = match.group(1)
            tool_args = match.group(2)
            description = match.group(3)
            
            # Try to parse args
            try:
                # Simple arg parsing - this could be enhanced
                if tool_args:
                    # For now, store as string
                    tool_input = {"raw_args": tool_args, "description": description}
                else:
                    tool_input = {"description": description}
            except:
                tool_input = {"raw_args": tool_args, "description": description}
            
            # Store pending tool call
            self.pending_tool_calls[tool_name] = {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Check for results
        for match in re.finditer(tool_result_pattern, output):
            tool_name = match.group(1)
            result = match.group(2)
            
            if tool_name in self.pending_tool_calls:
                # Complete the tool call
                pending = self.pending_tool_calls.pop(tool_name)
                self.capture_tool_call(
                    tool_name=tool_name,
                    tool_input=pending["tool_input"],
                    tool_output=result
                )
        
        # Check for errors
        for match in re.finditer(tool_error_pattern, output):
            tool_name = match.group(1)
            error = match.group(2)
            
            if tool_name in self.pending_tool_calls:
                # Complete with error
                pending = self.pending_tool_calls.pop(tool_name)
                self.capture_tool_call(
                    tool_name=tool_name,
                    tool_input=pending["tool_input"],
                    error=error
                )
    
    def finalize(self):
        """Finalize capture for this message."""
        # Store any accumulated crew output
        if self.crew_output_buffer:
            self.debug_storage["crew_output"].extend(self.crew_output_buffer)
            
            # Keep only last 10 crew outputs
            if len(self.debug_storage["crew_output"]) > 10:
                self.debug_storage["crew_output"] = self.debug_storage["crew_output"][-10:]