import re
import json
from typing import List, Dict, Any, Union
from datetime import datetime
from crewai.llm import LLM
from crewai.llms.base_llm import BaseLLM
from app.services.thinking_token_manager import thinking_token_manager
from shared.protocol.models import ThinkingToken
import logging

logger = logging.getLogger(__name__)


def extract_thinking_tokens_from_response(response: str) -> tuple[str, List[ThinkingToken]]:
    """Extract thinking tokens from LLM response.
    
    Looks for patterns like:
    - <thinking>...</thinking>
    - [REASONING] ... [/REASONING]
    - Tool selection thoughts before "Action:"
    
    Returns cleaned response and extracted tokens.
    """
    thinking_tokens = []
    cleaned_response = response
    
    # Extract <thinking> tags
    thinking_pattern = r'<thinking>(.*?)</thinking>'
    thinking_matches = re.finditer(thinking_pattern, response, re.DOTALL)
    for match in thinking_matches:
        content = match.group(1).strip()
        if content:
            thinking_tokens.append(ThinkingToken(
                timestamp=datetime.now(),
                content=content,
                token_type="reasoning",
                metadata={"source": "thinking_tag"}
            ))
            cleaned_response = cleaned_response.replace(match.group(0), "")
    
    # Extract [REASONING] blocks
    reasoning_pattern = r'\[REASONING\](.*?)\[/REASONING\]'
    reasoning_matches = re.finditer(reasoning_pattern, response, re.DOTALL)
    for match in reasoning_matches:
        content = match.group(1).strip()
        if content:
            thinking_tokens.append(ThinkingToken(
                timestamp=datetime.now(),
                content=content,
                token_type="reasoning",
                metadata={"source": "reasoning_block"}
            ))
            cleaned_response = cleaned_response.replace(match.group(0), "")
    
    # Extract pre-action thoughts (text before "Action:" or "Thought:")
    action_pattern = r'^(.*?)(?:Action:|Thought:)'
    action_match = re.search(action_pattern, cleaned_response, re.DOTALL)
    if action_match and action_match.group(1).strip():
        pre_action_text = action_match.group(1).strip()
        # Only capture if it's substantive (more than a few words)
        if len(pre_action_text.split()) > 5:
            thinking_tokens.append(ThinkingToken(
                timestamp=datetime.now(),
                content=pre_action_text,
                token_type="planning",
                metadata={"source": "pre_action"}
            ))
    
    return cleaned_response, thinking_tokens


def capture_tool_selection_thinking(response: str) -> List[ThinkingToken]:
    """Capture thinking related to tool selection."""
    thinking_tokens = []
    
    # Look for tool selection patterns
    tool_pattern = r'(?:I need to|I should|I will|Let me)\s+(?:use|call|invoke)\s+(\w+)'
    tool_matches = re.finditer(tool_pattern, response, re.IGNORECASE)
    for match in tool_matches:
        thinking_tokens.append(ThinkingToken(
            timestamp=datetime.now(),
            content=match.group(0),
            token_type="tool_selection",
            metadata={"tool": match.group(1)}
        ))
    
    return thinking_tokens


def enhanced_get_llm_response(
    llm: Union[LLM, BaseLLM],
    messages: List[Dict[str, str]],
    callbacks: List[Any],
    printer: Any,
) -> str:
    """Enhanced version of get_llm_response that captures thinking tokens."""
    
    
    # Import here to avoid circular dependency
    from app.services.tool_execution_monitor import tool_execution_monitor
    
    # Start capturing thinking tokens
    thinking_token_manager.start_capture()
    
    try:
        # Analyze the prompt to add context
        if messages:
            last_message = messages[-1].get("content", "")
            if "tool" in last_message.lower() or "action" in last_message.lower():
                thinking_token_manager.add_token(
                    content=f"Processing request: {last_message[:100]}...",
                    token_type="context",
                    metadata={"stage": "prompt_analysis"}
                )
        
        # Call the original LLM
        answer = llm.call(
            messages,
            callbacks=callbacks,
        )
        
        if not answer:
            printer.print(
                content="Received None or empty response from LLM call.",
                color="red",
            )
            raise ValueError("Invalid response from LLM call - None or empty.")
        
        # Extract thinking tokens from the response
        cleaned_answer, extracted_tokens = extract_thinking_tokens_from_response(answer)
        
        # Add extracted tokens to the manager
        for token in extracted_tokens:
            thinking_token_manager.add_token(
                content=token.content,
                token_type=token.token_type,
                metadata=token.metadata
            )
        
        # Capture tool selection thinking
        tool_tokens = capture_tool_selection_thinking(answer)
        
        for token in tool_tokens:
            thinking_token_manager.add_token(
                content=token.content,
                token_type=token.token_type,
                metadata=token.metadata
            )
        
        # Check if answer contains tool invocation pattern
        if "Action:" in answer and "Action Input:" in answer:
            # Extract tool name and input
            import re
            action_match = re.search(r'Action:\s*(.+)', answer)
            input_match = re.search(r'Action Input:\s*(.+)', answer, re.DOTALL)
            
            if action_match:
                tool_name = action_match.group(1).strip()
                tool_input = {}
                
                if input_match:
                    try:
                        # Try to parse as JSON
                        input_text = input_match.group(1).strip()
                        # Find JSON object in the input
                        json_match = re.search(r'\{.*\}', input_text, re.DOTALL)
                        if json_match:
                            tool_input = json.loads(json_match.group(0))
                    except:
                        tool_input = {"raw": input_match.group(1).strip()}
                
                # Notify tool monitor about tool start
                tool_execution_monitor.on_tool_start(tool_name, tool_input)
        
        
        return answer  # Return original answer to maintain compatibility
        
    except Exception as e:
        printer.print(
            content=f"Error during LLM call: {e}",
            color="red",
        )
        raise e
    finally:
        # Don't stop capture here - let the message processor handle it
        pass


# Monkey patch the original function
import crewai.utilities.agent_utils

# Store original for reference
original_get_llm_response = crewai.utilities.agent_utils.get_llm_response

# Also patch the LLM.call method since CrewAI might use it directly
try:
    from crewai.llm import LLM
    original_llm_call = LLM.call
    
    def enhanced_llm_call(self, messages, *args, **kwargs):
        """Enhanced LLM.call that captures thinking tokens."""
        # Start capture if not already started
        if not thinking_token_manager.is_capturing():
            thinking_token_manager.start_capture()
        
        # Call original
        result = original_llm_call(self, messages, *args, **kwargs)
        
        # Extract thinking patterns
        if result:
            cleaned_result, extracted_tokens = extract_thinking_tokens_from_response(str(result))
            
            # Add tokens to manager
            for token in extracted_tokens:
                thinking_token_manager.add_token(
                    content=token.content,
                    token_type=token.token_type,
                    metadata=token.metadata
                )
        
        return result
    
    # Apply the patch
    LLM.call = enhanced_llm_call
    logger.info("[THINKING_TOKEN_CAPTURE] Successfully patched LLM.call method")
    
except Exception as e:
    logger.error(f"[THINKING_TOKEN_CAPTURE] Failed to patch LLM.call: {e}")
    raise

# Apply the patch
crewai.utilities.agent_utils.get_llm_response = enhanced_get_llm_response