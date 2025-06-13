# OAuth Flow Testing Guide

## Overview
This guide walks through testing the complete OAuth flow with the new two-layer session pattern.

## Prerequisites
1. Both services (auth and agents) must be running
2. Frontend must be accessible
3. Shopify app credentials must be configured

## Test Steps

### 1. Start Services
```bash
# Terminal 1: Start auth service
cd auth
make run

# Terminal 2: Start agents service  
cd agents
make run

# Terminal 3: Start homepage/frontend
cd homepage
npm run dev
```

### 2. Test OAuth Flow

1. **Navigate to Shopify Onboarding**
   - Go to the frontend URL
   - Start a new conversation with workflow: `shopify_onboarding`
   - You should see the onboarding flow with a "Connect to Shopify" button

2. **Click Connect to Shopify**
   - This should redirect you to Shopify's OAuth page
   - Log in with your test store credentials
   - Approve the app permissions

3. **Verify Redirect & Cookie**
   - After approval, you should be redirected back to the chat
   - Open browser dev tools → Application → Cookies
   - Look for `hirecj_session` cookie:
     - Should have domain `.hirecj.ai` (in production)
     - Should be HTTP-only and Secure
     - Should have a valid session ID starting with `sess_`

4. **Verify Post-Auth Workflow**
   - The chat should automatically show the `shopify_post_auth` workflow
   - You should see:
     - Connection confirmation message
     - Store overview with key metrics
     - Transition to the appropriate next workflow

### 3. Test Session Persistence

1. **Refresh the Page**
   - The session should persist
   - You should still be logged in
   - The conversation should resume where you left off

2. **Open New Tab**
   - Navigate to the same conversation URL
   - You should see the same session state
   - No need to re-authenticate

### 4. Check Logs

**Auth Service Logs:**
```
[OAUTH_INSTALL] Initiating OAuth for shop: your-store.myshopify.com
[OAUTH_CALLBACK] Received callback for shop: your-store.myshopify.com
[OAUTH_CALLBACK] Set session cookie for user <user_id> (domain: .hirecj.ai)
[OAUTH] Successfully notified agents service of OAuth completion
```

**Agents Service Logs:**
```
[INTERNAL_API] OAuth completion notification for conversation: <conversation_id>
[POST_OAUTH] Handling OAuth completion for conversation: <conversation_id>
[POST_OAUTH] Created session <session_id> with shopify_post_auth workflow
[POST_OAUTH] Successfully prepared post-auth state
[POST_OAUTH] Retrieved post-auth state for conversation <conversation_id>
```

## Common Issues

### Cookie Not Set
- Check if the domain is correct in auth service logs
- Verify HTTPS is being used (cookies are secure-only)
- Check browser console for any cookie-related errors

### Workflow Doesn't Transition
- Verify the agents service received the OAuth completion notification
- Check if PostOAuthHandler created the session successfully
- Ensure WebSocket reconnects after redirect

### Session Not Found
- Check if the cookie is being sent with requests
- Verify the session hasn't expired (24-hour TTL)
- Check database for the session record

## Debug Commands

```bash
# Check if web_sessions table has records
cd agents
python -c "
from app.utils.supabase_util import get_db_session
from shared.db_models import WebSession
from sqlalchemy import select
with get_db_session() as db:
    count = db.query(WebSession).count()
    print(f'Total sessions: {count}')
    recent = db.query(WebSession).order_by(WebSession.created_at.desc()).first()
    if recent:
        print(f'Most recent: {recent.session_id} for user {recent.user_id}')
"

# Check OAuth completion states in memory
curl http://localhost:8001/api/v1/internal/oauth/completed \
  -H "Content-Type: application/json" \
  -d '{
    "shop_domain": "test-store.myshopify.com",
    "is_new": false,
    "conversation_id": "test-conv-123",
    "user_id": "test-user-123"
  }'
```

## Success Criteria

✅ OAuth flow completes without errors
✅ Session cookie is set with correct domain
✅ User sees shopify_post_auth workflow content
✅ Session persists across page refreshes
✅ No session_update messages in WebSocket
✅ User identity is available in all requests