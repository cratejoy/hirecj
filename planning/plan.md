# Agent Editor Playground - WebSocket Architecture Plan

## Executive Summary

The editor playground needs to test agents without duplicating the complex production WebSocket infrastructure. This plan proposes a simplified test harness where the editor-backend acts as a proxy between the editor UI and the agent service, stripping away production concerns while maintaining the core conversation functionality.

## Current Architecture Analysis

### Production Chat System
```
Homepage (React) <--WebSocket--> Homepage Backend <---> Agent Service
                                      |                      |
                                   Sessions              Workflows
                                   Auth/OAuth            CrewAI Agents
                                   Analytics             Data Providers
```

### Key Components
- **Frontend**: `useWebSocketChat` hook with reconnection, queuing, progress tracking
- **Message Protocol**: Bidirectional with types like `start_conversation`, `message`, `cj_thinking`, `cj_message`
- **Session Management**: Complex auth flows, anonymous/authenticated sessions, OAuth callbacks
- **Workflow System**: Priority-based selection, smooth transitions, workflow-specific requirements

## Proposed Editor Architecture

### Simplified Test Harness
```
Editor UI <--WebSocket--> Editor Backend <--WebSocket Client--> Agent Service
    |                           |                                     |
Playground View          Test Orchestrator                    Existing Agents
Persona/Scenario         Simplified Protocol                  Real Workflows
Trust Level              No Auth/Sessions                     Real Processing
```

## Implementation Plan

### Phase 1: Editor WebSocket Endpoint

Create `/ws/playground` endpoint in editor-backend that:
- Accepts connections from the editor UI
- Creates a single-use test session with the agent service
- Injects persona, scenario, and trust level into agent context
- Strips auth/session complexity

```python
# editor-backend/app/api/websocket/playground.py
@router.websocket("/ws/playground")
async def playground_websocket(websocket: WebSocket):
    await websocket.accept()
    
    # Create agent client connection
    agent_ws = await connect_to_agent_service()
    
    # Bridge messages between editor and agent
    await bridge_websockets(websocket, agent_ws)
```

### Phase 2: Simplified Message Protocol

Editor → Editor-Backend:
```typescript
interface PlaygroundMessage {
  type: 'start' | 'message' | 'reset'
  data: {
    workflow: string
    persona: Persona
    scenario: Scenario
    trustLevel: number
    text?: string  // for 'message' type
  }
}
```

Editor-Backend → Agent Service (transforms to):
```typescript
{
  type: 'start_conversation',
  data: {
    workflow: string,
    // Inject test context
    test_mode: true,
    test_context: {
      persona: { /* full persona data */ },
      scenario: { /* full scenario data */ },
      trust_level: number
    }
  }
}
```

### Phase 3: Agent Service Test Mode

Minimal changes to agent service:
- Recognize `test_mode` flag
- Skip auth/session checks for test sessions
- Inject test context into agent's data providers
- Auto-cleanup test sessions after inactivity

```python
# agents/platforms/web/handlers/conversation.py
if message_data.get('test_mode'):
    # Create ephemeral test session
    session = create_test_session(message_data['test_context'])
    # Skip auth flows
    workflow = message_data['workflow']
```

### Phase 4: Editor UI Integration

Update PlaygroundView to use WebSocket:
```typescript
// usePlaygroundChat.ts
export function usePlaygroundChat() {
  const ws = useRef<WebSocket>()
  
  const startConversation = (config: PlaygroundConfig) => {
    ws.current = new WebSocket('/ws/playground')
    
    ws.current.onopen = () => {
      ws.current.send(JSON.stringify({
        type: 'start',
        data: {
          workflow: config.workflow,
          persona: config.persona,
          scenario: config.scenario,
          trustLevel: config.trustLevel
        }
      }))
    }
  }
  
  return { startConversation, sendMessage, messages, thinking }
}
```

### Phase 4.1: Workflow Switching & Chat Management

#### Core Principle: "New Workflow = New Conversation"

When a user changes the workflow dropdown:
1. **Immediately reset the conversation** - clears all messages
2. **Return to the appropriate starter view** - agent-initiated (play button) or merchant-initiated (input field)
3. **Keep the WebSocket connection alive** - no need to reconnect
4. **Preserve persona/scenario/trust settings** - these carry over

#### WebSocket Protocol for State Management

```typescript
// Workflow change
{
  type: 'reset',
  data: {
    reason: 'workflow_change',
    new_workflow: 'daily_checkin'
  }
}

// Server acknowledges
{
  type: 'reset_complete',
  data: {
    workflow: 'daily_checkin',
    ready: true
  }
}

// User-initiated clear
{
  type: 'reset',
  data: {
    reason: 'user_clear'
  }
}
```

#### State Machine

```
IDLE (no workflow) 
  → SELECT_WORKFLOW → READY (starter view)
  
READY (starter view)
  → START → CONVERSING
  → CHANGE_WORKFLOW → READY (new workflow)
  
CONVERSING
  → CLEAR → READY (same workflow)
  → CHANGE_WORKFLOW → READY (new workflow)
  → SEND_MESSAGE → CONVERSING
```

#### UI Behavior

**Clear Button**:
- Always visible in the workflow selector bar
- Returns to starter view for current workflow
- Keeps all settings intact

**Persona/Scenario/Trust Changes**:
- Can change anytime without reset
- During conversation: Next message uses new context
- Before starting: Used when conversation begins

**Edge Cases**:
- Rapid switching: Debounce workflow changes
- Network issues: Reconnect preserves current workflow
- Empty state: Show placeholder if no workflow selected

### Phase 5: Data Provider Integration

Create test-aware data providers:
```python
# agents/data_providers/test_merchant_provider.py
class TestMerchantDataProvider(MerchantDataProvider):
    def __init__(self, test_context):
        self.persona = test_context['persona']
        self.scenario = test_context['scenario']
        
    async def get_business_name(self):
        return self.persona['business']
        
    async def get_current_metrics(self):
        # Return scenario-appropriate test data
        return generate_test_metrics(self.scenario)
```

## Benefits

1. **Minimal Duplication**: Reuses existing agent infrastructure
2. **Simple Interface**: Editor doesn't need auth, sessions, or complex state
3. **Real Testing**: Uses actual agent workflows and processing
4. **Clean Separation**: Test mode clearly separated from production
5. **Easy Maintenance**: Changes to agent system automatically reflected
6. **Flexible Testing**: Can inject any persona/scenario combination

## Technical Decisions

### Why Editor-Backend as Proxy?
- Already exists and has access to workflow/persona files
- Can transform messages and add test context
- Isolates test traffic from production
- Can add editor-specific features (save/load conversations, etc.)

### Why Not Direct Connection?
- Would require duplicating session management
- Would need auth bypass in production code
- Harder to inject test context cleanly
- More security concerns

### Why WebSocket vs REST?
- Maintains same real-time feel as production
- Supports progress updates (CJ thinking)
- Allows for future features (interrupt, branch conversation)
- Consistent with production architecture

## Migration Path

1. Start with basic message pass-through
2. Add persona/scenario injection
3. Implement progress tracking
4. Add conversation management (save/load)
5. Add advanced features (branch, rewind, compare)

## Security Considerations

- Test mode only accessible through editor-backend
- No access to real merchant data
- Ephemeral sessions auto-expire
- Clear labeling of test vs production data
- Rate limiting on playground endpoint

## Future Enhancements

1. **Conversation Branching**: Try different responses from same point
2. **A/B Testing**: Compare different prompts/workflows side-by-side  
3. **Regression Testing**: Save conversations as test cases
4. **Performance Profiling**: Measure response times, token usage
5. **Collaborative Editing**: Multiple users testing same agent

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                EDITOR UI (Port 3457)                         │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                         PlaygroundView                              │     │
│  │  • Workflow Selector                                                │     │
│  │  • Persona/Scenario/Trust Level Controls                           │     │
│  │  • Conversation UI (AgentInitiated/MerchantInitiated)              │     │
│  │  • usePlaygroundChat() hook                                         │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ WebSocket
                                        │ /ws/playground
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EDITOR BACKEND (Port 8001)                          │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    Playground WebSocket Handler                     │     │
│  │  • Accepts editor connections                                       │     │
│  │  • Creates test session with agent service                          │     │
│  │  • Injects persona/scenario context                                │     │
│  │  • Bridges messages bidirectionally                                 │     │
│  │  • Handles test mode lifecycle                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ WebSocket Client
                                        │ ws://localhost:8000/ws/chat
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT SERVICE (Port 8000)                          │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                     Existing WebSocket Handler                      │     │
│  │  • Recognizes test_mode flag                                        │     │
│  │  • Skips auth for test sessions                                     │     │
│  │  • Creates ephemeral test session                                   │     │
│  │  • Routes to normal message processing                              │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                        │                                      │
│                                        ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    Test-Aware Data Providers                        │     │
│  │  • TestMerchantDataProvider: Returns persona data                   │     │
│  │  • TestMetricsProvider: Generates scenario-appropriate metrics      │     │
│  │  • TestUniverseProvider: Provides consistent test universe          │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                        │                                      │
│                                        ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                     CrewAI Agent Processing                         │     │
│  │  • Uses selected workflow (from editor)                             │     │
│  │  • Uses test data providers                                         │     │
│  │  • Normal agent reasoning and tool usage                            │     │
│  │  • Returns formatted responses                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Message Flow Example

### Starting Agent-Initiated Conversation:

1. **User clicks Play button in editor**
   ```typescript
   // Editor UI sends:
   {
     type: 'start',
     data: {
       workflow: 'daily_checkin',
       persona: { id: 'sarah_chen', name: 'Sarah Chen', ... },
       scenario: { id: 'growth_stall', metrics: { ... } },
       trustLevel: 3
     }
   }
   ```

2. **Editor Backend transforms and forwards**
   ```typescript
   // To Agent Service:
   {
     type: 'start_conversation',
     data: {
       workflow: 'daily_checkin',
       test_mode: true,
       test_context: {
         persona: { /* full data */ },
         scenario: { /* full data */ },
         trust_level: 3
       }
     }
   }
   ```

3. **Agent processes and responds**
   ```typescript
   // Agent Service sends:
   {
     type: 'cj_thinking',
     progress: { status: 'analyzing_metrics' }
   }
   // Then:
   {
     type: 'cj_message',
     data: {
       content: "Good morning Sarah! I see you're up early. I've been looking at your numbers...",
       timestamp: "2024-01-15T..."
     }
   }
   ```

4. **Editor Backend forwards to UI**
   - Passes through thinking indicators
   - Forwards CJ messages unchanged
   - Maintains WebSocket connection

## Success Metrics

- Zero duplicate agent logic
- <100ms additional latency vs production
- Same message types as production
- Easy to add new test scenarios
- Clear separation of concerns