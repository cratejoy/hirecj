# Phase 3.6: Custom Distribution App Flow (Beta) - Detailed Implementation Guide

## 🚨 CRITICAL DISCOVERY: Custom Distribution Apps Work Differently!

After extensive research and testing, we discovered that Shopify custom distribution apps **DO NOT use OAuth**. Instead, they require manual token generation and sharing. This is completely different from public apps.

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Manual token entry is simpler than complex OAuth flows
2. **No Cruft**: Remove ALL OAuth/token exchange code - it doesn't apply to custom apps
3. **Break It & Fix It Right**: Complete breaking change from OAuth to manual token flow
4. **Long-term Elegance**: Temporary beta solution that works reliably
5. **Backend-Driven**: Backend validates tokens, frontend just collects them
6. **Single Source of Truth**: One auth pattern for beta - manual token entry
7. **No Over-Engineering**: Don't build OAuth for apps that don't support it
8. **Thoughtful Logging**: Clear logs for token validation and storage

## ✅ DOs and ❌ DON'Ts

### ✅ DO:
- **DO** implement the manual token entry flow exactly as specified
- **DO** validate tokens by making a test API call to Shopify
- **DO** provide clear instructions for merchants to find their token
- **DO** make it clear this is a beta limitation
- **DO** store tokens securely in Redis
- **DO** handle invalid tokens gracefully

### ❌ DON'T:
- **DON'T** try to implement OAuth - it doesn't work for custom distribution
- **DON'T** look for id_token or authorization codes - they don't exist
- **DON'T** implement token exchange - there's nothing to exchange
- **DON'T** use App Bridge or embedded app features
- **DON'T** hide that this is a manual process

## The Actual Flow

### 1. Installation
When merchants click the custom install link:
- They see Shopify's app installation screen
- They click "Install app"
- Shopify redirects to your App URL with: `shop`, `hmac`, `timestamp`, `host`
- **NO OAuth code or token is provided!**

### 2. Token Entry (Our Implementation)
After redirect, we show a form where merchants:
- See clear beta testing message
- Get step-by-step instructions
- Enter their manually generated access token
- Submit for validation

### 3. Token Generation (Merchant's Steps)
Merchants must:
1. Go to Shopify Admin
2. Settings → Apps and sales channels
3. Click on HireCJ
4. Click "API credentials"
5. Click "Reveal token once"
6. Copy the token (shown only once!)
7. Paste into our form

### 4. Token Validation
We validate the token by:
- Making a test API call to Shopify
- Storing if valid
- Showing error if invalid

## Implementation Details

### Connected Endpoint (Shows Form)
**File**: `auth/app/api/shopify_custom.py`

```python
@router.get("/connected")
async def handle_shopify_redirect(
    shop: str = Query(...),
    hmac: Optional[str] = Query(None),
    host: Optional[str] = Query(None),
    timestamp: Optional[str] = Query(None),
    conversation_id: Optional[str] = Query(None)
):
    """
    Handle redirect from Shopify after custom app installation.
    Shows form for manual token entry (beta requirement).
    """
    # Returns HTML form with:
    # - Beta testing notice
    # - Clear instructions
    # - Token input field
    # - Submit to /save-token
```

### Save Token Endpoint
**File**: `auth/app/api/shopify_custom.py`

```python
@router.post("/save-token")
async def save_merchant_token(
    shop: str = Form(...),
    token: str = Form(...),
    conversation_id: Optional[str] = Form(None)
):
    """
    Validate and save manually-provided access token.
    """
    # 1. Validate token with test API call
    # 2. Store in Redis if valid
    # 3. Redirect to chat with success
    # 4. Show error page if invalid
```

## Frontend Changes

The Shopify button now simply redirects - no API calls needed:
```typescript
const handleConnect = () => {
    const installUrl = import.meta.env.VITE_SHOPIFY_CUSTOM_INSTALL_LINK;
    const urlWithConversation = `${installUrl}&conversation_id=${conversationId}`;
    window.location.href = urlWithConversation;
};
```

## Database Schema

### Redis Storage
```
merchant:{shop_domain} -> JSON {
  merchant_id: string
  shop_domain: string
  access_token: string (manually provided)
  created_at: ISO datetime
  last_seen: ISO datetime
}
```

## Testing Flow

1. Click "Connect Shopify" button
2. Install app on Shopify
3. Get redirected to token entry form
4. See beta notice and instructions
5. Go to Shopify Admin to get token
6. Paste token and submit
7. Token validated and stored
8. Redirect to chat with success

## Why This Approach?

**Custom Distribution Reality**:
- Shopify Partner Dashboard custom apps with "custom distribution" don't support OAuth
- This is different from "custom apps" created directly in store admin
- The only way to get tokens is manual generation by the merchant
- This is a Shopify limitation, not our choice

**Beta Advantage**:
- Simpler implementation (no OAuth complexity)
- More transparent (merchants see exactly what's happening)
- Easier to debug (clear error messages)
- Works reliably (no token exchange issues)

## Security Considerations

- Tokens are validated before storage
- Invalid tokens are rejected immediately
- Tokens stored encrypted in Redis
- HTTPS required for token submission
- Clear warnings about one-time token display

## Common Issues

### "Invalid Token" Error
- Merchant didn't copy the full token
- Token doesn't have required permissions
- Token was revoked or expired

### "Connection Error"
- Network issues reaching Shopify
- Invalid shop domain
- Rate limiting

## Future Improvements

Once out of beta, options include:
1. Becoming a public app (requires Shopify approval)
2. Using Shopify's newer API patterns
3. Automated token provisioning (if Shopify adds support)

For now, this manual process is the **only way** custom distribution apps can work.

## Summary

- **No OAuth**: Custom distribution apps can't use OAuth
- **Manual tokens**: Merchants must generate and share tokens
- **Beta process**: Extra step clearly marked as temporary
- **Simple implementation**: Just collect and validate tokens
- **Works today**: This is the correct approach for custom distribution

This isn't a workaround - it's how Shopify designed custom distribution apps to work.