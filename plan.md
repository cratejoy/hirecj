# HireCJ Development Plan

## 📊 Current Status

### ✅ Completed Phases

1. **Phase 1: Foundation** ✅
   - Onboarding workflow, CJ agent, OAuth button component
   - [📄 Detailed Documentation](docs/shopify-onboarding/phase-1-foundation.md)

2. **Phase 2: Auth Flow Integration** ✅
   - OAuth callbacks, shop domain identifier, context updates
   - [📄 Detailed Documentation](docs/shopify-onboarding/phase-2-auth-flow.md)

3. **Phase 3.7: OAuth 2.0 Implementation** ✅
   - Full OAuth flow with HMAC verification, token storage
   - [📄 Detailed Documentation](docs/shopify-onboarding/phase-3.7-oauth-implementation.md)
   - See also: [Phase 3 OAuth Production](docs/shopify-onboarding/phase-3-oauth-production.md), [Phase 3 Testing](docs/shopify-onboarding/phase-3-testing.md)

4. **Phase 4.0: True Environment Centralization** ✅
   - Single .env pattern with automatic distribution
   - [📄 Detailed Documentation](docs/phase-4.0-env-centralization.md)

5. **Phase 4.1: UI Actions Pattern** ✅
   - Parser, workflow config, WebSocket integration
   - [📄 Detailed Documentation](docs/shopify-onboarding/phase-4-ui-actions.md)

6. **Phase 4.5: User Identity & Persistence** ✅
   - PostgreSQL user identity, fact storage, session management
   - [📄 Detailed Documentation](docs/shopify-onboarding/phase-4.5-user-identity.md)

7. **Phase 4.6: System Events Architecture** ✅
   - YAML-based system event handling for OAuth responses
   - [📄 Detailed Documentation](docs/shopify-onboarding/phase-4.6-system-events.md)

8. **Phase 4.6.5: Workflow-Driven Requirements** ✅
   - All workflow requirements moved to YAML files
   - All workflow behavior moved to YAML files (Phase 2.5)
   - Zero hardcoded workflow logic remaining
   - Backend serves requirements to frontend
   - Enhanced debug interface for troubleshooting

9. **Phase 4.7: Backend-Authoritative User Identity** ✅
   - Verified backend is sole authority for user ID generation
   - Frontend never generates user IDs (only conversation/message IDs)
   - All services use shared.user_identity module
   - User IDs follow consistent format: usr_xxxxxxxx
   - No changes needed - system already correctly implemented

10. **Phase 5.1: Shopify API Infrastructure** ✅
    - Extended Shopify API client with GraphQL support
    - Implemented authentication and error handling
    - Tested with real Shopify store (cratejoy-dev)

11. **Phase 5.2: Data Service Layer** ✅
    - Created ShopifyDataFetcher service (simplified from original QuickShopifyInsights)
    - Implemented pure data fetching methods (no analysis)
    - Added Redis caching with TTL
    - **Important**: Simplified away the tier1/tier2/tier3 system as unnecessary complexity
    - All analysis/insights generation moved to CJ agent

12. **Phase 5.3: Atomic Shopify Tools** ✅
    - Created 4 atomic tools in `agents/app/agents/shopify_tools.py`:
      - `get_shopify_store_counts` - Basic store metrics
      - `get_shopify_store_overview` - GraphQL-powered overview
      - `get_shopify_recent_orders` - Recent order data
      - `get_shopify_orders_last_week` - Weekly order analysis
    - Tools dynamically loaded when OAuth metadata indicates Shopify connection
    - All tools return raw JSON for agent analysis (no pre-processing)

13. **Phase 5.3.5: PostgreSQL-Only Token Storage** ✅
    - Created `store_test_shopify_token.py` script for testing token storage
    - Implemented `MerchantService` for PostgreSQL-only token retrieval in agents
    - Tokens stored in `merchant_integrations` table
    - No Redis dependency for token storage in agents service

14. **Phase 5.4: Auth Service Migration** ✅
    - Updated `auth` service to store tokens in PostgreSQL via `merchant_storage`
    - Tokens now stored in `merchant_integrations` table (single source of truth)
    - **IMPORTANT**: Redis still used for OAuth state management (ephemeral data)
    - This hybrid approach is intentional: persistent tokens in PostgreSQL, temporary OAuth state in Redis

15. **Phase 5.5: Workflow Integration** ✅
    - Integrated Shopify tools into `shopify_onboarding` workflow
    - Updated workflow YAML to leverage Shopify data
    - Prevented premature workflow transitions during OAuth
    - Fixed UI to prevent page reloads during Shopify connection

### ⏳ In Progress

**Phase 5.5.6: OAuth Flow Alignment** (12 hours) 🚨 CRITICAL
- Fix conversation continuity during OAuth redirect
- Implement proper system event generation
- Align WebSocket implementation with workflow spec
- Ensure OAuth completion triggers expected system messages
- [📄 Documentation](docs/oauth-flow-fix/README.md)

### 📅 Upcoming Phases

1. **Phase 5: Quick Value Demo** (Total: 25.5 hours)
   - **Phase 5.1**: API Infrastructure ✅ COMPLETED
   - **Phase 5.2**: Data Service Layer ✅ COMPLETED
   - **Phase 5.3**: Atomic Shopify Tools ✅ COMPLETED
   - **Phase 5.3.5**: PostgreSQL-Only Token Storage ✅ COMPLETED
   - **Phase 5.4**: Auth Service Migration ✅ COMPLETED
   - **Phase 5.5**: Workflow Integration ✅ COMPLETED
   - **Phase 5.5.5**: Post-OAuth Workflow ✅ COMPLETED
   - **Phase 5.5.6**: OAuth Flow Alignment (12 hours) 🚨 IN PROGRESS
   - **Phase 5.6**: Agent Registration (1 hour)
   - **Phase 5.7**: Testing & Validation (3 hours)
   - [📄 Detailed Documentation](docs/shopify-onboarding/phase-5-quick-value.md)


---

## 🚨 Critical Issue: OAuth Flow Misalignment

### Discovery (Phase 5.5.6)

During testing of the OAuth flow, we discovered a fundamental architectural issue:

**The Problem:**
1. OAuth redirect loses conversation context (new WebSocket connection)
2. Implementation uses WebSocket messages but workflow expects system events
3. Conversation ID isn't preserved through the OAuth flow
4. Debug code in `oauth_complete` handler never fires due to context mismatch

**The Impact:**
- OAuth completion doesn't trigger expected workflow responses
- Users get stuck after connecting Shopify
- System can't provide immediate value with insights

**The Solution:**
Phase 5.5.6 implements a comprehensive fix that:
- Preserves conversation state through OAuth redirect
- Converts WebSocket messages to proper system events
- Aligns implementation with workflow specification
- Ensures seamless user experience

This is a **CRITICAL** fix that blocks all OAuth-dependent functionality.

---

## 🏗️ Phase 5.2 Review: Implementation vs Plan

### What Changed During Implementation

The original plan called for a complex three-tier progressive loading system with QuickShopifyInsights service. During implementation, we correctly identified this as unnecessary complexity and simplified:

**Original Plan:**
- QuickShopifyInsights service with tier1/tier2/tier3 methods
- Progressive loading with timing controls
- Analysis and insights generation in the service

**What We Built:**
- ShopifyDataFetcher service with simple data methods
- Pure data fetching - no analysis
- All intelligence moved to CJ agent

### North Star Principles Adherence

✅ **BETTER than plan** - The implementation follows North Star principles more closely:

1. **Simplify**: Removed unnecessary tier abstraction
2. **No Cruft**: Direct data methods instead of complex tiers  
3. **No Over-Engineering**: Built for actual needs, not hypothetical progressive loading
4. **Backend-Driven**: Agent handles all intelligence
5. **Single Source of Truth**: One clear way to fetch data

### Next Steps

1. Update Phase 5 documentation to reflect simplified architecture ✅ DONE
2. Continue with Phase 5.3: Create shopify_data tool for CJ
3. Ensure tool follows same simple pattern as data fetcher

---

## 🔍 Phase 5 Implementation Summary

### What We Built vs Original Plan

**Original Vision:**
- Complex QuickShopifyInsights service with tier1/tier2/tier3 progressive loading
- Analysis and insights generation in the service layer
- Complete removal of Redis from the system

**What We Actually Built (Better!):**
- Simple ShopifyDataFetcher with direct data methods
- 4 atomic Shopify tools that return raw JSON
- All intelligence in the CJ agent (where it belongs)
- Hybrid storage: tokens in PostgreSQL, OAuth state in Redis

### Current Architecture

**Token Storage:**
- Tokens stored in PostgreSQL `merchant_integrations` table
- Both auth and agents services use PostgreSQL for tokens
- Single source of truth achieved ✅

**OAuth Flow:**
- Redis still used for ephemeral OAuth state (nonces, etc.)
- This is intentional and correct - OAuth state is temporary
- Clean separation: persistent data in PostgreSQL, ephemeral in Redis

**Tools:**
- Shopify tools dynamically loaded when OAuth metadata present
- Tools follow existing patterns (return simple JSON)
- No async/sync mixing or other anti-patterns

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

---

## 🚨 What We're NOT Building

- **No** complex state management libraries
- **No** over-abstraction of simple concepts
- **No** backwards compatibility with old hardcoded system
- **No** frontend-specific workflow knowledge
- **No** special cases or exceptions

Focus: Backend-driven, YAML-configured, simple and elegant solutions.
