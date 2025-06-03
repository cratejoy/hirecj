# Phase 2: Auth Flow Integration - Implementation Guide

## ✅ Status: COMPLETE

Phase 2 implements Shopify OAuth as the identity system, detecting new vs returning merchants and updating conversation context accordingly.

## 🎯 Phase Objectives

1. Implement OAuth flow that uses shop domain as the sole identifier
2. Detect new vs returning merchants during OAuth callback
3. Update conversation context with OAuth completion status
4. Create seamless frontend flow with redirect handling

## 📋 What Was Built

### 1. Frontend OAuth Components

#### OAuth Button Component (`homepage/src/components/OAuthButton.tsx`)
```typescript
export const OAuthButton: React.FC<OAuthButtonProps> = ({
  provider,
  conversationId,
  text = 'Connect Shopify',
  className = '',
  disabled = false
}) => {
  const handleOAuthClick = () => {
    const authBaseUrl = import.meta.env.VITE_AUTH_URL || 'http://localhost:8103';
    const oauthUrl = `${authBaseUrl}/api/v1/oauth/${provider}/authorize?conversation_id=${conversationId}&redirect_uri=${encodeURIComponent(window.location.origin + '/chat')}`;
    
    // Open OAuth flow in popup window
    window.open(oauthUrl, 'shopify-oauth', `width=${width},height=${height}...`);
  };
  // ...
};
```

#### OAuth Callback Hook (`homepage/src/hooks/useOAuthCallback.ts`)
```typescript
export const useOAuthCallback = (
  onSuccess: (params: OAuthCallbackParams) => void,
  onError: (error: string) => void
) => {
  // Handles OAuth redirect parameters
  // Cleans URL after processing
  // Calls appropriate handlers
};
```

#### OAuth Success Handler (`homepage/src/pages/SlackChat.tsx`)
```typescript
const handleOAuthSuccess = useCallback((params: any) => {
  // Update chat config with merchant ID
  if (params.merchant_id) {
    setChatConfig(prev => ({
      ...prev,
      merchantId: params.merchant_id
    }));
  }
  
  // Send OAuth complete to WebSocket
  if (wsChat.isConnected) {
    wsChat.sendSpecialMessage({
      type: 'oauth_complete',
      data: {
        provider: 'shopify',
        is_new: params.is_new === 'true',
        merchant_id: params.merchant_id,
        shop_domain: params.shop
      }
    });
  }
}, [wsChat, setChatConfig, toast]);
```

### 2. Backend OAuth Handling

#### OAuth Routes (`auth/app/api/oauth.py`)
```python
@router.get("/shopify/authorize")
async def shopify_authorize(
    conversation_id: str,
    redirect_uri: str,
    shop: Optional[str] = None
):
    # Generate secure state
    # Store state with conversation context
    # Redirect to Shopify OAuth

@router.get("/shopify/callback")
async def shopify_callback(
    code: str,
    state: str,
    shop: str
):
    # Validate state
    # Exchange code for token
    # Check if merchant exists (by shop domain)
    # Determine new vs returning
    # Redirect back to frontend with context
```

#### WebSocket OAuth Handler (`agents/app/platforms/web_platform.py`)
```python
elif message_type == "oauth_complete":
    # Handle OAuth completion from Shopify
    oauth_data = data.get("data", {})
    
    # Update session with real merchant information
    if merchant_id and merchant_id != "onboarding_user":
        session.merchant_name = merchant_id
    
    # Store OAuth metadata in session
    session.oauth_metadata.update({
        "provider": provider,
        "is_new_merchant": is_new,
        "shop_domain": shop_domain,
        "authenticated": True
    })
    
    # Generate context-aware response
    if is_new:
        oauth_context = f"New Shopify merchant authenticated from {shop_domain}"
    else:
        oauth_context = f"Returning Shopify merchant authenticated from {shop_domain}"
    
    # Let CJ respond naturally
    response = await self.message_processor.process_message(
        session=session,
        message=oauth_context,
        sender="system"
    )
```

### 3. CJ Agent OAuth Awareness

#### OAuth Context in CJ (`agents/app/agents/cj_agent.py`)
```python
def _extract_onboarding_context(self) -> str:
    """Extract onboarding-specific context from conversation state."""
    context_parts = []
    
    # Phase tracking
    # ...
    
    # Check for OAuth status
    oauth_metadata = getattr(self, 'oauth_metadata', None)
    if oauth_metadata and oauth_metadata.get('authenticated'):
        is_new = oauth_metadata.get('is_new_merchant', True)
        shop_domain = oauth_metadata.get('shop_domain', 'their store')
        
        if is_new:
            context_parts.append(f"OAuth Status: NEW merchant authenticated from {shop_domain}")
        else:
            context_parts.append(f"OAuth Status: RETURNING merchant authenticated from {shop_domain}")
    else:
        context_parts.append("OAuth Status: Not yet authenticated")
    
    return "\n".join(context_parts)
```

#### System Message Support (`agents/app/services/message_processor.py`)
```python
# Support system messages (OAuth context)
if sender != "system":
    # Add to conversation history
    session.conversation.add_message(msg)

# Handle system messages
if sender in ["merchant", "system"]:
    response = await self._get_cj_response(
        session, 
        message, 
        is_system=sender=="system"
    )
```

## 🏗️ Architecture Decisions

### Shop Domain as Identity
- No visitor tracking or cookies needed
- Shop domain is unique and verifiable
- Clean separation between anonymous and authenticated

### In-Memory State for Demo
- Using dictionaries for OAuth state and merchant sessions
- Production would use Redis or database
- Simple and sufficient for current needs

### OAuth Popup Flow
- Better UX than full page redirect
- Keeps conversation context intact
- Standard pattern for OAuth flows

### System Messages
- OAuth context sent as "system" messages
- Don't pollute conversation history
- Allow CJ to respond naturally to auth events

## 🧪 Testing

### Manual Testing Flow
1. Start new conversation (always onboarding workflow)
2. Wait for CJ greeting
3. Click "Connect Shopify" when offered
4. Enter shop domain in popup
5. Complete Shopify OAuth
6. Verify redirect back to chat
7. Confirm CJ acknowledges authentication
8. Test both new and returning merchant flows

### Test Scenarios
- New merchant: First time authentication
- Returning merchant: Shop domain already in system
- OAuth error: Invalid shop or cancelled auth
- State expiration: Wait > 10 minutes
- WebSocket disconnection during OAuth

## 🚀 Next Steps (Phase 3)

With OAuth identity in place, Phase 3 will implement:
- Quick insights service for Shopify data
- Store snapshot queries (products, orders)
- Progressive data loading
- Real-time insights in conversation

## 📝 Key Files Modified

### Frontend
- `/homepage/src/components/OAuthButton.tsx` (NEW)
- `/homepage/src/hooks/useOAuthCallback.ts` (NEW)
- `/homepage/src/hooks/useWebSocketChat.ts`
- `/homepage/src/pages/SlackChat.tsx`

### Auth Service
- `/auth/app/api/oauth.py` (NEW)
- `/auth/app/main.py`

### Agents Service
- `/agents/app/platforms/web_platform.py`
- `/agents/app/services/message_processor.py`
- `/agents/app/agents/cj_agent.py`

## 🔧 Configuration

### Environment Variables
```bash
# Auth Service
SHOPIFY_CLIENT_ID=your_shopify_app_client_id
SHOPIFY_CLIENT_SECRET=your_shopify_app_client_secret
SHOPIFY_SCOPES=read_products,read_orders,read_customers

# Frontend
VITE_AUTH_URL=http://localhost:8103  # Or ngrok URL
```

### OAuth Redirect URLs
When setting up Shopify app:
- Development: `http://localhost:8103/api/v1/oauth/shopify/callback`
- Ngrok: `https://your-tunnel.ngrok.io/api/v1/oauth/shopify/callback`
- Production: `https://auth.hirecj.ai/api/v1/oauth/shopify/callback`

## 🎉 Phase 2 Complete!

The OAuth identity system is now fully functional. Merchants can authenticate with Shopify, and the system correctly identifies new vs returning users based on shop domain.

## 🔑 Implementation Highlights

### Key Architectural Decisions
1. **No Visitor Tracking**: Clean slate until OAuth consent
2. **Shop Domain as ID**: Natural, verifiable merchant identifier  
3. **In-Memory State**: Simple solution for demo/MVP
4. **System Messages**: Clean separation of auth events from chat

### What Makes This Elegant
- Zero cookies or tracking before consent
- Natural conversation flow determines path
- Shop domain prevents duplicate merchants
- OAuth popup maintains conversation context
- CJ responds intelligently to auth state

### Security Considerations
- Secure state parameter with expiration
- HMAC validation on Shopify callbacks
- Token encryption at rest (TODO for production)
- No PII stored before OAuth consent

The foundation is now set for Phase 3, where we'll demonstrate immediate value by showing quick insights from the merchant's Shopify store.