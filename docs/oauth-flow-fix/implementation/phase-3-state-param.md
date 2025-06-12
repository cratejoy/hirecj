# Phase 3: State Parameter (If Needed)

## Overview
If sessionStorage approach proves insufficient, pass conversation_id through OAuth state parameter.

## Changes

### 1. ShopifyOAuthButton.tsx
```typescript
const initiateOAuth = (shop: string) => {
  const authUrl = import.meta.env.VITE_AUTH_URL;
  const params = new URLSearchParams({
    shop: shop,
    conversation_id: conversationId  // Add this
  });
  const installUrl = `${authUrl}/api/v1/shopify/install?${params}`;
  window.location.href = installUrl;
};
```

### 2. shopify_oauth.py (Auth Service)
```python
@router.get("/install")
async def initiate_oauth(
    shop: Optional[str] = Query(None),
    conversation_id: Optional[str] = Query(None),  # New
):
    # Embed conversation_id in state
    state_data = {
        "nonce": shopify_auth.generate_state(),
        "conversation_id": conversation_id
    }
    state = base64.b64encode(json.dumps(state_data).encode()).decode()
    
    # Store enhanced state
    redis_client.setex(
        f"{STATE_PREFIX}{state}",
        STATE_TTL,
        json.dumps({
            "shop": shop,
            "conversation_id": conversation_id
        })
    )

@router.get("/callback")
async def handle_oauth_callback(...):
    # Extract conversation_id from state
    if state:
        stored_data = redis_client.get(f"{STATE_PREFIX}{state}")
        if stored_data:
            data = json.loads(stored_data)
            conversation_id = data.get("conversation_id")
    
    # Include in redirect
    redirect_params = {
        "oauth": "complete",
        "conversation_id": conversation_id or "",
        # ... other params
    }
```

## When to Use
- If sessionStorage is cleared by browser
- If multiple tabs cause confusion
- If we need stronger guarantees

## Testing
1. conversation_id survives full OAuth flow
2. State validation still works
3. No security implications