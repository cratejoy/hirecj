# Phase 3.5: Shopify Custom App Support - Design Document

## 🎯 Problem Statement

Shopify custom apps use a different installation flow than public apps:
- **Public Apps**: Standard OAuth flow with authorization URL
- **Custom Apps**: Pre-approved install link with session token authentication

Our current implementation only supports the public app flow, causing "Unauthorized Access" errors when merchants try to connect custom apps.

## 🌟 Solution Overview

Create a dual-mode OAuth system that elegantly handles both app types without code duplication or user confusion.

## 🏗️ Technical Design

### 1. Configuration

Add to root `.env`:
```bash
# Shopify App Configuration
SHOPIFY_APP_TYPE=custom  # or "public"
SHOPIFY_CUSTOM_INSTALL_LINK=https://admin.shopify.com/oauth/install_custom_app?client_id=...
```

### 2. Frontend Flow

#### Current Flow (Public Apps)
```typescript
// User clicks "Connect Shopify"
// → Enter shop domain
// → Redirect to: /oauth/authorize
// → Complete OAuth
// → Return to chat
```

#### New Flow (Custom Apps)
```typescript
// User clicks "Connect Shopify"
// → System checks SHOPIFY_APP_TYPE
// → If custom:
//   - Open SHOPIFY_CUSTOM_INSTALL_LINK in popup
//   - Listen for installation complete
//   - Exchange session token for access token
// → Return to chat
```

### 3. Backend Architecture

#### New Endpoints

```python
# auth/app/api/shopify_custom.py

@router.post("/api/v1/shopify/custom/install")
async def initiate_custom_install(request: CustomInstallRequest):
    """
    Returns the custom install link for frontend to open.
    Stores conversation context for post-install.
    """
    return {
        "install_url": settings.shopify_custom_install_link,
        "session_id": generate_session_id()
    }

@router.post("/api/v1/shopify/custom/verify")
async def verify_custom_installation(request: VerifyRequest):
    """
    Called after merchant installs the custom app.
    Exchanges session token for access token.
    """
    # Validate session token from Shopify
    # Exchange for API access token
    # Store merchant session
    # Return success with merchant info
```

#### Updated OAuth Router

```python
# auth/app/api/oauth.py

@router.get("/shopify/authorize")
async def shopify_authorize(...):
    # Check app type
    if settings.shopify_app_type == "custom":
        raise HTTPException(
            status_code=400,
            detail="Custom apps should use /custom/install endpoint"
        )
    
    # Existing public app flow...
```

### 4. Frontend Implementation

#### ShopifyOAuthButton Enhancement

```typescript
// homepage/src/components/ShopifyOAuthButton.tsx

const handleConnect = async () => {
  const appType = import.meta.env.VITE_SHOPIFY_APP_TYPE || 'public';
  
  if (appType === 'custom') {
    await handleCustomAppFlow();
  } else {
    await handlePublicAppFlow();
  }
};

const handleCustomAppFlow = async () => {
  // 1. Get install link from backend
  const { install_url, session_id } = await fetch(
    `${authBaseUrl}/api/v1/shopify/custom/install`,
    { method: 'POST', body: { conversation_id } }
  ).then(r => r.json());
  
  // 2. Open install link in popup
  const popup = window.open(install_url, 'shopify-install', '...');
  
  // 3. Poll for installation complete
  const checkInstallation = setInterval(async () => {
    try {
      const result = await fetch(
        `${authBaseUrl}/api/v1/shopify/custom/verify`,
        { method: 'POST', body: { session_id } }
      ).then(r => r.json());
      
      if (result.installed) {
        clearInterval(checkInstallation);
        popup?.close();
        onSuccess(result);
      }
    } catch (e) {
      // Not installed yet, keep polling
    }
  }, 2000);
};
```

### 5. Session Token Validation

```python
# auth/app/services/shopify_session.py

import jwt
from shopify import Session

class ShopifySessionValidator:
    """Validates Shopify session tokens for custom apps."""
    
    async def validate_session_token(self, token: str) -> dict:
        """
        Validates a Shopify session token.
        Returns shop domain and session info.
        """
        # Decode and verify JWT
        # Check issuer, audience, etc.
        # Return validated session data
        
    async def exchange_for_access_token(
        self, 
        session_token: str,
        shop_domain: str
    ) -> str:
        """
        Exchanges a session token for an API access token.
        """
        # Call Shopify token exchange endpoint
        # Store access token
        # Return token for API calls
```

## 🔄 Migration Strategy

1. **Phase 1**: Add configuration without breaking existing flow
2. **Phase 2**: Implement custom app endpoints
3. **Phase 3**: Update frontend to support both modes
4. **Phase 4**: Test with real custom app
5. **Phase 5**: Document setup for both app types

## 🎨 UX Considerations

### Same Experience for Merchants
- Single "Connect Shopify" button
- No visible difference in flow
- CJ responds identically regardless of app type

### Developer Experience
- Clear configuration in `.env`
- Automatic detection of app type
- Same conversation flow post-authentication

## 🔒 Security Considerations

1. **Session Token Validation**: Properly validate JWT signatures
2. **CORS**: Allow popups from Shopify domains
3. **Token Storage**: Same secure storage for both token types
4. **Rate Limiting**: Prevent polling abuse

## 📋 Implementation Checklist

- [ ] Add `SHOPIFY_APP_TYPE` to environment config
- [ ] Create custom app endpoints in auth service
- [ ] Implement session token validator
- [ ] Update ShopifyOAuthButton for dual-mode
- [ ] Add polling mechanism for installation status
- [ ] Test with custom app credentials
- [ ] Update documentation
- [ ] Add error handling for edge cases

## 🚀 Benefits

1. **Backwards Compatible**: Existing public app flow unchanged
2. **Future Proof**: Easy to add more app types
3. **Clean Architecture**: Config-driven behavior
4. **Minimal Frontend Changes**: Logic stays in backend
5. **Unified Experience**: Merchants see no difference