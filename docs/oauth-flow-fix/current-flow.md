# Current OAuth Flow (Broken)

## Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant WS as WebSocket
    participant A as Auth Service
    participant S as Shopify
    participant B as Backend

    U->>F: Click "Connect Shopify"
    F->>F: Store conversation_id in sessionStorage
    Note over F: conversation_id = "web_session_abc123"
    F->>A: Redirect to /api/v1/shopify/install
    A->>S: OAuth Authorization
    S->>A: Callback with code
    A->>F: Redirect to /chat?oauth=complete
    Note over F: Page reload, new WebSocket connection
    F->>WS: New connection
    WS->>B: Create NEW conversation_id
    Note over B: conversation_id = "web_session_xyz789"
    F->>WS: Send oauth_complete message
    Note over B: Message sent to WRONG conversation
    B->>B: Debug halt code NEVER FIRES
    Note over B: No system event generated
```

## Key Problems

1. **Lost Context**: Page reload creates new WebSocket with new conversation_id
2. **Wrong Target**: oauth_complete sent to wrong conversation
3. **No System Event**: Workflow expects system message, not WebSocket message
4. **Race Condition**: WebSocket might not be ready when oauth_complete sent