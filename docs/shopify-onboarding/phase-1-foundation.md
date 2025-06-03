# Phase 1: Foundation - Detailed Implementation Guide

## Overview

This phase establishes the foundation for the Shopify onboarding experience by creating the workflow definition, updating the frontend to default to onboarding, and building the OAuth button component.

## Deliverables Checklist

- [ ] Create `shopify_onboarding.yaml` workflow file
- [ ] Update `SlackChat.tsx` to default to onboarding workflow
- [ ] Remove configuration modal bypass
- [ ] Create `OAuthButton.tsx` component
- [ ] Update CJ agent context for onboarding awareness
- [ ] Add workflow to conversation catalog
- [ ] Test conversation flow end-to-end

## Step-by-Step Implementation

### 1. Create Shopify Onboarding Workflow

**File**: `agents/prompts/workflows/shopify_onboarding.yaml`

```yaml
name: "Shopify Onboarding"
description: "Natural onboarding flow for all new conversations"
version: "1.0.0"
active: true

# IMPORTANT: Workflows define WHAT happens, not HOW to communicate
# - Define milestones, data to pull, topics to cover
# - DO NOT include tone, style, or personality instructions
# - Communication style is controlled by agent prompts only

workflow: |
  WORKFLOW: Shopify Onboarding
  GOAL: Guide merchants through connecting Shopify and support systems while naturally detecting if they're new or returning
  
  CONVERSATION FLOW:
  
  1. Opening & Natural Detection
     OBJECTIVES:
     - Warm greeting and introduction as CJ
     - Naturally determine if new or returning user
     - Set beta/early product expectations
     - Get merchant's name if new
     
     NATURAL DETECTION APPROACH:
     - Ask "Is this our first time chatting?" or similar
     - Listen for hints about previous usage
     - Don't force rigid yes/no responses
     
  2. Shopify Connection (Adapt based on detection)
     FOR NEW USERS:
     - Explain value proposition clearly
     - Emphasize read-only, no changes
     - Mention unpublished app status
     - Present OAuth button when ready
     
     FOR RETURNING USERS:
     - Welcome back message
     - Quick re-authentication
     - Skip lengthy explanations
     - Get them logged in fast
     
  3. Post-OAuth Response
     CONTEXT AVAILABLE: oauth_complete, is_new, shop_domain, merchant_id
     
     FOR NEW MERCHANTS (is_new=true):
     - "Taking a look around your store now..."
     - Pull quick insights (products, orders, trends)
     - Show immediate value
     - Natural transition to support systems
     
     FOR RETURNING MERCHANTS (is_new=false):
     - "Great to see you again! I remember your store..."
     - Quick status update on their metrics
     - Transition to ad-hoc support mode
     - Ask how you can help today
     
  4. Support System Connection (New merchants only)
     APPROACH:
     - Only offer to new merchants
     - Position as optional but valuable
     - Ask what they use for support
     - Handle supported systems (OAuth flow)
     - Graceful waitlist for unsupported
     
  5. Wrap Up & Next Steps
     FOR NEW MERCHANTS:
     - Explain analysis timeline
     - Offer notification options (email, browser)
     - Set clear expectations
     - Thank them for trying beta
     
     FOR RETURNING MERCHANTS:
     - Transition to regular workflow
     - Remind them of capabilities
     - Natural conversation continuation
  
  CONTEXT TRACKING:
  - merchant_name: Captured during intro
  - shopify_connected: Boolean status
  - support_connected: Boolean status
  - is_new_merchant: From OAuth callback
  - shop_domain: From Shopify OAuth
  - notification_preference: email|browser|none
  
  SUCCESS CRITERIA:
  - Natural conversation flow maintained
  - Clear value demonstrated post-OAuth
  - Appropriate path for new vs returning
  - No configuration modals needed
  - Beta expectations set clearly
```

### 2. Update Frontend to Default to Onboarding

**File**: `homepage/src/pages/SlackChat.tsx`

Update the component to remove the configuration modal bypass and default to onboarding:

```typescript
// Remove these lines (around line 35-37):
// TODO: TEMPORARY BYPASS - Re-enable configuration modal later
// const [showConfigModal, setShowConfigModal] = useState(false);

// Replace with:
const [showConfigModal] = useState(false); // Always skip config modal

// Update initial chatConfig (around line 46-51):
const [chatConfig, setChatConfig] = useState<ChatConfig>({
  scenarioId: null, // No demo scenario
  merchantId: null, // Will be set after OAuth
  conversationId: uuidv4(),
  workflow: 'shopify_onboarding' // Always start with onboarding
});

// Add state for OAuth status
const [oauthStatus, setOauthStatus] = useState<{
  isComplete: boolean;
  isNew?: boolean;
  merchantId?: string;
  shopDomain?: string;
}>({ isComplete: false });

// Remove or comment out the demo merchant auto-start
```

**File**: `homepage/src/pages/SlackChat.tsx` (handleOAuthComplete)

Add handler for OAuth completion:

```typescript
const handleOAuthComplete = useCallback((params: URLSearchParams) => {
  const isNew = params.get('is_new') === 'true';
  const merchantId = params.get('merchant_id');
  const shopDomain = params.get('shop');
  const conversationId = params.get('conversation_id');
  
  if (conversationId === chatConfig.conversationId) {
    setOauthStatus({
      isComplete: true,
      isNew,
      merchantId: merchantId || undefined,
      shopDomain: shopDomain || undefined
    });
    
    // Update chat config with merchant ID
    if (merchantId) {
      setChatConfig(prev => ({
        ...prev,
        merchantId
      }));
    }
    
    // Send OAuth complete message to CJ
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'oauth_complete',
        data: {
          provider: 'shopify',
          is_new: isNew,
          merchant_id: merchantId,
          shop_domain: shopDomain
        }
      }));
    }
  }
}, [chatConfig.conversationId, ws]);

// Add useEffect to check URL params on mount
useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  if (params.get('oauth') === 'complete') {
    handleOAuthComplete(params);
    // Clean URL
    window.history.replaceState({}, '', window.location.pathname);
  }
}, [handleOAuthComplete]);
```

### 3. Create OAuth Button Component

**File**: `homepage/src/components/OAuthButton.tsx`

```typescript
import React from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, Store, HelpCircle, Zap } from 'lucide-react';

interface OAuthButtonProps {
  provider: 'shopify' | 'freshdesk' | 'zendesk' | 'gorgias';
  conversationId: string;
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onAuthStart?: () => void;
}

const providerConfig = {
  shopify: {
    icon: Store,
    text: 'Connect Shopify',
    loadingText: 'Connecting to Shopify...',
    className: 'bg-[#96BF48] hover:bg-[#7FA03D] text-white'
  },
  freshdesk: {
    icon: HelpCircle,
    text: 'Connect Freshdesk',
    loadingText: 'Connecting to Freshdesk...',
    className: 'bg-[#2C5282] hover:bg-[#234261] text-white'
  },
  zendesk: {
    icon: Zap,
    text: 'Connect Zendesk',
    loadingText: 'Connecting to Zendesk...',
    className: 'bg-[#03363D] hover:bg-[#022B31] text-white'
  },
  gorgias: {
    icon: HelpCircle,
    text: 'Connect Gorgias',
    loadingText: 'Connecting to Gorgias...',
    className: 'bg-[#FB6B1A] hover:bg-[#E55A0C] text-white'
  }
};

export const OAuthButton: React.FC<OAuthButtonProps> = ({
  provider,
  conversationId,
  variant = 'primary',
  size = 'md',
  className = '',
  onAuthStart
}) => {
  const [isLoading, setIsLoading] = React.useState(false);
  const config = providerConfig[provider];
  const Icon = config.icon;
  
  const handleClick = () => {
    setIsLoading(true);
    onAuthStart?.();
    
    // Build OAuth URL
    const authUrl = new URL(`${import.meta.env.VITE_AUTH_URL || 'http://localhost:8103'}/api/v1/oauth/${provider}/authorize`);
    authUrl.searchParams.set('conversation_id', conversationId);
    authUrl.searchParams.set('redirect_uri', `${window.location.origin}/chat`);
    
    // For Shopify, we might need to ask for shop domain first
    if (provider === 'shopify') {
      // TODO: Implement shop domain modal if needed
      // For now, assuming we'll handle it in the auth service
    }
    
    // Redirect to OAuth
    window.location.href = authUrl.toString();
  };
  
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2',
    lg: 'px-6 py-3 text-lg'
  };
  
  const baseClasses = variant === 'primary' ? config.className : '';
  
  return (
    <Button
      onClick={handleClick}
      disabled={isLoading}
      className={`${baseClasses} ${sizeClasses[size]} ${className} inline-flex items-center gap-2`}
      variant={variant === 'secondary' ? 'outline' : 'default'}
    >
      {isLoading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          {config.loadingText}
        </>
      ) : (
        <>
          <Icon className="h-4 w-4" />
          {config.text}
        </>
      )}
    </Button>
  );
};
```

### 4. Update CJ Agent Context

**File**: `agents/app/agents/cj_agent.py`

Add onboarding awareness to the agent's context building:

```python
# In get_agent_response method, around line 150-160
# Add to context building:

# Check if we're in onboarding workflow
is_onboarding = workflow_name == "shopify_onboarding"
oauth_context = {}

if is_onboarding:
    # Extract OAuth context from conversation state
    oauth_context = {
        "shopify_connected": state.context.get("shopify_connected", False),
        "is_new_merchant": state.context.get("is_new_merchant"),
        "shop_domain": state.context.get("shop_domain"),
        "merchant_name": state.context.get("merchant_name"),
        "oauth_complete": state.context.get("oauth_complete", False)
    }
    
    # Add to prompt context
    prompt = prompt.replace(
        "{oauth_context}",
        f"OAuth Status: {json.dumps(oauth_context, indent=2)}"
    )
```

### 5. Add Workflow to Conversation Catalog

**File**: `agents/config/conversation_catalog.yaml`

Add the onboarding workflow to the catalog:

```yaml
workflows:
  shopify_onboarding:
    name: "Shopify Onboarding"
    description: "Natural onboarding flow for new merchants"
    file: "prompts/workflows/shopify_onboarding.yaml"
    contexts:
      - "new_visitor"
      - "returning_visitor"
    capabilities:
      - "oauth_integration"
      - "natural_routing"
      - "quick_insights"
```

### 6. Update Message Processor

**File**: `agents/app/services/message_processor.py`

Handle OAuth complete messages:

```python
# In process_message method, add new message type handler:

elif message_type == "oauth_complete":
    # Extract OAuth data
    oauth_data = data.get("data", {})
    provider = oauth_data.get("provider")
    is_new = oauth_data.get("is_new", True)
    merchant_id = oauth_data.get("merchant_id")
    shop_domain = oauth_data.get("shop_domain")
    
    # Update conversation context
    state.context["oauth_complete"] = True
    state.context["shopify_connected"] = provider == "shopify"
    state.context["is_new_merchant"] = is_new
    state.context["shop_domain"] = shop_domain
    
    if merchant_id:
        state.context["merchant_id"] = merchant_id
        # Update session with merchant ID
        session.merchant_id = merchant_id
    
    # Save state
    await self._save_conversation_state(conversation_id, state)
    
    # Generate CJ's response to OAuth completion
    agent_response = await self._get_agent_response(
        session=session,
        user_message=f"OAuth {provider} completed",
        send_system_message=send_system_message,
        correlation_id=correlation_id
    )
    
    await send_cj_message(agent_response)
```

## Testing Checklist

### Unit Tests

1. **Workflow Loading Test**
   ```python
   # tests/test_workflow_loader.py
   def test_shopify_onboarding_workflow_loads():
       loader = WorkflowLoader()
       workflow = loader.load_workflow("shopify_onboarding")
       assert workflow is not None
       assert workflow.name == "Shopify Onboarding"
   ```

2. **OAuth Button Component Test**
   ```typescript
   // homepage/src/components/__tests__/OAuthButton.test.tsx
   describe('OAuthButton', () => {
     it('renders with correct provider styling', () => {
       // Test each provider
     });
     
     it('constructs correct OAuth URL', () => {
       // Test URL generation
     });
   });
   ```

### Integration Tests

1. **End-to-End Conversation Flow**
   - Start new conversation
   - Verify onboarding workflow starts
   - Test natural routing based on responses
   - Verify OAuth button appears at right time

2. **OAuth Flow Test**
   - Click OAuth button
   - Verify redirect to auth service
   - Simulate callback with new/returning status
   - Verify conversation continues appropriately

### Manual Testing Script

1. **New User Path**
   ```
   1. Open fresh browser (incognito)
   2. Navigate to /chat
   3. CJ should greet and ask if first time
   4. Respond "yes" or "yeah, first time"
   5. CJ should explain value prop
   6. OAuth button should appear
   7. Click button -> Shopify OAuth
   8. Complete OAuth
   9. Return to chat with insights
   ```

2. **Returning User Path**
   ```
   1. Start conversation
   2. When asked if first time, say "no, I've used this before"
   3. CJ should offer quick login
   4. OAuth flow should be streamlined
   5. Post-OAuth should recognize returning status
   ```

## Common Issues & Solutions

### Issue 1: OAuth Redirect Loop
**Symptom**: User keeps getting redirected back to OAuth
**Solution**: Check conversation_id is being preserved through OAuth flow

### Issue 2: Workflow Not Found
**Symptom**: Error loading shopify_onboarding workflow
**Solution**: Ensure workflow file is in correct location and catalog is updated

### Issue 3: Context Not Persisting
**Symptom**: OAuth status lost after completion
**Solution**: Verify conversation state is being saved in message processor

## Performance Considerations

1. **Workflow Loading**: Cache workflow definition after first load
2. **OAuth State**: Use secure state parameter to prevent CSRF
3. **Quick Insights**: Implement with timeout to prevent blocking

## Security Checklist

- [ ] OAuth state parameter includes HMAC signature
- [ ] Conversation ID validated on OAuth callback
- [ ] No sensitive data in URL parameters
- [ ] HTTPS required for production OAuth
- [ ] Rate limiting on OAuth endpoints

## Next Phase Dependencies

This phase creates the foundation that Phase 2 (Auth Flow Integration) will build upon:
- OAuth button component ready for auth service integration
- Conversation context structure defined
- Workflow handles both new and returning paths
- Frontend ready to receive OAuth callbacks