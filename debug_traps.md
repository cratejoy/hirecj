# OAuth Flow Debug Traps

I've added 11 debug traps to trace exactly what's happening. Here's what each trap catches:

## Frontend Traps

### TRAP 1: OAuth Callback Detection
- **Location**: SlackChat.tsx initialization
- **Triggers**: When URL has `oauth=complete`
- **Shows**: URL params, conversation IDs from OAuth and sessionStorage

### TRAP 2: Conversation ID Mismatch  
- **Location**: SlackChat.tsx initialization
- **Triggers**: OAuth callback WITHOUT conversation_id param
- **Shows**: Alert + console error with ID sources

### TRAP 3: OAuth Success Handler
- **Location**: SlackChat handleOAuthSuccess
- **Triggers**: When OAuth success callback runs
- **Shows**: Current vs OAuth conversation IDs, WebSocket state

### TRAP 4: System Event Send
- **Location**: SlackChat handleOAuthSuccess
- **Triggers**: Before sending system_event
- **Shows**: Complete event data being sent

### TRAP 5: Start Conversation After OAuth
- **Location**: useWebSocketChat onopen
- **Triggers**: When WebSocket sends start_conversation after OAuth
- **Shows**: Alert + conversation details

### TRAP 6: WebSocket Close After OAuth
- **Location**: useWebSocketChat onclose  
- **Triggers**: When WebSocket closes with OAuth params in URL
- **Shows**: Close code, reason, conversation ID

### TRAP 7: System Event Send Attempt
- **Location**: useWebSocketChat sendSpecialMessage
- **Triggers**: When trying to send system_event
- **Shows**: WebSocket ready state, message data

### TRAP 8: System Event Sent
- **Location**: useWebSocketChat sendSpecialMessage
- **Triggers**: When system_event successfully sent
- **Shows**: Exact data sent to WebSocket

### TRAP 9: System Event Queued
- **Location**: useWebSocketChat sendSpecialMessage
- **Triggers**: When system_event queued (WebSocket not ready)
- **Shows**: Ready state, queue length

### TRAP 10: Queue Flush With System Event
- **Location**: useWebSocketChat flushMessageQueue
- **Triggers**: When flushing queue that contains system_event
- **Shows**: Queue contents, all messages

### TRAP 11: URL Cleaning
- **Location**: useOAuthCallback
- **Triggers**: After OAuth callback processed
- **Shows**: URL before/after cleaning, callback data

## What To Look For

1. **Do you see TRAP 1?** - OAuth callback detected
2. **Do you see TRAP 2?** - Missing conversation ID (BAD)
3. **Do you see TRAP 3 & 4?** - OAuth handler running
4. **Do you see TRAP 5?** - New conversation starting (BAD)
5. **Do you see TRAP 6?** - WebSocket disconnecting 
6. **Do you see TRAP 7, 8, or 9?** - System event send status
7. **Do you see TRAP 10?** - System event in queue
8. **Do you see TRAP 11?** - URL being cleaned

## Backend Check

The server logs show NO system_event received, which means either:
- It's never sent (check TRAP 7-9)
- WebSocket disconnects before send (check TRAP 6)
- It's queued but not flushed (check TRAP 10)