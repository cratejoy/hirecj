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
    - Refactored `get_shopify_data` into atomic tools (`get_shopify_store_counts`, etc.)
    - Created `agents/app/agents/shopify_tools.py` to house new tools
    - Updated `ShopifyDataFetcher` to use synchronous methods
    - Aligned documentation with new, simplified tool structure

13. **Phase 5.3.5: PostgreSQL-Only Token Storage** ✅
    - Created `store_test_shopify_token.py` script to seed tokens
    - Implemented `MerchantService` for PostgreSQL-only token retrieval
    - Removed Redis dependency for tokens in the `agents` service

### ⏳ In Progress

### 📅 Upcoming Phases

1. **Phase 5: Quick Value Demo** (Total: 11.5 hours)
   - **Phase 5.1**: API Infrastructure ✅ COMPLETED
   - **Phase 5.2**: Data Service Layer ✅ COMPLETED
   - **Phase 5.3**: Atomic Shopify Tools ✅ COMPLETED
   - **Phase 5.3.5**: PostgreSQL-Only Token Storage ✅ COMPLETED
   - **Phase 5.4**: Auth Service Migration (2 hours) - Reduced scope
   - **Phase 5.5**: Workflow Integration (2 hours)
   - **Phase 5.6**: Agent Registration (1 hour)
   - **Phase 5.7**: Testing & Validation (3 hours)
   - [📄 Detailed Documentation](docs/shopify-onboarding/phase-5-quick-value.md)

2. **Phase 5.4: Auth Service Migration** (2 hours) - **SIMPLIFIED**
   - Update auth service to store tokens in PostgreSQL during OAuth
   - Migrate any critical production tokens from Redis
   - Remove ALL Redis token storage code
   - **Why**: Complete migration to single source of truth
   - **Note**: Existing Redis tokens will stop working - requires re-auth

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

## 🔍 Architecture Discovery: Token Storage

### Important Finding
During Phase 5.2 implementation, we discovered that Shopify access tokens are stored in **Redis**, not PostgreSQL:

**Actual Architecture:**
- Auth service stores tokens in Redis during OAuth completion
- Key format: `merchant:{shop_domain}`
- TTL: 24 hours
- PostgreSQL merchants table only has: id, name, is_test, created_at, updated_at
- No `shopify_access_token` column exists in PostgreSQL

**Solution: Phase 5.3.5 (PostgreSQL-Only)**
- Can't easily test with Redis-only tokens
- PostgreSQL `merchant_integrations` table already exists with perfect schema
- Phase 5.3.5 uses PostgreSQL exclusively - no Redis fallback
- Clean break: existing Redis tokens won't work until migrated
- **This is the right approach**: No compatibility shims, just move forward

**Phase 5.4 Completes Migration**
- Auth service starts storing all new tokens in PostgreSQL
- One-time migration for critical production tokens
- Remove ALL Redis token code
- Single source of truth achieved

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
