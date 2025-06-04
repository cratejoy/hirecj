# Phase 3.5: Replace OAuth with Custom App Flow

## 🎯 Goal

Remove the broken standard OAuth flow and replace it with Shopify's custom app installation flow.

## 🔥 What We're Removing

All standard OAuth code that doesn't work with custom apps:
- `/oauth/shopify/authorize` endpoint
- `/oauth/shopify/callback` complexity
- OAuth state management
- Redirect URI handling
- Shop domain prompts (custom install link includes it)

## ✨ What We're Building

A simple custom app flow:

```
1. User clicks "Connect Shopify"
2. Open custom install link in popup
3. User installs the app
4. Validate session token
5. Exchange for access token
6. Done - continue conversation
```

## 📋 Implementation Steps

### 1. Environment Configuration

Add to auth `.env`:
```bash
# Shopify Custom App Configuration
SHOPIFY_CUSTOM_INSTALL_LINK=https://admin.shopify.com/oauth/install_custom_app?client_id=2b337814e5611cc5143a7fc0f16abc14&signature=...
```

### 2. Simplify Backend

#### Remove These Files/Endpoints
```python
# auth/app/api/oauth.py
- DELETE: /oauth/shopify/authorize
- DELETE: /oauth/shopify/callback
- DELETE: OAuth state management code
```

#### Add Simple Custom App Handler
```python
# auth/app/api/shopify.py

@router.get("/install")
async def get_install_link():
    """Return the custom install link for frontend."""
    return {
        "install_url": settings.shopify_custom_install_link,
        "app_installed": check_if_installed()
    }

@router.post("/validate-session")
async def validate_session(session_token: str):
    """
    Validate session token after app installation.
    Exchange for access token if valid.
    """
    # Decode JWT
    # Verify signature
    # Exchange for access token
    # Store in merchant sessions
    return {"success": True, "merchant_id": "..."}
```

### 3. Simplify Frontend

#### Update ShopifyOAuthButton
```typescript
// No more shop domain input needed!
const handleConnect = async () => {
  // 1. Get install link
  const { install_url } = await fetch(
    `${authBaseUrl}/api/v1/shopify/install`
  ).then(r => r.json());
  
  // 2. Open in popup
  const popup = window.open(install_url, 'shopify-install');
  
  // 3. Wait for installation
  // (Shopify will close the popup after install)
  
  // 4. Validate session
  // (Implementation depends on how Shopify provides the session token)
};
```

### 4. Session Token Handling

Shopify custom apps use JWT session tokens. We need to:

```python
import jwt
from datetime import datetime

def validate_shopify_session(token: str) -> dict:
    """Validate Shopify session token."""
    try:
        # Decode without verification first to get the header
        unverified = jwt.decode(token, options={"verify_signature": False})
        
        # Get Shopify's public key for verification
        # Verify the JWT properly
        payload = jwt.decode(
            token,
            key=get_shopify_public_key(),
            algorithms=["RS256"],
            audience=settings.shopify_client_id
        )
        
        return {
            "shop_domain": payload["dest"],
            "user_id": payload["sub"],
            "valid": True
        }
    except Exception as e:
        logger.error(f"Invalid session token: {e}")
        return {"valid": False}
```

## 🗑️ Code to Delete

1. **Backend:**
   - `auth/app/api/oauth.py` - entire OAuth flow
   - OAuth state management
   - Redirect handling

2. **Frontend:**
   - Shop domain input component
   - OAuth redirect handling
   - State parameter management

## 🎯 End Result

- Simpler codebase (less code = less bugs)
- Working Shopify connection
- No confusing OAuth errors
- Faster implementation
- Easier to maintain

## 🚀 Benefits of This Approach

1. **It Actually Works**: No more "Unauthorized Access" errors
2. **Less Code**: Remove ~200 lines of broken OAuth code
3. **Simpler Flow**: No redirects, states, or callbacks
4. **Better UX**: One click to connect (no shop domain input)
5. **Shopify Native**: Uses Shopify's intended flow for custom apps

## 📝 Migration Notes

Since no one can use the current OAuth flow (it's broken), we can safely:
1. Delete all OAuth code
2. Implement custom app flow
3. No backwards compatibility needed
4. No migration required

This is a perfect example of "Break It & Fix It Right" from our North Star principles!