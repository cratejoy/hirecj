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

### Phase 1: Foundation ✅ COMPLETE
**Deliverables:**
- [x] Onboarding workflow definition (`shopify_onboarding.yaml`)
- [x] Default workflow routing (always start with onboarding)
- [x] CJ agent context updates for onboarding awareness
- [x] OAuth button React component
- [x] WebSocket connection fix for onboarding workflow
- [x] CJ initial greeting implementation

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-1-foundation.md)**

### Phase 2: Auth Flow Integration ✅ COMPLETE
**Deliverables:**
- [x] OAuth callback enhancement to detect new/returning merchants
- [x] Shop domain as primary identifier (no visitor tracking)
- [x] Conversation context updates post-OAuth
- [x] Frontend OAuth flow with redirect handling

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-2-auth-flow.md)**

### Phase 3: OAuth Production Ready ⚠️ NEEDS CUSTOM APP SUPPORT
**Deliverables:**
- [x] Configure real Shopify OAuth credentials
- [x] Fix ngrok tunnel integration for OAuth callbacks
- [x] Verify new vs returning merchant detection implementation
- [ ] Support Shopify custom app installation flow *(NEW REQUIREMENT)*
- [ ] Test OAuth flow end-to-end with real Shopify (manual testing required)
- [ ] Test CJ's response to OAuth completion (manual testing required)

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-3-oauth-production.md)**
📄 **[Testing Guide →](docs/shopify-onboarding/phase-3-testing.md)**

**Implementation Summary:**
- OAuth credentials configured in auth/.env.secrets
- Tunnel detection working correctly via unified env config
- Homepage automatically uses correct auth service URL
- New vs returning merchant detection already implemented
- **DISCOVERED:** Custom apps require different installation flow than public apps

### Phase 3.5: Replace OAuth with Custom App Flow ⚠️ NEEDS COMPLETION
**Problem:** We're using Shopify custom apps, which don't support standard OAuth. Current implementation causes "Unauthorized Access" errors.

**Simple Solution: Remove OAuth, Use Custom App Flow Only**
```
Custom App Flow:
├── Frontend opens custom install link
├── Merchant installs app
├── Backend validates session token
└── Exchange for API access token
```

**Current Status: FAILURE by North Star Standards**
- ❌ Shortcuts taken (mocked tokens)
- ❌ Half-measures (disabled JWT verification)
- ❌ Compatibility shims (OAuth code still exists)
- ❌ "Good enough" solution (demo-only quality)

📄 **[Audit Report →](docs/shopify-onboarding/phase-3.5-audit.md)**

**Completed (But Improperly):**
1. **Partially Removed OAuth Code:**
   - [x] Commented out `/oauth/shopify/*` endpoints ❌ Should be deleted
   - [x] Removed OAuth state management
   - [x] Removed shop domain input dialog

2. **Basic Custom App Flow:**
   - [x] Added `SHOPIFY_CUSTOM_INSTALL_LINK` to env config
   - [x] Frontend opens install link directly
   - [x] Backend handles session tokens ❌ But mocked
   - [x] Polling mechanism ❌ With magic numbers

**Required to Meet North Star Standards:**

### 🔥 Immediate Actions (Do Now)
1. **Delete ALL OAuth Code**
   - [ ] Delete `auth/app/api/oauth.py` completely
   - [ ] Delete `auth/app/providers/` directory
   - [ ] Remove commented OAuth routes from `main.py`
   - [ ] Delete any OAuth-related tests

2. **Fix Magic Numbers**
   - [ ] Create `shared/constants.py` with:
     ```python
     SHOPIFY_INSTALL_POLL_INTERVAL_MS = 2000
     SHOPIFY_INSTALL_TIMEOUT_MS = 600000  # 10 minutes
     ```
   - [ ] Update frontend to use constants
   - [ ] Update backend timeouts to use constants

### 📦 Proper Implementation (This Week)
3. **Real Session Token Handling**
   - [ ] Add Shopify App Bridge to frontend
   - [ ] Implement proper session token retrieval
   - [ ] Add PyJWT with RS256 support
   - [ ] Fetch and cache Shopify's public key
   - [ ] Implement proper JWT verification

4. **Real Token Exchange**
   - [ ] Research Shopify token exchange API
   - [ ] Implement actual API call to Shopify
   - [ ] Handle token storage properly
   - [ ] Add retry logic with exponential backoff

5. **Proper Storage**
   - [ ] Add Redis configuration to `.env`
   - [ ] Replace in-memory dicts with Redis
   - [ ] Add proper TTLs to sessions
   - [ ] Handle Redis connection failures gracefully

### ✅ Definition of Done
- Zero OAuth code remains in codebase
- No mocked implementations
- No disabled security checks
- No magic numbers
- Proper persistent storage
- Production-ready code that fully works

**Only when ALL items are complete can this be marked as IMPLEMENTED**

📄 **[Implementation Guide →](docs/shopify-onboarding/phase-3.5-custom-app-only.md)**
📄 **[Testing Guide →](docs/shopify-onboarding/phase-3.5-testing.md)**
📄 **[Completion Checklist →](docs/shopify-onboarding/phase-3.5-completion.md)** *(TODO)*

### Phase 4: UI Actions Pattern ✅ COMPLETE
**Deliverables:**
- [x] Parser implementation to extract {{oauth:shopify}} markers
- [x] Workflow configuration to enable UI components
- [x] Message processor integration to parse UI elements
- [x] Platform layer passes ui_elements through WebSocket
- [x] Frontend UI element rendering with pattern matching fallback
- [ ] End-to-end testing of complete flow

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-4-ui-actions.md)**

### Phase 5: Quick Value Demo
**Deliverables:**
- [ ] Quick insights service for Shopify data
- [ ] Store snapshot queries (products, orders, customers)
- [ ] Progressive data loading mechanism
- [ ] Conversation UI showing real-time insights

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-5-quick-value.md)** *(TODO)*

### Phase 6: Support System Connection
**Deliverables:**
- [ ] Support system provider detection logic
- [ ] Interest list for unsupported systems
- [ ] OAuth flows for supported systems
- [ ] Graceful handling of unsupported providers

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-6-support-systems.md)** *(TODO)*

### Phase 7: Notification & Polish
**Deliverables:**
- [ ] Email notification capture and sending
- [ ] Browser notification implementation
- [ ] Beta messaging throughout experience
- [ ] Error handling and edge cases

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-7-notifications.md)** *(TODO)*

### Phase 8: Testing & Refinement
**Deliverables:**
- [ ] End-to-end flow testing suite
- [ ] Performance optimization
- [ ] Security review
- [ ] Documentation and deployment guide

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-8-testing.md)** *(TODO)*

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

## 📚 Detailed Implementation Documentation

Each phase has a comprehensive implementation guide with exact code, file paths, and step-by-step instructions:

**[📁 View all implementation guides →](docs/shopify-onboarding/)**

The guides include:
- Complete code implementations
- Exact file paths and changes
- API specifications
- Database schemas
- Testing procedures
- Security considerations
- Common issues & solutions

Use the [phase template](docs/shopify-onboarding/PHASE_TEMPLATE.md) when creating new guides.

## 🔧 Side Quest: Unified Environment Configuration

### Current Pain Points
- Each service has its own `.env` file with duplicated service URLs
- Homepage needs to know Auth and Agents URLs
- Tunnel detection updates multiple files
- Hard to manage secrets across services
- OAuth redirect URLs need coordination

### Proposed Solution: Root `.env` with Service Overrides

```
/hirecj/
├── .env                    # Shared configuration
├── .env.local             # Local overrides (gitignored)
├── .env.tunnel            # Auto-generated tunnel URLs
├── auth/
│   └── .env.secrets       # Auth-specific secrets only
├── agents/
│   └── .env.secrets       # API keys only
└── homepage/
    └── .env               # Vite requires this, but minimal
```

### Implementation Tasks ✅ COMPLETE
- [x] Create root `.env.example` with shared config structure
- [x] Update `/shared/env_loader.py` for hierarchical loading
- [x] Modify each service's `config.py` to load env files in order
- [x] Update homepage's `vite.config.ts` to read parent env
- [x] Enhance tunnel detector to write service URLs once
- [x] Migrate existing env vars to new structure
- [x] Update documentation and setup scripts
- [x] Create verification script to test configuration

### Benefits
- **Single source of truth** for service URLs
- **Secrets stay isolated** per service
- **Tunnel detection** updates one place
- **Easy local dev** - just copy root `.env.example`
- **Gradual migration** - existing files still work

### North Star Alignment
- ✅ **Simplify**: One place for shared config
- ✅ **No Cruft**: Remove URL duplication
- ✅ **Long-term Elegance**: Clear separation of concerns
- ✅ **No Over-Engineering**: Reuses existing patterns