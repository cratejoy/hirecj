# Full OAuth Implementation Test

## What's Implemented

1. **HMAC Verification** - All requests from Shopify are verified
2. **State Parameter** - CSRF protection with Redis storage
3. **Token Exchange** - Authorization code exchanged for access token
4. **Token Storage** - Access tokens stored securely in Redis
5. **Frontend Integration** - Button collects shop domain and initiates OAuth

## Prerequisites

- [ ] Redis running: `redis-cli ping` should return PONG
- [ ] Ngrok tunnels active: `make tunnels`
- [ ] Auth service running: `make dev-auth`
- [ ] Homepage running: `make dev-homepage`
- [ ] Agents service running: `make dev-agents`

## Test Steps

### 1. Clear Previous Data (Optional)
```bash
redis-cli
> del merchant:cratejoy-dev
> keys oauth_state:*
> exit
```

### 2. Start Fresh Chat
1. Navigate to https://amir.hirecj.ai/chat
2. Start a new conversation
3. CJ should present the "Connect Shopify" button

### 3. Click Connect Shopify
1. Click the button
2. If no saved shop:
   - Enter: `cratejoy-dev` or `cratejoy-dev.myshopify.com`
   - Click "Connect"
3. If shop was saved, it will redirect immediately

### 4. OAuth Flow
1. **Redirect to Auth Service**
   - URL: `https://amir-auth.hirecj.ai/api/v1/shopify/install?shop=cratejoy-dev.myshopify.com`
   - Check logs for: `[OAUTH_INSTALL] Initiating OAuth for shop: cratejoy-dev.myshopify.com`

2. **Redirect to Shopify**
   - URL: `https://cratejoy-dev.myshopify.com/admin/oauth/authorize?...`
   - Should see permissions page
   - Click "Install app"

3. **Callback from Shopify**
   - URL: `https://amir-auth.hirecj.ai/api/v1/shopify/callback?code=...&shop=...&hmac=...&state=...`
   - Check logs for:
     - `[OAUTH_CALLBACK] Received callback for shop: cratejoy-dev.myshopify.com`
     - `[TOKEN_EXCHANGE] Success for shop: cratejoy-dev.myshopify.com`
     - `[STORE_TOKEN] Created new merchant: cratejoy-dev.myshopify.com`

4. **Redirect to Frontend**
   - URL: `https://amir.hirecj.ai/chat?oauth=complete&is_new=true&merchant_id=merchant_cratejoy-dev&shop=cratejoy-dev.myshopify.com`
   - Should see success toast
   - CJ should acknowledge connection

### 5. Verify Token Storage
```bash
redis-cli
> get merchant:cratejoy-dev.myshopify.com
```

Should see JSON with:
- merchant_id
- shop_domain
- access_token
- created_at

### 6. Test Token Works (Optional)
Navigate to: `https://amir-auth.hirecj.ai/api/v1/shopify/test-shop?shop=cratejoy-dev.myshopify.com`

Should see shop data if token is valid.

## Security Verification

### HMAC Verification Test
Try to forge a callback:
```
https://amir-auth.hirecj.ai/api/v1/shopify/callback?shop=fake.myshopify.com&hmac=invalid&timestamp=123
```
Should redirect with error=invalid_hmac

### State Verification Test
1. Start OAuth flow, note the state parameter in Shopify URL
2. Try callback with wrong state:
```
https://amir-auth.hirecj.ai/api/v1/shopify/callback?shop=cratejoy-dev.myshopify.com&state=wrong&...
```
Should redirect with error=invalid_state

## Common Issues

### "Failed to initialize OAuth flow"
- Redis not running or not accessible
- Check: `redis-cli ping`

### "Invalid HMAC signature"  
- Client secret mismatch
- Check SHOPIFY_CLIENT_SECRET in .env.secrets

### "Token exchange failed"
- Invalid authorization code
- Network issues
- Check auth service logs for details

### Frontend doesn't redirect
- Check browser console for errors
- Verify VITE_AUTH_URL is set correctly

## Success Criteria

- [ ] Complete OAuth flow without errors
- [ ] Token stored in Redis
- [ ] Frontend receives OAuth completion
- [ ] Chat continues with authenticated merchant
- [ ] Security checks (HMAC, state) work correctly

## What's Next

After successful OAuth:
1. CJ can make API calls using the stored token
2. Phase 4 UI actions will have access to Shopify data
3. Can fetch products, orders, customers as needed