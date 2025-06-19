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

✅ **Phase 2 Complete**: Connected to real LLM data with clean implementation
- Phase 2.1 ✅ **COMPLETE**: Implemented cleaner callback registration
  - Register DebugCallback directly with `litellm.input_callback` and `litellm.success_callback`
  - No modifications to CrewAI or venv needed
  - Proper cleanup in try/finally block
  - `log_pre_api_call` is being invoked and capturing prompts successfully
- Phase 2.2 ✅ **COMPLETE**: Protocol updates implemented
  - Added `message_id` to `CJMessageData`
  - Added `message_details` to `DebugRequestData` type literal
  - Generated TypeScript types successfully
- Phase 2.3 Backend ✅ **COMPLETE**: Backend integration working
  - `utility_handlers.py` handles `message_details` requests
  - Message-specific debug data aggregation implemented
  - Workflow handlers include `message_id` in all responses
- Phase 2.3 Frontend ✅ **COMPLETE**: Frontend fully implemented
  - `usePlaygroundChat` hook updated with `requestMessageDetails` method
  - `MessageDetailsView` requests and displays real debug data
  - Loading states and error handling implemented
  - Promise-based request/response pattern working

**🚨 DISCOVERY**: CrewAI sets callbacks wrong! It only sets `litellm.callbacks` but LiteLLM actually uses:
- `litellm.input_callback` for pre-API calls (where `log_pre_api_call` is invoked) ✅ WORKING
- `litellm.success_callback` for post-API success (where `log_success_event` is invoked) ⚠️ NOT BEING CALLED

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

### ❌ Original Approach (Global Callback Manipulation)
We implemented this but it's messy:
- Manipulates global `litellm.callbacks` 
- Requires saving/restoring original callbacks
- Affects ALL LiteLLM calls globally
- Complex cleanup logic

### ✅ Better Approach (Use LiteLLM's Callback Lists Directly)
Instead of modifying CrewAI or using global manipulation, we can register our callbacks directly:

```python
# In message_processor.py _get_cj_response method
import litellm

# Create debug callback
debug_callback = DebugCallback(session.id, session.debug_data)
debug_callback.set_message_id(message_id)

# Register with LiteLLM's actual callback lists
if debug_callback not in litellm.input_callback:
    litellm.input_callback.append(debug_callback)
if debug_callback not in litellm.success_callback:
    litellm.success_callback.append(debug_callback)

# Set debug callback for tool logger
ToolLogger.set_debug_callback(debug_callback)

# Create agent (no need to pass debug_callback anymore!)
cj_agent = create_cj_agent(
    merchant_name=session.conversation.merchant_name,
    scenario_name=session.conversation.scenario_name,
    # ... other params - NO debug_callback needed!
)

# ... existing crew execution code ...

# Clean up callbacks after processing
try:
    # ... get response ...
finally:
    # Remove callbacks to prevent memory leaks
    if debug_callback in litellm.input_callback:
        litellm.input_callback.remove(debug_callback)
    if debug_callback in litellm.success_callback:
        litellm.success_callback.remove(debug_callback)
    debug_callback.finalize()
    ToolLogger.set_debug_callback(None)
```

This is MUCH cleaner because:
- No modifications to CrewAI or venv needed
- Works with existing agent creation code
- Properly scoped to message processing
- Clean registration and removal
- Uses LiteLLM's intended callback mechanism

### Phase 2.1 (Revised): Register Callbacks with LiteLLM Directly

#### Step 1: Keep the DebugCallback as-is
**File**: `agents/app/services/debug_callback.py` (no changes needed)

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

#### Step 2: Update Message Processor
**File**: `agents/app/services/message_processor.py`

Update the `_get_cj_response` method:
```python
# In _get_cj_response method

# Generate unique message ID
import uuid
import litellm
message_id = f"msg_{uuid.uuid4().hex[:8]}"

# Create debug callback
from app.services.debug_callback import DebugCallback
from app.services.tool_logger import ToolLogger
debug_callback = DebugCallback(session.id, session.debug_data)
debug_callback.set_message_id(message_id)

# Register with LiteLLM's callback lists
if debug_callback not in litellm.input_callback:
    litellm.input_callback.append(debug_callback)
if debug_callback not in litellm.success_callback:
    litellm.success_callback.append(debug_callback)

# Set debug callback for tool logger
ToolLogger.set_debug_callback(debug_callback)

try:
    # Create agent (no debug_callback parameter needed!)
    cj_agent = create_cj_agent(
        merchant_name=session.conversation.merchant_name,
        scenario_name=session.conversation.scenario_name,
        # ... other params - NO debug_callback!
    )

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
    
    return response

finally:
    # Clean up callbacks
    if debug_callback in litellm.input_callback:
        litellm.input_callback.remove(debug_callback)
    if debug_callback in litellm.success_callback:
        litellm.success_callback.remove(debug_callback)
    debug_callback.finalize()
    ToolLogger.set_debug_callback(None)
```

That's it! No agent modifications needed, just register and clean up the callbacks.

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

The cleaner implementation is NOW IN PRODUCTION:
- ✅ DebugCallback registered directly with LiteLLM's callback lists
- ✅ No CrewAI or venv modifications needed
- ✅ Works with existing agent code unchanged
- ✅ Clean registration and cleanup pattern in try/finally
- ✅ Prompts are being captured with correct message IDs
- ⚠️ Responses not being captured (log_success_event not invoked)

The approach is superior because:
1. **Clean**: No third-party code modifications
2. **Scoped**: Callbacks are registered per message and cleaned up
3. **Simple**: Uses LiteLLM's documented callback mechanism
4. **Maintainable**: All changes in our code, no monkey-patching

### Test Results
- ✅ Callbacks register properly with LiteLLM
- ✅ `log_pre_api_call` is invoked and captures prompts
- ✅ Message IDs are included in all responses
- ⚠️ `log_success_event` is NOT being invoked by LiteLLM
- ⚠️ Tool calls are not being captured (depends on log_success_event)

## Implementation Complete!

All phases of the Message Details View have been successfully implemented:
- ✅ Phase 1: Static UI with hardcoded data
- ✅ Phase 2: Connected to real LLM data with clean callback registration
- ✅ Phase 3: Fixed response capture with CompositeCallback
- ✅ Frontend Integration: Full request/response flow working

The feature is now production-ready and captures:
- Full LLM prompts with messages, tools, and parameters
- Complete LLM responses with content, tool calls, and usage stats
- Tool execution logs (pending decorator implementation)
- Performance metrics and timing data

## Future Enhancements (Optional)

### Cleanup Tasks
- ✅ COMPLETE: The `debug_callback` parameter was never added to function signatures (good!)
- ✅ COMPLETE: `log_success_event` issue resolved with CompositeCallback in Phase 3

### Phase 2.3: Frontend Integration ✅ **COMPLETE**
- ✅ Updated `usePlaygroundChat` hook:
  - Added `requestMessageDetails` method with promise-based pattern
  - Handles `debug_response` messages
  - Stores debug data by message ID
- ✅ Updated `MessageDetailsView`:
  - Accepts `messageId` and `onRequestDetails` props
  - Requests debug data when opened
  - Displays real prompt/response data
  - Has loading and error states

### ✅ Phase 3: Fix Response Capture (COMPLETE)

#### Problem Analysis
The root cause was identified:
1. We register DebugCallback with `litellm.success_callback` ✅
2. ExtendedAgent adds thinking callback to `litellm.success_callback` ✅  
3. CrewAI's Agent creates executor with `callbacks=[TokenCalcHandler(...)]`
4. CrewAI passes these callbacks to the LLM, which uses them instead of the global callbacks

#### Solution Implemented: Override create_agent_executor in ExtendedAgent
Successfully intercepted executor creation in our ExtendedAgent subclass:

1. **Created CompositeCallback class** that forwards calls to multiple callbacks
2. **Overrode create_agent_executor** to capture existing callbacks before parent creates executor
3. **Merged callbacks** using CompositeCallback to ensure both TokenCalcHandler and DebugCallback receive events

```python
# CompositeCallback forwards all events to multiple handlers
class CompositeCallback(CustomLogger):
    def log_success_event(self, *args, **kwargs):
        for cb in self.callbacks:
            if hasattr(cb, 'log_success_event'):
                cb.log_success_event(*args, **kwargs)

# ExtendedAgent preserves our callbacks when creating executor
def create_agent_executor(self, tools=None, task=None):
    # Capture existing callbacks
    existing_callbacks = list(litellm.success_callback)
    
    # Call parent (which sets callbacks=[TokenCalcHandler])
    super().create_agent_executor(tools, task)
    
    # Replace with composite that includes all callbacks
    all_callbacks = self.agent_executor.callbacks + existing_callbacks
    self.agent_executor.callbacks = [CompositeCallback(all_callbacks)]
```

#### Test Results
✅ **Both prompt and response are now captured successfully!**
- CompositeCallback receives and forwards log_success_event
- DebugCallback captures full response with model, duration, and content
- TokenCalcHandler still works (no regression)
- Clean solution at the agent level, no CrewAI patching needed

Example output:
```
Response captured: ✅
  Model: o3-mini-2025-01-31
  Duration: PT3.448383S
  Content preview: As CJ, I'd say: "Hey there! I actually focus on e-commerce support...
```

### Phase 3.5: Capture Thinking Tokens (NEW)
**Goal**: Capture thinking/reasoning tokens from models that support them (e.g., o1 models)

#### Implementation Steps:

1. **Enhance Debug Callback to Capture Detailed Token Usage**
   - Update `log_success_event` in `debug_callback.py` to check for `completion_tokens_details`
   - Extract `reasoning_tokens` and `output_tokens` separately
   - Store thinking content if exposed by the model

```python
# In debug_callback.py log_success_event method
if hasattr(response_obj, 'usage') and response_obj.usage:
    usage_dict = response_obj.usage.dict()
    
    # Check for detailed token breakdown (o1 models)
    if hasattr(response_obj.usage, 'completion_tokens_details'):
        details = response_obj.usage.completion_tokens_details
        usage_dict['completion_tokens_details'] = {
            'reasoning_tokens': getattr(details, 'reasoning_tokens', 0),
            'output_tokens': getattr(details, 'output_tokens', 0)
        }
```

2. **Capture Reasoning Content**
   - Check if response includes separate reasoning content
   - Store reasoning separately from regular content
   - Handle both streaming and non-streaming responses

3. **Update Frontend Display**
   - Show reasoning tokens separately in MessageDetailsView
   - Add "Thinking Tokens" section if reasoning_tokens > 0
   - Display reasoning content in collapsible section

4. **Testing**
   - Test with o1-mini or o1-preview models
   - Verify reasoning tokens are captured
   - Ensure backward compatibility with non-reasoning models

#### Status: ⚠️ PARTIALLY COMPLETE

Implementation complete:
- ✅ Added `_extract_usage_with_details` method to capture completion_tokens_details
- ✅ Enhanced frontend to display reasoning tokens in main view
- ✅ Added thinking token count to performance metrics
- ✅ Maintains backward compatibility with non-reasoning models
- ❌ **MISSING**: Actual reasoning/thinking content (only capturing token counts)

### Phase 3.6: Capture Actual Thinking Traces ✅
**Goal**: Extract and display the CrewAI agent thinking content that's already being captured

#### 🔍 Investigation Results

**Initial Assumption**: We thought we needed to capture thinking/reasoning fields from o1 models
**Reality Discovered**: CrewAI agents already output detailed thinking traces as part of their ReAct loop!

**Current System Architecture**:
```
1. CrewAI Agent executes task
   ↓
2. Outputs "Thought:" prefixed reasoning as part of ReAct pattern
   ↓
3. LiteLLM returns full content (thoughts + actions + final response)
   ↓
4. ConversationThinkingCallback extracts and logs with [THINKING]
   ↓
5. DebugCallback stores full content in debug_data
   ↓
6. Currently: Thinking is mixed with response in the UI
```

**Key Components We Found**:
- `ConversationThinkingCallback` - Already extracts thinking for logging
- `ExtendedAgent` - Sets up thinking callbacks
- Message content includes full ReAct loop output
- Tests verify thoughts shouldn't leak to users (`internal_thoughts_boundaries.yaml`)

#### The Discovery:
We already capture thinking traces! CrewAI agents output "Thought:" prefixed content as part of their reasoning process. This is currently:
- Logged by `ConversationThinkingCallback` with [THINKING] prefix  
- Included in the regular message content in debug_callback.py
- But NOT separated out for display in the message details view
- Confirmed by test cases that explicitly check thoughts don't leak to merchants

Example of what we're already capturing:
```
Thought: I need to check the recent support tickets to understand what customers are complaining about.

Action: get_recent_tickets_from_db
Action Input: {}

Observation: [ticket data returned]

Thought: I can see several tickets about shipping delays. Let me analyze the patterns...
```

This thinking content is valuable for debugging but shouldn't be shown in the main response.

#### 🎯 Why This is Simpler Than Expected

1. **No Model-Specific Code Needed**: Works with any model CrewAI uses
2. **Data Already Flowing**: Thinking content is already in our debug responses
3. **Pattern is Consistent**: CrewAI's ReAct format is predictable
4. **Just Need Parsing**: Simply extract "Thought:" sections from existing data

#### 📊 Current Data Flow Example

When a user asks "What are our top complaints?", here's what happens:
```
1. User Message → CJ Agent
2. Agent Response (what we capture):
   "Thought: I need to check recent tickets to identify complaint patterns.
    
    Action: get_recent_tickets_from_db
    Action Input: {}
    
    Observation: [30 tickets returned...]
    
    Thought: I can see shipping delays are mentioned in 12 tickets...
    
    Based on the recent tickets, your top complaints are:
    1. Shipping delays (40% of tickets)..."

3. What user sees: Only the final part starting with "Based on..."
4. What debug view should show: The complete thinking process
```

#### Implementation Steps:

1. **Parse Thinking Content from Messages in debug_callback.py**
   ```python
   # In log_success_event, after extracting message content
   if choice.message.content:
       content = choice.message.content
       
       # Extract thinking sections (CrewAI format)
       thinking_content = []
       clean_content = []
       
       lines = content.split('\n')
       in_thought = False
       current_thought = []
       
       for line in lines:
           if line.strip().startswith('Thought:'):
               in_thought = True
               current_thought = [line[8:].strip()]  # Remove "Thought:" prefix
           elif in_thought and line.strip() and not line.strip().startswith(('Action:', 'Observation:')):
               current_thought.append(line)
           else:
               if in_thought and current_thought:
                   thinking_content.append('\n'.join(current_thought))
                   current_thought = []
                   in_thought = False
               
               # Only add non-thought lines to clean content
               if not line.strip().startswith('Thought:'):
                   clean_content.append(line)
       
       # Store both versions
       if thinking_content:
           response_data["thinking_content"] = '\n\n'.join(thinking_content)
           response_data["clean_content"] = '\n'.join(clean_content).strip()
           logger.info(f"[DEBUG_CALLBACK] Extracted {len(thinking_content)} thinking sections")
   ```

2. **Update Frontend MessageDetailsView.tsx**
   ```typescript
   {/* Agent Thinking Process */}
   {responseData.thinking_content && (
     <>
       <Separator className="my-4" />
       <div className="space-y-2">
         <div className="flex items-center justify-between">
           <h4 className="font-medium text-sm">AGENT THINKING PROCESS</h4>
           <Button
             variant="ghost"
             size="sm"
             onClick={() => copyToClipboard(responseData.thinking_content, 'thinking')}
           >
             {copiedItems.has('thinking') ? <Check /> : <Copy />}
           </Button>
         </div>
         <div className="bg-muted/50 rounded-lg p-4 max-h-96 overflow-y-auto">
           <pre className="text-xs whitespace-pre-wrap font-mono">
             <code>{responseData.thinking_content}</code>
           </pre>
         </div>
       </div>
     </>
   )}
   
   {/* Also update the displayed content to use clean_content if available */}
   <p className="text-sm whitespace-pre-wrap pr-10">
     {responseData.clean_content || choice.message.content}
   </p>
   ```

3. **Key Benefits**
   - Shows CrewAI agent's step-by-step reasoning process
   - Separates thinking from the final response shown to users
   - Helps debug agent behavior and decision making
   - Uses content we're already capturing, just displays it better

4. **Testing Strategy**
   - Test with any CrewAI agent task that requires reasoning
   - Verify "Thought:" sections are extracted correctly
   - Ensure clean_content doesn't include thinking traces
   - Check that thinking appears in dedicated UI section

#### Status: ✅ Complete

**Implementation Details**:
- Added `_extract_thinking_content` method to `debug_callback.py` that parses "Thought:" sections
- Fixed datetime handling bug in `log_success_event` (was causing TypeError with timedelta formatting)
- Updated `MessageDetailsView.tsx` to display thinking content in dedicated "AGENT THINKING PROCESS" section
- Response now shows `clean_content` (without thinking traces) when available
- Added proper logging to track thinking extraction

#### 📋 Investigation Summary

**What We Thought We Needed**:
- Special handling for o1 model thinking fields
- New API response parsing for reasoning_content
- Model-specific implementations

**What We Actually Have**:
- ✅ CrewAI agents already output thinking traces
- ✅ ConversationThinkingCallback already parses them
- ✅ Full content is captured in debug_data
- ✅ Pattern is consistent and well-tested

**Implementation Complexity**: 
- Initially estimated: High (new API fields, model detection)
- Actual: Low (parse existing strings, display in UI)

**Next Steps**: Simply parse and display what we're already capturing!

### Phase 4: Tool Integration Enhancement ✅ COMPLETE
- ✅ Enhance tool execution capture with @log_tool_execution decorator
- ✅ Parse tool arguments more intelligently
- ✅ Capture tool execution timing

#### Implementation Details:
- Enhanced `log_tool_execution` decorator with:
  - Start/end time capture
  - Duration calculation in seconds
  - Better argument parsing for CrewAI tools
  - Proper handling of string, dict, and other input types
- Updated `ToolCallCapture` dataclass to include timing fields
- Applied decorator to all tools in:
  - `database_tools.py` (17 tools)
  - `shopify_tools.py` (all tools)
  - `universe_tools.py` (all tools)
- Frontend displays execution time in milliseconds

### Phase 5: UI Polish
- ❌ Add syntax highlighting for JSON/code in prompts
- ✅ Add copy buttons for prompts/responses - COMPLETE
- ❌ Add search/filter within message details
- ❌ Show token usage visualization

#### Completed UI Improvements:
- ✅ Added copy buttons with visual feedback (checkmark) to:
  - Prompt messages
  - Response content
  - Tool call arguments
  - Tool execution outputs
- ✅ Formatted JSON with proper indentation using JSON.stringify(data, null, 2)
- ✅ Used existing lucide-react icons (no new dependencies)
- ✅ Added overflow handling for long content

### Phase 6: Performance & Persistence
- ❌ Add caching layer for debug data
- ❌ Implement debug data persistence to database
- ❌ Add export functionality (JSON/Markdown)

