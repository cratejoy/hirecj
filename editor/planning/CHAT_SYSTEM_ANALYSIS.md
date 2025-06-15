# HireCJ Chat System Architecture Analysis

## Overview

The HireCJ chat system implements a real-time WebSocket-based communication between the React homepage and the Python agent stack. The system supports authenticated and anonymous users, workflow transitions, session management, and various message types.

## Architecture Flow

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│  React Homepage │       │   Express Proxy  │       │  FastAPI Agent  │
│   (Port 3456)   │ <---> │   (Port 3456)    │ <---> │   (Port 8000)   │
└─────────────────┘       └──────────────────┘       └─────────────────┘
        ↓                          ↓                          ↓
   useWebSocketChat         http-proxy-middleware       WebPlatform
```

## Key Components

### 1. Frontend (React Homepage)

#### WebSocket Client Hook (`useWebSocketChat.ts`)
- **Location**: `/homepage/src/hooks/useWebSocketChat.ts`
- **Purpose**: Manages WebSocket connection lifecycle and message handling
- **Key Features**:
  - Auto-reconnection with exponential backoff
  - Message queueing when disconnected
  - Progress tracking for CJ responses
  - Workflow update handling
  - OAuth callback processing

#### Connection Management
```typescript
// Connection states
type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error' | 'closed';

// WebSocket URL resolution (prefers same-origin for cookie support)
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const host = window.location.host;
const defaultUrl = `${protocol}//${host}`;
```

### 2. Proxy Layer (Express)

#### Proxy Configuration (`routes.ts`)
- **Location**: `/homepage/server/routes.ts`
- **Purpose**: Proxies WebSocket and API requests to the agent service
- **Configuration**:
  ```typescript
  // WebSocket proxy
  const wsProxy = createProxyMiddleware({
    target: agentsTarget,
    changeOrigin: true,
    ws: true,
    pathFilter: '/ws/chat/**'
  });
  ```

### 3. Agent Stack (FastAPI)

#### WebSocket Endpoint (`main.py`)
- **Location**: `/agents/app/main.py`
- **Endpoint**: `/ws/chat`
- **Handler**: Delegates to WebPlatform

#### Platform Architecture
The agent stack uses a platform-based architecture:

```
WebPlatform
├── WebSocketHandler (connection management)
├── MessageHandlers (message routing)
│   ├── ConversationHandlers (chat messages)
│   ├── SessionHandlers (session lifecycle)
│   ├── WorkflowHandlers (workflow transitions)
│   └── UtilityHandlers (ping, debug)
└── SessionManager (session state)
```

## Session Management

### Session Types

1. **Anonymous Sessions**
   - ID Format: `anon_{uuid}`
   - No persistence between connections
   - Limited features

2. **Authenticated Sessions**
   - ID Format: `user_{user_id}_{session_hash}`
   - Persisted via cookies (`hirecj_session`)
   - Full feature access
   - OAuth state management

### Session Flow

1. **Connection Establishment**:
   ```python
   # WebSocketHandler checks for session cookie
   session_id = websocket.cookies.get("hirecj_session")
   
   # Creates conversation ID based on auth status
   if authenticated:
       conversation_id = f"user_{user_id}_{session_hash}"
   else:
       conversation_id = f"anon_{uuid}"
   ```

2. **Session Creation**:
   - Frontend sends `start_conversation` message
   - Backend determines workflow based on:
     - OAuth callback state
     - User request
     - Existing integrations
     - Authentication status

## Workflow System

### Workflow Selection Logic

```python
async def _select_workflow(ws_session, start_data, user_id):
    # Priority order:
    # 1. OAuth callback override (one-shot)
    if override := ws_session.get("data", {}).pop("next_workflow"):
        return override
    
    # 2. Client-requested workflow
    if workflow := start_data.get("workflow"):
        return workflow
    
    # 3. User has Shopify integration → post-auth workflow
    if user_id and has_shopify_integration(user_id):
        return "shopify_post_auth"
    
    # 4. Skip onboarding for authenticated users
    if user_id and workflow == "shopify_onboarding":
        return "ad_hoc_support"
```

### Workflow Transitions

1. **User-Initiated Transitions**:
   ```typescript
   // Frontend sends
   {
     type: "workflow_transition",
     data: {
       new_workflow: "target_workflow",
       user_initiated: true
     }
   }
   ```

2. **System-Initiated Transitions**:
   - OAuth completion triggers
   - Authentication state changes
   - Workflow-specific rules

## Message Types and Protocol

### Client → Server Messages

```typescript
// Start conversation
{
  type: "start_conversation",
  data: {
    merchant_id?: string,
    scenario?: string,
    workflow?: string
  }
}

// Send message
{
  type: "message",
  text: string
}

// Request fact check
{
  type: "fact_check",
  data: { messageIndex: number }
}

// Workflow transition
{
  type: "workflow_transition",
  data: { 
    new_workflow: string,
    user_initiated: boolean
  }
}

// System events (OAuth, etc)
{
  type: "system_event",
  event: string,
  data: any
}
```

### Server → Client Messages

```typescript
// System messages
{
  type: "system",
  message: string
}

// CJ thinking indicator
{
  type: "cj_thinking",
  progress: {
    status: string,
    toolsCalled?: number,
    currentTool?: string
  }
}

// CJ response
{
  type: "cj_message",
  data: {
    content: string,
    timestamp: string,
    factCheckStatus?: string,
    ui_elements?: Array<{
      id: string,
      type: string,
      provider: string,
      placeholder: string
    }>
  }
}

// Workflow updates
{
  type: "workflow_updated",
  data: {
    workflow: string,
    previous: string
  }
}

// Conversation started
{
  type: "conversation_started",
  data: {
    conversationId: string,
    merchantId: string,
    scenario: string,
    workflow: string,
    workflow_requirements: object
  }
}
```

## OAuth Integration

### OAuth Flow with Chat System

1. **Pre-OAuth**:
   - User starts in `shopify_onboarding` workflow
   - CJ guides through OAuth process
   - Frontend shows Shopify OAuth button

2. **OAuth Callback**:
   - Auth service sets `next_workflow` in session
   - User redirected back to homepage
   - WebSocket reconnects with session cookie

3. **Post-OAuth**:
   - Session handler detects `next_workflow` flag
   - Transitions to `shopify_post_auth` workflow
   - Clears one-shot flag from database

## Key Features

### 1. Real-Time Progress Updates
- Backend sends `cj_thinking` messages during processing
- Shows tool usage and elapsed time
- Smooth transition to final response

### 2. Fact Extraction
- Automatic on disconnect if user authenticated
- Extracts conversation facts to user's knowledge base
- Non-blocking background process

### 3. UI Elements
- Messages can include interactive elements
- Shopify OAuth buttons
- Action prompts
- Structured data displays

### 4. Session Persistence
- Conversations saved on disconnect
- Can resume sessions with message history
- Workflow state preserved

## Error Handling

### Connection Errors
- Automatic reconnection with backoff
- Message queue for offline sending
- Connection state feedback to user

### Universe Not Found
- Special error type for missing data
- Clear user messaging
- Fallback options provided

### Workflow Errors
- Invalid workflow transitions blocked
- Requirements validation
- Graceful degradation

## Security Considerations

1. **Cookie-Based Auth**:
   - HTTPOnly session cookies
   - Same-origin WebSocket preferred
   - CORS configuration for cross-origin

2. **Message Validation**:
   - Type checking on all messages
   - Size limits enforced
   - Rate limiting potential

3. **Session Security**:
   - Session expiration
   - User context validation
   - OAuth state verification

## Development Setup

### Environment Variables
```bash
# Frontend
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000  # Optional override

# Backend
AGENTS_SERVICE_URL=http://localhost:8000
```

### Testing WebSocket
1. Use backend test page: `http://localhost:8000/ws-test`
2. Frontend chat interface
3. WebSocket debugging tools

## Common Patterns

### Starting a Conversation
```javascript
// 1. Connect WebSocket
const { sendMessage, isConnected } = useWebSocketChat({
  enabled: true,
  merchantId: "demo",
  scenario: "default",
  workflow: "shopify_onboarding"
});

// 2. Wait for connection
// 3. Start conversation (automatic on connection)
// 4. Send messages
sendMessage("Hello CJ!");
```

### Handling Workflow Transitions
```javascript
// Listen for workflow updates
onWorkflowUpdated: (newWorkflow, previousWorkflow) => {
  console.log(`Transitioned from ${previousWorkflow} to ${newWorkflow}`);
  // Update UI accordingly
}
```

### OAuth Completion
```javascript
// After OAuth callback
sendSpecialMessage({
  type: "system_event",
  event: "oauth_complete",
  data: { provider: "shopify" }
});
```

## Future Considerations

1. **Scalability**:
   - Consider message queue (Redis/RabbitMQ)
   - Horizontal scaling of WebSocket servers
   - Session storage in distributed cache

2. **Features**:
   - File uploads
   - Voice messages
   - Screen sharing
   - Multi-user conversations

3. **Performance**:
   - Message pagination
   - Lazy loading of history
   - WebSocket compression
   - Binary protocol for efficiency