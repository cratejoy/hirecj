# Agent Editor Playground - WebSocket Architecture Plan

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Every decision should make the code simpler, not more complex
   - This means: Don't add features we don't need yet
   - This does NOT mean: Remove existing requirements or functionality
   - Keep what's needed, remove what's not
2. **No Cruft**: Remove all redundant code, validation, and unnecessary complexity
3. **Break It & Fix It Right**: No backwards compatibility shims - make breaking changes and migrate properly
4. **Long-term Elegance**: Choose performant, compiler-enforced solutions that prevent subtle bugs
5. **Backend-Driven**: Let the backend handle complexity, frontend should be a thin client
6. **Single Source of Truth**: One pattern, one way to do things, no alternatives
7. **No Over-Engineering**: Design for current needs only - no hypothetical features, no "maybe later" code
8. **Thoughtful Logging & Instrumentation**: We value visibility into system behavior with appropriate log levels
   - Use proper log levels (debug, info, warning, error)
   - Log important state changes and decisions
   - But don't log sensitive data or spam the logs

## 🤖 Operational Guidelines

- **No Magic Values**: Never hardcode values inline. Use named constants, configuration, or explicit parameters
  - ❌ `if count > 10:` 
  - ✅ `if count > MAX_RETRIES:`
- **No Unsolicited Optimizations**: Only implement what was explicitly requested
  - Don't add caching unless asked
  - Don't optimize algorithms unless asked
  - Don't refactor unrelated code unless asked
  - If you see an opportunity for improvement, mention it but don't implement it
- **NEVER Create V2 Versions**: When asked to add functionality, ALWAYS update the existing code
  - ❌ Creating `analytics_lib_v2.py`, `process_data_v2.py`, `utils_v2.py`, etc.
  - ✅ Adding new functions to existing files
  - ✅ Updating existing functions to support new parameters
  - ✅ Refactoring existing code to handle new requirements
- **Clean Up When Creating PRs**: When asked to create a pull request, ALWAYS:
  - Remove any test files that are no longer needed
  - Delete orphaned or superseded libraries
  - Clean up temporary scripts
  - Ensure no duplicate functionality remains
  - The PR should be clean and ready to merge

## Personal Preferences (Amir)
- Always prefer the long term right solution that is elegant, performant and ideally compiler enforced
- Never introduce backwards compatibility shims unless specifically requested
- Prefer breaking changes and the hard work of migrating to the new single correct pattern
- Don't introduce new features unless specifically asked to
- Don't build in CI steps unless specifically asked to
- Don't introduce benchmarking & performance management steps unless specifically asked to
- Do not implement shims without explicit approval. They are hacks.

## Executive Summary

The editor playground needs to test agents without duplicating the complex production WebSocket infrastructure. This plan proposes a simplified approach where the editor-backend acts as a proxy between the editor UI and the agent service, leveraging the existing anonymous session support in the agent service rather than creating a separate test mode.

## Current Architecture Analysis

### Production Chat System (Post-Protocol Refactor)
```
Homepage (React) <--WebSocket--> Homepage Backend <---> Agent Service
      |                              |                      |
Protocol Types               Pydantic Models         CrewAI Agents
(generated TS)              Session Management      Data Providers
                           Auth/OAuth               Workflows
```

### Key Components After Protocol Refactor
- **Shared Protocol**: `shared/protocol/models.py` defines all WebSocket messages using Pydantic v2
- **Type Generation**: `pydantic2ts` generates TypeScript interfaces from Pydantic models
- **Frontend**: Typed `useWebSocketChat` hook with full protocol type safety
- **Message Validation**: Runtime validation using Pydantic's `TypeAdapter`
- **Session Management**: Complex auth flows, anonymous/authenticated sessions, OAuth callbacks
- **Workflow System**: Priority-based selection, workflow-specific agent behaviors

## Proposed Editor Architecture

### Simplified Architecture
```
Editor UI <--WebSocket--> Editor Backend <--WebSocket Client--> Agent Service
    |                           |                                     |
Protocol Types           Message Transform                    Existing Agents
Playground View         Anonymous Sessions                    Real Workflows
                       No Auth Required                      Real Data Providers
```

## Implementation Checklist

Each phase below requires **Amir's approval** before proceeding to the next phase.

- [x] Phase 1: Protocol Models - Define Playground Messages ✅
- [x] Phase 2: Protocol Generation - Update and Run ✅
- [x] Phase 3: Editor Protocol Setup ✅
- [x] Phase 4: Editor Backend - WebSocket Endpoint Setup ✅ (Tested and working)
- [x] Phase 5: Editor Backend - WebSocket Bridge Implementation ✅
- [x] Phase 6: Editor Backend - Message Forwarding Functions ✅
- [x] Phase 7: Editor Backend - Message Transformation ✅
- [x] Phase 8: Editor Backend - Router Integration ✅ (Already completed)
- [x] Phase 9: Revert Test Mode - Use Anonymous Sessions ✅
- [x] Phase 10: Editor Frontend - Create usePlaygroundChat Hook ✅
- [ ] Phase 11: Editor Frontend - WebSocket Connection Management ⏸️ **[Get Amir Approval]**
- [ ] Phase 12: Editor Frontend - Message Handling ⏸️ **[Get Amir Approval]**
- [ ] Phase 13: Editor Frontend - Action Functions ⏸️ **[Get Amir Approval]**
- [ ] Phase 14: Editor Frontend - Hook Lifecycle ⏸️ **[Get Amir Approval]**
- [ ] Phase 15: Editor Frontend - PlaygroundView Integration ⏸️ **[Get Amir Approval]**
- [ ] Phase 16: Testing Infrastructure ⏸️ **[Get Amir Approval]**
- [ ] Phase 17: Documentation and Polish ⏸️ **[Get Amir Approval]**

## Implementation Plan (17 Phases)

### Phase 1: Protocol Models - Define Playground Messages ✅
**Goal**: Add playground-specific message types to the protocol

**Status**: Completed as planned

1. **Added to `shared/protocol/models.py`**:
```python
class PlaygroundStartMsg(BaseModel):
    """Simplified start message for playground testing"""
    type: Literal["playground_start"] = "playground_start"
    workflow: str
    persona_id: str
    scenario_id: str
    trust_level: int
    
class PlaygroundResetMsg(BaseModel):
    """Reset playground conversation"""
    type: Literal["playground_reset"] = "playground_reset"
    reason: Literal["workflow_change", "user_clear"]
    new_workflow: Optional[str] = None

# Updated IncomingMessage union to include:
    PlaygroundStartMsg,
    PlaygroundResetMsg,
```

### Phase 2: Protocol Generation - Update and Run ✅
**Goal**: Generate TypeScript types for editor

**Status**: Completed with enhancements

1. **Updated `shared/protocol/generate.sh`**:
```bash
# Generate for homepage
pydantic2ts --module shared.protocol.models --output homepage/src/protocol/generated.ts
echo "✅ TypeScript types generated for homepage at homepage/src/protocol/generated.ts"

# Generate for editor
pydantic2ts --module shared.protocol.models --output editor/src/protocol/generated.ts
echo "✅ TypeScript types generated for editor at editor/src/protocol/generated.ts"

echo "✅ All TypeScript types generated successfully!"
```
2. ✅ Ran generation script: `cd shared/protocol && ./generate.sh`
3. ✅ Verified `editor/src/protocol/generated.ts` contains PlaygroundStartMsg and PlaygroundResetMsg

### Phase 3: Editor Protocol Setup ✅
**Goal**: Create protocol structure with type guards

**Status**: Completed with additional features

1. ✅ Created `editor/src/protocol/` directory
2. ✅ Created `editor/src/protocol/index.ts` with enhanced implementation:
```typescript
// Re-export all generated types
export * from './generated';

// Import and rename UserMsg for consistency
import type {
  UserMsg as MessageMsg,  // Rename for consistency
  // ... other imports
} from './generated';

// Playground-specific discriminated unions
export type PlaygroundIncomingMessage = 
  | PlaygroundStartMsg | PlaygroundResetMsg | MessageMsg;
  
export type PlaygroundOutgoingMessage =
  | ConversationStartedMsg | CJMessageMsg | CJThinkingMsg 
  | ErrorMsg | SystemMsg;

// Comprehensive type guards (more than originally planned)
export function isPlaygroundStart(msg: any): msg is PlaygroundStartMsg
export function isPlaygroundReset(msg: any): msg is PlaygroundResetMsg
export function isMessage(msg: any): msg is MessageMsg
export function isCjMessage(msg: any): msg is CJMessageMsg
export function isCjThinking(msg: any): msg is CJThinkingMsg
export function isConversationStarted(msg: any): msg is ConversationStartedMsg
export function isError(msg: any): msg is ErrorMsg
export function isSystem(msg: any): msg is SystemMsg

// Helper functions for union type checking
export function isPlaygroundIncomingMessage(msg: any): msg is PlaygroundIncomingMessage
export function isPlaygroundOutgoingMessage(msg: any): msg is PlaygroundOutgoingMessage
```

**Additional Work Required**: 
- Restored `editor/src/lib/utils.ts` and `editor/src/components/ui/button.tsx` from git history
- These files were accidentally deleted in commit 8a2ac2a and were blocking TypeScript compilation

### Phase 4: Editor Backend - WebSocket Endpoint Setup ✅
**Goal**: Create basic WebSocket endpoint with protocol imports

**Status**: Completed with import handling

1. ✅ Created `editor-backend/app/api/websocket/` directory
2. ✅ Created `playground.py` with:
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError
from shared.protocol.models import (
    IncomingMessage, OutgoingMessage,
    PlaygroundStartMsg, StartConversationMsg,
    PlaygroundResetMsg, EndConversationMsg,
    ErrorMsg
)
import websockets
import asyncio
import uuid
import logging

router = APIRouter()

# Validation adapters
incoming_adapter = TypeAdapter(IncomingMessage)
outgoing_adapter = TypeAdapter(OutgoingMessage)

@router.websocket("/ws/playground")
async def playground_websocket(websocket: WebSocket):
    await websocket.accept()
    logging.info("Playground WebSocket connected")
    # Implementation continues in next phase
```

**Additional Implementation Details**:
- Added proper import handling for shared module (with fallback for development)
- Created `__init__.py` with proper exports
- Registered the WebSocket router in `editor-backend/app/main.py`
- TypeAdapter instances created for message validation
- Endpoint available at `/ws/playground`

### Phase 5: Editor Backend - WebSocket Bridge Implementation ✅
**Goal**: Create bidirectional message bridge

**Status**: Completed and tested

**Implementation Details**:
1. ✅ Added `websockets==12.0` to requirements.txt
2. ✅ Implemented full WebSocket bridge in `playground.py`:
   - `playground_websocket`: Main endpoint that accepts editor connections and connects to agent
   - `bridge_connections`: Manages bidirectional message flow using asyncio tasks
   - `editor_to_agent`: Forwards messages from editor to agent service
   - `agent_to_editor`: Forwards messages from agent to editor
3. ✅ Added proper error handling:
   - ConnectionRefusedError when agent service is unavailable
   - Graceful disconnection handling for both sides
   - Session ID tracking for debugging
4. ✅ Created test script `test_phase5_bridge.py` to verify functionality

**Key Features**:
- Unique session IDs for each playground connection
- Concurrent bidirectional message forwarding
- Proper cleanup when either side disconnects
- Error messages sent to editor if agent is unavailable
- Debug logging for message flow

### Phase 6: Editor Backend - Message Forwarding Functions ✅
**Goal**: Implement bidirectional message forwarding with validation

**Status**: Completed and tested

**Implementation Details**:
1. ✅ Updated `editor_to_agent` function:
   - Added validation using `incoming_adapter.validate_json()`
   - Catches ValidationError and sends ErrorMsg back to editor
   - Logs valid message types for debugging
   - Messages still forwarded as-is (transformation in Phase 7)

2. ✅ Updated `agent_to_editor` function:
   - Added validation using `outgoing_adapter.validate_json()`
   - Logs warnings for invalid agent messages but still forwards them
   - Ensures agent protocol compliance monitoring

3. ✅ Fixed ErrorMsg structure:
   - Corrected to use `text` field instead of `data` field
   - Applied fix to both validation errors and connection errors

4. ✅ Created test script `test_phase6_validation.py`:
   - Tests valid message acceptance
   - Tests invalid message rejection with error response
   - Tests unknown message type handling

**Key Features**:
- Type-safe message validation on both directions
- Helpful error messages for debugging
- Non-blocking validation for agent messages
- Proper error message format

### Phase 7: Editor Backend - Message Transformation ✅
**Goal**: Transform playground messages to agent protocol

**Status**: Needs simplification - remove test mode

**Updated Implementation**:
1. Transform `PlaygroundStartMsg` → `StartConversationMsg`:
   - Use `persona_id` as `shop_subdomain`
   - Use `scenario_id` directly
   - Use `workflow` from the message
   - No test_mode flag or test_context
2. Transform `PlaygroundResetMsg` → `EndConversationMsg`
3. Pass through `UserMsg` and other messages unchanged

**Simplified transformation**:
```python
if isinstance(msg, PlaygroundStartMsg):
    data = StartConversationData(
        workflow=msg.workflow,
        shop_subdomain=msg.persona_id,  # Use persona_id as shop identifier
        scenario_id=msg.scenario_id
    )
    return StartConversationMsg(type="start_conversation", data=data)
```

### Phase 8: Editor Backend - Router Integration ✅
**Goal**: Register WebSocket router in main app

**Status**: Already completed during initial implementation

**Verification**:
- ✅ Import exists: `from app.api.websocket import playground` (line 15)
- ✅ Router included: `app.include_router(playground.router)` (line 127)
- ✅ WebSocket endpoint accessible at `/ws/playground`
- ✅ All previous phase tests confirm router is working

### Phase 9: Revert Test Mode - Use Anonymous Sessions
**Goal**: Remove test mode and use existing anonymous session support

**Implementation Steps**:
1. Revert changes from previous Phase 9:
   - Remove test mode detection from `session_handlers.py`
   - Remove `_handle_test_mode_start` method
   - Remove raw_data parameter passing
2. Simplify Phase 7 transformation:
   - Remove test_mode flag and test_context
   - Direct field mapping only
3. Let agent service handle playground connections as anonymous sessions:
   - Agent already supports anonymous connections
   - No authentication required
   - Uses real workflows and prompts

**Benefits**:
- No code bifurcation
- Simpler maintenance
- Uses real agent infrastructure
- POC demonstrates actual functionality
        return self.persona.get("business_name", "Test Business")
        
    async def get_merchant_email(self) -> str:
        return self.persona.get("email", "test@example.com")
        
    async def get_industry(self) -> str:
### Phase 10: Editor Frontend - Create usePlaygroundChat Hook
**Goal**: Set up WebSocket hook with basic structure

1. Create `editor/src/hooks/` directory
2. **Create `editor/src/hooks/usePlaygroundChat.ts`**:
```typescript
import { useCallback, useEffect, useRef, useState } from 'react';
import { 
  PlaygroundIncomingMessage, 
  PlaygroundOutgoingMessage,
  PlaygroundStartMsg,
  PlaygroundResetMsg,
  MessageMsg,
  CjMessageMsg,
  CjThinkingMsg,
  ConversationStartedMsg
} from '@/protocol';

interface PlaygroundConfig {
  workflow: string;
  personaId: string;
  scenarioId: string;
  trustLevel: number;
}

export function usePlaygroundChat() {
  const [messages, setMessages] = useState<CjMessageMsg[]>([]);
  const [thinking, setThinking] = useState<CjThinkingMsg | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  
  // Implementation continues...
}
```

### Phase 11: Editor Frontend - WebSocket Connection Management
**Goal**: Implement connection with auto-reconnect

1. **Add connection logic**:
```typescript
const connect = useCallback(() => {
  if (ws.current?.readyState === WebSocket.OPEN) return;
  
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/playground`;
  ws.current = new WebSocket(wsUrl);
  
  ws.current.onopen = () => {
    console.log('WebSocket connected');
    setIsConnected(true);
    clearTimeout(reconnectTimeout.current);
  };
  
  ws.current.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
  
  ws.current.onclose = () => {
    setIsConnected(false);
    setConversationStarted(false);
    clearTimeout(reconnectTimeout.current);
    reconnectTimeout.current = setTimeout(connect, 1000);
  };
  
  // Message handler next...
}, []);
```

### Phase 12: Editor Frontend - Message Handling
**Goal**: Handle incoming WebSocket messages

1. **Add message handler**:
```typescript
ws.current.onmessage = (event) => {
  const msg: PlaygroundOutgoingMessage = JSON.parse(event.data);
  
  switch (msg.type) {
    case 'conversation_started':
      setConversationStarted(true);
      break;
      
    case 'cj_message':
      setMessages(prev => [...prev, msg]);
      setThinking(null);
      break;
      
    case 'cj_thinking':
      setThinking(msg);
      break;
      
    case 'error':
      console.error('WebSocket error:', msg.data);
      break;
      
    default:
      console.log('Unknown message type:', msg.type);
  }
};
```

### Phase 13: Editor Frontend - Action Functions
**Goal**: Implement conversation control functions

1. **Add action functions**:
```typescript
const startConversation = useCallback((config: PlaygroundConfig) => {
  if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
    console.error('WebSocket not connected');
    return;
  }
  
  const msg: PlaygroundStartMsg = {
    type: 'playground_start',
    workflow: config.workflow,
    persona_id: config.personaId,
    scenario_id: config.scenarioId,
    trust_level: config.trustLevel
  };
  
  ws.current.send(JSON.stringify(msg));
  setMessages([]);
  setThinking(null);
}, []);

const sendMessage = useCallback((text: string) => {
  if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
    console.error('WebSocket not connected');
    return;
  }
  
  const msg: MessageMsg = {
    type: 'message',
    data: { text }
  };
  
  ws.current.send(JSON.stringify(msg));
}, []);

const resetConversation = useCallback((
  reason: 'workflow_change' | 'user_clear', 
  newWorkflow?: string
) => {
  if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
    console.error('WebSocket not connected');
    return;
  }
  
  const msg: PlaygroundResetMsg = {
    type: 'playground_reset',
    reason,
    new_workflow: newWorkflow
  };
  
  ws.current.send(JSON.stringify(msg));
  setMessages([]);
  setThinking(null);
  setConversationStarted(false);
}, []);
```

### Phase 14: Editor Frontend - Hook Lifecycle
**Goal**: Complete hook with lifecycle and return values

1. **Add lifecycle and return**:
```typescript
useEffect(() => {
  connect();
  
  return () => {
    clearTimeout(reconnectTimeout.current);
    ws.current?.close();
  };
}, [connect]);

return {
  messages,
  thinking,
  isConnected,
  conversationStarted,
  startConversation,
  sendMessage,
  resetConversation
};
```

### Phase 15: Editor Frontend - PlaygroundView Integration
**Goal**: Update PlaygroundView to use real WebSocket

1. **Update `editor/src/views/PlaygroundView.tsx`**:
```typescript
import { usePlaygroundChat } from '@/hooks/usePlaygroundChat';

export function PlaygroundView() {
  const {
    messages,
    thinking,
    isConnected,
    conversationStarted,
    startConversation,
    sendMessage,
    resetConversation
  } = usePlaygroundChat();
  
  // Remove all mock conversation logic
  
  const handleWorkflowChange = (newWorkflow: string) => {
    if (conversationStarted) {
      resetConversation('workflow_change', newWorkflow);
    }
    setSelectedWorkflow(newWorkflow);
  };
  
  const handleStart = () => {
    startConversation({
      workflow: selectedWorkflow,
      personaId: selectedPersona.id,
      scenarioId: selectedScenario.id,
      trustLevel: trustLevel
    });
  };
  
  // Add connection status UI
  if (!isConnected) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">
          Connecting to playground service...
        </div>
      </div>
    );
  }
  
  // Rest of UI implementation...
}
```

### Phase 16: Testing Infrastructure
**Goal**: Implement end-to-end testing and session management

1. **Test all workflows** with different personas/scenarios
2. **Add session cleanup**:
```python
# In agent service
class TestSessionManager:
    async def cleanup_inactive_sessions(self):
        """Remove test sessions after 30 minutes of inactivity"""
        current_time = datetime.utcnow()
        for session_id, last_activity in self.sessions.items():
            if (current_time - last_activity).seconds > 1800:
                await self.end_session(session_id)
```
3. **Create test utilities** for conversation export/import
4. **Add protocol message inspector** in editor UI

### Phase 17: Documentation and Polish
**Goal**: Final polish and documentation

1. **Update README files** with WebSocket setup instructions
2. **Add error handling** for edge cases
3. **Performance optimization**: connection pooling, message queuing
4. **Security review**: ensure test mode isolation
5. **Create developer guide** for adding new message types

## Benefits

1. **Protocol Consistency**: Uses the same TypeScript generation process as homepage
2. **Type Safety**: End-to-end type safety from editor UI through to agent service
3. **Minimal Duplication**: Reuses existing agent infrastructure and protocol
4. **Simple Interface**: Editor doesn't need auth, sessions, or complex state
5. **Real Testing**: Uses actual agent workflows and processing logic
6. **Clean Separation**: Test mode clearly separated from production
7. **Easy Maintenance**: Protocol changes automatically propagate to editor

## Technical Decisions

### Why Editor-Backend as Proxy?
- Already exists with access to personas/scenarios data
- Can transform messages and inject test context
- Isolates test traffic from production
- Enables editor-specific features without modifying agent service

### Why Extend Existing Protocol?
- Maintains type safety across the entire system
- Leverages existing validation and generation infrastructure
- Ensures compatibility with future protocol changes
- Reduces maintenance burden

### Why WebSocket vs REST?
- Maintains same real-time feel as production
- Supports progress updates (CJ thinking states)
- Enables future features (conversation branching, interruption)
- Consistent with production architecture

## Security Considerations

- Test mode only accessible through editor-backend
- No access to real merchant data
- Ephemeral sessions with automatic cleanup
- Clear labeling of test vs production data
- Rate limiting on playground endpoint
- No authentication tokens in test mode

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                EDITOR UI (Port 3457)                         │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                         PlaygroundView                              │     │
│  │  • Workflow Selector                                                │     │
│  │  • Persona/Scenario/Trust Level Controls                           │     │
│  │  • Conversation UI (using protocol types)                          │     │
│  │  • usePlaygroundChat() hook                                         │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                    │                                          │
│                          Protocol Types (generated)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ WebSocket
                                        │ /api/ws/playground
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EDITOR BACKEND (Port 8001)                          │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    Playground WebSocket Handler                     │     │
│  │  • Validates messages using Protocol TypeAdapter                    │     │
│  │  • Transforms PlaygroundStartMsg → StartConversationMsg             │     │
│  │  • Injects test_mode flag and test_context                         │     │
│  │  • Bridges bidirectional message flow                               │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                    │                                          │
│                          Protocol Models (Pydantic)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ WebSocket Client
                                        │ ws://localhost:8000/ws/chat
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT SERVICE (Port 8000)                          │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                     WebSocket Handler (Enhanced)                    │     │
│  │  • Recognizes test_mode flag in StartConversationMsg                │     │
│  │  • Creates ephemeral test session (no auth required)                │     │
│  │  • Initializes test data providers with persona/scenario            │     │
│  │  • Routes to normal workflow processing                             │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                        │                                      │
│                                        ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    Test Data Providers                              │     │
│  │  • TestMerchantDataProvider: Returns persona-based data             │     │
│  │  • TestMetricsProvider: Generates scenario-appropriate metrics      │     │
│  │  • TestUniverseProvider: Provides consistent test universe          │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                        │                                      │
│                                        ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                     CrewAI Agent Processing                         │     │
│  │  • Uses selected workflow from editor                               │     │
│  │  • Operates on test data (not production)                           │     │
│  │  • Normal agent reasoning and tool usage                            │     │
│  │  • Returns formatted responses via protocol                         │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Message Flow Example

### Starting Agent-Initiated Conversation:

1. **User clicks Play button in editor**
   ```typescript
   // Editor UI sends (using generated types):
   const msg: PlaygroundStartMsg = {
     type: 'playground_start',
     workflow: 'daily_checkin',
     persona_id: 'sarah_chen',
     scenario_id: 'growth_stall', 
     trust_level: 3
   }
   ```

2. **Editor Backend transforms and forwards**
   ```python
   # Transforms to StartConversationMsg:
   {
     "type": "start_conversation",
     "data": {
       "workflow": "daily_checkin",
       "test_mode": True,
       "test_context": {
         "persona": { /* full persona data */ },
         "scenario": { /* full scenario data */ },
         "trust_level": 3,
         "session_id": "playground_abc123"
       }
     }
   }
   ```

3. **Agent Service processes with test providers**
   ```python
   # Agent Service sends (using protocol):
   CjThinkingMsg(
     type="cj_thinking",
     data={"progress": {"status": "analyzing_metrics"}}
   )
   
   # Then:
   CjMessageMsg(
     type="cj_message",
     data={
       "content": "Good morning Sarah! I see you're up early...",
       "timestamp": "2024-01-15T08:30:00Z"
     }
   )
   ```

4. **Editor Backend forwards unchanged**
   - Protocol messages pass through without modification
   - Type safety maintained end-to-end

## Success Metrics

- Zero duplicate agent logic
- <100ms additional latency vs production
- Same message types and flow as production
- 100% type coverage with no any types
- Seamless protocol updates via regeneration
- Clear separation of test and production code