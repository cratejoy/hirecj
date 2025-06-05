# Minimal OAuth Flow Test

## Purpose
Test our basic understanding of Shopify OAuth flow with minimal implementation.

## What We're Testing
- ✅ OAuth app configuration is correct
- ✅ Shopify recognizes our app
- ✅ Authorization redirect works
- ✅ Callback receives authorization code
- ✅ All required parameters are sent by Shopify

## Test Steps

### 1. Start Services
```bash
# Terminal 1: Start ngrok tunnels
make tunnels

# Terminal 2: Start auth service
make dev-auth
```

### 2. Check Auth Service
Navigate to: https://amir-auth.hirecj.ai/docs

You should see:
- `/api/v1/shopify/install` endpoint
- `/api/v1/shopify/callback` endpoint

### 3. Initiate OAuth Flow

Navigate to:
```
https://amir-auth.hirecj.ai/api/v1/shopify/install?shop=YOUR_SHOP.myshopify.com
```

Replace `YOUR_SHOP` with your actual shop subdomain.

### 4. Expected Flow

1. **Redirect to Shopify**
   - You should be redirected to Shopify's OAuth permission page
   - URL should be: `https://YOUR_SHOP.myshopify.com/admin/oauth/authorize?...`

2. **Permission Screen**
   - You'll see app permissions: "Read products, Read orders"
   - Click "Install app"

3. **Callback Redirect**
   - Shopify redirects to: `https://amir-auth.hirecj.ai/api/v1/shopify/callback?...`
   - You'll see JSON response showing received parameters

### 5. Check Logs
In the auth service terminal, look for:
```
[OAUTH_TEST] Install requested for shop: YOUR_SHOP.myshopify.com
[OAUTH_TEST] Redirecting to: https://...
[OAUTH_TEST] Callback received!
[OAUTH_TEST] shop: YOUR_SHOP.myshopify.com
[OAUTH_TEST] code: abc123def456...
[OAUTH_TEST] hmac: 1234567890abcdef...
```

## Success Criteria

✅ **OAuth Initiation Works** if:
- Shopify shows permission screen
- No "app not found" errors

✅ **Callback Works** if:
- JSON response shows `has_code: true`
- JSON response shows `has_hmac: true`
- Logs show authorization code received

## What This Validates

1. **App Configuration**
   - Client ID is correct
   - Redirect URL is properly configured
   - App is recognized by Shopify

2. **OAuth Flow**
   - We can initiate OAuth
   - Shopify sends back authorization code
   - All expected parameters are present

## Next Steps

If this test succeeds, we can implement:
1. HMAC verification
2. State parameter for CSRF protection
3. Token exchange
4. Proper error handling
5. Frontend integration

## Troubleshooting

**"App not found" error**
- Check client ID in .env.secrets
- Verify app exists in Partners Dashboard

**"Invalid redirect URI" error**
- Check callback URL in Partners Dashboard
- Must be exactly: `https://amir-auth.hirecj.ai/api/v1/shopify/callback`

**No authorization code**
- Check if you approved the permissions
- Look for error parameters in callback