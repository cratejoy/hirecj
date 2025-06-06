# Shopify Login & Onboarding Plan

## 📊 Current Status Summary

### ✅ Completed Phases
1. **Phase 1: Foundation** - Onboarding workflow, CJ agent, OAuth button component
2. **Phase 2: Auth Flow Integration** - OAuth callbacks, shop domain identifier, context updates
3. **Phase 3.7: OAuth 2.0 Implementation** - Full OAuth flow with HMAC verification, token storage
4. **Phase 4.0: True Environment Centralization** - Single .env pattern with automatic distribution
5. **Phase 4.1: UI Actions Pattern** - Parser, workflow config, WebSocket integration

### 🎯 Current Priority
**Phase 4.5: User Identity & Persistence** - Library complete, needs integration with services

### 📅 Upcoming Phases
- Phase 5: Quick Value Demo
- Phase 6: Support System Connection
- Phase 7: Notification & Polish
- Phase 8: Testing & Refinement

### 🚀 Next Steps
1. Configure Supabase connection and run identity schema migration
2. Integrate user_identity library into auth service for OAuth
3. Integrate archival service into agents for conversation persistence
4. Test end-to-end user identity flow

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

### Phase 4.0: True Environment Centralization ✅ COMPLETE
**Goal:** Implement TRUE single .env file management with zero exceptions. Fix the broken multi-file pattern.

**Deliverables:**
- [x] Audit and consolidate ALL environment variables across services
- [x] Create master .env.example with every variable needed
- [x] Rewrite env_loader.py to enforce single source (no fallbacks)
- [x] Create distribute_env.py script for automatic distribution
- [x] Update all services to use centralized pattern
- [x] Remove ALL bypass paths (load_dotenv, direct access)
- [x] Update Makefile and documentation

**Achieved:**
- Developers now manage exactly ONE .env file
- Automatic distribution to services via `make dev`
- No service can bypass the centralized pattern
- Startup validation catches missing resources early
- Git hooks prevent accidental service .env commits

📄 **[Implementation Complete →](docs/phase-4.0-env-centralization.md)**

### Phase 4.1: UI Actions Pattern ✅ COMPLETE
**Deliverables:**
- [x] Parser implementation to extract {{oauth:shopify}} markers
- [x] Workflow configuration to enable UI components
- [x] Message processor integration to parse UI elements
- [x] Platform layer passes ui_elements through WebSocket
- [x] Frontend UI element rendering with pattern matching fallback
- [ ] End-to-end testing of complete flow

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-4-ui-actions.md)**

### Phase 4.5: User Identity & Persistence (SIMPLIFIED) ✅ COMPLETE
**Goal:** Add minimal user identity for persistent "your store" insights across sessions.

**Revised Architecture (Much Simpler):**
- User IDs generated from shop domains (usr_xxx format)
- Direct Supabase writes - no Redis archival complexity
- Conversations saved directly as they happen
- Simple 3-table schema in Supabase (users, conversations, user_facts)

**What We're Actually Building:**
```python
# Core identity functions - ~100 lines
generate_user_id(shop_domain) → "usr_12345678"
get_or_create_user(shop_domain, email) → (user_id, is_new)
save_conversation_message(user_id, message) → None
get_user_conversations(user_id) → List[messages]

# Fact storage functions - ~40 lines (planned)
append_fact(user_id, fact, source) → None
get_user_facts(user_id) → List[facts]
```

**The Simplified Flow:**
```
Shopify OAuth → Generate User ID → Save Messages Directly
      ↓              ↓                    ↓
  Shop Domain    usr_xxx ID           Supabase
```

**Minimal Schema:**
```sql
-- 1. Users (from OAuth)
CREATE TABLE users (
    id VARCHAR(50) PRIMARY KEY,
    shop_domain VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Conversations (direct writes)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(50) REFERENCES users(id),
    message JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. User Facts (single JSONB document)
CREATE TABLE user_facts (
    user_id VARCHAR(50) PRIMARY KEY REFERENCES users(id),
    facts JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Just 2 indexes
CREATE INDEX idx_users_shop ON users(shop_domain);
CREATE INDEX idx_conv_user ON conversations(user_id);
```

**Fact Storage Design:**
- Single JSONB array per user containing all facts
- Append new facts with: `facts = facts || jsonb_build_array($new_fact)`
- Facts stored as: `{"fact": "...", "source": "conv_123", "learned_at": "2024-..."}`
- One row per user, updated atomically
- ~40 lines for `append_fact()` and `get_facts()` functions

**Benefits of Simplified Approach:**
- ✅ **No Redis Complexity**: Direct DB writes, no archival needed
- ✅ **No Over-Engineering**: Just store messages as they come
- ✅ **Dead Simple**: Can be understood in 5 minutes
- ✅ **Still Enables Phase 5**: "Your store had 5 orders yesterday..."

**Implementation Status:**
- [x] Built over-engineered library (1,072 lines) ❌
- [x] Created simplified version (109 lines) ✅
- [x] Replace complex library with simple version ✅
- [x] Remove Redis archival assumptions ✅
- [x] Integrate direct PostgreSQL writes ✅
- [x] Add fact storage functions (50 lines)
- [x] Remove old file-based merchant memory system
  - [x] Delete merchant_memory.py service
  - [x] Remove dedicated test files
  - [x] Update user_identity tests
### Minimum Viable Integration ✅ COMPLETE
- [x] **Database Setup** (30 min) ✅
  - [x] Test connection with scripts/test_user_identity.py
  - [x] Run migration via create_identity_tables.py
  - [x] Verify tables created and basic CRUD works
  - [x] Created stub merchant_memory.py to avoid breaking imports
  
- [x] **Auth Service Integration** (1 hour) ✅
  - [x] Import user_identity in shopify_oauth.py
  - [x] Add get_or_create_user() call after token exchange
  - [x] NO NEED to pass user_id in redirect (backend generates it)
  
- [x] **Minimal Agents Integration** (2 hours) ✅
  - [x] Add user_id field to Session class
  - [x] Generate user_id from shop_domain in WebSocket
  - [x] Update message_processor to save conversations
  - [x] Update oauth_complete handler to generate user_id
  - [x] Skip fact migration for MVP

### Full Integration (Later)
- [ ] Update agents service completely
  - [ ] Remove all MerchantMemory imports (5 files)
  - [ ] Update session_manager to use user_identity facts
  - [ ] Update fact_extractor to use append_fact
  - [ ] Clean up data/merchant_memory directory
- [ ] Frontend updates
  - [ ] Accept user_id from OAuth redirect
  - [ ] Include user_id when creating WebSocket session
- [ ] Full testing
  - [ ] Test fact persistence across sessions
  - [ ] Verify old file-based system removed

📄 **[Updated Simple Implementation Guide →](docs/shopify-onboarding/phase-4.5-user-identity-simple.md)**

## 📊 Phase 4.5 Implementation Audit - FINAL

### Final Implementation Grade: A+

**From D to A+**: We successfully identified and fixed the over-engineering problem, then elegantly added fact storage without complexity.

After deep analysis, we discovered:
1. **The agents service doesn't use Redis for conversations** - uses in-memory + file storage
2. **The archival system solves a non-existent problem** - no Redis TTL to worry about
3. **We built 1,072 lines when ~100 would suffice** - 10x overengineering

### What We Built vs What Was Needed

| What We Built | What Was Actually Needed |
|--------------|-------------------------|
| Complex Redis archival service (349 lines) | Nothing - Redis isn't used |
| SQLAlchemy ORM with 3 models | Simple SQL with 2 tables |
| Event tracking system | Not needed for POC |
| Background archival loops | Direct writes on message |
| 11 database indexes | 2 indexes |
| Error handling, retries, transactions | Let it fail in POC |
| **Total: 1,072 lines** | **Total: ~100 lines** |

### The Root Cause

The complexity cascade:
1. **Assumed Redis usage** (wrong assumption)
2. **Built archival for Redis TTL** (solving non-problem)
3. **"Shared library" triggered production mindset** (overbuilding)
4. **SQLAlchemy brought complexity tax** (ORM overhead)

### The Elegant Solution

Direct PostgreSQL writes with minimal fact storage:
```python
# Identity & conversations
generate_user_id(shop_domain) → "usr_12345678"
save_conversation_message(user_id, message)

# Facts (replacing file-based system)
append_fact(user_id, fact, source)  # Atomic JSONB append
get_user_facts(user_id) → [facts]   # Simple list return
```

**Final Implementation:**
- 6 functions, 190 lines total (with logging)
- 3 simple tables (users, conversations, user_facts)
- Facts stored as JSONB array per user
- No background services, no Redis, no complexity
- Thoughtful logging added (8 strategic log points)

### North Star Violations

- ❌ **Simplify**: Added massive unnecessary complexity
- ❌ **No Over-Engineering**: Built for hypothetical scale
- ❌ **No Cruft**: 90% of code is cruft
- ❌ **Current Needs Only**: Built for production during discovery

### Lesson Learned

**Always verify assumptions before building.** We built an elaborate archival system for Redis data that doesn't exist. Classic case of solving the wrong problem elegantly.

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

### Phase 4.6: System Events Architecture 🎯 CURRENT PRIORITY
**Goal:** Enable CJ to naturally respond to system events like OAuth completion by adding explicit instructions to workflow YAML files.

**Problem:** Currently when OAuth completes, CJ receives a vague system message "New Shopify merchant authenticated from {shop}" with instructions to "respond appropriately" - but has no specific guidance on HOW to respond, resulting in silence.

**Solution:** Add system event handling instructions directly to the workflow YAML that CJ already sees. No hidden prompt mutations, no complex code - just clear instructions.

**Implementation Pattern:**
```yaml
# In shopify_onboarding.yaml workflow
SYSTEM EVENT HANDLING:
When you receive a message from sender "system", handle these patterns:

For "New Shopify merchant authenticated from [store]":
- Respond: "Perfect! I've successfully connected to your store at [store]."
- Then: "Give me just a moment to look around and get familiar with your setup..."

For "Returning Shopify merchant authenticated from [store]":
- Respond: "Welcome back! I've reconnected to [store]."
- Then: "Let me quickly refresh my memory about your store..."
```

**Deliverables:**

**1. Workflow YAML Update** *(30 minutes)*
- [ ] Add SYSTEM EVENT HANDLING section to shopify_onboarding.yaml
- [ ] Define responses for oauth_complete (new vs returning)
- [ ] Add instructions for future events (data loading, errors)
- [ ] Test that CJ follows the instructions

**Benefits:**
- ✅ **Transparent**: All behavior visible in workflow YAML
- ✅ **Simple**: Zero code changes required
- ✅ **Debuggable**: Read YAML = understand behavior
- ✅ **Extensible**: Add new events by editing YAML
- ✅ **Natural**: CJ already knows how to follow instructions

**Critical Design Principle:** No runtime prompt mutations. Everything CJ sees must be visible in:
1. Base prompt file (e.g., `v6.0.1.yaml`)
2. Workflow file (e.g., `shopify_onboarding.yaml`)

**Timeline: 30 minutes** (YAML editing only)

📄 **[Detailed Implementation Guide →](docs/shopify-onboarding/phase-4.6-system-events.md)**

### Phase 5: Quick Value Demo
**Goal:** Show immediate value after Shopify connection by providing quick insights about their store WITHOUT requiring full data dumps or complex ETL.

**Core Strategy: Progressive Data Disclosure**
Instead of syncing all data, we fetch exactly what we need for the conversation using a three-tier approach:

#### Tier 1: Instant Metrics (< 500ms)
```python
# Uses existing REST count endpoints - no pagination needed
{
    "customers": api.get_customer_count(),           # e.g., 1,234
    "total_orders": api.get_order_count(),          # e.g., 5,678  
    "active_orders": api.get_order_count("open")    # e.g., 12
}
```

#### Tier 2: Quick Insights (< 2s) 
```python
# Single GraphQL query for rich data
query = """
{
  shop { name, currencyCode }
  orders(first: 10, reverse: true) {
    edges { node {
      createdAt
      totalPriceSet { shopMoney { amount } }
      lineItems(first: 5) { edges { node { title, quantity } } }
    }}
  }
  products(first: 5, sortKey: INVENTORY_TOTAL, reverse: true) {
    edges { node { title, totalInventory, priceRangeV2 {...} } }
  }
}
"""
```

#### Tier 3: Deeper Analysis (< 5s)
```python
# Targeted REST queries with strict limits
last_week_orders = api.get_orders(
    updated_at_min=(datetime.now() - timedelta(days=7)).isoformat(),
    limit=50  # Small, manageable dataset
)
```

**Deliverables:**

**1. GraphQL Client Extension** *(2 hours)*
- [ ] Add `ShopifyGraphQL` class to `shopify_util.py`
- [ ] Implement `get_store_pulse()` query method
- [ ] Add proper error handling and rate limiting

**2. Quick Insights Service** *(4 hours)*
- [ ] Create `app/services/quick_insights.py`
- [ ] Implement three-tier data fetching:
  - [ ] `tier_1_snapshot()` - REST count endpoints
  - [ ] `tier_2_insights()` - GraphQL store pulse
  - [ ] `tier_3_analysis()` - Limited REST queries
- [ ] Add 15-minute Redis caching for demo phase

**3. Natural Language Generator** *(3 hours)*
- [ ] Create `generate_quick_insights()` function
- [ ] Transform data into conversational insights:
  ```python
  # Input: {"recent_revenue": 1234.56, "order_velocity": 3.2}
  # Output: ["You've made $1,234.56 in the last 10 orders",
  #          "Your store is averaging 3.2 orders per day"]
  ```
- [ ] Handle edge cases (new stores, no recent orders)

**4. CJ Agent Integration** *(3 hours)*
- [ ] Update `handle_oauth_complete()` in CJ agent
- [ ] Implement progressive disclosure flow:
  ```python
  # 1. Instant gratification
  yield "Great! I can see you have 1,234 customers in your store."
  
  # 2. Show we're analyzing
  yield "Let me take a quick look at your recent activity..."
  
  # 3. Deliver insights naturally
  for insight in insights:
      yield insight
      await asyncio.sleep(0.5)  # Natural pacing
  
  # 4. Transition to next phase
  yield "I'm already seeing some patterns. Would you like me to connect..."
  ```

**5. Error Handling & Edge Cases** *(2 hours)*
- [ ] Handle stores with no data gracefully
- [ ] Manage API rate limits
- [ ] Fallback messages for API failures
- [ ] Test with various store sizes

**The Enhanced Experience:**
```
After OAuth:
├── [0-500ms] "Great! I can see you have 1,234 customers"
├── [500ms-2s] "Let me look at your recent activity..."
├── [2-3s] "You've made $12,456 in the last 10 orders"
├── [3-4s] "Your store is averaging 5.2 orders per day"  
├── [4-5s] "'Blue Widget' is your best stocked product"
├── [5-6s] "I'm seeing some interesting patterns..."
└── [6s+] "Would you like me to connect your support system?"
```

**Success Metrics:**
- Time to first insight: < 500ms
- Total onboarding time: < 30 seconds
- Zero full data dumps during demo
- API calls per session: < 5
- Cache hit rate: > 80% during demos

**Why This Approach:**
- ✅ **No ETL Complexity**: Direct API calls, no sync infrastructure
- ✅ **Instant Value**: First response in under 500ms
- ✅ **Conversation-Driven**: Data follows dialogue naturally
- ✅ **Efficient**: Never fetch more than needed
- ✅ **Demo-Optimized**: 15-min cache perfect for onboarding

**Timeline: 14 hours total** (2 days)
- Day 1: GraphQL client, Quick Insights service
- Day 2: Natural language, CJ integration, testing

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