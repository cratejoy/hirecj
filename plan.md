# Shopify Login & Onboarding Plan

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Every decision should make the code simpler, not more complex
2. **No Cruft**: Remove all redundant code, validation, and unnecessary complexity
3. **Break It & Fix It Right**: No backwards compatibility shims - make breaking changes and migrate properly
4. **Long-term Elegance**: Choose performant, compiler-enforced solutions that prevent subtle bugs
5. **Backend-Driven**: Let the backend handle complexity, frontend should be a thin client
6. **Single Source of Truth**: One pattern, one way to do things, no alternatives
7. **No Over-Engineering**: Design for current needs only - no hypothetical features
8. **Thoughtful Logging & Instrumentation**: Appropriate visibility into system behavior

## 🚀 Implementation Phases

### Phase 1: Foundation
**Deliverables:**
- [ ] Onboarding workflow definition (`shopify_onboarding.yaml`)
- [ ] Default workflow routing (always start with onboarding)
- [ ] CJ agent context updates for onboarding awareness
- [ ] OAuth button React component

### Phase 2: Auth Flow Integration
**Deliverables:**
- [ ] OAuth callback enhancement to detect new/returning merchants
- [ ] Shop domain as primary identifier (no visitor tracking)
- [ ] Conversation context updates post-OAuth
- [ ] Frontend OAuth flow with redirect handling

### Phase 3: Quick Value Demo
**Deliverables:**
- [ ] Quick insights service for Shopify data
- [ ] Store snapshot queries (products, orders, customers)
- [ ] Progressive data loading mechanism
- [ ] Conversation UI showing real-time insights

### Phase 4: Support System Connection
**Deliverables:**
- [ ] Support system provider detection logic
- [ ] Interest list for unsupported systems
- [ ] OAuth flows for supported systems
- [ ] Graceful handling of unsupported providers

### Phase 5: Notification & Polish
**Deliverables:**
- [ ] Email notification capture and sending
- [ ] Browser notification implementation
- [ ] Beta messaging throughout experience
- [ ] Error handling and edge cases

### Phase 6: Testing & Refinement
**Deliverables:**
- [ ] End-to-end flow testing suite
- [ ] Performance optimization
- [ ] Security review
- [ ] Documentation and deployment guide

## 🏛️ System Architecture Overview

### Identity Architecture: Shopify OAuth as the Gate

**Core Principle**: No visitor tracking, no spam records. Shopify OAuth is both authentication and identity.

```
New Visitor Flow:
┌────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Visit    │────▶│   Always    │────▶│   Shopify    │────▶│  New/Return │
│   Site     │     │  Onboarding │     │    OAuth     │     │  Detection  │
└────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
                         │                                           │
                         ▼                                           ▼
                   "Hi! First time?"                          Check shop exists
                   Natural routing                            Continue accordingly
```

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User's Browser                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────┐          ┌────────────────────────────┐  │
│  │                      │          │                            │  │
│  │   Homepage (React)   │ WebSocket│    OAuth Redirect Flow     │  │
│  │    Port: 3456        ├─────────►│    (Shopify/Support)       │  │
│  │                      │          │                            │  │
│  └──────────┬───────────┘          └──────────┬─────────────────┘  │
│             │                                  │                    │
└─────────────┼──────────────────────────────────┼────────────────────┘
              │ REST API                         │ OAuth
              ▼                                  ▼
┌─────────────────────────────────┐  ┌──────────────────────────────┐
│                                 │  │                              │
│      Agents Service             │  │      Auth Service            │
│      Port: 8000                 │  │      Port: 8103              │
│                                 │  │                              │
│  ┌─────────────────────────┐   │  │  ┌────────────────────────┐  │
│  │   WebSocket Handler     │   │  │  │  OAuth Providers       │  │
│  │   - Default: Onboarding │   │  │  │  - Shopify (Identity)  │  │
│  │   - Message Router      │   │  │  │  - FreshDesk           │  │
│  └───────────┬─────────────┘   │  │  │  - Zendesk             │  │
│              │                  │  │  └────────────────────────┘  │
│  ┌───────────▼─────────────┐   │  │                              │
│  │   Message Processor     │   │  │  ┌────────────────────────┐  │
│  │   - Parse & Route       │   │  │  │  OAuth Callback Logic  │  │
│  │   - Context Building    │   │  │  │  - Shop Domain Check   │  │
│  │   - State Management    │   │  │  │  - New/Return Status   │  │
│  └───────────┬─────────────┘   │  │  │  - Context Updates     │  │
│              │                  │  │  └────────────────────────┘  │
│  ┌───────────▼─────────────┐   │  │                              │
│  │      CJ Agent           │   │  └──────────────────────────────┘
│  │   - Always Onboarding   │   │
│  │   - Natural Routing     │   │  ┌──────────────────────────────┐
│  │   - Tool Integration    │   │  │                              │
│  └───────────┬─────────────┘   │  │    Database Service         │
│              │                  │  │    Port: 8002               │
│  ┌───────────▼─────────────┐   │  │                              │
│  │   Quick Insights        │   │  │  ┌────────────────────────┐  │
│  │   - Store Snapshot      │   │  │  │  PostgreSQL            │  │
│  │   - Basic Analytics     │   │  │  │  - Merchants (by shop) │  │
│  │   - Progressive Load    │   │  │  │  - OAuth Tokens        │  │
│  └─────────────────────────┘   │  │  │  - No Visitor Records  │  │
│                                 │  │  └────────────────────────┘  │
└─────────────────────────────────┘  └──────────────────────────────┘
```

### Data Flow Sequences

#### 1. **First Visit Flow**
```
1. User visits site
2. Frontend starts WebSocket with workflow="shopify_onboarding"
3. CJ: "Hi! I'm CJ, here to help with your customer support. First time chatting?"
4. Natural conversation determines path
5. OAuth button presented when appropriate
```

#### 2. **OAuth Identity Flow**
```
1. User clicks "Connect Shopify"
2. Homepage → Auth Service: /oauth/shopify/authorize?conversation_id=X
3. Auth Service → Shopify: Redirect with read-only scopes
4. User authorizes on Shopify
5. Shopify → Auth Service: Callback with code + shop domain
6. Auth Service:
   - Exchanges code for token
   - Checks if shop domain exists in DB
   - Returns: { is_new: bool, merchant_id?: str, shop: str }
7. Auth Service → Homepage: Redirect with context
8. Homepage → Agents: "oauth_complete" with new/returning status
9. CJ Agent: Continues appropriately based on status
```

#### 3. **Returning Merchant Detection**
```
OAuth Callback Logic:
if (shop_exists_in_database):
    return {
        "is_new": false,
        "merchant_id": existing_merchant.id,
        "redirect": "/chat?returning=true"
    }
else:
    return {
        "is_new": true,
        "shop_domain": shop,
        "redirect": "/chat?continue_onboarding=true"
    }
```

### Frontend Simplification

#### 1. **Remove Configuration Modal**
```typescript
// SlackChat.tsx - Simplified
const [chatConfig] = useState<ChatConfig>({
  workflow: 'shopify_onboarding',  // Always start here
  conversationId: uuidv4(),
  merchantId: null  // Set after OAuth
});

// Optional: Show hint for returning merchants
const lastShopDomain = localStorage.getItem('last_shop_domain');
{lastShopDomain && (
  <Button size="sm" onClick={() => startOAuth()}>
    Shop owner? Login →
  </Button>
)}
```

#### 2. **OAuth Button Component**
```typescript
interface OAuthButtonProps {
  provider: 'shopify' | 'freshdesk' | 'zendesk';
  conversationId: string;
  variant?: 'primary' | 'secondary';
}

// Usage in chat
<OAuthButton 
  provider="shopify"
  conversationId={chatConfig.conversationId}
  variant="primary"
/>
```

### Backend Intelligence

#### 1. **Workflow Selection**
```python
# agents/app/services/message_processor.py
async def start_conversation(data: dict):
    # Always use shopify_onboarding for new conversations
    workflow = "shopify_onboarding"
    
    # After OAuth, workflow can change based on merchant status
    if data.get("oauth_complete") and not data.get("is_new"):
        workflow = "ad_hoc_support"
```

#### 2. **OAuth Callback Enhancement**
```python
# auth/app/providers/shopify.py
async def handle_callback(self, code: str, state: str, shop: str):
    # Exchange code for token
    token_data = await self.exchange_code(code, shop)
    
    # Check merchant existence by shop domain
    merchant = await db.get_merchant_by_shop_domain(shop)
    
    # Build redirect URL with context
    redirect_params = {
        "conversation_id": state_data.get("conversation_id"),
        "is_new": merchant is None,
        "shop": shop
    }
    
    if merchant:
        redirect_params["merchant_id"] = str(merchant.id)
    
    return redirect_to_frontend(redirect_params)
```

### CJ's Conversational Routing

```yaml
# agents/prompts/workflows/shopify_onboarding.yaml
workflow: |
  WORKFLOW: Shopify Onboarding
  GOAL: Natural conversation that adapts to new/returning merchants
  
  OPENING LOGIC:
  - Greet warmly and gauge if new/returning
  - "I'm CJ, here to help with your customer support. First time chatting?"
  - If hints at returning: "Welcome back! Let's get you logged in with Shopify"
  - If new: Continue onboarding flow
  
  OAUTH COMPLETION HANDLING:
  - Check oauth_complete context
  - If is_new=false: "Great to see you again! I remember your store..."
  - If is_new=true: "Awesome! Taking a look around your store now..."
```

## 🎯 The Experience We're Building

### What We Want

A conversational onboarding flow where CJ naturally guides new users through connecting their Shopify store and (optionally) their support system. The experience should feel like chatting with a knowledgeable colleague who's helping you get set up, not filling out forms or clicking through a wizard.

### The Vibe

- **Conversational**: Natural back-and-forth dialogue, not a rigid flow
- **Respectful**: CJ acknowledges she's new/beta, respects the merchant's time
- **Value-First**: Shows immediate value after connection (quick insights)
- **Low-Friction**: Minimal steps, clear benefits, easy escape hatches
- **Progressive**: Start with read-only, upgrade permissions later as needed
- **No Tracking**: No cookies or visitor records until OAuth consent

### The Flow

1. **Every Visit Starts Fresh**
   - No visitor tracking or cookies
   - Always begins with onboarding workflow
   - Natural conversation determines path

2. **Identity Through Conversation**
   - CJ asks if first time or returning
   - Presents appropriate options
   - OAuth button when ready

3. **Shopify OAuth = Identity**
   - Shop domain becomes unique identifier
   - Backend checks for existing merchant
   - Routes appropriately post-OAuth

4. **Quick Value Demo**
   - Immediate insights after connection
   - Shows understanding of their business
   - Builds trust for next steps

5. **Support System Offer** (Optional)
   - Natural progression after Shopify
   - Same elegant OAuth flow
   - Graceful handling of unsupported

6. **Natural Conclusion**
   - Notification preferences
   - Clear next steps
   - Ready for future visits

## 🏗️ Implementation Details

### Phase 1: Foundation Implementation

**Onboarding Workflow Definition**
```yaml
# agents/prompts/workflows/shopify_onboarding.yaml
name: "Shopify Onboarding"
description: "Natural onboarding for all new conversations"

workflow: |
  WORKFLOW: Shopify Onboarding
  GOAL: Guide merchants through setup while detecting new/returning naturally
  
  CONVERSATION FLOW:
  1. Opening & Detection
     - Warm greeting and introduction
     - Natural detection of new/returning
     - Set beta expectations
  
  2. Shopify Connection
     - Value proposition
     - OAuth trigger
     - Handle both new and returning paths
  
  3. Support System (if new)
     - Only for new merchants
     - Optional and low pressure
     - Waitlist for unsupported
  
  4. Wrap Up
     - Different for new vs returning
     - Set appropriate expectations
```

### Phase 2: Auth Flow Implementation

**No Visitor Tracking Required**
```python
# No visitor tables or tracking
# Shop domain is the only identifier needed

# auth/app/models.py
class Merchant(Base):
    id = Column(UUID, primary_key=True)
    shop_domain = Column(String, unique=True, index=True)
    shopify_access_token = Column(String)
    created_at = Column(DateTime)
    # No visitor_id or tracking fields
```

### Phase 3: Quick Insights Implementation

**Same as original plan - immediate value after OAuth**

### Phase 4: Support System Implementation

**Only offered to new merchants during onboarding**

## 🎨 Key Design Decisions

### Why No Visitor Tracking?
- **Privacy First**: No tracking until explicit consent (OAuth)
- **No Spam Records**: Bots never make it past OAuth
- **Elegant Simplicity**: Shop domain is the perfect identifier
- **GDPR Friendly**: No PII until merchant opts in

### Why Always Start with Onboarding?
- **Natural Flow**: Conversation determines the path
- **No Configuration**: Remove complexity for users
- **Flexible**: CJ adapts based on responses
- **Future Proof**: Easy to add more intelligence later

### Why Shopify OAuth as Identity?
- **Verified Identity**: Can't fake a shop domain
- **Business Context**: Know exactly who they are
- **Single Source**: No duplicate records or conflicts
- **Clean Data**: Only real merchants in database

## 📊 Success Metrics

### Onboarding Funnel
1. Conversation Started → Engaged with CJ (target: 90%)
2. Engaged → Shopify OAuth Started (target: 70%)
3. OAuth Started → OAuth Completed (target: 85%)
4. New Merchant → Support Connected (target: 40%)
5. Returning → Re-engaged (target: 95%)

### Quality Indicators
- Zero spam/bot records in database
- Time to first insight: < 30 seconds
- Natural conversation flow: > 4.5/5 rating
- OAuth error rate: < 5%

## 🚨 What We're NOT Building

- **No** visitor tracking or analytics
- **No** cookies before OAuth
- **No** complex routing logic
- **No** pre-registration flows
- **No** merchant selection UI
- **No** configuration modals

Focus: Natural conversation that intelligently adapts based on Shopify OAuth identity.

## 🔄 Next Steps After This Sprint

1. **Enhanced Returning Experience**: Personalized greetings based on history
2. **Multi-Store Support**: Handle merchants with multiple shops
3. **Team Invites**: Let merchants add team members
4. **Advanced Routing**: Remember conversation preferences
5. **Analytics**: Post-OAuth tracking for improvements

But first: **nail the natural, privacy-first onboarding experience**.