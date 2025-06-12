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

16. **Phase 6.5: Pre-warmed Session WebSocket Integration** ✅
    - WebSocket `handle_start_conversation` now detects cached sessions from SessionInitiator
    - First CJ message is delivered instantly after OAuth hand-off

17. **Phase 6.55: Seamless Shopify Redirect** ✅
    - `/shopify/install` now supports `mode=json`, returning the final Shopify OAuth URL
    - Frontend fetches this URL, displays a spinner, and navigates directly to Shopify
    - Removes visible intermediate hop and prevents double-submission

18. **Phase 6.6: Final Testing & Cleanup** ⏳

### ⏳ In Progress

**Phase 5.5.5: Fix Page Refresh on Shopify Domain Entry**
- **Issue**: When entering a Shopify domain in the OAuth button and pressing Enter, the page refreshes
- **Root Cause**: Main chat input's `handleKeyDown` in SlackChat.tsx missing `e.preventDefault()`
- **Fix**: Add `e.preventDefault()` to line 520 in SlackChat.tsx
- **Status**: Issue identified, awaiting fix

### ✅ Recently Completed

**Phase 6.1: OAuth Flow Fix & Two-Layer Session Pattern** ✅
- **Completed**: 2025-06-11
- **Summary**: Successfully implemented two-layer session pattern and fixed OAuth flow
- **Key Changes**:
  - HTTP sessions for user identity (PostgreSQL-backed with web_sessions table)
  - WebSocket sessions for conversation state only
  - Removed all session_update message handling
  - Renamed SessionInitiator → PostOAuthHandler for clarity
  - Fixed OAuth workflow transition (shopify_onboarding → shopify_post_auth)
  - Set cookie domain to .hirecj.ai for cross-subdomain access
- **Documentation**: 
  - [Phase 1 Summary](docs/oauth-flow-fix/phase-1-completed.md)
  - [Testing Guide](docs/oauth-flow-fix/phase-2-testing-guide.md)

**Phase 6.2: WebSocket Proxy Architecture** ✅
- **Completed**: 2025-06-11
- **Summary**: Implemented single-domain proxy to solve cross-domain cookie issue
- **Key Changes**:
  - Added WebSocket proxy to homepage Express server
  - Routes `/ws/*` requests through `amir.hirecj.ai` to agents service
  - Frontend uses same-origin WebSocket connections
  - Cookies work automatically - no cross-domain issues
- **Benefits**:
  - Single domain for all connections
  - No workarounds or hacks needed
  - Standard production architecture
- **Documentation**: [Proxy Architecture](docs/oauth-flow-fix/phase-3-proxy-architecture.md)

### 🛠️ Current Issue Fix

**OAuth Tables Missing**: The `oauth_csrf_state` table was introduced in commit 526c604 when Redis was replaced with database storage, but no SQL migration was created.
- **Fix**: Created migration 007_create_oauth_tables.sql to add both `oauth_csrf_state` and `oauth_completion_state` tables
- **Status**: Migration file created, needs to be run

### 📅 Upcoming Phases

1.  **Phase 6: Server-Side OAuth Handoff (Implementation)**
    *   **Phase 6.0**: Refactor Workflow YAMLs for New Architecture.
    *   **Phase 6.1**: Create Internal API Endpoint in Agent Service.
    *   **Phase 6.2**: Implement `SessionInitiator` Service.
    *   **Phase 6.3**: Update Auth Service to Call Internal Endpoint.
    *   **Phase 6.4**: Deprecate & Remove Old DB Handoff Flow.
    *   **Phase 6.5**: Update WebSocket Handler for Pre-warmed Sessions.
    *   **Phase 6.6**: Final Testing & Documentation Cleanup.

2.  **Phase 7: Demo & Refinement**
    *   End-to-end testing of the full Shopify onboarding and data retrieval flow.
    *   Refine agent prompts and tools based on live data.
    *   Prepare for the next major feature development cycle.

---

## New Architecture: Server-to-Server OAuth Handoff

### The Problem
The previous OAuth completion flow was overly complex and unreliable. It depended on the user's browser to bridge communication between the Auth Service and the Agent Service using a database "dead drop" table (`oauth_completion_state`). This introduced potential race conditions and points of failure.

### The Solution: Direct Server-to-Server Handoff
We will implement a simpler, more robust server-to-server architecture. When the Auth Service successfully exchanges the Shopify code for an access token, it will make a direct, internal API call to the Agent Service. This call will instruct the Agent Service to pre-prepare the user's session and CJ's initial welcome message.

The key benefits are:
- **Reliability**: The critical state transfer is a single, synchronous server-to-server call. It either succeeds or fails cleanly.
- **Simplicity**: The complex database polling and state-checking logic is removed.
- **Performance**: The user's perceived performance is better because by the time their browser loads the chat page, the session is fully initialized and CJ's first message is waiting for them.

### New Control Flow Diagram
```text
+---------------------------+       +------------------+      +------------------+      +------------------+
|    User Browser/Frontend  |       |   Auth Service   |      |     Database     |      |   Agent Service  |
+---------------------------+       +------------------+      +------------------+      +------------------+
              |                             |                       |                       |
              |   <-- 1. Redirect with `code` & `state` from Shopify
              |                             |                       |                       |
              |--- 2. GET /api/v1/shopify/callback -->
              |                             |                       |                       |
              |                  [auth/app/api/shopify_oauth.py]
              |                             |                       |                       |
              |             (Verifies state, exchanges code for token, stores in DB)
              |                             |                       |                       |
              |                             |--- 3. Internal API Call [INITIATE] ---------->|
              |                             |    (POST /internal/v1/session/initiate)       |
              |                             |    Payload: { shop_domain, is_new, conv_id }  |
              |                             |                       |                       |
              |                             |                       |  [agents/app/main.py - New Endpoint]
              |                             |                       |                       |
              |                             |                       |  - Creates Session
              |                             |                       |  - Sets workflow to 'shopify_post_auth'
              |                             |                       |  - Generates CJ's first message
              |                             |                       |  - Caches session & message by conv_id
              |                             |                       |                       |
              |                             |<-- 4. Receives HTTP 200 OK ------------------|
              |                             |                       |                       |
              |<-- 5. Redirect to /chat?conversation_id=...
              |      (User is redirected AFTER server-side work is complete)
              |                             |                       |                       |
              |--- 6. Open WebSocket to /ws/chat/{id} ------------------------------------->|
              |                             |                       |                       |
              |                                        [agents/app/platforms/web/websocket_handler.py]
              |                             |                       |                       |
              |--- 7. Send 'start_conversation' message ---------------------------------->|
              |                             |                       |                       |
              |                                         [agents/app/platforms/web/session_handlers.py]
              |                             |                       |                       |
              |                             |                       |  - Finds cached session for {id}
              |                             |                       |  - Loads the pre-generated state
              |                             |                       |                       |
              |<-- 8. IMMEDIATELY Send pre-generated CJ message ---------------------------|
              |                             |                       |                       |
```

## Implementation Plan: Phase 6

This plan breaks down the architectural change into small, manageable, and testable steps.

### Phase 6.0: Refactor Workflow YAMLs

-   **Goal**: Align workflow configurations with the new server-to-server OAuth handoff architecture.
-   **Tasks**:
    1.  **Simplify `shopify_onboarding.yaml`**: Remove the `SYSTEM EVENT HANDLING` block. This logic is now obsolete, as the `SessionInitiator` will create a new session with the `shopify_post_auth` workflow. This change makes the onboarding workflow's single purpose clear: guiding a user to authentication.
    2.  **Verify `shopify_post_auth.yaml`**: Confirm that its `system`-initiated behavior is perfectly aligned with the new architecture, where it will be triggered by the `SessionInitiator`. No changes are needed for this file.

### Implementation Checklist

- [x] **Phase 6.0**: Refactor Workflow YAMLs.
    - [x] Simplify `shopify_onboarding.yaml` by removing legacy system event handling.
    - [x] Confirm `shopify_post_auth.yaml` is correctly designed for the new architecture.
- [x] **Phase 6.1**: Create Internal API Endpoint in Agent Service.
    - [x] Create internal API request models in `shared/models/api.py`.
    - [x] Create internal router and endpoint in `agents/app/api/routes/internal.py`.
    - [x] Register internal router in `agents/app/main.py`.
- [x] **Phase 6.2**: Implement a `SessionInitiator` service to handle the session pre-preparation logic.
    - [x] Create `SessionInitiator` service in `agents/app/services/session_initiator.py`.
    - [x] Implement session creation and message pre-generation logic.
    - [x] Update internal API endpoint to use the new service.
- [x] **Phase 6.3**: Update the Auth Service to call the new internal endpoint.
    - [x] Remove database handoff logic from `auth/app/api/shopify_oauth.py`.
    - [x] Add `httpx` call to Agent Service's `/internal/session/initiate` endpoint.
    - [x] Added error handling to gracefully degrade if the handoff fails.
- [x] **Phase 6.4**: Deprecate & Remove Old DB Handoff Flow.
- [x] **Phase 6.5**: Update the WebSocket handler for pre-warmed sessions. **(Completed)**
- [ ] **Phase 6.6**: Final Testing & Cleanup. **(Only this phase remains outstanding)**

### Phase 6.1: Create Internal API Endpoint

-   **Goal**: Create a new, non-public API endpoint in the Agent Service for the Auth Service to call.
-   **Tasks**:
    1.  [x] Create a new router file: `agents/app/api/routes/internal.py`.
    2.  [x] Define a Pydantic model for the request body: `OAuthHandoffRequest` in `shared/models/api.py`.
    3.  [x] Add a `POST /api/v1/internal/session/initiate` endpoint.
    4.  [x] For now, the endpoint will only log the received data and return a `200 OK` response.
    5.  [x] Include the new router in `agents/app/main.py`.

### Phase 6.2: Implement `SessionInitiator` Service

-   **Goal**: Isolate the session pre-preparation logic into a dedicated service.
-   **Tasks**:
    1.  [x] Create a new service file: `agents/app/services/session_initiator.py`.
    2.  [x] Create a `SessionInitiator` class.
    3.  [x] Implement a method `prepare_oauth_session(request: OAuthHandoffRequest)`.
    4.  [x] This method will:
        -   Call `SessionManager` to create a new session with the correct workflow (`shopify_post_auth`).
        -   Call `MessageProcessor` to generate CJ's first message.
        -   Store the session object and the first message in a simple in-memory dictionary, keyed by `conversation_id`.
    5.  [x] Update the internal API endpoint from Phase 6.1 to use this new service.

### Phase 6.3: Update Auth Service to Call New Endpoint

-   **Goal**: Modify the Auth Service to use the new server-to-server handoff mechanism.
-   **Tasks**:
    1.  [x] In `auth/app/api/shopify_oauth.py`, inside the `handle_oauth_callback` function.
    2.  [x] Remove the code that writes to the `OAuthCompletionState` table.
    3.  [x] Add an `httpx` API call to `POST {AGENTS_SERVICE_URL}/api/v1/internal/session/initiate`.
    4.  [x] The Auth service now waits for a successful `200 OK` from the Agent service before proceeding.
    5.  [x] If the call fails, it logs a critical error but still redirects the user to the frontend, allowing the flow to gracefully degrade.

### Phase 6.4: Deprecate & Remove Old DB Handoff Flow

-   **Goal**: Clean up all code related to the old, unreliable database handoff mechanism.
-   **Tasks**:
    1.  [x] In `agents/app/platforms/web/oauth_handler.py`, deprecated the `OAuthHandler` class and removed all logic.
    2.  [x] In `agents/app/platforms/web/session_handlers.py`, removed all calls to the `oauth_handler`.
    3.  [x] In `shared/db_models.py`, deleted the `OAuthCompletionState` model definition.
    4.  [x] **Manual Action Required**: A database migration must be created and applied to run: `DROP TABLE oauth_completion_state;`

### Phase 6.5: Update WebSocket Handler for Pre-warmed Sessions

-   **Goal**: Adapt the WebSocket connection logic to use the pre-warmed sessions.
-   **Tasks**:
    1.  [x] In `agents/app/platforms/web/session_handlers.py`, inside `handle_start_conversation`, added logic to check the `SessionInitiator` cache for a pre-warmed session.
    2.  [x] If a session is found, it is loaded, the pre-generated message sent, and the normal session creation flow is bypassed.
    3.  [x] If no pre-warmed session is found, the handler proceeds with the normal, non-authenticated flow.

### Phase 6.6: Final Testing & Cleanup

-   **Goal**: Ensure the new end-to-end flow is working correctly and clean up documentation.
-   **Tasks**:
    1.  Manually test the full Shopify OAuth flow.
    2.  Verify that CJ's welcome message appears instantly after the redirect.
    3.  Review logs in both Auth and Agent services to confirm the internal API call is working.
    4.  Update this `plan.md` to mark Phase 6 as complete.

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

---

## 🚨 Hotfix: Missing OAuth Database Tables (2025-01-11)

### Issue
After the Phase 5.2 refactor (commit 526c604), we moved OAuth state management from Redis to PostgreSQL but forgot to create the corresponding database migration. This causes the error:
```
relation "oauth_csrf_state" does not exist
```

### Root Cause
- Commit 526c604 added SQLAlchemy models for `OAuthCSRFState` and `OAuthCompletionState` in `shared/db_models.py`
- No corresponding SQL migration was created to add these tables to the database

### Fix
- [x] Created migration file: `agents/app/migrations/007_create_oauth_tables.sql`
- [x] Run migration: `cd agents && python scripts/run_migration.py app/migrations/007_create_oauth_tables.sql`

### Migration Contents
Creates two tables:
1. `oauth_csrf_state` - For CSRF protection during OAuth flow
2. `oauth_completion_state` - For OAuth completion handoff between services

Both tables include appropriate indexes for performance and cleanup operations.
