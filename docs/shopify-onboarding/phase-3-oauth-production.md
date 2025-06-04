# Phase 3: OAuth Production Ready - Implementation Guide

> **⚠️ CRITICAL UPDATE**: This guide is for PUBLIC Shopify apps only. If you have a custom distribution app (created through Partners dashboard with a custom install link), OAuth WILL NOT WORK. See [Phase 3.6: Custom Distribution Flow](phase-3.6-custom-distribution-flow.md) for the correct implementation.

## 🎯 Phase Objectives

Make Shopify OAuth work end-to-end with real credentials and ngrok tunnels. No data loading yet - just get authentication working reliably.

**North Star Principles Applied:**
- **Simplify**: Just OAuth, nothing else
- **No Cruft**: Remove placeholder values, use real credentials
- **Long-term Elegance**: Proper tunnel detection and configuration
- **Single Source of Truth**: Environment variables drive all URLs

## 📋 Implementation Steps

### 1. Configure Real Shopify OAuth Credentials

#### Create Shopify App (if not already done)
1. Go to https://partners.shopify.com
2. Create a new app or use existing
3. Set OAuth callback URL: `https://amir-auth.hirecj.ai/api/v1/oauth/shopify/callback`
4. Copy your Client ID and Client Secret

#### Update Auth Service Configuration
```bash
# auth/.env
SHOPIFY_CLIENT_ID=your_real_client_id_here
SHOPIFY_CLIENT_SECRET=your_real_client_secret_here
SHOPIFY_SCOPES=read_products,read_orders,read_customers

# These should already be set by tunnel detector
# PUBLIC_URL=https://amir-auth.hirecj.ai
# OAUTH_REDIRECT_BASE_URL=https://amir-auth.hirecj.ai
```

### 2. Fix Frontend Auth URL Configuration

The frontend needs to know where the auth service is running.

#### Update Homepage Environment
```bash
# homepage/.env
VITE_AUTH_URL=https://amir-auth.hirecj.ai
```

#### Verify OAuth Button Uses Correct URL
The OAuth button should already use `VITE_AUTH_URL` from the environment:

```typescript
// homepage/src/components/OAuthButton.tsx
const authBaseUrl = import.meta.env.VITE_AUTH_URL || 'http://localhost:8103';
```

### 3. Ensure Ngrok Tunnel Configuration

#### Verify Tunnel Detection Works
Both services should detect their tunnel URLs automatically:

```bash
# Check auth service tunnel
cat auth/.env.tunnel
# Should show:
# PUBLIC_URL=https://amir-auth.hirecj.ai
# OAUTH_REDIRECT_BASE_URL=https://amir-auth.hirecj.ai

# Check homepage tunnel  
cat homepage/.env.tunnel
# Should show:
# PUBLIC_URL=https://amir.hirecj.ai
# VITE_PUBLIC_URL=https://amir.hirecj.ai
```

#### Auth Service Auto-Detection
The auth service already has tunnel detection in `config.py`:

```python
# auth/app/config.py
@field_validator("oauth_redirect_base_url", mode="before")
@classmethod
def detect_tunnel_url(cls, v: Optional[str], values) -> str:
    """Automatically detect and use ngrok tunnel URL if available."""
    # Reads from .env.tunnel if available
```

### 4. Fix OAuth Callback URL Port

The auth service config has wrong default port (8003 instead of 8103).

```python
# auth/app/config.py - Line 132
# Change from:
default_url = f"http://localhost:{values.get('app_port', 8003)}"
# To:
default_url = f"http://localhost:{values.get('app_port', 8103)}"

# Also update line 60:
# Change from:
oauth_redirect_base_url: str = Field(
    "http://localhost:8003",
    env="OAUTH_REDIRECT_BASE_URL"
)
# To:
oauth_redirect_base_url: str = Field(
    "http://localhost:8103",
    env="OAUTH_REDIRECT_BASE_URL"
)
```

### 5. Verify CORS Configuration

Ensure the auth service allows requests from the frontend:

```python
# auth/app/main.py
# The CORS middleware should already include frontend origins
# The config auto-builds allowed origins including tunnel URLs
```

### 6. Test OAuth Flow End-to-End

#### Start All Services
```bash
# Terminal 1: Start auth service
cd auth && make dev

# Terminal 2: Start agents service  
cd agents && make dev

# Terminal 3: Start homepage
cd homepage && npm run dev
```

#### Test Flow
1. Open https://amir.hirecj.ai in browser
2. Start conversation with CJ
3. When prompted, click "Connect Shopify"
4. Enter your test shop domain (e.g., "test-store" or "test-store.myshopify.com")
5. Complete Shopify OAuth
6. Verify redirect back to chat
7. Confirm CJ acknowledges authentication

### 7. Debug Common Issues

#### Issue: "Shop domain required"
- The OAuth flow needs a shop domain
- Frontend should handle this in the OAuth popup

#### Issue: OAuth callback fails
- Check auth service logs for the exact error
- Verify SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET are set correctly
- Ensure callback URL in Shopify app matches exactly

#### Issue: CORS errors
- Check browser console for specific CORS error
- Verify auth service is using tunnel URL
- Check allowed_origins in auth service logs

#### Issue: "Invalid state parameter"
- State expired (>10 minutes)
- Try the OAuth flow again

### 8. Verify New vs Returning Detection

The auth service tracks merchants by shop domain:

```python
# auth/app/api/oauth.py
# Check if merchant is new or returning
is_new = shop not in _merchant_sessions
```

Test both flows:
1. New merchant: Use a shop domain that hasn't authenticated before
2. Returning merchant: Use the same shop domain again

CJ should respond differently based on `is_new` status.

## 🧪 Success Criteria

Phase 3 is complete when:
- [ ] Real Shopify OAuth credentials are configured
- [ ] OAuth flow works with ngrok tunnels
- [ ] Shop domain entry works (popup or inline)
- [ ] OAuth completes and redirects back to chat
- [ ] CJ acknowledges OAuth completion
- [ ] New vs returning merchant detection works
- [ ] No CORS or tunnel-related errors

## 🔧 Configuration Checklist

### Auth Service
- [ ] `SHOPIFY_CLIENT_ID` set to real value
- [ ] `SHOPIFY_CLIENT_SECRET` set to real value  
- [ ] `.env.tunnel` has correct `OAUTH_REDIRECT_BASE_URL`
- [ ] Default ports fixed in `config.py`

### Homepage
- [ ] `VITE_AUTH_URL` points to auth tunnel URL
- [ ] `.env.tunnel` has correct `VITE_PUBLIC_URL`

### Shopify App
- [ ] Callback URL matches auth service tunnel URL
- [ ] App has required scopes

## 🚀 Next Steps (Phase 4)

Once OAuth is working reliably, Phase 4 will add:
- Shopify API integration
- Quick insights service
- Progressive data loading
- Real-time store analysis

But first, nail the OAuth flow with real credentials and tunnels!

## 📝 Key Implementation Notes

### Simplicity First
- No mock data or placeholders
- Real credentials only
- Focus on OAuth working, nothing else

### Tunnel-Aware Configuration
- Services auto-detect their public URLs
- No hardcoded localhost URLs in production paths
- Environment variables drive everything

### Error Handling
- Clear error messages in logs
- Graceful fallbacks
- No silent failures

The goal: Click "Connect Shopify" → Complete OAuth → Back in chat with CJ acknowledging success. That's it!