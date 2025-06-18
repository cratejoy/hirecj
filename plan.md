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

## Phase 2: Connect to Real Data

### Phase 2.1: Verify Data Availability (FIRST PRIORITY)
**Goal**: Confirm we can access all needed debug data before building anything

#### Understanding Current Infrastructure
Based on the merged code:
1. **LiteLLM Logging Already Enabled**: `main.py` sets `LITELLM_LOG=DEBUG` and `LITELLM_VERBOSE=true`
2. **Callback Infrastructure Exists**: `ExtendedAgent` and `ConversationThinkingCallback` already hook into LiteLLM
3. **Debug Storage Ready**: `Session.debug_data` already has structure for storing prompts/responses

#### Step 1: Create LiteLLM Debug Callback
**New File**: `agents/app/services/litellm_debug_callback.py`

```python
from litellm.integrations.custom_logger import CustomLogger
from typing import Dict, Any, Optional
import json
from datetime import datetime
from shared.logging_config import get_logger

logger = get_logger(__name__)

class LiteLLMDebugCallback(CustomLogger):
    """Captures raw LiteLLM API calls for debugging."""
    
    def __init__(self, session_id: str, debug_storage: Dict[str, Any]):
        super().__init__()
        self.session_id = session_id
        self.debug_storage = debug_storage
        self.current_message_id = None
    
    def set_message_id(self, message_id: str):
        """Set the current message ID for associating debug data."""
        self.current_message_id = message_id
    
    def log_pre_api_call(self, model: str, messages: list, kwargs: Dict[str, Any]) -> None:
        """Capture the raw API request before it's sent."""
        try:
            # Extract the full prompt
            prompt_data = {
                "message_id": self.current_message_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature"),
                "max_tokens": kwargs.get("max_tokens"),
                "tools": kwargs.get("tools", []),
                "tool_choice": kwargs.get("tool_choice"),
                "metadata": {
                    "provider": kwargs.get("custom_llm_provider"),
                    "api_base": kwargs.get("api_base"),
                    "headers": {k: v for k, v in kwargs.get("headers", {}).items() 
                               if k.lower() not in ["authorization", "x-api-key"]},  # Sanitize
                }
            }
            
            # Store in debug storage
            self.debug_storage["llm_prompts"].append(prompt_data)
            
            # Keep only last 10 prompts
            if len(self.debug_storage["llm_prompts"]) > 10:
                self.debug_storage["llm_prompts"].pop(0)
                
            logger.info(f"[LITELLM_DEBUG] Captured prompt for message {self.current_message_id}")
            
        except Exception as e:
            logger.error(f"[LITELLM_DEBUG] Error capturing prompt: {e}")
    
    def log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float) -> None:
        """Capture the raw API response."""
        try:
            response_data = {
                "message_id": self.current_message_id,
                "timestamp": datetime.utcnow().isoformat(),
                "duration": end_time - start_time,
                "model": response_obj.model if hasattr(response_obj, 'model') else None,
                "usage": response_obj.usage.dict() if hasattr(response_obj, 'usage') else None,
                "choices": [
                    {
                        "message": choice.message.dict() if hasattr(choice, 'message') else None,
                        "finish_reason": choice.finish_reason if hasattr(choice, 'finish_reason') else None,
                    }
                    for choice in (response_obj.choices if hasattr(response_obj, 'choices') else [])
                ],
                "system_fingerprint": response_obj.system_fingerprint if hasattr(response_obj, 'system_fingerprint') else None,
            }
            
            # Store in debug storage
            self.debug_storage["llm_responses"].append(response_data)
            
            # Keep only last 10 responses
            if len(self.debug_storage["llm_responses"]) > 10:
                self.debug_storage["llm_responses"].pop(0)
                
            logger.info(f"[LITELLM_DEBUG] Captured response for message {self.current_message_id}")
            
        except Exception as e:
            logger.error(f"[LITELLM_DEBUG] Error capturing response: {e}")
```

#### Step 2: Hook Into Message Processor
**File**: `agents/app/services/message_processor.py`

Add debug callback integration:
```python
# In _get_cj_response method, before creating agent

# Generate unique message ID
import uuid
message_id = f"msg_{uuid.uuid4().hex[:8]}"

# Create debug callback
from app.services.litellm_debug_callback import LiteLLMDebugCallback
debug_callback = LiteLLMDebugCallback(session.id, session.debug_data)
debug_callback.set_message_id(message_id)

# Add to litellm callbacks
import litellm
if debug_callback not in litellm.success_callback:
    litellm.success_callback.append(debug_callback)
if debug_callback not in litellm._async_success_callback:
    litellm._async_success_callback.append(debug_callback)

try:
    # ... existing crew execution code ...
    
    # After getting response, store message_id
    response_data["message_id"] = message_id
    
finally:
    # Clean up callback
    if debug_callback in litellm.success_callback:
        litellm.success_callback.remove(debug_callback)
    if debug_callback in litellm._async_success_callback:
        litellm._async_success_callback.remove(debug_callback)
```

#### Step 3: Test and Verify
1. Start agent service
2. Send test message through playground
3. Use debug request endpoint to retrieve captured data
4. Verify we capture:
   - Full messages array with system/user/assistant messages
   - Model parameters (temperature, max_tokens)
   - Tool definitions
   - Token usage
   - Response content and tool calls
   - Timing information

### Phase 2.2: Protocol and Data Flow
**Goal**: Extend protocol to support message IDs and debug requests

#### Step 1: Extend CJMessageData
**File**: `shared/protocol/models.py`

```python
class CJMessageData(BaseModel):
    content: str
    factCheckStatus: Optional[str] = "available"
    timestamp: datetime
    ui_elements: Optional[List[Dict[str, Any]]] = None
    message_id: Optional[str] = None  # NEW: For debug lookups
```

#### Step 2: Update Debug Request Handler
The existing `utility_handlers.py` already supports debug types. We need to add "message_details":

```python
# In handle_debug_request, add new case:
if debug_type == "message_details":
    message_id = message.data.get("message_id")
    if not message_id:
        # Return error
        pass
    
    # Find the debug data for this message
    for prompt in session.debug_data.get("llm_prompts", []):
        if prompt.get("message_id") == message_id:
            debug_data["prompt"] = prompt
            break
    
    for response in session.debug_data.get("llm_responses", []):
        if response.get("message_id") == message_id:
            debug_data["response"] = response
            break
```

#### Step 3: TypeScript Protocol Update
Run protocol generation after Python changes:
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

