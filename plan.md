# Message Details View Implementation Plan

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Every decision should make the code simpler, not more complex
2. **No Cruft**: Remove all redundant code, validation, and unnecessary complexity
3. **Break It & Fix It Right**: No backwards compatibility shims - make breaking changes and migrate properly
4. **Long-term Elegance**: Choose performant, compiler-enforced solutions that prevent subtle bugs
5. **Backend-Driven**: Let the backend handle complexity, frontend should be a thin client
6. **Single Source of Truth**: One pattern, one way to do things, no alternatives
7. **No Over-Engineering**: Design for current needs only - no hypothetical features, no "maybe later" code
8. **Thoughtful Logging & Instrumentation**: We value visibility into system behavior with appropriate log levels

## Overview
Implement a detailed message view for the playground that shows the full LLM prompt, response, tool calls, and metadata when clicking the "📋 Details" button on CJ agent messages.

## Current Implementation Status
✅ **Phase 1 Complete**: Created static UI with hardcoded data
- Added Details button to agent messages in PlaygroundView
- Created MessageDetailsView component with hardcoded example data
- Implemented split-view layout matching the design doc
- Added animations, backdrop, and keyboard support

✅ **Phase 2 Complete**: Connected to real LLM data
- Created DebugCallback class extending LiteLLM's CustomLogger
- Integrated with message_processor to capture raw API calls
- Added message_id to link UI messages with debug data
- Updated protocol with minimal changes
- Frontend requests and displays real debug data
- Shows prompt, response, tool calls, and timing information

## Existing Infrastructure Discovery

After deep analysis of the merged code, we have MORE infrastructure than initially thought:

### 1. **LiteLLM Integration**
- `main.py` already enables `LITELLM_LOG=DEBUG` and `LITELLM_VERBOSE=true`
- `ExtendedAgent` manages LiteLLM callbacks in `execute_task()`
- `ConversationThinkingCallback` shows how to create custom loggers

### 2. **Debug Storage Structure**
`Session.debug_data` already exists with:
```python
{
    "llm_prompts": [],      # Ready for LLM prompts
    "llm_responses": [],    # Ready for LLM responses  
    "tool_calls": [],       # Ready for tool execution logs
    "crew_output": [],      # Ready for CrewAI output
    "timing": {}            # Ready for performance metrics
}
```

### 3. **Debug Request Infrastructure**
- Protocol already supports: `llm_prompts`, `llm_responses`, `tool_calls`, `crew_output`, `timing`
- `utility_handlers.py` already looks for this data in `session.debug_data`
- Just need to populate the data!

### 4. **Tool Logging Pattern**
All tools already log with consistent patterns:
- `[TOOL CALL] tool_name(args) - Description`
- `[TOOL RESULT] tool_name() - Result summary`
- `[TOOL ERROR] tool_name() - Error details`

### 5. **CustomLogger Methods Available**
From LiteLLM's CustomLogger base class:
- `log_pre_api_call(model, messages, kwargs)` - Perfect for capturing prompts!
- `log_success_event(kwargs, response_obj, start_time, end_time)` - For responses
- `log_stream_event()` - For streaming responses
- `log_failure_event()` - For error handling

## Phase 2: Connect to Real Data

### Phase 2.1: Create Debug Capture Infrastructure

#### Step 1: Create Comprehensive Debug Callback
**New File**: `agents/app/services/debug_callback.py`

```python
from litellm.integrations.custom_logger import CustomLogger
from typing import Dict, Any, Optional, List
import json
from datetime import datetime
from shared.logging_config import get_logger
from dataclasses import dataclass, asdict
import re

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
```

#### Step 2: Create Tool Capture Logger
**New File**: `agents/app/services/tool_logger.py`

```python
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
```

#### Step 3: Hook Into Message Processor
**File**: `agents/app/services/message_processor.py`

```python
# In _get_cj_response method, before creating agent

# Generate unique message ID
import uuid
message_id = f"msg_{uuid.uuid4().hex[:8]}"

# Create debug callback
from app.services.debug_callback import DebugCallback
from app.services.tool_logger import ToolLogger
debug_callback = DebugCallback(session.id, session.debug_data)
debug_callback.set_message_id(message_id)

# Set debug callback for tool logger
ToolLogger.set_debug_callback(debug_callback)

# Hook into stdout to capture crew output
import io
import sys
original_stdout = sys.stdout
capture_buffer = io.StringIO()

class TeeOutput:
    def __init__(self, *outputs):
        self.outputs = outputs
    
    def write(self, data):
        for output in self.outputs:
            output.write(data)
        # Also capture to debug callback
        if debug_callback:
            debug_callback.capture_crew_output(data)
    
    def flush(self):
        for output in self.outputs:
            if hasattr(output, 'flush'):
                output.flush()

sys.stdout = TeeOutput(original_stdout, capture_buffer)

# Add to litellm callbacks using the ExtendedAgent pattern
original_callbacks = []
if hasattr(litellm, 'callbacks'):
    original_callbacks = litellm.callbacks.copy()
    litellm.callbacks.append(debug_callback)

try:
    # Create agent with message ID stored
    cj_agent = create_cj_agent(...)
    
    # ... existing crew execution code ...
    
    # After getting response, include message_id
    if isinstance(response, dict):
        response["message_id"] = message_id
    else:
        # Convert to dict format with message_id
        response = {
            "type": "message_with_ui",
            "content": response,
            "ui_elements": [],
            "message_id": message_id
        }
    
finally:
    # Restore stdout
    sys.stdout = original_stdout
    
    # Finalize debug callback
    debug_callback.finalize()
    
    # Clear tool logger callback
    ToolLogger.set_debug_callback(None)
    
    # Restore litellm callbacks
    if hasattr(litellm, 'callbacks'):
        litellm.callbacks = original_callbacks
```

### Phase 2.2: Minimal Protocol Updates

#### Step 1: Add message_id to CJMessageData
**File**: `shared/protocol/models.py`

```python
class CJMessageData(BaseModel):
    content: str
    factCheckStatus: Optional[str] = "available"
    timestamp: datetime
    ui_elements: Optional[List[Dict[str, Any]]] = None
    message_id: Optional[str] = None  # NEW: Unique ID for debug lookups
```

#### Step 2: Add message_details to DebugRequestData
**File**: `shared/protocol/models.py`

```python
class DebugRequestData(BaseModel):
    type: Literal["snapshot", "session", "state", "metrics", "prompts", 
                   "llm_prompts", "llm_responses", "tool_calls", "crew_output", 
                   "timing", "message_details"]  # Add message_details
    message_id: Optional[str] = None  # NEW: For message-specific requests
```

#### Step 3: Update Debug Handler
**File**: `agents/app/platforms/web/utility_handlers.py`

Add to `handle_debug_request` method:
```python
if debug_type == "message_details":
    message_id = message.data.get("message_id")
    if not message_id:
        debug_response = DebugResponseMsg(
            type="debug_response",
            data={"error": "message_id required for message_details request"}
        )
        await self.platform.send_validated_message(websocket, debug_response)
        return
    
    # Aggregate all debug data for this message
    debug_data["message_id"] = message_id
    
    # Find matching prompt
    for prompt in session.debug_data.get("llm_prompts", []):
        if prompt.get("message_id") == message_id:
            debug_data["prompt"] = prompt
            break
    
    # Find matching response
    for response in session.debug_data.get("llm_responses", []):
        if response.get("message_id") == message_id:
            debug_data["response"] = response
            break
    
    # Find matching tool calls
    debug_data["tool_calls"] = [
        tc for tc in session.debug_data.get("tool_calls", [])
        if tc.get("message_id") == message_id
    ]
    
    # Find matching crew output
    debug_data["crew_output"] = [
        co for co in session.debug_data.get("crew_output", [])
        if co.get("message_id") == message_id
    ]
```

#### Step 4: Generate TypeScript Types
```bash
cd shared/protocol
./generate.sh
```

### Phase 2.3: Frontend Integration
**Goal**: Update frontend to request and display debug data

#### Step 1: Update WebSocket Hook
**File**: `editor/src/hooks/usePlaygroundChat.ts`

```typescript
// Add to message storage
interface CJMessageMsg {
  type: "cj_message";
  data: {
    content: string;
    timestamp: string;
    factCheckStatus?: string | null;
    ui_elements?: any[] | null;
    message_id?: string | null;  // NEW
  };
}

// Add debug request method
const requestMessageDetails = useCallback((messageId: string) => {
  if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
    console.error('WebSocket not connected');
    return;
  }
  
  const msg: DebugRequestMsg = {
    type: 'debug_request',
    data: {
      type: 'message_details',
      message_id: messageId
    }
  };
  
  ws.current.send(JSON.stringify(msg));
}, []);

// Handle debug responses
case 'debug_response':
  const debugData = msg.data;
  if (debugData.message_id) {
    // Store or emit debug data for the message
    console.log('Debug data received:', debugData);
  }
  break;
```

#### Step 2: Update MessageDetailsView
**File**: `editor/src/components/playground/MessageDetailsView.tsx`

```typescript
interface MessageDetailsViewProps {
  isOpen: boolean;
  onClose: () => void;
  messageId?: string;
  onRequestDetails?: (messageId: string) => void;
}

// Add loading state and data fetching
const [loading, setLoading] = useState(false);
const [debugData, setDebugData] = useState<any>(null);

useEffect(() => {
  if (isOpen && messageId && onRequestDetails) {
    setLoading(true);
    onRequestDetails(messageId);
  }
}, [isOpen, messageId, onRequestDetails]);

// Display real data when available
if (loading && !debugData) {
  return <LoadingSpinner />;
}

// Use debugData.prompt.messages for left panel
// Use debugData.response for right panel
```

### Phase 2.4: Testing & Validation
**Goal**: Ensure everything works correctly

#### Test Plan:
1. **Basic Message Flow**
   - Send a simple message
   - Click Details button
   - Verify prompt and response display correctly

2. **Tool Calling Messages**
   - Send message that triggers tool use
   - Verify tool definitions in prompt
   - Verify tool calls and outputs in response

3. **Edge Cases**
   - Large prompts (context with many messages)
   - Multiple rapid messages
   - Network errors
   - Missing debug data

4. **Performance Validation**
   - Measure impact on message latency
   - Check memory usage with debug storage
   - Verify cleanup of old debug data

### Implementation Summary

This implementation leverages existing infrastructure:
- LiteLLM callbacks for capturing raw API data
- Session debug storage already in place
- Debug request handler framework exists
- Protocol extension is backwards compatible

The approach is elegant because:
1. **Non-intrusive**: Only captures data when debug storage exists
2. **Performant**: Uses existing callback system, no additional API calls
3. **Simple**: Reuses existing patterns and infrastructure
4. **Complete**: Captures all raw LLM data including headers and metadata

## Next Steps

### Phase 3: Tool Integration Enhancement
- Enhance tool execution capture with @log_tool_execution decorator
- Parse tool arguments more intelligently
- Capture tool execution timing

### Phase 4: UI Polish
- Add syntax highlighting for JSON/code in prompts
- Add copy buttons for prompts/responses
- Add search/filter within message details
- Show token usage visualization

### Phase 5: Performance & Persistence
- Add caching layer for debug data
- Implement debug data persistence to database
- Add export functionality (JSON/Markdown)

