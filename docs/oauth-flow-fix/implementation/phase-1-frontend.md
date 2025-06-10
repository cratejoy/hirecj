# Phase 1: Frontend Fixes

## Overview
Fix conversation continuity and convert to system events.

## Changes

### 1. useOAuthCallback.ts
```typescript
// BEFORE: Expects conversation_id in URL (not there)
conversation_id: params.get('conversation_id') || '',

// AFTER: Retrieve from sessionStorage
const storedConversationId = sessionStorage.getItem('shopify_oauth_conversation_id');
const callbackData: OAuthCallbackParams = {
  oauth: 'complete',
  conversation_id: storedConversationId || '',
  // ... rest of params
};

// Clean up storage
sessionStorage.removeItem('shopify_oauth_conversation_id');
```

### 2. SlackChat.tsx
```typescript
// BEFORE: Sends oauth_complete message
wsChat.sendSpecialMessage({
  type: 'oauth_complete',
  data: { /* ... */ }
});

// AFTER: Send system_event with retry
const sendSystemEvent = async () => {
  if (wsChat.isConnected) {
    wsChat.sendSpecialMessage({
      type: 'system_event',
      data: {
        event_type: 'oauth_complete',
        provider: 'shopify',
        is_new: params.is_new === 'true',
        merchant_id: params.merchant_id,
        shop_domain: params.shop,
        conversation_id: params.conversation_id
      }
    });
    return true;
  }
  // Retry logic...
};
```

## Testing
1. OAuth flow preserves conversation_id
2. system_event sent instead of oauth_complete
3. Retry mechanism works if WebSocket not ready