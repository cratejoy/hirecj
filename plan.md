# Shopify Login & Onboarding Plan

## 📊 Current Status Summary

### ✅ Completed Phases
1. **Phase 1: Foundation** - Onboarding workflow, CJ agent, OAuth button component
2. **Phase 2: Auth Flow Integration** - OAuth callbacks, shop domain identifier, context updates
3. **Phase 3.7: OAuth 2.0 Implementation** - Full OAuth flow with HMAC verification, token storage
4. **Phase 4: UI Actions Pattern** - Parser, workflow config, WebSocket integration

### 🎯 Current Priority
**Phase 5: Quick Value Demo** - Show immediate insights after Shopify connection

### 📅 Upcoming Phases
- Phase 6: Support System Connection
- Phase 7: Notification & Polish
- Phase 8: Testing & Refinement

### 🚀 Next Steps
1. Test the OAuth flow end-to-end with the auth service running
2. Begin Phase 5 implementation for quick value demonstration
3. Ensure CJ provides immediate value post-OAuth connection

---

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

### Phase 3.5: ~~Complex App Bridge Implementation~~ ❌ ABANDONED
**Problem:** We implemented a complex App Bridge solution that requires embedded context, but our use case needs everything to work on hirecj.ai directly.

**What We Built (Overly Complex):**
- App Bridge integration requiring embedded context
- Session token retrieval from within Shopify admin
- Complex dual-context handling
- JWT verification and token exchange (good parts)

**Why It Failed:** Fundamental mismatch - we need merchants to use HireCJ from hirecj.ai, not from within Shopify admin.

### Phase 3.6: ~~Manual Token Entry (Custom Distribution)~~ ❌ ABANDONED
**Problem:** Discovered that custom distribution apps don't support OAuth - they require manual token generation and entry by merchants. This creates friction in the onboarding process.

**What We Built:**
- Manual token entry form with beta notice
- Token validation endpoint
- Instructions for merchants to generate tokens

**Why It Failed:** Not a technical failure, but a Shopify limitation. Custom distribution apps simply don't support OAuth. To use OAuth, we need a different app type.

### Phase 3.7: OAuth 2.0 Implementation ✅ COMPLETE
**Solution:** Switch from custom distribution to OAuth-enabled app. Implement standard Shopify OAuth 2.0 authorization code grant flow.

**The Right Flow:**
```
OAuth Flow:
├── User clicks "Connect Shopify" on hirecj.ai
├── Enter shop domain (if not saved)
├── Redirect to https://{shop}/admin/oauth/authorize
├── User approves permissions
├── Shopify redirects back with authorization code
├── Backend exchanges code for access token
├── Store token in Redis
└── Redirect to chat - authenticated!
```

**What We Built:**
- ✅ HMAC verification utility for secure OAuth callbacks
- ✅ Full OAuth endpoints with proper security (nonce validation)
- ✅ Token exchange and storage in Redis
- ✅ Updated frontend button to always collect shop domain
- ✅ Fixed async/sync issues in auth service
- ✅ Removed shop domain persistence (always ask)
- ✅ Proper error handling and logging

**Benefits:**
- Standard OAuth flow that works for any app type
- No manual token entry required
- Production-ready authentication
- Can eventually become a public app
- Seamless merchant experience

📄 **[Implementation Guide →](docs/shopify-onboarding/phase-3.7-oauth-implementation.md)**

### What We Keep from 3.5:
- ✅ OAuth code deletion (already done)
- ✅ Magic number fixes (already done)
- ✅ JWT verification service (reusable)
- ✅ Token exchange service (reusable)
- ❌ App Bridge integration (remove)
- ❌ Polling mechanism (remove)
- ❌ Complex context handling (remove)

### Phase 4.0: True Environment Centralization 🚨 CRITICAL FOUNDATION
**Goal:** Implement TRUE single .env file management with zero exceptions. Fix the broken multi-file pattern.

**Deliverables:**
- [ ] Audit and consolidate ALL environment variables across services
- [ ] Create master .env.example with every variable needed
- [ ] Rewrite env_loader.py to enforce single source (no fallbacks)
- [ ] Create distribute_env.py script for automatic distribution
- [ ] Update all services to use centralized pattern
- [ ] Remove ALL bypass paths (load_dotenv, direct access)
- [ ] Update Makefile and documentation

**Why This Must Happen First:**
- Current system forces developers to manage 10+ .env files
- Utility files bypass centralized config
- No enforcement of single source pattern
- This blocks clean implementation of all future phases

📄 **[Implementation Plan →](docs/phase-4.0-env-centralization.md)**

### Phase 4.1: UI Actions Pattern ✅ COMPLETE
**Deliverables:**
- [x] Parser implementation to extract {{oauth:shopify}} markers
- [x] Workflow configuration to enable UI components
- [x] Message processor integration to parse UI elements
- [x] Platform layer passes ui_elements through WebSocket
- [x] Frontend UI element rendering with pattern matching fallback
- [ ] End-to-end testing of complete flow

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-4-ui-actions.md)**

### Phase 4.5: User Identity & Persistence 🆕 NEXT PRIORITY
**Goal:** Add minimal user identity system and conversation persistence without complex schemas.

**Why Now:** Phase 5 (Quick Value Demo) needs persistent user identity to show "your store" insights across sessions.

**Deliverables:**
- [ ] Internal user IDs (usr_xxx format) linked to Shopify shops
- [ ] Conversation archival from Redis to PostgreSQL
- [ ] User conversation history API
- [ ] Automatic Redis → PostgreSQL sync before TTL expiry
- [ ] Event logging for analytics (OAuth, conversations, etc.)

**The Architecture:**
```
Shopify OAuth → Our User ID → Linked Conversations → Archived History
     ↓              ↓                 ↓                    ↓
  (Auth)      (Identity)         (Redis)            (PostgreSQL)
```

**Benefits:**
- ✅ **Preserves History**: Conversations never lost after 24h Redis TTL
- ✅ **Enables Personalization**: "Welcome back! Last time we discussed..."
- ✅ **Simple Schema**: Just 3 tables with JSONB for flexibility
- ✅ **Future Ready**: Foundation for user preferences, analytics, etc.

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-4.5-user-identity.md)**

---

## Development Environment Updates

### Recent Environment Changes (Phase 3.7 - Phase 5)

**New Required Environment Variables:**
- `SHOPIFY_CLIENT_ID` - Required for Shopify OAuth
- `SHOPIFY_CLIENT_SECRET` - Required for Shopify OAuth

**Tunnel Configuration Updates:**
- Auth service now uses `HOMEPAGE_URL` from `.env.tunnel` for OAuth redirects
- Added `env_ignore_empty=True` to Pydantic configs to prevent empty string overrides
- Fixed `.env.tunnel` loading order (now has highest precedence)

**CORS Configuration:**
- Both `frontend_url` and `homepage_url` are now added to allowed origins
- Automatic detection of hirecj.ai domains for CORS

**Debug System:**
- Browser console now has `window.cj` debug commands (enabled by default)
- Commands: `cj.debug()`, `cj.session()`, `cj.prompts()`, `cj.context()`
- Backend debug_request handler provides session and state information

**OAuth Flow Requirements:**
- Must use tunnels for OAuth (localhost redirects won't work)
- Shopify app must be configured with proper redirect URLs
- JSON serialization fix for datetime objects in merchant storage

📄 **[Full Environment Setup Guide →](README_ENV_SETUP.md)**

---

### Phase 5: Quick Value Demo 🎯 CURRENT PRIORITY
**Goal:** Show immediate value after Shopify connection by providing quick insights about their store.

**Deliverables:**
- [ ] Quick insights service for Shopify data
- [ ] Store snapshot queries (products, orders, customers)
- [ ] Progressive data loading mechanism
- [ ] Conversation UI showing real-time insights
- [ ] CJ's value-driven responses post-OAuth

**The Experience:**
```
After OAuth:
├── "Great! Taking a quick look at your store..."
├── Progressive loading of insights
├── Show key metrics (products, recent orders, etc.)
├── Natural transition to support system connection
└── Build trust through immediate value
```

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

## 🔧 Side Quest: Unified Environment Configuration ✅ COMPLETE

### Previous Pain Points (NOW RESOLVED)
- ~~Each service has its own `.env` file with duplicated service URLs~~
- ~~Homepage needs to know Auth and Agents URLs~~
- ~~Tunnel detection updates multiple files~~
- ~~Hard to manage secrets across services~~
- ~~OAuth redirect URLs need coordination~~

### Implemented Solution: Single Root `.env` with Service Secrets

```
/hirecj/
├── .env                    # Main configuration file (developers edit this)
├── .env.local             # Local overrides (optional, gitignored)
├── .env.tunnel            # Auto-generated tunnel URLs (gitignored)
├── auth/
│   ├── .env               # Service overrides (minimal, mostly empty)
│   └── .env.secrets       # Auth-specific secrets (gitignored)
├── agents/
│   ├── .env               # Service overrides (minimal, mostly empty)
│   └── .env.secrets       # API keys (gitignored)
└── homepage/
    └── (no .env needed)   # Vite reads from root .env via config
```

### Developer Experience ✅
1. **Initial Setup (One-time)**:
   ```bash
   cp .env.example .env
   cp auth/.env.secrets.example auth/.env.secrets
   cp agents/.env.secrets.example agents/.env.secrets
   ```

2. **That's it!** Services automatically load configuration in this order:
   - Root `.env` (shared config)
   - Root `.env.local` (local overrides if exists)
   - Root `.env.tunnel` (auto-generated tunnel URLs)
   - Service `.env.secrets` (sensitive data)
   - Service `.env` (service-specific overrides - rarely needed)

### Verification
```bash
python scripts/verify_env_config.py
```

### Benefits Achieved
- ✅ **Single `.env` file** for all shared configuration
- ✅ **Secrets isolated** in service-specific `.env.secrets` files
- ✅ **Tunnel detection** updates only `.env.tunnel`
- ✅ **Simple setup** - just copy 3 files and go
- ✅ **No duplication** - service URLs defined once

### Documentation
- 📄 **[Environment Setup Guide →](README_ENV_SETUP.md)**
- 📄 **[Dev Environment Changes →](docs/DEV_ENVIRONMENT_CHANGES.md)**

## 🔍 Console Debug System

### Overview
An elegant console-based debug system that exposes CJ's internal state through simple JavaScript commands, providing real-time visibility without any UI complexity.

### Design: `window.cj` API

```javascript
// Browser console commands:
cj.debug()        // Show current state snapshot
cj.session()      // Session & auth info
cj.prompts()      // Last 5 prompts sent to CJ
cj.context()      // Current conversation context
cj.events()       // Start live event stream
cj.stop()         // Stop event stream
cj.help()         // Show all available commands
```

### Console Output Format

```javascript
// Example cj.debug() output:
🤖 CJ Debug Snapshot
├── 📊 Session
│   ├── ID: abc-123-def-456
│   ├── Status: ✅ Authenticated
│   ├── Merchant: cratejoy.myshopify.com
│   └── Connected: 5 minutes ago
├── 🧠 CJ State
│   ├── Workflow: shopify_onboarding
│   ├── Model: claude-3-opus (temp: 0.2)
│   ├── Tools: [shopify_api, memory_store, fact_checker]
│   └── Memory Facts: 12
└── 💬 Recent Activity
    ├── 14:23:45 oauth_complete     New merchant
    ├── 14:23:46 workflow_change    ad_hoc_support
    └── 14:23:47 tool_use          shopify_api.get_orders
```

### Implementation Components

1. **Frontend (SlackChat.tsx)**:
   - Expose `window.cj` debug interface
   - Handle debug WebSocket messages
   - Format console output beautifully

2. **WebSocket Handler (web_platform.py)**:
   - Add `debug_request` message handler
   - Return formatted debug data
   - Stream live events when requested

3. **Production Safety**:
   - Only enable in development by default
   - Allow production access via localStorage flag
   - No sensitive data in console by default

### Benefits
- **Zero UI complexity** - Just console commands
- **Developer-native** - Uses familiar browser console
- **Easy to extend** - Add new commands as needed
- **No bundle impact** - It's just console logs
- **Fast to implement** - Minimal code changes

### North Star Alignment
- ✅ **Simplify**: Console commands instead of UI
- ✅ **No Cruft**: Minimal implementation
- ✅ **Long-term Elegance**: Clean API design
- ✅ **No Over-Engineering**: Just what's needed for debugging