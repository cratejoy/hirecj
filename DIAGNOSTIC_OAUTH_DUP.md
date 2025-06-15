# OAuth Duplicate Message Diagnostics

## Issue
Getting two "Shopify authentication complete!" messages after OAuth completion.

## Diagnostic Logs Added

### Frontend (useWebSocketChat.ts)
- `[CJ_DUP]` - Logs when CJ messages contain "authentication complete"

### Backend Logs
1. **Agent Creation**
   - `[AGENT_CREATE]` - When create_cj_agent is called
   - `[AGENT_INIT]` - When CJAgent is initialized
   
2. **OAuth Flow**
   - `[OAUTH_HOOK]` - When handle_oauth_complete is called
   
3. **Workflow Transitions**
   - `[WORKFLOW_HOOK]` - When workflow transition happens
   - `[WORKFLOW_INITIAL]` - When initial workflow action is triggered
   
4. **Message Generation**
   - `[MSG_GEN]` - When CJ generates a response with OAuth content

## Expected Flow
1. User completes OAuth
2. Auth service sets `next_workflow: shopify_post_auth` in session
3. Frontend sends `oauth_complete` message
4. Backend handle_oauth_complete stores OAuth metadata
5. On next start_conversation, workflow transitions to shopify_post_auth
6. shopify_post_auth initial_action triggers "SYSTEM_EVENT: shopify_oauth_complete"
7. CJ generates ONE authentication complete message

## What to Look For
- Multiple `[AGENT_CREATE]` or `[AGENT_INIT]` with same session
- Multiple `[MSG_GEN]` with has_oauth_complete=true
- Timing between `[OAUTH_HOOK]` and `[WORKFLOW_HOOK]`
- Whether `[WORKFLOW_INITIAL]` is called twice

## Theories
1. **Double Agent Init** - Agent recreated after OAuth
2. **Multiple Workflow Hooks** - Both OAuth and workflow transition trigger messages  
3. **Race Condition** - Generic message before data loads, detailed message after