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

#### Step 1: Add Debug Logging to Message Processor
**File**: `agents/app/services/message_processor.py`

Add comprehensive debug logging to understand exactly what data is available:
```python
# In _get_cj_response method, after line 167 (crew creation)
logger.info("[DEBUG_CAPTURE] ========== CREW EXECUTION START ==========")
logger.info(f"[DEBUG_CAPTURE] Model: {cj_agent.model_name}")
logger.info(f"[DEBUG_CAPTURE] Provider: {cj_agent.provider}")
logger.info(f"[DEBUG_CAPTURE] Tools: {[t.name for t in cj_agent.tools]}")

# Before crew.kickoff() - capture the full context
logger.info("[DEBUG_CAPTURE] Full agent backstory:")
logger.info(cj_agent.backstory[:500] + "..." if len(cj_agent.backstory) > 500 else cj_agent.backstory)

# After crew.kickoff() - capture all outputs
logger.info("[DEBUG_CAPTURE] ========== CREW EXECUTION COMPLETE ==========")
logger.info(f"[DEBUG_CAPTURE] Result type: {type(result)}")
logger.info(f"[DEBUG_CAPTURE] Result attributes: {dir(result)}")
if hasattr(result, '__dict__'):
    logger.info(f"[DEBUG_CAPTURE] Result dict: {result.__dict__}")
```

#### Step 2: Test Data Capture
1. Start the agent service with debug logging
2. Send a test message through the playground
3. Verify we can see:
   - Full prompt/backstory
   - Model configuration
   - Tool calls and outputs
   - Token usage
   - Timing information
4. Document exactly what data structures are available

#### Step 3: Investigate CrewAI Internals
**Research Tasks**:
1. Check if CrewAI exposes callbacks for tool execution
2. Find where token usage is stored in the result
3. Determine how to capture intermediate LLM calls
4. Test if we can access the raw LLM request/response

### Phase 2.2: Design Data Storage
**Goal**: Determine how to store debug data without impacting performance

#### Option A: In-Memory Cache (Recommended)
```python
class DebugDataStore:
    def __init__(self, max_entries=100):
        self._store = {}  # message_id -> debug_data
        self._order = []  # LRU tracking
        self._max_entries = max_entries
    
    def store(self, message_id: str, debug_data: dict):
        # Store with LRU eviction
        pass
    
    def retrieve(self, message_id: str) -> Optional[dict]:
        # Get debug data if available
        pass
```

#### Option B: Session-Based Storage
- Store debug data in the Session object
- Clear on session end
- Simpler but uses more memory

### Phase 2.3: Protocol Extension
**Goal**: Add debug support without breaking existing clients

#### Step 1: Extend Message Protocol
**File**: `shared/protocol/models.py`
```python
# Option 1: Add to existing message (backwards compatible)
class CJMessageData(BaseModel):
    content: str
    factCheckStatus: Optional[str] = "available"
    timestamp: datetime
    ui_elements: Optional[List[Dict[str, Any]]] = None
    message_id: Optional[str] = None  # NEW: Unique ID for debug lookups
    
# Option 2: Separate debug response (cleaner)
class DebugMessageData(BaseModel):
    message_id: str
    prompt: str
    response: str
    model: str
    temperature: float
    max_tokens: int
    tool_calls: List[Dict[str, Any]]
    timing: Dict[str, float]
    token_usage: Dict[str, int]
```

#### Step 2: Update TypeScript Types
Regenerate protocol types after Python changes.

### Phase 2.4: Backend Implementation
**Goal**: Capture and serve debug data

#### Step 1: Implement Debug Capture
**File**: `agents/app/services/message_processor.py`
1. Generate unique message IDs
2. Capture debug context during execution
3. Store in debug data store
4. Include message_id in response

#### Step 2: Add Debug Handler
**File**: `agents/app/platforms/web/message_handlers.py`
```python
async def handle_debug_request(self, data: dict):
    msg_type = data.get("type")
    if msg_type == "message_details":
        message_id = data.get("messageId")
        debug_data = self.debug_store.retrieve(message_id)
        if debug_data:
            await self.send_message(DebugResponseMsg(
                type="debug_response",
                data={"messageId": message_id, "debug": debug_data}
            ))
```

### Phase 2.5: Frontend Integration
**Goal**: Request and display real debug data

#### Step 1: Update Message Storage
**File**: `editor/src/hooks/usePlaygroundChat.ts`
- Store message IDs with messages
- Add debug request method
- Handle debug responses

#### Step 2: Update MessageDetailsView
**File**: `editor/src/components/playground/MessageDetailsView.tsx`
- Accept messageId prop
- Show loading state
- Request debug data on mount
- Display real data when received
- Handle errors gracefully

### Phase 2.6: Testing & Validation
**Goal**: Ensure everything works correctly

1. Test with simple messages
2. Test with tool-calling messages
3. Test with large prompts/responses
4. Verify performance impact
5. Test error cases

### Understanding the Current Architecture

#### 1. **Message Flow**
```
Frontend (Editor) → WebSocket → Editor Backend → Agent Backend
```

- **Frontend**: `usePlaygroundChat` hook manages WebSocket connection
- **Editor Backend**: Bridges WebSocket messages between frontend and agent
- **Agent Backend**: 
  - `MessageProcessor` orchestrates the conversation
  - `CJAgent` (CrewAI agent) generates responses using LLMs
  - Tool calls are made through CrewAI's tool system

#### 2. **Key Components**

**Frontend (Editor)**:
- `usePlaygroundChat.ts`: WebSocket client, receives `CJMessageMsg` objects
- `PlaygroundView.tsx`: Renders messages and UI
- Protocol types in `editor/src/protocol/generated.ts`

**Agent Backend**:
- `message_processor.py`: Main orchestrator at `agents/app/services/message_processor.py:116`
  - Creates CJAgent
  - Builds CrewAI Task with user message
  - Executes via `crew.kickoff()`
  - Logs prompt/response at lines 176-192
- `cj_agent.py`: Agent configuration at `agents/app/agents/cj_agent.py`
  - Builds context and backstory
  - Configures tools
  - Uses CrewAI Agent wrapper

#### 3. **Current Debug Information Available**
From code analysis, these are already being logged:
- LLM prompts (line 176-181 in message_processor.py)
- LLM responses (line 190-192)
- Tool calls (via CrewAI's verbose mode)
- Timing information

### Implementation Plan

#### Step 1: Extend Protocol Messages
Add debug metadata to existing messages without breaking compatibility.

**File**: `shared/protocol/models.py`

```python
class CJMessageData(BaseModel):
    content: str
    factCheckStatus: Optional[str] = "available"
    timestamp: datetime
    ui_elements: Optional[List[Dict[str, Any]]] = None
    # NEW: Debug metadata (only populated when requested)
    debug_metadata: Optional[Dict[str, Any]] = None
```

#### Step 2: Capture Debug Information in Agent
Modify the message processor to capture and store debug data.

**File**: `agents/app/services/message_processor.py`

Add a debug context manager:
```python
class DebugContext:
    def __init__(self):
        self.prompt = None
        self.response = None
        self.tool_calls = []
        self.model_config = {}
        self.timing = {}
        self.crew_output = None
```

Modify `_get_cj_response` to capture debug data:
1. Capture the full prompt after context building
2. Intercept tool calls via CrewAI callbacks
3. Capture timing and model configuration
4. Store crew execution output

#### Step 3: Add Debug Request Support
Enable frontend to request debug data for specific messages.

**Protocol Addition**:
```typescript
// Already exists in protocol
interface DebugRequestData {
  type: "snapshot" | "session" | "state" | "metrics" | "prompts" | "message_details";
  messageId?: string;  // For message-specific debug requests
}
```

**WebSocket Handler**: Add handler in `agents/app/platforms/web/message_handlers.py` to respond to debug requests with captured data.

#### Step 4: Frontend Integration

**Modify `usePlaygroundChat`**:
1. Add method to request debug data for a specific message
2. Store debug metadata with messages when received

**Update `MessageDetailsView`**:
1. Accept message ID as prop
2. Request debug data when opened
3. Display real data instead of hardcoded content

### Elegant Design Principles

1. **Non-intrusive**: Debug data is only captured/sent when explicitly requested
2. **Backwards Compatible**: Existing message flow remains unchanged
3. **Performant**: No overhead during normal operation
4. **Extensible**: Easy to add more debug information types

### Implementation Order

1. **Backend First**:
   - Extend protocol with optional debug metadata
   - Add debug context capture in message processor
   - Implement debug request handler

2. **Frontend Integration**:
   - Update WebSocket hook to handle debug requests/responses
   - Modify MessageDetailsView to use real data
   - Add loading states and error handling

3. **Testing & Polish**:
   - Test with various message types and tool calls
   - Add proper TypeScript types
   - Optimize performance for large prompts/responses

### Technical Details

#### Capturing CrewAI/LangChain Data
CrewAI uses LangChain under the hood. We can intercept:
- LLM calls via callbacks
- Tool executions via tool decorators
- Token usage via model response metadata

#### WebSocket Message Flow
```
1. User clicks Details → 
2. Frontend sends: {type: "debug_request", data: {type: "message_details", messageId: "xyz"}}
3. Backend retrieves debug context for message
4. Backend sends: {type: "debug_response", data: {messageId: "xyz", debug: {...}}}
5. Frontend displays in MessageDetailsView
```

### Next Steps

With this plan, we can elegantly connect the Message Details View to real agent data without disrupting the existing conversation flow. The implementation preserves our North Star principles by keeping things simple and avoiding unnecessary complexity.