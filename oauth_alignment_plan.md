# OAuth Flow Alignment Plan

## 🎯 Objective

Elegantly align the OAuth implementation with the workflow specification, ensuring conversation continuity and proper system event handling.

## 🔍 Current State Analysis

### Problems Identified
1. **Conversation Context Loss**: OAuth redirect creates new WebSocket connection with different conversation_id
2. **Parallel Implementations**: WebSocket messages vs system events creating confusion
3. **Race Conditions**: WebSocket might not be connected when oauth_complete is sent
4. **Missing System Events**: Workflow expects system messages that aren't generated

### Root Cause
The OAuth flow was designed without considering the stateless nature of HTTP redirects and the need for conversation continuity across page reloads.

## 🌟 North Star Solution

Create a **single, elegant flow** that maintains conversation state through OAuth and generates proper system events.

## 📋 Implementation Phases

### Phase 1: Conversation Continuity (2 hours)

#### 1.1 Frontend: Preserve Conversation State
**File:** `homepage/src/hooks/useOAuthCallback.ts`

```typescript
const handleCallback = useCallback(() => {
  const params = new URLSearchParams(window.location.search);
  
  // Retrieve stored conversation ID
  const storedConversationId = sessionStorage.getItem('shopify_oauth_conversation_id');
  
  if (params.get('oauth') === 'complete') {
    const callbackData: OAuthCallbackParams = {
      oauth: 'complete',
      conversation_id: storedConversationId || '', // Use stored ID
      is_new: params.get('is_new') || 'true',
      merchant_id: params.get('merchant_id') || undefined,
      shop: params.get('shop') || undefined,
    };
    
    // Clean up storage
    sessionStorage.removeItem('shopify_oauth_conversation_id');
    
    onSuccess(callbackData);
  }
}, [onSuccess, onError]);
```

#### 1.2 Frontend: Ensure WebSocket Connection
**File:** `homepage/src/pages/SlackChat.tsx`

```typescript
const handleOAuthSuccess = useCallback(async (params: any) => {
  console.log('[SlackChat] OAuth success:', params);
  
  // Update user session
  if (params.merchant_id && params.shop) {
    userSession.setMerchant(params.merchant_id, params.shop);
  }
  
  // Wait for WebSocket connection
  const maxRetries = 10;
  let retries = 0;
  
  const sendOAuthComplete = async () => {
    if (wsChat.isConnected) {
      // Send as system event, not regular message
      wsChat.sendSpecialMessage({
        type: 'system_event',
        data: {
          event_type: 'oauth_complete',
          provider: 'shopify',
          is_new: params.is_new === 'true',
          merchant_id: params.merchant_id,
          shop_domain: params.shop,
          conversation_id: params.conversation_id
        }
      });
      return true;
    }
    
    if (retries < maxRetries) {
      retries++;
      await new Promise(resolve => setTimeout(resolve, 500));
      return sendOAuthComplete();
    }
    
    return false;
  };
  
  const sent = await sendOAuthComplete();
  if (!sent) {
    toast({
      title: "Connection Issue",
      description: "Please refresh the page to see your Shopify connection.",
      variant: "warning"
    });
  }
}, [wsChat, userSession, toast]);
```

### Phase 2: Backend System Event Generation (3 hours)

#### 2.1 Convert WebSocket Message to System Event
**File:** `agents/app/platforms/web_platform.py`

Replace the current `oauth_complete` handler:

```python
elif message_type == "system_event":
    # Handle system events from frontend
    event_data = data.get("data", {})
    event_type = event_data.get("event_type")
    
    if event_type == "oauth_complete":
        await self._handle_oauth_system_event(
            websocket, conversation_id, event_data
        )
    else:
        logger.warning(f"Unknown system event type: {event_type}")

async def _handle_oauth_system_event(
    self, websocket, conversation_id: str, event_data: Dict[str, Any]
):
    """Convert OAuth completion to proper system event."""
    
    provider = event_data.get("provider")
    is_new = event_data.get("is_new", True)
    merchant_id = event_data.get("merchant_id")
    shop_domain = event_data.get("shop_domain")
    original_conversation_id = event_data.get("conversation_id")
    
    logger.info(f"[OAUTH_SYSTEM_EVENT] Processing OAuth completion: "
               f"provider={provider}, is_new={is_new}, "
               f"shop_domain={shop_domain}, "
               f"original_conversation={original_conversation_id}")
    
    # Get the session (use original conversation ID if provided)
    session_id = original_conversation_id or conversation_id
    session = self.session_manager.get_session(session_id)
    
    if not session:
        logger.error(f"[OAUTH_ERROR] No session found for {session_id}")
        await self._send_error(websocket, "Session expired. Please start over.")
        return
    
    # Update session with OAuth data
    if merchant_id and merchant_id != "onboarding_user":
        session.merchant_name = merchant_id
    
    if shop_domain:
        user_id, _ = get_or_create_user(shop_domain)
        session.user_id = user_id
    
    # Store OAuth metadata
    session.oauth_metadata = {
        "provider": provider,
        "is_new_merchant": is_new,
        "shop_domain": shop_domain,
        "authenticated": True,
        "authenticated_at": datetime.now().isoformat()
    }
    
    # Generate the system message that workflow expects
    system_message = (
        f"New Shopify merchant authenticated from {shop_domain}"
        if is_new else
        f"Returning Shopify merchant authenticated from {shop_domain}"
    )
    
    # Process as system message
    response = await self.message_processor.process_message(
        session=session,
        message=system_message,
        sender="system"
    )
    
    # Send response
    await websocket.send_json({
        "type": "cj_message",
        "data": {
            "content": response,
            "factCheckStatus": "available",
            "timestamp": datetime.now().isoformat(),
        }
    })
```

### Phase 3: Alternative Approach - State Parameter (4 hours)

If Phase 1-2 proves insufficient, implement OAuth state parameter:

#### 3.1 Auth Service: Preserve Conversation ID
**File:** `auth/app/api/shopify_oauth.py`

```python
@router.get("/install")
async def initiate_oauth(
    shop: Optional[str] = Query(None),
    conversation_id: Optional[str] = Query(None),  # New parameter
    # ... other params
):
    # Generate state with embedded conversation_id
    state_data = {
        "nonce": shopify_auth.generate_state(),
        "conversation_id": conversation_id
    }
    state = base64.b64encode(json.dumps(state_data).encode()).decode()
    
    # Store in Redis with conversation context
    redis_client.setex(
        f"{STATE_PREFIX}{state}",
        STATE_TTL,
        json.dumps({
            "shop": shop,
            "conversation_id": conversation_id
        })
    )
    
    # Continue with OAuth flow...

@router.get("/callback")
async def handle_oauth_callback(
    # ... params
):
    # Decode state to get conversation_id
    if state:
        try:
            decoded = json.loads(base64.b64decode(state).decode())
            conversation_id = decoded.get("conversation_id")
        except:
            conversation_id = None
    
    # ... rest of callback handling
    
    # Include conversation_id in redirect
    redirect_params = {
        "oauth": "complete",
        "is_new": str(is_new).lower(),
        "merchant_id": merchant_id,
        "shop": shop,
        "conversation_id": conversation_id or ""
    }
```

#### 3.2 Frontend: Pass Conversation ID
**File:** `homepage/src/components/ShopifyOAuthButton.tsx`

```typescript
const initiateOAuth = (shop: string) => {
  // ... validation
  
  const authUrl = import.meta.env.VITE_AUTH_URL || 'https://amir-auth.hirecj.ai';
  const params = new URLSearchParams({
    shop: shop,
    conversation_id: conversationId  // Pass through OAuth
  });
  const installUrl = `${authUrl}/api/v1/shopify/install?${params}`;
  
  window.location.href = installUrl;
};
```

### Phase 4: Workflow Alignment (1 hour)

#### 4.1 Ensure Workflow Handles System Events
**File:** `agents/prompts/workflows/shopify_onboarding.yaml`

Already correctly configured to handle:
- "New Shopify merchant authenticated from [store_domain]"
- "Returning Shopify merchant authenticated from [store_domain]"

No changes needed here.

### Phase 5: Testing & Validation (2 hours)

#### 5.1 Test Scenarios
1. **Fresh OAuth Flow**: New user connecting Shopify
2. **Returning User**: Existing user reconnecting
3. **Page Refresh During OAuth**: Ensure state is preserved
4. **Slow Connection**: Test retry mechanism
5. **Session Expiry**: Handle expired sessions gracefully

#### 5.2 Debug Tooling
Add temporary logging:

```python
# In web_platform.py
logger.info(f"[OAUTH_DEBUG] Session lookup: {session_id}")
logger.info(f"[OAUTH_DEBUG] Session found: {session is not None}")
logger.info(f"[OAUTH_DEBUG] System message: {system_message}")
logger.info(f"[OAUTH_DEBUG] Response: {response[:100]}...")
```

## 🚀 Implementation Order

1. **Day 1**: Phase 1 (Frontend fixes) - Quick wins
2. **Day 2**: Phase 2 (Backend system events) - Core functionality
3. **Day 3**: Phase 3 (State parameter) - Only if needed
4. **Day 4**: Phase 4-5 (Testing & cleanup)

## ✅ Success Criteria

1. OAuth flow maintains conversation continuity
2. System events are properly generated and handled
3. Workflow responds with appropriate messages
4. No race conditions or lost state
5. Clean, elegant code following North Star principles

## 🎯 Key Principles

1. **Single Source of Truth**: One way to handle OAuth completion
2. **Simplify**: Remove parallel implementations
3. **Backend-Driven**: Let backend handle complexity
4. **No Magic**: Clear, explicit state management
5. **Elegant Solutions**: Fix root causes, not symptoms

## 📊 Risk Mitigation

1. **Fallback**: If state is lost, create new conversation gracefully
2. **Timeout**: Don't wait forever for WebSocket connection
3. **User Feedback**: Clear messages about what's happening
4. **Logging**: Comprehensive debug information

## 🔄 Migration Strategy

1. Deploy Phase 1-2 first (non-breaking)
2. Test thoroughly in staging
3. Add feature flag for Phase 3 if needed
4. Remove old oauth_complete handler after validation

## 📝 Notes

- The root issue is treating OAuth as a stateful flow in a stateless HTTP world
- The solution maintains state through the redirect cycle
- System events provide clean abstraction between transport and business logic
- This approach scales to other OAuth providers (Klaviyo, etc.)

## 🎉 End State

A single, elegant OAuth flow where:
1. User clicks Connect → OAuth → Returns to same conversation
2. System event triggers workflow response
3. CJ provides immediate value with Shopify insights
4. Natural transition to support workflows

No race conditions. No lost state. No confusion.

## 📍 Quick Reference: Key Files to Modify

### Frontend
- `homepage/src/hooks/useOAuthCallback.ts` - Retrieve stored conversation ID
- `homepage/src/pages/SlackChat.tsx` - Convert to system_event message
- `homepage/src/components/ShopifyOAuthButton.tsx` - Pass conversation_id if using state approach

### Backend
- `agents/app/platforms/web_platform.py` - Replace oauth_complete handler with system_event
- `auth/app/api/shopify_oauth.py` - Add conversation_id handling if using state approach

### Configuration
- `agents/prompts/workflows/shopify_onboarding.yaml` - Already configured correctly

## 🔨 Implementation Checklist

- [ ] Phase 1.1: Update useOAuthCallback to retrieve sessionStorage
- [ ] Phase 1.2: Update SlackChat to send system_event with retry
- [ ] Phase 2.1: Replace oauth_complete handler with system_event handler
- [ ] Test: Basic OAuth flow with conversation continuity
- [ ] Phase 3 (if needed): Implement state parameter approach
- [ ] Remove debug/halt code from web_platform.py
- [ ] Add comprehensive logging for troubleshooting
- [ ] Test all scenarios in checklist
- [ ] Remove old oauth_complete code paths
- [ ] Update documentation