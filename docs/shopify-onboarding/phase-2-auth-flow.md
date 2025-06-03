# Phase 2: Auth Flow Integration - Detailed Implementation Guide

## Overview

This phase implements the intelligent OAuth flow that detects new vs returning merchants using shop domain as the sole identifier. No visitor tracking, no spam records.

## Deliverables Checklist

- [ ] Enhance Shopify OAuth callback to check merchant existence
- [ ] Update database models (no visitor tracking)
- [ ] Implement conversation context updates post-OAuth
- [ ] Add frontend OAuth redirect handling
- [ ] Create merchant registration flow for new shops
- [ ] Add shop domain validation
- [ ] Implement secure state parameter with HMAC

## Prerequisites

- Phase 1 completed (OAuth button, onboarding workflow)
- Auth service running with Shopify provider
- Database service connected

## Step-by-Step Implementation

### 1. Database Schema Updates

**File**: `database/migrations/XXXX_add_shopify_merchant_fields.py`

```python
"""Add Shopify-specific merchant fields

Revision ID: xxxx
Revises: yyyy
Create Date: 2024-XX-XX
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add Shopify-specific fields to merchants table
    op.add_column('merchants', 
        sa.Column('shop_domain', sa.String(255), unique=True, index=True)
    )
    op.add_column('merchants',
        sa.Column('shopify_shop_id', sa.String(255), unique=True)
    )
    op.add_column('merchants',
        sa.Column('shop_name', sa.String(255))
    )
    op.add_column('merchants',
        sa.Column('shop_email', sa.String(255))
    )
    op.add_column('merchants',
        sa.Column('shop_currency', sa.String(3))
    )
    op.add_column('merchants',
        sa.Column('shop_timezone', sa.String(50))
    )
    op.add_column('merchants',
        sa.Column('shopify_access_token', sa.Text)  # Encrypted
    )
    op.add_column('merchants',
        sa.Column('shopify_scopes', sa.Text)  # JSON array
    )
    
    # Add index for shop domain lookups
    op.create_index('idx_merchants_shop_domain', 'merchants', ['shop_domain'])

def downgrade():
    op.drop_index('idx_merchants_shop_domain', 'merchants')
    op.drop_column('merchants', 'shop_domain')
    op.drop_column('merchants', 'shopify_shop_id')
    op.drop_column('merchants', 'shop_name')
    op.drop_column('merchants', 'shop_email')
    op.drop_column('merchants', 'shop_currency')
    op.drop_column('merchants', 'shop_timezone')
    op.drop_column('merchants', 'shopify_access_token')
    op.drop_column('merchants', 'shopify_scopes')
```

### 2. Auth Service OAuth Enhancement

**File**: `auth/app/providers/shopify.py`

Update the OAuth callback to detect new vs returning merchants:

```python
import hmac
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlencode

async def handle_callback(
    self, 
    code: str, 
    state: str, 
    shop: str,
    hmac_param: str,
    timestamp: str
) -> Dict[str, Any]:
    """Enhanced callback that detects new vs returning merchants"""
    
    # 1. Verify HMAC to prevent tampering
    if not self._verify_webhook_hmac(hmac_param, {
        'code': code,
        'shop': shop,
        'state': state,
        'timestamp': timestamp
    }):
        raise ValueError("Invalid HMAC signature")
    
    # 2. Decode and verify state
    state_data = self._decode_state(state)
    conversation_id = state_data.get('conversation_id')
    
    # 3. Exchange code for access token
    token_response = await self._exchange_code_for_token(code, shop)
    access_token = token_response['access_token']
    scopes = token_response['scope'].split(',')
    
    # 4. Fetch shop information
    shop_info = await self._get_shop_info(shop, access_token)
    
    # 5. Check if merchant exists
    async with get_db() as db:
        existing_merchant = await db.query(Merchant).filter(
            Merchant.shop_domain == shop
        ).first()
        
        if existing_merchant:
            # Returning merchant - update token
            existing_merchant.shopify_access_token = encrypt(access_token)
            existing_merchant.shopify_scopes = json.dumps(scopes)
            existing_merchant.last_login = datetime.utcnow()
            await db.commit()
            
            return {
                'success': True,
                'is_new': False,
                'merchant_id': str(existing_merchant.id),
                'shop_domain': shop,
                'redirect_url': self._build_redirect_url(
                    conversation_id=conversation_id,
                    is_new=False,
                    merchant_id=str(existing_merchant.id),
                    shop=shop
                )
            }
        else:
            # New merchant - create record
            new_merchant = Merchant(
                id=str(uuid.uuid4()),
                shop_domain=shop,
                shopify_shop_id=str(shop_info['id']),
                shop_name=shop_info['name'],
                shop_email=shop_info['email'],
                shop_currency=shop_info['currency'],
                shop_timezone=shop_info['timezone'],
                shopify_access_token=encrypt(access_token),
                shopify_scopes=json.dumps(scopes),
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            db.add(new_merchant)
            await db.commit()
            
            return {
                'success': True,
                'is_new': True,
                'merchant_id': str(new_merchant.id),
                'shop_domain': shop,
                'redirect_url': self._build_redirect_url(
                    conversation_id=conversation_id,
                    is_new=True,
                    merchant_id=str(new_merchant.id),
                    shop=shop
                )
            }

def _build_redirect_url(
    self, 
    conversation_id: str,
    is_new: bool,
    merchant_id: str,
    shop: str
) -> str:
    """Build redirect URL with context"""
    params = {
        'oauth': 'complete',
        'conversation_id': conversation_id,
        'is_new': str(is_new).lower(),
        'merchant_id': merchant_id,
        'shop': shop
    }
    
    base_url = self.settings.frontend_url.rstrip('/')
    return f"{base_url}/chat?{urlencode(params)}"

async def _get_shop_info(self, shop: str, access_token: str) -> Dict[str, Any]:
    """Fetch shop information from Shopify"""
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://{shop}/admin/api/2024-01/shop.json",
            headers=headers
        )
        response.raise_for_status()
        return response.json()['shop']
```

### 3. Frontend OAuth Handling

**File**: `homepage/src/hooks/useOAuthCallback.ts`

Create a hook to handle OAuth callbacks:

```typescript
import { useEffect, useCallback } from 'react';
import { useLocation, useRoute } from 'wouter';

interface OAuthCallbackParams {
  oauth: string;
  conversation_id: string;
  is_new: string;
  merchant_id?: string;
  shop?: string;
  error?: string;
}

export const useOAuthCallback = (
  onSuccess: (params: OAuthCallbackParams) => void,
  onError: (error: string) => void
) => {
  const [location, setLocation] = useLocation();
  
  const handleCallback = useCallback(() => {
    const params = new URLSearchParams(window.location.search);
    
    if (params.get('oauth') === 'complete') {
      const callbackData: OAuthCallbackParams = {
        oauth: 'complete',
        conversation_id: params.get('conversation_id') || '',
        is_new: params.get('is_new') || 'true',
        merchant_id: params.get('merchant_id') || undefined,
        shop: params.get('shop') || undefined,
        error: params.get('error') || undefined
      };
      
      if (callbackData.error) {
        onError(callbackData.error);
      } else {
        onSuccess(callbackData);
      }
      
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [onSuccess, onError]);
  
  useEffect(() => {
    handleCallback();
  }, [handleCallback]);
  
  return { handleCallback };
};
```

**File**: `homepage/src/pages/SlackChat.tsx`

Update to use the OAuth callback hook:

```typescript
// Add OAuth callback handling
const handleOAuthSuccess = useCallback((params: OAuthCallbackParams) => {
  // Store shop domain for future visits (optional UX enhancement)
  if (params.shop) {
    localStorage.setItem('last_shop_domain', params.shop);
  }
  
  // Update chat config
  if (params.merchant_id) {
    setChatConfig(prev => ({
      ...prev,
      merchantId: params.merchant_id
    }));
  }
  
  // Send OAuth complete to WebSocket
  if (ws.current?.readyState === WebSocket.OPEN) {
    ws.current.send(JSON.stringify({
      type: 'oauth_complete',
      data: {
        provider: 'shopify',
        is_new: params.is_new === 'true',
        merchant_id: params.merchant_id,
        shop_domain: params.shop
      }
    }));
  }
}, [ws]);

const handleOAuthError = useCallback((error: string) => {
  toast({
    title: "Authentication Failed",
    description: error || "Unable to connect to Shopify. Please try again.",
    variant: "destructive"
  });
}, [toast]);

// Use the hook
useOAuthCallback(handleOAuthSuccess, handleOAuthError);
```

### 4. State Parameter Security

**File**: `auth/app/providers/base.py`

Add HMAC-secured state parameter:

```python
import base64
import json
import hmac
import hashlib
from datetime import datetime, timedelta

def _encode_state(self, data: Dict[str, Any]) -> str:
    """Encode state with HMAC signature"""
    # Add timestamp for expiry
    data['ts'] = datetime.utcnow().isoformat()
    
    # Encode data
    json_data = json.dumps(data, sort_keys=True)
    encoded = base64.urlsafe_b64encode(json_data.encode()).decode()
    
    # Add HMAC
    signature = hmac.new(
        self.settings.jwt_secret.encode(),
        encoded.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{encoded}.{signature}"

def _decode_state(self, state: str) -> Dict[str, Any]:
    """Decode and verify state parameter"""
    try:
        encoded, signature = state.rsplit('.', 1)
        
        # Verify HMAC
        expected_sig = hmac.new(
            self.settings.jwt_secret.encode(),
            encoded.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid state signature")
        
        # Decode data
        json_data = base64.urlsafe_b64decode(encoded).decode()
        data = json.loads(json_data)
        
        # Check timestamp (5 minute expiry)
        ts = datetime.fromisoformat(data['ts'])
        if datetime.utcnow() - ts > timedelta(minutes=5):
            raise ValueError("State parameter expired")
        
        return data
        
    except Exception as e:
        logger.error(f"State decode error: {e}")
        raise ValueError("Invalid state parameter")
```

### 5. Message Processor Updates

**File**: `agents/app/services/message_processor.py`

Already covered in Phase 1, but ensure oauth_complete handling includes merchant updates:

```python
# In handle_oauth_complete method
if merchant_id and not session.merchant_id:
    # First time merchant connection
    session.merchant_id = merchant_id
    
    # Load merchant memory if returning
    if not is_new:
        memory_service = MerchantMemoryService()
        merchant_memory = await memory_service.load_memory(merchant_id)
        session.merchant_memory = merchant_memory
```

## API Specifications

### OAuth Authorize Endpoint
```
GET /api/v1/oauth/shopify/authorize
Query Parameters:
  - conversation_id: string (required)
  - redirect_uri: string (required)
  
Response: 302 Redirect to Shopify
```

### OAuth Callback Endpoint
```
GET /api/v1/oauth/shopify/callback
Query Parameters:
  - code: string
  - shop: string
  - state: string (HMAC signed)
  - hmac: string
  - timestamp: string
  
Response: 302 Redirect to frontend with:
  - oauth=complete
  - conversation_id=xxx
  - is_new=true/false
  - merchant_id=xxx (if not new)
  - shop=xxx.myshopify.com
```

## Testing Checklist

### Unit Tests

1. **State Parameter Security**
   ```python
   def test_state_parameter_hmac():
       # Test encoding/decoding with HMAC
       # Test tampering detection
       # Test expiry
   ```

2. **Merchant Detection**
   ```python
   def test_new_merchant_detection():
       # Test shop doesn't exist
       
   def test_returning_merchant_detection():
       # Test shop exists
   ```

### Integration Tests

1. **Full OAuth Flow - New Merchant**
   - Start with no merchant record
   - Complete OAuth
   - Verify merchant created
   - Verify is_new=true in callback

2. **Full OAuth Flow - Returning Merchant**
   - Pre-create merchant record
   - Complete OAuth
   - Verify token updated
   - Verify is_new=false in callback

## Security Considerations

1. **HMAC Validation**: Always verify Shopify's HMAC on callbacks
2. **State Parameter**: Include timestamp and verify signature
3. **Token Storage**: Encrypt access tokens at rest
4. **Shop Domain Validation**: Ensure proper format (xxx.myshopify.com)
5. **Rate Limiting**: Implement on OAuth endpoints

## Common Issues & Solutions

### Issue 1: State Parameter Mismatch
**Symptom**: "Invalid state parameter" error
**Solution**: Ensure JWT secret is same across services

### Issue 2: Shop Domain Format
**Symptom**: Merchant not found when should be returning
**Solution**: Normalize shop domain (remove https://, ensure .myshopify.com)

## Next Phase Dependencies

Phase 3 (Quick Value Demo) requires:
- Merchant ID available in session
- Access token retrievable
- Shop domain for API calls