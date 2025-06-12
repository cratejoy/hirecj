# Workflow Synchronization Test Plan

## What We Fixed

The frontend now updates its workflow state when receiving the `conversation_started` message from the backend. This ensures frontend and backend are always in sync.

## Testing the Fix

### 1. OAuth Flow Test
1. Start with `shopify_onboarding` workflow
2. Click OAuth button to connect Shopify
3. Complete OAuth flow
4. On return:
   - Backend sends `conversation_started` with `workflow: 'shopify_post_auth'`
   - Frontend updates to `shopify_post_auth`
   - URL updates to show `?workflow=shopify_post_auth`
   - UI shows post-auth experience

### 2. Page Reload Test
1. After OAuth, reload the page
2. Frontend sends `start_conversation` with whatever workflow is in URL
3. Backend responds with actual session workflow
4. Frontend updates to match backend's workflow

### 3. Direct Navigation Test
1. Navigate to `?workflow=shopify_onboarding&conversation_id=<existing-post-auth-id>`
2. Backend knows this conversation is post-auth
3. Sends `conversation_started` with `workflow: 'shopify_post_auth'`
4. Frontend updates to correct workflow

## Expected Console Logs

```javascript
// On WebSocket connection after OAuth:
[client.websocket] Conversation started {
  conversationId: "...",
  workflow: "shopify_post_auth",  // From backend
  ...
}
[client.websocket] Updating workflow from conversation_started {
  workflow: "shopify_post_auth",
  source: "backend"
}
[SlackChat] URL updated after workflow transition {
  from: "shopify_onboarding",
  to: "shopify_post_auth",
  url: "...?workflow=shopify_post_auth"
}
```

## Benefits

1. **No Silent Failures**: Frontend always reflects actual workflow
2. **Single Source of Truth**: Backend controls workflow state
3. **Elegant**: Frontend simply follows backend's lead
4. **User-Friendly**: URL and UI always show correct state