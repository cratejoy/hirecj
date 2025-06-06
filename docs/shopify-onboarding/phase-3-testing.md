# Phase 3: OAuth Production Testing Guide

## 🎯 Testing Overview

Phase 3 implementation is complete. Here's what has been configured:

### ✅ Completed Tasks
1. **OAuth Port Configuration**: Already correctly set to 8103
2. **Shopify Credentials**: Configured in auth/.env.secrets
   - Client ID: 2b337814e5611cc5143a7fc0f16abc14
   - Client Secret: (configured)
3. **Homepage Auth URL**: Automatically loads from unified env config
4. **Tunnel Detection**: Working correctly
   - Auth service: https://amir-auth.hirecj.ai
   - Homepage: https://amir.hirecj.ai
5. **Merchant Detection**: Logic implemented in auth service

## 📋 Manual Testing Steps

### 1. Verify Shopify App Configuration
1. Go to https://partners.shopify.com
2. Find your app (using Client ID: 2b337814e5611cc5143a7fc0f16abc14)
3. Verify OAuth callback URL is set to:
   ```
   https://amir-auth.hirecj.ai/api/v1/oauth/shopify/callback
   ```

### 2. Start All Services
```bash
# Terminal 1: Auth service
cd auth && make dev

# Terminal 2: Agents service  
cd agents && make dev

# Terminal 3: Homepage
cd homepage && npm run dev
```

### 3. Test OAuth Flow

#### New Merchant Test
1. Open https://amir.hirecj.ai
2. Start conversation with CJ
3. When prompted, click "Connect Shopify"
4. Enter a test shop domain (e.g., "test-store-new")
5. Complete Shopify OAuth
6. Verify:
   - Redirect back to chat works
   - URL contains `is_new=true`
   - CJ acknowledges as new merchant

#### Returning Merchant Test
1. Use the same shop domain again
2. Click "Connect Shopify"
3. Complete OAuth
4. Verify:
   - URL contains `is_new=false`
   - CJ acknowledges as returning merchant

### 4. Check Logs

#### Auth Service Logs
Look for:
```
[OAUTH_SUCCESS] OAuth completed for shop=test-store.myshopify.com, is_new=true, merchant_id=merchant_abc123
📡 Using detected tunnel URL: https://amir-auth.hirecj.ai
```

#### Frontend Console
Check for:
- No CORS errors
- OAuth complete event with correct parameters

## 🐛 Troubleshooting

### Common Issues

1. **"Shop domain required" error**
   - Make sure to enter a shop domain in the popup
   - Format: "store-name" or "store-name.myshopify.com"

2. **OAuth callback fails**
   - Check Shopify app callback URL matches exactly
   - Verify credentials in auth/.env.secrets

3. **CORS errors**
   - Auth service should auto-detect tunnel URLs
   - Check auth service logs for allowed origins

4. **"Invalid state" error**
   - State expires after 10 minutes
   - Try the OAuth flow again

## ✅ Success Criteria

- [ ] OAuth flow completes without errors
- [ ] Shop domain entry works smoothly
- [ ] Redirect back to chat preserves conversation
- [ ] New merchants see is_new=true
- [ ] Returning merchants see is_new=false
- [ ] CJ responds appropriately based on merchant status
- [ ] No CORS or tunnel errors

## 🚀 Next Steps

Once all tests pass, Phase 3 is complete! Phase 4 will add:
- Shopify API integration
- Quick insights service
- Store data visualization