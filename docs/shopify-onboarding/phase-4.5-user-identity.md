# Phase 4.5: User Identity & Persistence - Implementation Guide

## 🎯 Phase Objectives

Implement a minimal user identity system that preserves conversation history without complex schemas, enabling personalized experiences across sessions while maintaining simplicity.

**North Star Principles Applied:**
- **Simplify**: Just 3 tables with JSONB for flexibility
- **No Cruft**: No complex user management, Shopify OAuth is our identity
- **Backend-Driven**: All identity logic in backend services
- **Single Source of Truth**: usr_xxx ID links everything
- **No Over-Engineering**: Only what Phase 5 needs for "your store" insights

## ✅ Master Implementation Checklist

### ✅ Phase 4.5.0: Backend User Identity System (COMPLETE)
- [x] Created `shared/user_identity.py` - 174 lines of simple PostgreSQL functions
- [x] Implemented 6 core functions:
  - [x] `generate_user_id()` - Deterministic usr_xxx from shop domain
  - [x] `get_or_create_user()` - Create/retrieve user by shop
  - [x] `save_conversation_message()` - Store messages in PostgreSQL
  - [x] `get_user_conversations()` - Retrieve conversation history
  - [x] `append_fact()` - Add facts to user's JSONB array
  - [x] `get_user_facts()` - Retrieve user facts
- [x] Created PostgreSQL migration (003_user_identity.sql)
- [x] Integrated with OAuth flow in auth service
- [x] Migrated fact extraction from merchant_memory to user_identity
- [x] Added comprehensive unit tests
- [x] Successfully tested with cratejoy-dev OAuth

### ✅ Phase 4.5.1: OAuth Integration (COMPLETE)
- [x] Updated auth service to call `get_or_create_user()` after OAuth
- [x] Frontend receives merchant_id in OAuth callback
- [x] User identity created in PostgreSQL on first OAuth
- [x] Fixed environment variable distribution for OAUTH_REDIRECT_BASE_URL
- [x] Simplified OAuth redirect URL configuration (no magic fallbacks)

### 🎨 Phase 4.5.2: Frontend User Session Management (NEXT)
- [ ] **2.1 Create useUserSession Hook**
  - [ ] Create `homepage/src/hooks/useUserSession.ts`
  - [ ] Implement localStorage persistence for merchantId and shopDomain
  - [ ] Add state management with useState + useEffect
  - [ ] Export typed interface for hook return values
  - [ ] Add methods: setMerchant, clearMerchant

- [ ] **2.2 Integrate with SlackChat**
  - [ ] Replace scattered merchantId state with useUserSession
  - [ ] Update OAuth callback to use setMerchant()
  - [ ] Remove redundant localStorage calls
  - [ ] Ensure merchant persists across page reloads
  - [ ] Update debug interface to show persistent vs ephemeral state

- [ ] **2.3 Update WebSocket Integration**
  - [ ] Pass merchantId from useUserSession to WebSocket
  - [ ] Ensure new conversations use persisted merchant
  - [ ] Test workflow changes preserve merchant connection
  - [ ] Verify OAuth → refresh → new conversation flow

## 🏗️ Architecture Summary

### Backend: Simple PostgreSQL Functions
- Single file: `shared/user_identity.py` (174 lines)
- Direct PostgreSQL with psycopg2
- 3 tables: users, conversations, user_facts
- JSONB for flexible fact storage

### Frontend: Standard React Hook Pattern
- `useUserSession` hook for persistent user state
- localStorage + useState + useEffect
- No Context, no Redux, just a simple hook
- ~40 lines of code

### Key Decisions
- Shop domain generates deterministic user IDs
- No complex user management - Shopify OAuth is identity
- Backend owns all identity logic
- Frontend just persists merchantId + shopDomain
- Ephemeral state (conversationId) stays local to components

## 📊 Database Schema (Implemented)

```sql
-- Users table
CREATE TABLE users (
    id VARCHAR(50) PRIMARY KEY,  -- usr_xxx format
    shop_domain VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conversations archive
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id),
    message JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User facts (learned information)
CREATE TABLE user_facts (
    user_id VARCHAR(50) PRIMARY KEY REFERENCES users(id),
    facts JSONB DEFAULT '[]'::jsonb
);
```

## 🚀 Next Steps

After completing the frontend useUserSession hook, Phase 4.5 will be complete. This provides:
- Persistent user identity across sessions
- Clean separation of persistent (user) vs ephemeral (conversation) state
- Foundation for Phase 5 personalization features
- Simple, maintainable architecture following React best practices