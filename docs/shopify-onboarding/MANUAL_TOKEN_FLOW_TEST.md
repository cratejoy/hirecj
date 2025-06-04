# Manual Token Entry Flow - Test Plan

## Prerequisites
- [ ] Redis running locally: `brew services start redis`
- [ ] Auth service running: `make dev-auth`
- [ ] Homepage running: `make dev-homepage`
- [ ] Agents service running: `make dev-agents`

## Test Steps

### 1. Start Fresh Chat
1. Navigate to http://localhost:3456/chat
2. Start a new conversation
3. Note the conversation_id in the URL

### 2. Click Connect Shopify
1. CJ should present the "Connect Shopify" button
2. Click the button
3. Should redirect to Shopify install page

### 3. Install App on Shopify
1. On Shopify's install page, click "Install app"
2. Should redirect to auth service token entry form
3. URL should be: `http://localhost:8103/api/v1/shopify/connected?shop=...&hmac=...`

### 4. Token Entry Form
Verify the form displays:
- [ ] Beta testing notice (blue box)
- [ ] Shop domain shown correctly
- [ ] Clear instructions (6 steps)
- [ ] Password input field
- [ ] "Complete Setup" button
- [ ] Warning about one-time token

### 5. Get Access Token from Shopify
1. Open new tab, go to Shopify Admin
2. Settings → Apps and sales channels
3. Find HireCJ app
4. Click "API credentials"
5. Click "Reveal token once"
6. Copy the token (starts with `shpat_`)

### 6. Submit Token
1. Return to token entry form
2. Paste the token
3. Click "Complete Setup"

### 7. Verify Success Redirect
Should redirect to: `http://localhost:3456/chat?oauth=complete&is_new=true&merchant_id=...&shop=...`
- [ ] OAuth toast notification appears
- [ ] CJ acknowledges connection
- [ ] Shop domain stored in localStorage
- [ ] WebSocket receives oauth_complete message

### 8. Test Invalid Token
1. Start flow again with new conversation
2. At token entry, submit invalid token (e.g., "invalid_token")
3. Should see error page with:
   - "Invalid Token" heading
   - Instructions to check token
   - "Go Back and Try Again" link

## Backend Verification

Check logs for:
```
[SHOPIFY_CONNECTED] App installed for shop: {shop}
[SAVE_TOKEN] Attempting to save token for shop: {shop}
[SAVE_TOKEN] New merchant created: {shop}
```

Check Redis:
```bash
redis-cli
> keys merchant:*
> get merchant:cratejoy
```

## Common Issues

### "Connection refused" on auth service
- Ensure auth service is running: `make dev-auth`
- Check port 8103 is free

### Redis connection error
- Start Redis: `brew services start redis`
- Check Redis is running: `redis-cli ping`

### Token validation fails
- Ensure token starts with `shpat_`
- Token must be from the correct shop
- Token must have required permissions

## Success Criteria
- [ ] Complete flow works end-to-end
- [ ] Token stored in Redis
- [ ] Frontend receives OAuth parameters
- [ ] Chat continues with authenticated merchant
- [ ] Error handling works for invalid tokens