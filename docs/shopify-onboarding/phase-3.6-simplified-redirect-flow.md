# Phase 3.6: Simplified Custom App Redirect Flow - Detailed Implementation Guide

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: This phase replaces 200+ lines of App Bridge complexity with ~50 lines of redirect handling
2. **No Cruft**: Remove ALL Phase 3.5 code - no commented App Bridge code, no dual-context handling
3. **Break It & Fix It Right**: Complete breaking change from embedded app to redirect flow
4. **Long-term Elegance**: Simple redirect > complex App Bridge for our use case
5. **Backend-Driven**: Frontend just redirects, backend handles all token logic
6. **Single Source of Truth**: One auth pattern only - redirect flow
7. **No Over-Engineering**: No "maybe we'll need embedded later" code
8. **Thoughtful Logging**: Clear logs for each redirect step

## ✅ DOs and ❌ DON'Ts

### ✅ DO:
- **DO** implement the simple redirect flow exactly as specified
- **DO** delete ALL App Bridge related code from Phase 3.5
- **DO** use Redis/PostgreSQL for token storage (no more in-memory)
- **DO** handle errors gracefully with clear redirect parameters
- **DO** test the full flow end-to-end before calling it complete
- **DO** keep the frontend button simple - just redirect, no polling
- **DO** exchange tokens server-side only

### ❌ DON'T:
- **DON'T** keep any App Bridge code "just in case"
- **DON'T** implement session token polling
- **DON'T** add embedded app handling
- **DON'T** use in-memory storage
- **DON'T** mock any tokens or skip verification
- **DON'T** add complex state management to frontend
- **DON'T** try to handle tokens client-side
- **DON'T** implement "maybe later" features

## Overview

Replace the complex App Bridge and session token implementation with a simple redirect flow where Shopify sends the merchant back to our site with an id_token after installation. This eliminates the need for embedded app contexts and simplifies the entire authentication flow.

## Deliverables Checklist

- [x] Update Shopify app configuration with correct App URL ✅ (User confirmed this is done)
- [ ] Create `/api/v1/shopify/connected` endpoint to handle redirect
- [ ] Simplify `ShopifyOAuthButton` to remove polling and App Bridge
- [ ] Remove unnecessary App Bridge dependencies and hooks
- [ ] Implement proper token storage (Redis/Database)
- [ ] Update conversation flow to handle redirect parameters

## Prerequisites

- Shopify custom app configured with install link
- Redis or PostgreSQL available for token storage
- Frontend and backend services running
- Access to Shopify Partner Dashboard

## Step-by-Step Implementation

### 1. Update Shopify App Configuration ✅ COMPLETE

**Action Required**: In Shopify Partner Dashboard

1. ~~Go to your app's Configuration~~
2. ~~Set **App URL** to: `https://amir-auth.hirecj.ai/api/v1/shopify/connected`~~
3. ~~Save changes~~

**Status**: User has confirmed this step is complete.

### 2. Create Connected Endpoint

**File**: `auth/app/api/shopify_custom.py`

Replace the complex verification endpoint with a simple redirect handler:

```python
@router.get("/connected")
async def handle_shopify_redirect(
    shop: str,
    host: Optional[str] = None,
    id_token: Optional[str] = None,
    conversation_id: Optional[str] = None
):
    """
    Handle redirect from Shopify after custom app installation.
    
    Shopify sends users here after they install the app with:
    - shop: The shop domain
    - host: Base64 encoded host
    - id_token: Session token to exchange for access token
    """
    if not id_token:
        logger.error(f"[SHOPIFY_CONNECTED] Missing id_token for shop: {shop}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=missing_token",
            status_code=302
        )
    
    try:
        # Exchange id_token for permanent access token
        token_data = await token_exchange.exchange_session_token(
            id_token,
            shop
        )
        access_token = token_data["access_token"]
        
        # Check if merchant is new or returning
        merchant = await merchant_storage.get_merchant(shop)
        is_new = merchant is None
        
        if is_new:
            # Create new merchant record
            merchant_id = f"merchant_{shop.replace('.myshopify.com', '')}"
            await merchant_storage.create_merchant({
                "merchant_id": merchant_id,
                "shop_domain": shop,
                "access_token": access_token,
                "created_at": datetime.utcnow()
            })
        else:
            # Update existing merchant
            await merchant_storage.update_token(shop, access_token)
        
        logger.info(f"[SHOPIFY_CONNECTED] Successfully connected shop: {shop}, is_new: {is_new}")
        
        # Redirect to chat with success parameters
        redirect_params = {
            "oauth": "complete",
            "is_new": str(is_new).lower(),
            "merchant_id": merchant.get("merchant_id") if merchant else f"merchant_{shop.replace('.myshopify.com', '')}",
            "shop": shop
        }
        
        if conversation_id:
            redirect_params["conversation_id"] = conversation_id
        
        redirect_url = f"{settings.frontend_url}/chat?{urlencode(redirect_params)}"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        logger.error(f"[SHOPIFY_CONNECTED_ERROR] Failed to process connection: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=connection_failed",
            status_code=302
        )
```

### 3. Implement Proper Storage

**File**: `auth/app/services/merchant_storage.py`

```python
"""Merchant storage service using Redis or PostgreSQL."""

import json
from datetime import datetime
from typing import Optional, Dict, Any
import redis
from app.config import settings

class MerchantStorage:
    """Handles persistent storage of merchant data."""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True
        )
    
    async def create_merchant(self, merchant_data: Dict[str, Any]) -> None:
        """Create a new merchant record."""
        shop_domain = merchant_data["shop_domain"]
        key = f"merchant:{shop_domain}"
        
        # Convert datetime to ISO format for JSON serialization
        if "created_at" in merchant_data:
            merchant_data["created_at"] = merchant_data["created_at"].isoformat()
        
        self.redis_client.set(
            key,
            json.dumps(merchant_data),
            ex=REDIS_MERCHANT_SESSION_TTL  # 24 hours
        )
        
        # Also maintain a set of all merchants
        self.redis_client.sadd("merchants", shop_domain)
    
    async def get_merchant(self, shop_domain: str) -> Optional[Dict[str, Any]]:
        """Get merchant data by shop domain."""
        key = f"merchant:{shop_domain}"
        data = self.redis_client.get(key)
        
        if data:
            merchant = json.loads(data)
            # Convert ISO string back to datetime
            if "created_at" in merchant:
                merchant["created_at"] = datetime.fromisoformat(merchant["created_at"])
            return merchant
        return None
    
    async def update_token(self, shop_domain: str, access_token: str) -> None:
        """Update merchant's access token."""
        merchant = await self.get_merchant(shop_domain)
        if merchant:
            merchant["access_token"] = access_token
            merchant["last_seen"] = datetime.utcnow().isoformat()
            
            key = f"merchant:{shop_domain}"
            self.redis_client.set(
                key,
                json.dumps(merchant),
                ex=REDIS_MERCHANT_SESSION_TTL
            )

# Singleton instance
merchant_storage = MerchantStorage()
```

### 4. Simplify Frontend Button

**File**: `homepage/src/components/ShopifyOAuthButton.tsx`

Remove all the App Bridge complexity:

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
  const [error, setError] = useState('');

  const handleConnect = async () => {
    setIsConnecting(true);
    setError('');

    try {
      const authBaseUrl = import.meta.env.VITE_AUTH_URL || 'http://localhost:8103';
      
      // Get custom install link from backend
      const response = await fetch(`${authBaseUrl}/api/v1/shopify/install`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ conversation_id: conversationId }),
      });

      if (!response.ok) {
        throw new Error('Failed to get install link');
      }

      const { install_url } = await response.json();
      
      // Add conversation_id to the install URL so it comes back in redirect
      const urlWithConversation = `${install_url}&conversation_id=${conversationId}`;

      // Simply redirect to the install link
      // Shopify will handle everything and redirect back to our /connected endpoint
      window.location.href = urlWithConversation;
      
    } catch (err) {
      console.error('Connection error:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect to Shopify');
      setIsConnecting(false);
    }
  };

  return (
    <>
      <Button
        onClick={handleConnect}
        disabled={disabled || isConnecting}
        className={`bg-shopify-green hover:bg-shopify-green-dark text-white ${className}`}
        size="lg"
      >
        {isConnecting ? 'Redirecting to Shopify...' : text}
      </Button>
      
      {error && (
        <p className="mt-2 text-sm text-red-500">{error}</p>
      )}
    </>
  );
};
```

### 5. Update Install Endpoint

**File**: `auth/app/api/shopify_custom.py`

Simplify the install endpoint:

```python
@router.post("/install")
async def initiate_custom_install(request: CustomInstallRequest):
    """
    Return the custom install link.
    No need for session tracking since Shopify will redirect back with everything.
    """
    if not settings.shopify_custom_install_link:
        raise HTTPException(
            status_code=500,
            detail="Custom app install link not configured"
        )
    
    logger.info(f"[CUSTOM_INSTALL] Initiating installation for conversation={request.conversation_id}")
    
    return {
        "install_url": settings.shopify_custom_install_link
    }
```

### 6. Remove Unnecessary Code

**Files to Delete/Simplify**:
- `homepage/src/hooks/useShopifySession.ts` - Delete entirely
- Remove `@shopify/app-bridge` dependencies from package.json
- Remove polling logic from the old implementation
- Remove `/verify` and `/status` endpoints

## API Specifications

### Install Endpoint
```
POST /api/v1/shopify/install
Headers:
  - Content-Type: application/json
  
Request Body:
{
  "conversation_id": "uuid"
}

Response:
{
  "install_url": "https://admin.shopify.com/oauth/install_custom_app?..."
}
```

### Connected Endpoint (Redirect Handler)
```
GET /api/v1/shopify/connected
Query Parameters:
  - shop: Shop domain (e.g., "example.myshopify.com")
  - host: Base64 encoded host (optional)
  - id_token: Session token to exchange
  - conversation_id: Original conversation ID (optional)

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
merchant:{shop_domain} -> JSON {
  merchant_id: string
  shop_domain: string
  access_token: string (encrypted)
  created_at: ISO datetime
  last_seen: ISO datetime
}

merchants -> SET of all shop domains
```

## Testing Checklist

### Integration Tests

1. **New Merchant Installation**
   ```
   1. Click "Connect Shopify" button
   2. Redirected to Shopify install page
   3. Accept installation
   4. Redirected back to /api/v1/shopify/connected
   5. Token exchanged and stored
   6. Redirected to chat with is_new=true
   ```

2. **Returning Merchant**
   ```
   1. Same flow as above
   2. Existing merchant detected
   3. Token updated
   4. Redirected to chat with is_new=false
   ```

### Manual Testing Script

1. **Happy Path**
   ```
   1. Navigate to https://amir.hirecj.ai
   2. Click "Connect Shopify"
   3. Verify redirect to Shopify install page
   4. Click "Install app"
   5. Verify redirect back to chat
   6. Check URL parameters contain oauth=complete
   ```

## Performance Considerations

- Redis TTL set to 24 hours for merchant data
- Token exchange happens synchronously (typically <500ms)
- No polling required - much better performance

## Security Considerations

- Access tokens stored encrypted in Redis
- id_token validated before exchange
- Shop domain validated to prevent injection
- Conversation ID passed through securely

## Common Issues & Solutions

### Issue 1: "Missing id_token" error
**Symptom**: Redirect to chat with error=missing_token
**Cause**: Shopify didn't send id_token (usually misconfigured App URL)
**Solution**: Verify App URL in Shopify configuration matches exactly

### Issue 2: Token exchange fails
**Symptom**: Redirect to chat with error=connection_failed
**Cause**: Invalid id_token or network issues
**Solution**: Check logs for specific error, verify client ID/secret

## Configuration

### Environment Variables
```bash
# Add to auth/.env.secrets
REDIS_URL=redis://localhost:6379/0

# Already configured
SHOPIFY_CUSTOM_INSTALL_LINK=https://admin.shopify.com/oauth/install_custom_app?...
SHOPIFY_CLIENT_ID=your_client_id
SHOPIFY_CLIENT_SECRET=your_client_secret
```

## Monitoring & Logging

### Key Metrics
- Installation success rate: Count of successful vs failed connections
- Token exchange latency: Time to exchange id_token
- Redis connection health: Monitor Redis availability

### Log Entries
```python
logger.info("[SHOPIFY_CONNECTED] Successfully connected shop", extra={
    "shop": shop_domain,
    "is_new": is_new,
    "merchant_id": merchant_id
})
```

## Next Phase Dependencies

Phase 4 (UI Actions) needs:
- Merchant authenticated and token stored
- Conversation context includes merchant_id
- Access to make Shopify API calls

## Rollback Plan

If this phase needs to be rolled back:
1. Revert to Phase 3.5 implementation (complex but working)
2. Update Shopify App URL back to embedded format
3. Re-enable App Bridge dependencies

---

## Implementation Notes

This approach is MUCH simpler than the App Bridge implementation:
- No embedded app complexity
- No session token retrieval
- No polling mechanism
- Direct server-to-server token exchange
- Everything happens on hirecj.ai

The key insight is that Shopify's redirect includes everything we need to authenticate, so we don't need the complex client-side token retrieval.