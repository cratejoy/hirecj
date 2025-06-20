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
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    
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
        
        # Validate we have a current message_id
        if not self.current_message_id:
            logger.warning(f"[DEBUG_CALLBACK] No current_message_id set, skipping prompt capture")
            return
            
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
    
    def _extract_usage_with_details(self, response_obj: Any, kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract usage information including thinking token details."""
        if not hasattr(response_obj, 'usage') or not response_obj.usage:
            return None
        
        # Get base usage dict
        usage_dict = response_obj.usage.dict()
        
        # Check for completion_tokens_details (o1 models)
        if hasattr(response_obj.usage, 'completion_tokens_details') and response_obj.usage.completion_tokens_details:
            details = response_obj.usage.completion_tokens_details
            usage_dict['completion_tokens_details'] = {
                'reasoning_tokens': getattr(details, 'reasoning_tokens', 0),
                'output_tokens': getattr(details, 'output_tokens', 0)
            }
            logger.info(f"[DEBUG_CALLBACK] Captured thinking tokens: reasoning={usage_dict['completion_tokens_details']['reasoning_tokens']}, output={usage_dict['completion_tokens_details']['output_tokens']}")
        
        return usage_dict
    
    def _extract_thinking_content(self, content: str) -> Dict[str, str]:
        """Extract thinking sections from CrewAI agent output."""
        if not content:
            return {"thinking_content": None, "clean_content": None}
        
        logger.info(f"[DEBUG_CALLBACK] _extract_thinking_content called with content length: {len(content)}")
        logger.debug(f"[DEBUG_CALLBACK] Content preview: {content[:100]}...")
        
        # ALL content from LLM responses during CrewAI execution is thinking/reasoning
        # The clean response comes from crew.kickoff() result, not from parsing LLM responses
        return {
            "thinking_content": content,  # The entire content IS thinking
            "clean_content": None  # Clean content comes from crew.kickoff()
        }
    
    def log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: Any, end_time: Any) -> None:
        """Capture the raw API response including tool calls."""
        logger.info(f"[DEBUG_CALLBACK] log_success_event called for message {self.current_message_id}")
        logger.info(f"[DEBUG_CALLBACK] Response object type: {type(response_obj)}")
        
        # Validate we have a current message_id
        if not self.current_message_id:
            logger.warning(f"[DEBUG_CALLBACK] No current_message_id set, skipping response capture")
            return
            
        try:
            # Convert times to float seconds if they're datetime objects
            if hasattr(start_time, 'timestamp'):
                start_time = start_time.timestamp()
            if hasattr(end_time, 'timestamp'):
                end_time = end_time.timestamp()
            duration = end_time - start_time
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
                "duration": duration,
                "model": response_obj.model if hasattr(response_obj, 'model') else kwargs.get('model'),
                "usage": self._extract_usage_with_details(response_obj, kwargs),
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
            
            # Extract thinking/reasoning content from the response
            thinking_content = None
            if hasattr(response_obj, 'choices') and response_obj.choices:
                choice = response_obj.choices[0]
                
                # Extract thinking content from CrewAI's ReAct pattern
                if response_data["choices"] and len(response_data["choices"]) > 0:
                    first_choice = response_data["choices"][0]
                    if first_choice["message"] and first_choice["message"]["content"]:
                        content = first_choice["message"]["content"]
                        extracted = self._extract_thinking_content(content)
                        
                        # Add thinking content to response data
                        if extracted["thinking_content"]:
                            response_data["thinking_content"] = extracted["thinking_content"]
                            response_data["clean_content"] = extracted["clean_content"]
            
            # Store in debug storage
            self.debug_storage["llm_responses"].append(response_data)
            
            # Keep only last 10 responses
            if len(self.debug_storage["llm_responses"]) > 10:
                self.debug_storage["llm_responses"].pop(0)
            
            # Update timing
            if "last_response_time" not in self.debug_storage["timing"]:
                self.debug_storage["timing"]["last_response_time"] = duration
            else:
                # Calculate running average
                prev_avg = self.debug_storage["timing"].get("avg_response_time", duration)
                count = self.debug_storage["timing"].get("response_count", 1)
                new_avg = (prev_avg * count + duration) / (count + 1)
                self.debug_storage["timing"]["avg_response_time"] = new_avg
                self.debug_storage["timing"]["response_count"] = count + 1
                self.debug_storage["timing"]["last_response_time"] = duration
                
            logger.info(f"[DEBUG_CALLBACK] Captured response for message {self.current_message_id} - {len(tool_calls)} tool calls, duration: {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"[DEBUG_CALLBACK] Error capturing response: {e}", exc_info=True)
    
    def capture_tool_call(self, tool_name: str, tool_input: Dict[str, Any], tool_output: Any = None, 
                         error: Optional[str] = None, start_time: Optional[float] = None,
                         end_time: Optional[float] = None, duration: Optional[float] = None):
        """Manually capture tool calls from tool execution logs."""
        # Validate we have a current message_id
        if not self.current_message_id:
            logger.warning(f"[DEBUG_CALLBACK] No current_message_id set, skipping tool call capture for {tool_name}")
            return
            
        try:
            tool_capture = ToolCallCapture(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                error=error,
                start_time=start_time,
                end_time=end_time,
                duration=duration
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
    
    def capture_final_response(self, response: str):
        """Capture the final response from crew.kickoff()."""
        try:
            if not self.current_message_id:
                logger.warning("[DEBUG_CALLBACK] No current message ID when capturing final response")
                return
            
            # Store the final response with the current message
            final_response_data = {
                "message_id": self.current_message_id,
                "final_response": response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add to a new storage key for final responses
            if "final_responses" not in self.debug_storage:
                self.debug_storage["final_responses"] = []
            
            self.debug_storage["final_responses"].append(final_response_data)
            
            # Keep only last 10 final responses
            if len(self.debug_storage["final_responses"]) > 10:
                self.debug_storage["final_responses"].pop(0)
            
            logger.info(f"[DEBUG_CALLBACK] Captured final response for message {self.current_message_id} - {len(response)} chars")
            
        except Exception as e:
            logger.error(f"[DEBUG_CALLBACK] Error capturing final response: {e}", exc_info=True)
    
    def capture_grounding(self, namespace: str, query: str, results: str, 
                         results_count: int = 0, cache_hit: bool = False,
                         error: Optional[str] = None):
        """Capture knowledge base grounding operations."""
        # Validate we have a current message_id
        if not self.current_message_id:
            logger.warning(f"[DEBUG_CALLBACK] No current_message_id set, skipping grounding capture for {namespace}")
            return
            
        try:
            grounding_data = {
                "message_id": self.current_message_id,
                "namespace": namespace,
                "query": query,
                "results_preview": results,  # Full results, no limit
                "results_count": results_count,
                "cache_hit": cache_hit,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add to debug storage
            if "grounding" not in self.debug_storage:
                self.debug_storage["grounding"] = []
                
            self.debug_storage["grounding"].append(grounding_data)
            
            # Keep only last 20 grounding operations
            if len(self.debug_storage["grounding"]) > 20:
                self.debug_storage["grounding"].pop(0)
                
            logger.info(f"[DEBUG_CALLBACK] Captured grounding for {namespace}: query='{query[:50]}...', "
                       f"results_count={results_count}, cache_hit={cache_hit}")
            
        except Exception as e:
            logger.error(f"[DEBUG_CALLBACK] Error capturing grounding: {e}", exc_info=True)
    
    def finalize(self):
        """Finalize capture for this message."""
        # Store any accumulated crew output
        if self.crew_output_buffer:
            self.debug_storage["crew_output"].extend(self.crew_output_buffer)
            
            # Keep only last 10 crew outputs
            if len(self.debug_storage["crew_output"]) > 10:
                self.debug_storage["crew_output"] = self.debug_storage["crew_output"][-10:]
        
        # Clear the current message ID to prevent this callback from capturing future data
        logger.info(f"[DEBUG_CALLBACK] Finalizing and clearing message_id {self.current_message_id}")
        self.current_message_id = None