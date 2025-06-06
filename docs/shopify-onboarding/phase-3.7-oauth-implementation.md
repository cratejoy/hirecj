# Phase 3.7: OAuth 2.0 Implementation - Detailed Implementation Guide

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Standard OAuth flow is simpler than manual token entry
2. **No Cruft**: Remove ALL manual token code - pure OAuth implementation
3. **Break It & Fix It Right**: Complete replacement of custom distribution with OAuth
4. **Long-term Elegance**: Production-ready OAuth that works for any Shopify app type
5. **Backend-Driven**: Backend handles OAuth complexity, frontend just initiates
6. **Single Source of Truth**: One auth pattern - OAuth 2.0 authorization code grant
7. **No Over-Engineering**: Standard OAuth, no custom flows
8. **Thoughtful Logging**: Clear logs for each OAuth step

## ✅ DOs and ❌ DON'Ts

### ✅ DO:
- **DO** implement standard OAuth 2.0 authorization code grant
- **DO** verify HMAC on all Shopify requests
- **DO** use state parameter to prevent CSRF
- **DO** exchange authorization codes promptly
- **DO** store tokens securely in Redis
- **DO** validate shop domain format
- **DO** handle errors gracefully

### ❌ DON'T:
- **DON'T** expose client secret in frontend code
- **DON'T** skip HMAC verification
- **DON'T** reuse authorization codes
- **DON'T** store tokens in plain text
- **DON'T** trust user input without validation
- **DON'T** implement custom auth flows

## Overview

Implement standard Shopify OAuth 2.0 authorization code grant flow. This replaces the manual token entry required for custom distribution apps with a seamless OAuth flow that works for any Shopify app type.

## Deliverables Checklist

- [ ] Configure app URLs in Shopify Partners Dashboard
- [ ] Implement `/api/v1/shopify/install` endpoint
- [ ] Implement `/api/v1/shopify/callback` endpoint  
- [ ] Add HMAC verification utilities
- [ ] Update frontend button to use OAuth flow
- [ ] Remove all manual token code
- [ ] Test complete OAuth flow
- [ ] Update documentation

## Prerequisites

- Shopify OAuth app created in Partners Dashboard
- Client ID: `596df18067f0540b4daf9f7a202854da`
- Client Secret: `6607991578670584036f4498350fad8c` (stored securely)
- Redis running for state/token storage
- Ngrok tunnels configured for HTTPS

## Step-by-Step Implementation

### 1. Configure Shopify App URLs

**In Shopify Partners Dashboard:**

1. Go to your app settings
2. Set **App URL**: `https://amir-auth.hirecj.ai/api/v1/shopify/install`
3. Add **Allowed redirection URL**: `https://amir-auth.hirecj.ai/api/v1/shopify/callback`
4. Save changes

### 2. Create HMAC Verification Utility

**File**: `auth/app/services/shopify_auth.py`

```python
"""Shopify OAuth utilities."""

import hmac
import hashlib
import secrets
import base64
from typing import Dict, Optional
from urllib.parse import urlencode
from app.config import settings

class ShopifyAuth:
    """Handle Shopify OAuth operations."""
    
    @staticmethod
    def verify_hmac(params: Dict[str, str]) -> bool:
        """
        Verify HMAC signature from Shopify.
        
        Args:
            params: Query parameters from Shopify
            
        Returns:
            True if HMAC is valid
        """
        # Extract and remove HMAC from params
        provided_hmac = params.pop('hmac', None)
        if not provided_hmac:
            return False
        
        # Sort parameters and create query string
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        
        # Calculate HMAC
        secret = settings.shopify_client_secret.encode('utf-8')
        message = query_string.encode('utf-8')
        calculated_hmac = hmac.new(
            secret, 
            message, 
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(calculated_hmac, provided_hmac)
    
    @staticmethod
    def validate_shop_domain(shop: str) -> bool:
        """
        Validate shop domain format.
        
        Args:
            shop: Shop domain (e.g., "example.myshopify.com")
            
        Returns:
            True if valid Shopify domain
        """
        if not shop:
            return False
        
        # Must end with .myshopify.com
        if not shop.endswith('.myshopify.com'):
            return False
        
        # Extract subdomain
        subdomain = shop.replace('.myshopify.com', '')
        
        # Validate subdomain format (alphanumeric and hyphens)
        import re
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]$'
        return bool(re.match(pattern, subdomain))
    
    @staticmethod
    def generate_state() -> str:
        """Generate secure random state for OAuth."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def build_auth_url(shop: str, state: str, redirect_uri: str) -> str:
        """
        Build Shopify OAuth authorization URL.
        
        Args:
            shop: Shop domain
            state: Random state for CSRF protection
            redirect_uri: OAuth callback URL
            
        Returns:
            Full authorization URL
        """
        params = {
            'client_id': settings.shopify_client_id,
            'scope': settings.shopify_scopes,
            'redirect_uri': redirect_uri,
            'state': state
        }
        
        query_string = urlencode(params)
        return f"https://{shop}/admin/oauth/authorize?{query_string}"

# Singleton instance
shopify_auth = ShopifyAuth()
```

### 3. Implement Install Endpoint

**File**: `auth/app/api/shopify_oauth.py`

```python
"""Shopify OAuth API routes."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from urllib.parse import urlencode

from app.config import settings
from app.services.merchant_storage import merchant_storage
from app.services.shopify_auth import shopify_auth

logger = logging.getLogger(__name__)

router = APIRouter()

# Redis keys
STATE_PREFIX = "oauth_state:"
STATE_TTL = 600  # 10 minutes


@router.get("/install")
async def initiate_oauth(
    shop: str = Query(..., description="Shop domain"),
    hmac: Optional[str] = Query(None, description="HMAC for verification"),
    timestamp: Optional[str] = Query(None, description="Request timestamp")
):
    """
    Initiate OAuth flow by redirecting to Shopify authorization page.
    
    This endpoint is called in two scenarios:
    1. Initial app installation (from Shopify with HMAC)
    2. Re-authorization (from our frontend)
    """
    logger.info(f"[OAUTH_INSTALL] Initiating OAuth for shop: {shop}")
    
    # Validate shop domain
    if not shopify_auth.validate_shop_domain(shop):
        logger.error(f"[OAUTH_INSTALL] Invalid shop domain: {shop}")
        raise HTTPException(status_code=400, detail="Invalid shop domain")
    
    # If HMAC provided, verify it (initial install from Shopify)
    if hmac:
        params = {"shop": shop, "hmac": hmac}
        if timestamp:
            params["timestamp"] = timestamp
            
        if not shopify_auth.verify_hmac(params.copy()):
            logger.error(f"[OAUTH_INSTALL] Invalid HMAC for shop: {shop}")
            raise HTTPException(status_code=401, detail="Invalid HMAC")
    
    # Generate and store state
    state = shopify_auth.generate_state()
    state_key = f"{STATE_PREFIX}{state}"
    
    # Store state with shop domain in Redis
    await merchant_storage.redis_client.setex(
        state_key,
        STATE_TTL,
        shop
    )
    
    logger.info(f"[OAUTH_INSTALL] Generated state for shop {shop}: {state}")
    
    # Build authorization URL
    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/shopify/callback"
    auth_url = shopify_auth.build_auth_url(shop, state, redirect_uri)
    
    logger.info(f"[OAUTH_INSTALL] Redirecting shop {shop} to authorization")
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def handle_oauth_callback(
    code: Optional[str] = Query(None, description="Authorization code"),
    shop: str = Query(..., description="Shop domain"),
    hmac: str = Query(..., description="HMAC for verification"),
    state: str = Query(..., description="State for CSRF protection"),
    timestamp: str = Query(..., description="Request timestamp"),
    host: Optional[str] = Query(None, description="Base64 encoded host")
):
    """
    Handle OAuth callback from Shopify with authorization code.
    Exchange code for access token and store it.
    """
    logger.info(f"[OAUTH_CALLBACK] Received callback for shop: {shop}")
    
    # Verify HMAC
    params = {
        "code": code,
        "shop": shop,
        "hmac": hmac,
        "state": state,
        "timestamp": timestamp
    }
    if host:
        params["host"] = host
    
    if not shopify_auth.verify_hmac(params.copy()):
        logger.error(f"[OAUTH_CALLBACK] Invalid HMAC for shop: {shop}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=invalid_hmac",
            status_code=302
        )
    
    # Verify state
    state_key = f"{STATE_PREFIX}{state}"
    stored_shop = await merchant_storage.redis_client.get(state_key)
    
    if not stored_shop or stored_shop != shop:
        logger.error(f"[OAUTH_CALLBACK] Invalid state for shop: {shop}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=invalid_state",
            status_code=302
        )
    
    # Delete used state
    await merchant_storage.redis_client.delete(state_key)
    
    # Check if we have authorization code
    if not code:
        logger.error(f"[OAUTH_CALLBACK] Missing authorization code for shop: {shop}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=missing_code",
            status_code=302
        )
    
    # Exchange code for access token
    try:
        token_url = f"https://{shop}/admin/oauth/access_token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": settings.shopify_client_id,
                    "client_secret": settings.shopify_client_secret,
                    "code": code
                }
            )
            
            if response.status_code != 200:
                logger.error(
                    f"[OAUTH_CALLBACK] Token exchange failed for shop {shop}: "
                    f"{response.status_code} - {response.text}"
                )
                return RedirectResponse(
                    url=f"{settings.frontend_url}/chat?error=token_exchange_failed",
                    status_code=302
                )
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            scope = token_data.get("scope", "")
            
            if not access_token:
                logger.error(f"[OAUTH_CALLBACK] No access token in response for shop: {shop}")
                return RedirectResponse(
                    url=f"{settings.frontend_url}/chat?error=no_token",
                    status_code=302
                )
        
        logger.info(f"[OAUTH_CALLBACK] Successfully exchanged code for token, shop: {shop}")
        
        # Check if merchant exists
        merchant = await merchant_storage.get_merchant(shop)
        is_new = merchant is None
        
        if is_new:
            # Create new merchant
            merchant_id = f"merchant_{shop.replace('.myshopify.com', '')}"
            await merchant_storage.create_merchant({
                "merchant_id": merchant_id,
                "shop_domain": shop,
                "access_token": access_token,
                "scope": scope,
                "created_at": datetime.utcnow()
            })
            logger.info(f"[OAUTH_CALLBACK] Created new merchant: {shop}")
        else:
            # Update existing merchant
            await merchant_storage.update_token(shop, access_token)
            merchant_id = merchant.get("merchant_id", f"merchant_{shop.replace('.myshopify.com', '')}")
            logger.info(f"[OAUTH_CALLBACK] Updated existing merchant: {shop}")
        
        # Redirect to frontend with success
        redirect_params = {
            "oauth": "complete",
            "is_new": str(is_new).lower(),
            "merchant_id": merchant_id,
            "shop": shop
        }
        
        redirect_url = f"{settings.frontend_url}/chat?{urlencode(redirect_params)}"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except httpx.RequestError as e:
        logger.error(f"[OAUTH_CALLBACK] Network error during token exchange: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=network_error",
            status_code=302
        )
    except Exception as e:
        logger.error(f"[OAUTH_CALLBACK] Unexpected error: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=internal_error",
            status_code=302
        )
```

### 4. Update Frontend Button

**File**: `homepage/src/components/ShopifyOAuthButton.tsx`

```typescript
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';

interface ShopifyOAuthButtonProps {
  conversationId: string;
  text?: string;
  className?: string;
  disabled?: boolean;
}

export const ShopifyOAuthButton: React.FC<ShopifyOAuthButtonProps> = ({
  conversationId,
  text = 'Connect Shopify',
  className = '',
  disabled = false
}) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const [shopDomain, setShopDomain] = useState('');
  const [showShopInput, setShowShopInput] = useState(false);

  const handleConnect = () => {
    // Check if we have a shop domain in localStorage
    const savedShop = localStorage.getItem('shopify_shop_domain');
    
    if (savedShop) {
      // Use saved shop domain
      initiateOAuth(savedShop);
    } else {
      // Show input for shop domain
      setShowShopInput(true);
    }
  };

  const initiateOAuth = (shop: string) => {
    setIsConnecting(true);
    
    // Validate shop domain format
    if (!shop.endsWith('.myshopify.com')) {
      shop = `${shop}.myshopify.com`;
    }
    
    // Save shop domain for future use
    localStorage.setItem('shopify_shop_domain', shop);
    
    // Redirect to auth service install endpoint
    const authUrl = import.meta.env.VITE_AUTH_URL || 'https://amir-auth.hirecj.ai';
    const installUrl = `${authUrl}/api/v1/shopify/install?shop=${encodeURIComponent(shop)}`;
    
    // Store conversation ID for later
    sessionStorage.setItem('shopify_oauth_conversation_id', conversationId);
    
    // Redirect to start OAuth flow
    window.location.href = installUrl;
  };

  if (showShopInput) {
    return (
      <div className="space-y-2">
        <input
          type="text"
          placeholder="yourstore.myshopify.com"
          value={shopDomain}
          onChange={(e) => setShopDomain(e.target.value)}
          className="w-full px-3 py-2 border rounded"
          onKeyPress={(e) => {
            if (e.key === 'Enter' && shopDomain) {
              initiateOAuth(shopDomain);
            }
          }}
        />
        <div className="flex gap-2">
          <Button
            onClick={() => initiateOAuth(shopDomain)}
            disabled={!shopDomain || isConnecting}
            className={`bg-shopify-green hover:bg-shopify-green-dark text-white ${className}`}
          >
            {isConnecting ? 'Redirecting...' : 'Connect'}
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setShowShopInput(false);
              setShopDomain('');
            }}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <Button
      onClick={handleConnect}
      disabled={disabled || isConnecting}
      className={`bg-shopify-green hover:bg-shopify-green-dark text-white ${className}`}
      size="lg"
    >
      {isConnecting ? 'Redirecting to Shopify...' : text}
    </Button>
  );
};
```

### 5. Update Main API Router

**File**: `auth/app/main.py`

Add the new OAuth router:

```python
from app.api import health, shopify_oauth

# Register routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(shopify_oauth.router, prefix="/api/v1/shopify", tags=["shopify"])
```

### 6. Configuration Updates

**File**: `auth/app/config.py`

Ensure these settings are available:

```python
# Shopify OAuth Configuration
shopify_client_id: str = Field(..., env="SHOPIFY_CLIENT_ID")
shopify_client_secret: str = Field(..., env="SHOPIFY_CLIENT_SECRET")
shopify_scopes: str = Field(
    "read_products,read_orders,read_customers",
    env="SHOPIFY_SCOPES"
)

# OAuth Redirect Configuration
oauth_redirect_base_url: str = Field(
    "https://amir-auth.hirecj.ai",
    env="OAUTH_REDIRECT_BASE_URL"
)
```

## API Specifications

### Install Endpoint
```
GET /api/v1/shopify/install
Query Parameters:
  - shop: Shop domain (required)
  - hmac: HMAC signature (optional, from Shopify)
  - timestamp: Request timestamp (optional)

Response:
302 Redirect to Shopify authorization page
```

### Callback Endpoint
```
GET /api/v1/shopify/callback
Query Parameters:
  - code: Authorization code
  - shop: Shop domain
  - hmac: HMAC signature
  - state: CSRF protection state
  - timestamp: Request timestamp
  - host: Base64 encoded host (optional)

Response:
302 Redirect to frontend with:
  - oauth=complete
  - is_new=true/false
  - merchant_id=merchant_xxx
  - shop=example.myshopify.com
```

## Database Schema

### Redis Keys
```
oauth_state:{state} -> shop_domain (TTL: 10 minutes)

merchant:{shop_domain} -> JSON {
  merchant_id: string
  shop_domain: string
  access_token: string (encrypted)
  scope: string
  created_at: ISO datetime
  last_seen: ISO datetime
}
```

## Testing Checklist

### Integration Tests

1. **Complete OAuth Flow**
   ```
   1. Click "Connect Shopify" button
   2. Enter shop domain (or use saved)
   3. Redirect to Shopify authorization
   4. Approve permissions
   5. Callback receives code
   6. Code exchanged for token
   7. Token stored in Redis
   8. Redirect to chat with success
   ```

2. **Security Tests**
   - Invalid HMAC returns error
   - Invalid state returns error
   - Missing code returns error
   - Invalid shop domain rejected
   - Expired state rejected

### Manual Testing Script

```bash
# 1. Start services
make tunnels
make dev-auth
make dev-homepage
make dev-agents

# 2. Navigate to chat
open https://amir.hirecj.ai/chat

# 3. Click Connect Shopify
# 4. Enter shop domain
# 5. Approve on Shopify
# 6. Verify redirect back with oauth=complete
```

## Security Considerations

### HMAC Verification
- All requests from Shopify must be HMAC verified
- Use constant-time comparison to prevent timing attacks
- Never trust user input without verification

### State Parameter
- Generate cryptographically secure random state
- Store in Redis with TTL
- Verify on callback to prevent CSRF
- Delete after use

### Token Storage
- Encrypt access tokens before storage
- Use Redis with appropriate TTL
- Never expose tokens to frontend
- Rotate encryption keys periodically

### Shop Domain Validation
- Must end with `.myshopify.com`
- Validate subdomain format
- Prevent injection attacks

## Common Issues & Solutions

### Issue 1: "Invalid HMAC" error
**Cause**: Query parameters modified or secret mismatch
**Solution**: Ensure client secret is correct and params unmodified

### Issue 2: "Invalid state" error
**Cause**: State expired or doesn't match
**Solution**: Check Redis connection and TTL settings

### Issue 3: Token exchange fails
**Cause**: Invalid code or network issues
**Solution**: Check logs for specific error, verify credentials

### Issue 4: Redirect loop
**Cause**: App URL misconfigured in Shopify
**Solution**: Verify App URL matches install endpoint

## Performance Considerations

- State stored in Redis with 10-minute TTL
- Token exchange typically < 500ms
- No polling required - direct redirects
- Single Redis lookup per callback

## Monitoring & Logging

### Key Metrics
- OAuth initiation rate
- Callback success rate
- Token exchange latency
- HMAC verification failures
- State validation failures

### Log Entries
```
[OAUTH_INSTALL] Initiating OAuth for shop: example.myshopify.com
[OAUTH_CALLBACK] Successfully exchanged code for token, shop: example.myshopify.com
[OAUTH_CALLBACK] Invalid HMAC for shop: example.myshopify.com
```

## Migration from Manual Token Entry

1. Deploy OAuth endpoints
2. Update frontend button
3. Test OAuth flow
4. Remove manual token endpoints
5. Update documentation

## Next Phase Dependencies

Phase 4 (UI Actions) needs:
- Merchant authenticated via OAuth
- Access token stored in Redis
- Shop domain available in context

## Rollback Plan

If OAuth implementation has issues:
1. Revert to manual token entry (Phase 3.6)
2. Update frontend to use manual flow
3. Investigate and fix OAuth issues
4. Re-deploy when ready

---

## Implementation Summary

This OAuth implementation provides:
- **Standard flow**: Works with any Shopify app type
- **Security**: HMAC verification, state parameter, validated domains
- **Simplicity**: No manual steps for merchants
- **Production ready**: Can be used for public apps

The key insight is that OAuth eliminates the manual token entry limitation of custom distribution apps, providing a seamless merchant experience.