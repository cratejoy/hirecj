# Target OAuth Flow (Fixed)

## Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant WS as WebSocket
    participant A as Auth Service
    participant S as Shopify
    participant B as Backend
    participant W as Workflow

    U->>F: Click "Connect Shopify"
    F->>F: Store conversation_id in sessionStorage
    Note over F: conversation_id = "web_session_abc123"
    F->>A: Redirect with ?conversation_id=abc123
    A->>S: OAuth Authorization
    S->>A: Callback with code
    A->>F: Redirect with conversation_id preserved
    F->>F: Retrieve conversation_id from callback
    F->>WS: Wait for connection
    WS->>B: Reuse existing conversation
    Note over B: conversation_id = "web_session_abc123"
    F->>WS: Send system_event message
    B->>B: Generate system message
    Note over B: "New Shopify merchant authenticated from X"
    B->>W: Process system message
    W->>B: Return insights response
    B->>WS: Send response to frontend
```

## Key Improvements

1. **Preserved Context**: conversation_id maintained through OAuth
2. **Correct Message Type**: system_event instead of oauth_complete
3. **Proper System Message**: Generates expected workflow trigger
4. **Connection Handling**: Waits for WebSocket before sending