# Phase 3.5: Custom App Flow Testing Guide

## 🎯 What's Changed

We've replaced the standard OAuth flow with Shopify's custom app installation flow:

- **Removed**: `/oauth/shopify/authorize` and `/oauth/shopify/callback` endpoints
- **Added**: `/shopify/install`, `/shopify/verify`, `/shopify/status` endpoints
- **Simplified**: No more shop domain input - the custom install link handles it
- **Better UX**: One click to connect, no redirects

## 📋 Pre-Testing Checklist

### 1. Verify Environment Configuration
```bash
# Check that custom install link is configured
grep SHOPIFY_CUSTOM_INSTALL_LINK auth/.env.secrets
# Should show: SHOPIFY_CUSTOM_INSTALL_LINK=https://admin.shopify.com/oauth/install_custom_app?...
```

### 2. Check Service Changes
- Auth service: New endpoints at `/api/v1/shopify/*`
- Frontend: Updated ShopifyOAuthButton component
- No shop domain dialog anymore

## 🧪 Testing Steps

### Step 1: Start Services
```bash
# Terminal 1: Auth service
cd auth && make dev

# Terminal 2: Agents service  
cd agents && make dev

# Terminal 3: Homepage
cd homepage && npm run dev
```

### Step 2: Test Installation Flow

1. **Open Chat**
   - Navigate to https://amir.hirecj.ai
   - Start conversation with CJ

2. **Click Connect Shopify**
   - Button should say "Connect Shopify"
   - No dialog should appear asking for shop domain
   - A popup window should open immediately

3. **In the Popup Window**
   - You should see Shopify's custom app installation page
   - It should already know your shop (from the install link)
   - Click "Install app"

4. **Watch the Magic**
   - The popup should close automatically
   - The button should show "Connecting..."
   - After a few seconds, you should be redirected back to chat

5. **Verify Success**
   - URL should contain parameters like:
     - `oauth=complete`
     - `is_new=true` (first time) or `is_new=false` (returning)
     - `merchant_id=merchant_xxx`
     - `shop=your-store.myshopify.com`
   - CJ should acknowledge the connection

### Step 3: Test Returning Merchant

1. **Repeat the Process**
   - Click "Connect Shopify" again with the same store
   - This time `is_new=false` should appear in the URL
   - CJ should recognize you as a returning merchant

## 📊 What to Check in Logs

### Auth Service Logs
```
[CUSTOM_INSTALL] Starting custom app installation for conversation=xxx
[CUSTOM_INSTALL_SUCCESS] Custom app installed for shop=xxx, is_new=true
```

### Frontend Console
- No errors about missing endpoints
- Polling requests to `/api/v1/shopify/status/{session_id}`
- Successful verification request to `/api/v1/shopify/verify`

## 🐛 Common Issues

### Issue: "Custom app install link not configured"
**Solution**: Make sure `SHOPIFY_CUSTOM_INSTALL_LINK` is set in auth/.env.secrets

### Issue: Popup blocked
**Solution**: Allow popups for the site in your browser

### Issue: Installation times out
**Possible causes**:
- Install link expired (check Shopify Partners dashboard)
- Session token validation not implemented (currently mocked)

### Issue: "Session not found" error
**Solution**: Don't wait too long between clicking Connect and installing

## 🔍 Debug Mode

To see more details, check the auth service logs:
```bash
# In the auth service terminal
# You should see detailed logs for each step
```

## ✅ Success Indicators

1. **Clean Flow**: Click button → Install in popup → Back to chat
2. **No Errors**: No console errors or failed requests
3. **Proper Detection**: New vs returning merchant status is correct
4. **CJ Response**: CJ acknowledges the connection appropriately

## 🚀 Next Steps

Once testing passes:
1. Implement real session token validation (currently mocked)
2. Add proper JWT verification with Shopify's public key
3. Implement actual token exchange API call
4. Add error recovery for edge cases

## 📝 Notes

- The `session_token` is currently mocked as 'mock-session-token'
- In production, this would come from Shopify App Bridge
- The polling interval is 2 seconds, timeout is 10 minutes
- Install sessions expire after 30 minutes