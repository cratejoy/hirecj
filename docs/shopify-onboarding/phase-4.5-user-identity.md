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

### ✅ Phase 4.5.0: Create User Identity Library (COMPLETE)
- [x] Created `shared/user_identity/` directory structure
- [x] Implemented models.py with SQLAlchemy models (renamed metadata→meta)
- [x] Implemented connection.py with Supabase connection
- [x] Implemented operations.py with core functions
- [x] Implemented queries.py with read operations
- [x] Implemented archival.py with conversation archival
- [x] Created migration SQL (001_initial.sql)
- [x] Wrote comprehensive unit tests
- [x] Updated shared/__init__.py to export user_identity

⚠️ **Note**: Supabase connection requires correct database password. Project URL is `txaitislqznncadkaffa.supabase.co` but the password needs to be obtained from Supabase dashboard.

### 🔧 Phase 4.5.1: Database Infrastructure (Day 1)
- [ ] **1.1 Environment Setup**
  - [ ] Verify Supabase dev credentials in .env (hire-cj-dev-amir)
  - [ ] Test connection string: `IDENTITY_SUPABASE_URL`
  - [ ] Get anon key from Supabase dashboard
  - [ ] Update .env with credentials
  - [ ] Run `make env-distribute` to propagate

- [ ] **1.2 Schema Creation**
  - [ ] Open Supabase SQL Editor for hire-cj-dev-amir
  - [ ] Run migration script (003_user_identity_supabase.sql)
  - [ ] Verify tables created: users, conversations, events
  - [ ] Test basic CRUD operations
  - [ ] Clean up test data

- [ ] **1.3 Database Service Integration**
  - [ ] Create `agents/app/services/identity_db.py`
  - [ ] Implement connection manager with NullPool
  - [ ] Add test_connection() function
  - [ ] Create pytest tests for database connectivity
  - [ ] Verify connection from agents service

### 👤 Phase 4.5.2: User Identity System (Day 1-2)
- [ ] **2.1 User ID Generation**
  - [ ] Update `auth/app/services/merchant_storage.py`
  - [ ] Implement generate_user_id() method (usr_xxx format)
  - [ ] Add get_or_create_user() method
  - [ ] Update create_merchant() to include user_id
  - [ ] Write tests for consistent ID generation

- [ ] **2.2 OAuth Integration**
  - [ ] Update OAuth callback in `auth/app/api/shopify_oauth.py`
  - [ ] Modify store_merchant_token() to return (merchant_id, user_id)
  - [ ] Include user_id in OAuth redirect params
  - [ ] Test OAuth flow end-to-end

- [ ] **2.3 Event Logging**
  - [ ] Create `auth/app/services/event_logger.py`
  - [ ] Implement log_user_event() function
  - [ ] Add event logging to OAuth flow
  - [ ] Test event insertion to Supabase

### 💾 Phase 4.5.3: Conversation Archival (Day 2)
- [ ] **3.1 Archival Service Setup**
  - [ ] Create `agents/app/services/conversation_archival.py`
  - [ ] Implement ConversationArchiver class
  - [ ] Add Redis scanning for conversations near TTL
  - [ ] Implement archive_conversation() method

- [ ] **3.2 Data Extraction**
  - [ ] Implement _get_conversation_data() from Redis
  - [ ] Handle message collection and sorting
  - [ ] Extract user_id from session/merchant data
  - [ ] Test data extraction logic

- [ ] **3.3 Background Service**
  - [ ] Implement run_archival_loop()
  - [ ] Add to main.py startup event
  - [ ] Configure 30-minute check interval
  - [ ] Test archival with mock data
  - [ ] Monitor logs for archival activity

### 🔌 Phase 4.5.4: History API (Day 2-3)
- [ ] **4.1 API Router Setup**
  - [ ] Create `agents/app/api/users.py`
  - [ ] Add router to main app
  - [ ] Implement authentication dependencies
  - [ ] Test basic route registration

- [ ] **4.2 Conversation Endpoints**
  - [ ] Implement GET /users/{user_id}/conversations
  - [ ] Add pagination support (limit/offset)
  - [ ] Implement GET /users/{user_id}/conversations/{id}
  - [ ] Add authorization checks
  - [ ] Test with curl/Postman

- [ ] **4.3 Profile Endpoint**
  - [ ] Implement GET /users/{user_id}/profile
  - [ ] Include conversation statistics
  - [ ] Test profile retrieval
  - [ ] Document API in code

### 🎨 Phase 4.5.5: Frontend Integration (Day 3)
- [ ] **5.1 WebSocket Updates**
  - [ ] Update SlackChat component to handle user_id
  - [ ] Modify OAuth callback handling
  - [ ] Store user_id in localStorage
  - [ ] Include user_id in WebSocket messages

- [ ] **5.2 Session Management**
  - [ ] Update session_manager.py to store user_id
  - [ ] Modify create_session() method
  - [ ] Store user_id in Redis session
  - [ ] Test session creation with user_id

- [ ] **5.3 UI Components**
  - [ ] Add ConversationHistory component
  - [ ] Show history link for authenticated users
  - [ ] Test UI updates
  - [ ] Verify user_id propagation

### ✅ Phase 4.5.6: End-to-End Testing (Day 3-4)
- [ ] **6.1 New User Flow**
  - [ ] Start fresh conversation
  - [ ] Complete Shopify OAuth
  - [ ] Verify user created in database
  - [ ] Check event logs
  - [ ] Verify conversation linked to user

- [ ] **6.2 Returning User Flow**
  - [ ] Start new conversation with same shop
  - [ ] Verify same user_id returned
  - [ ] Check conversation history accessible
  - [ ] Test profile endpoint

- [ ] **6.3 Archival Flow**
  - [ ] Create test conversation
  - [ ] Trigger archival (reduce TTL for testing)
  - [ ] Verify in Supabase database
  - [ ] Test retrieval via API

- [ ] **6.4 Production Readiness**
  - [ ] Document Supabase setup for production
  - [ ] Create production migration checklist
  - [ ] Update deployment documentation
  - [ ] Plan monitoring strategy

## ⏱️ Estimated Timeline: 3-4 Days

**Day 1**: Database setup (4.5.1) + Start user identity (4.5.2)
**Day 2**: Complete user identity + Archival service (4.5.3)
**Day 3**: API endpoints (4.5.4) + Frontend (4.5.5)
**Day 4**: End-to-end testing + Production prep

## 🚨 Critical Path Items

1. **Supabase Connection** - Blocks everything if not working
2. **User ID Generation** - Must be consistent and reliable
3. **OAuth Flow** - Must not break existing functionality
4. **Archival Service** - Must run reliably in background

## 📝 Success Criteria

Phase 4.5 is complete when:
- [ ] All checklist items above are complete
- [ ] Manual end-to-end test passes
- [ ] No regression in existing OAuth flow
- [ ] Archival service running without errors
- [ ] API endpoints return correct data
- [ ] Frontend shows user history link

## 🏗️ Architecture Overview

### Revised Architecture: Shared Python Library

After review, we decided to implement user identity as a shared Python library instead of service-specific integration. This provides:

1. **Direct Database Access**: No HTTP overhead
2. **Type Safety**: Python types instead of JSON APIs
3. **Reusability**: Both auth and agents services can import the same code
4. **Simpler Testing**: Mock the library, not HTTP calls

### Library Structure

```
shared/user_identity/
├── __init__.py       # Public API exports
├── models.py         # SQLAlchemy models
├── operations.py     # Core operations (create user, log events)
├── queries.py        # Read operations (get profile, history)
├── archival.py       # Conversation archival logic
├── connection.py     # Database connection management
└── migrations/       # SQL schema migrations
```

### Identity Flow

```
Shopify OAuth → User Creation → Session Enhancement → Conversation Archive
      ↓              ↓                ↓                      ↓
 (Shop Domain)   (usr_xxx ID)    (Redis Session)      (PostgreSQL)
      ↓              ↓                ↓                      ↓
   auth service   user_identity    agents service    user_identity
                     library                            library
```

### Why This Design?

1. **Shopify OAuth = Identity**: No separate registration, shop domain is unique
2. **Internal User IDs**: Clean usr_xxx format, not tied to external systems
3. **Flexible Storage**: JSONB allows evolution without migrations
4. **Automatic Archival**: Conversations preserved before Redis TTL
5. **Simple Queries**: User history by ID, no complex joins
6. **Shared Library**: Single implementation used by multiple services

## 📊 Database Schema

### Minimal 3-Table Design

```sql
-- 1. Users table (from Shopify OAuth)
CREATE TABLE users (
    id VARCHAR(50) PRIMARY KEY,  -- usr_xxx format
    shop_domain VARCHAR(255) UNIQUE NOT NULL,
    shopify_id VARCHAR(100),
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_shop_domain ON users(shop_domain);
CREATE INDEX idx_users_created_at ON users(created_at);

-- 2. Conversations archive
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id),
    merchant_id VARCHAR(100),  -- Keep for compatibility
    workflow_name VARCHAR(100),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    messages JSONB NOT NULL,  -- Full conversation history
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_started_at ON conversations(started_at);

-- 3. Events for analytics
CREATE TABLE events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id),
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_user_id ON events(user_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_created_at ON events(created_at);
```

## 🚀 Supabase Integration

### Development Setup with Supabase

We use Supabase for identity data storage, maintaining separation from production ETL data while leveraging the same infrastructure.

#### Step 1: Create Dev Supabase Project

1. **Dev Project Created**: `hire-cj-dev-amir` (us-east-1 region)
2. Get the anon key from: Supabase Dashboard > Settings > API > Project API keys > anon (public)
3. Keep this completely separate from production ETL data

#### Step 2: Configure Environment

```bash
# agents/.env.local

# Production ETL data (existing - DO NOT CHANGE)
SUPABASE_CONNECTION_STRING=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres

# Dev identity data (new - Phase 4.5)
IDENTITY_SUPABASE_URL=postgresql://postgres:hCqzUNjCg4QKvHyD@db.hire-cj-dev-amir.supabase.co:5432/postgres
IDENTITY_SUPABASE_ANON_KEY=eyJ... # Get from Supabase project settings > API
```

#### Step 3: Run Migration in Supabase

1. Go to [hire-cj-dev-amir Supabase Dashboard](https://supabase.com/dashboard/project/hire-cj-dev-amir)
2. Navigate to SQL Editor
3. Run the migration script (see Phase 4.5.1 below)

**Important Security Notes**:
- Keep identity data completely separate from production ETL/ticket data!
- Never commit the actual password to git (use .env.local which is gitignored)
- The connection string above is for your dev environment only

### Production Setup

For production, create a separate Supabase project for identity data.

#### Step 1: Create Production Supabase Project

1. Create another Supabase project: `hirecj-identity-prod`
2. Keep it separate from ETL/ticket data
3. Run the same migration script

#### Step 2: Configure Production Environment

```bash
# Set Heroku environment variables
heroku config:set IDENTITY_SUPABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres --app your-app
heroku config:set IDENTITY_SUPABASE_ANON_KEY=eyJ... --app your-app

# Verify separation from ETL data
heroku config:get SUPABASE_CONNECTION_STRING --app your-app  # Different project!
heroku config:get IDENTITY_SUPABASE_URL --app your-app      # Identity project
```

### Using the Shared User Identity Library

The user identity functionality is implemented as a shared library that can be imported by any service:

```python
# Example usage in auth service
from shared.user_identity import get_or_create_user, log_user_event

# During OAuth callback
user_id, is_new = get_or_create_user(
    shop_domain,
    email=shop_info.get("email"),
    name=shop_info.get("shop_owner")
)

log_user_event(user_id, "oauth_complete", {
    "shop": shop_domain,
    "first_time": is_new
})
```

```python
# Example usage in agents service
from shared.user_identity import archive_conversation, get_user_profile

# Archive conversation before Redis TTL
archive_conversation(conversation_id, redis_client, user_id)

# Get user history
profile = get_user_profile(user_id)
```

### Library Configuration

The shared library reads database configuration from environment variables:

```python
# The library expects these in .env:
IDENTITY_SUPABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
IDENTITY_SUPABASE_ANON_KEY=eyJ... # For future client features
```

No service-specific configuration is needed - the library handles all database connections internally.

### Migration Strategy

For Supabase, we run migrations directly in the SQL Editor rather than using local scripts:

```bash
# Directory structure (for reference)
agents/
  app/
    migrations/
      001_create_all_tables.sql         # ETL tables (production Supabase)
      002_create_daily_ticket_summaries.sql.old  # Old migration
      003_user_identity_supabase.sql    # Identity tables (dev Supabase)
```

**Important**: Run migrations in the correct Supabase project!
- ETL migrations (001, 002) → Production Supabase
- Identity migrations (003) → Identity Supabase

For automated migrations, you can use Supabase CLI:

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Link to your identity project
supabase link --project-ref hire-cj-dev-amir

# Run migration
supabase db push --file agents/app/migrations/003_user_identity_supabase.sql
```

### Environment Variable Hierarchy

Our setup respects the following precedence (via shared/env_loader.py):

1. **Environment variables** (highest priority)
2. **.env.tunnel** (for ngrok development)
3. **.env.local** (local overrides)
4. **Service .env** (service defaults)
5. **Config defaults** (lowest priority)

### Testing Database Connectivity

```python
# agents/tests/test_identity_db.py
"""Test identity Supabase setup."""

import pytest
from app.services.identity_db import test_connection, get_db
from sqlalchemy import text

def test_supabase_connection():
    """Test we can connect to identity Supabase."""
    assert test_connection() is True

def test_identity_schema_exists():
    """Test identity schema was created."""
    with get_db() as db:
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.schemata 
                WHERE schema_name = 'identity'
            )
        """))
        assert result.scalar() is True

def test_database_tables():
    """Test our tables exist in identity schema."""
    with get_db() as db:
        # Check users table
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'identity' 
                AND table_name = 'users'
            )
        """))
        assert result.scalar() is True
        
        # Check conversations table
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'identity' 
                AND table_name = 'conversations'
            )
        """))
        assert result.scalar() is True
```

### Deployment Commands

```bash
# Local Development
make dev                    # Starts all services
# Run migration in Supabase SQL Editor (no local command needed)

# Production
heroku config:set IDENTITY_SUPABASE_URL=$IDENTITY_SUPABASE_URL --app your-app
heroku config:set IDENTITY_SUPABASE_ANON_KEY=$IDENTITY_SUPABASE_ANON_KEY --app your-app
# Run migration in production Supabase SQL Editor
```

## 📋 Phased Implementation Approach

### Phase 4.5.1: Database Setup

**Goal**: Create database schema and test connectivity

#### Step 1: Create Migration File

Run this in your Supabase SQL Editor:

```sql
-- agents/app/migrations/003_user_identity_supabase.sql
-- Run this in the IDENTITY Supabase project, NOT production ETL!

-- Enable UUID extension (usually already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create identity schema for organization
CREATE SCHEMA IF NOT EXISTS identity;

-- Users table
CREATE TABLE IF NOT EXISTS identity.users (
    id VARCHAR(50) PRIMARY KEY,  -- usr_xxx format
    shop_domain VARCHAR(255) UNIQUE NOT NULL,
    shopify_id VARCHAR(100),
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_users_shop_domain ON identity.users(shop_domain);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON identity.users(created_at);

-- Conversations archive
CREATE TABLE IF NOT EXISTS identity.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(50) REFERENCES identity.users(id),
    merchant_id VARCHAR(100),  -- Keep for compatibility
    workflow_name VARCHAR(100),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    messages JSONB NOT NULL,  -- Full conversation history
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON identity.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_started_at ON identity.conversations(started_at);

-- Events table for analytics
CREATE TABLE IF NOT EXISTS identity.events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES identity.users(id),
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_user_id ON identity.events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON identity.events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON identity.events(created_at);

-- Grant permissions (Supabase specific)
GRANT USAGE ON SCHEMA identity TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA identity TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA identity TO anon, authenticated;

-- Future: Enable Row Level Security when needed
-- ALTER TABLE identity.users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE identity.conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE identity.events ENABLE ROW LEVEL SECURITY;
```

#### Step 2: Run Migration

```bash
# Option 1: Use Supabase SQL Editor (Recommended)
# 1. Go to your identity Supabase project dashboard
# 2. Navigate to SQL Editor
# 3. Paste the migration SQL above
# 4. Click "Run"

# Option 2: Use Supabase CLI (requires supabase link first)
supabase db push --file agents/app/migrations/003_user_identity_supabase.sql

# Verify tables were created
# In SQL Editor, run:
SELECT table_schema, table_name 
FROM information_schema.tables 
WHERE table_schema = 'identity';
```

#### Step 3: Test Queries

Run these in Supabase SQL Editor to verify setup:

```sql
-- Test user creation
INSERT INTO identity.users (id, shop_domain, email, name) 
VALUES ('usr_test123', 'test.myshopify.com', 'test@example.com', 'Test User');

-- Test conversation archive
INSERT INTO identity.conversations (user_id, workflow_name, started_at, messages)
VALUES (
    'usr_test123',
    'shopify_onboarding',
    NOW(),
    '[{"sender": "user", "content": "Hello"}, {"sender": "cj", "content": "Hi there!"}]'::jsonb
);

-- Test event logging
INSERT INTO identity.events (user_id, event_type, event_data)
VALUES ('usr_test123', 'oauth_complete', '{"shop": "test.myshopify.com"}'::jsonb);

-- Verify data
SELECT * FROM identity.users;
SELECT * FROM identity.conversations WHERE user_id = 'usr_test123';
SELECT * FROM identity.events WHERE user_id = 'usr_test123';

-- Clean up test data
DELETE FROM identity.events WHERE user_id = 'usr_test123';
DELETE FROM identity.conversations WHERE user_id = 'usr_test123';
DELETE FROM identity.users WHERE id = 'usr_test123';
```

**✅ Phase 4.5.1 Complete When:**
- [ ] Migration file created
- [ ] Tables created successfully
- [ ] Test data inserts work
- [ ] Indexes are in place

---

### Phase 4.5.2: User ID Generation

**Goal**: Integrate the shared library into auth service for user creation during OAuth

#### Step 1: Update OAuth Callback to Use Library

```python
# auth/app/api/shopify_oauth.py

from shared.user_identity import get_or_create_user, log_user_event

def store_merchant_token(shop: str, access_token: str) -> Tuple[str, str]:
    """
    Store merchant token and create/get user.
    
    Returns:
        Tuple of (merchant_id, user_id)
    """
    # Get shop info from Shopify API (optional)
    shop_info = get_shop_info(access_token)  # If you have this
    
    # Use the library to get or create user
    user_id, is_new = get_or_create_user(
        shop,
        email=shop_info.get("email") if shop_info else None,
        name=shop_info.get("shop_owner") if shop_info else None
    )
    
    # Check if merchant exists in Redis
    merchant = merchant_storage.get_merchant(shop)
    
    if merchant is None:
        # Create new merchant
        merchant_id = f"merchant_{shop.replace('.myshopify.com', '')}"
        merchant_storage.create_merchant({
            "merchant_id": merchant_id,
            "shop_domain": shop,
            "access_token": access_token,
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Log event using library
        log_user_event(user_id, "oauth_complete", {"shop": shop, "first_time": True})
        
        logger.info(f"[STORE_TOKEN] Created new merchant: {shop}, user: {user_id}")
        return f"new_{merchant_id}", user_id
    else:
        # Update existing merchant
        merchant_storage.update_token(shop, access_token)
        merchant_id = merchant.get("merchant_id", f"merchant_{shop.replace('.myshopify.com', '')}")
        
        # Log event using library
        log_user_event(user_id, "oauth_complete", {"shop": shop, "first_time": False})
        
        logger.info(f"[STORE_TOKEN] Updated existing merchant: {shop}, user: {user_id}")
        return merchant_id, user_id

@router.get("/callback")
async def handle_oauth_callback(...):
    """Enhanced to include user_id in redirect."""
    # ... existing validation ...
    
    # Exchange code for access token
    try:
        access_token = await exchange_code_for_token(shop, code)
        
        # Store merchant data and get IDs
        merchant_id, user_id = store_merchant_token(shop, access_token)
        is_new = merchant_id.startswith("new_")
        if is_new:
            merchant_id = merchant_id[4:]  # Remove prefix
        
        # Redirect with user_id
        redirect_params = {
            "oauth": "complete",
            "is_new": str(is_new).lower(),
            "merchant_id": merchant_id,
            "user_id": user_id,  # NEW
            "shop": shop
        }
        
        redirect_url = f"{settings.frontend_url}/chat?{urlencode(redirect_params)}"
        return RedirectResponse(url=redirect_url, status_code=302)
```

#### Step 3: Add Event Logging

```python
# auth/app/services/event_logger.py
"""Simple event logging to PostgreSQL."""

import json
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import text
from app.services.identity_db import get_db
import logging

logger = logging.getLogger(__name__)

def log_user_event(
    user_id: str, 
    event_type: str, 
    event_data: Dict[str, Any]
) -> None:
    """Log user event to PostgreSQL."""
    try:
        with get_db() as db:
            db.execute(text("""
                INSERT INTO identity.events (user_id, event_type, event_data, created_at)
                VALUES (:user_id, :event_type, :event_data, :created_at)
            """), {
                "user_id": user_id,
                "event_type": event_type,
                "event_data": json.dumps(event_data),
                "created_at": datetime.utcnow()
            })
            db.commit()
    except Exception as e:
        logger.error(f"Failed to log event: {e}")
        # Don't fail the request over logging
```

**✅ Phase 4.5.2 Complete When:**
- [ ] User ID generation working (usr_xxx format)
- [ ] OAuth callback includes user_id
- [ ] Events logged for user creation and OAuth
- [ ] Tests verify consistent ID generation

---

### Phase 4.5.3: Conversation Archival

**Goal**: Integrate the shared library's archival service into agents

#### Step 1: Create Archival Service Wrapper

```python
# agents/app/services/conversation_archival.py
"""Archive conversations from Redis to PostgreSQL."""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncpg
from redis import Redis
from app.config import settings
from shared.constants import REDIS_SESSION_TTL
import logging

logger = logging.getLogger(__name__)

class ConversationArchiver:
    """Archive conversations before Redis TTL expires."""
    
    def __init__(self):
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self.archive_before_ttl = timedelta(hours=2)  # Archive 2 hours before expiry
    
    async def archive_conversation(self, conversation_id: str) -> bool:
        """Archive a single conversation to PostgreSQL."""
        try:
            # Get conversation from Redis
            conv_data = self._get_conversation_data(conversation_id)
            if not conv_data:
                return False
            
            # Extract user_id from session or conversation
            user_id = conv_data.get("user_id")
            if not user_id:
                # Try to get from merchant data
                merchant_id = conv_data.get("merchant_id")
                if merchant_id:
                    # Look up user_id from merchant
                    user_id = await self._get_user_id_from_merchant(merchant_id)
            
            if not user_id:
                logger.warning(f"No user_id found for conversation {conversation_id}")
                return False
            
            # Use identity database connection
            from app.services.identity_db import get_db
            from sqlalchemy import text
            
            with get_db() as db:
                # Insert conversation
                db.execute(text("""
                    INSERT INTO identity.conversations 
                    (id, user_id, merchant_id, workflow_name, started_at, ended_at, messages, metadata)
                    VALUES (:id, :user_id, :merchant_id, :workflow, :started_at, :ended_at, :messages, :metadata)
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": conversation_id,
                    "user_id": user_id,
                    "merchant_id": conv_data.get("merchant_id"),
                    "workflow": conv_data.get("workflow_name", "unknown"),
                    "started_at": conv_data.get("started_at"),
                    "ended_at": conv_data.get("ended_at", datetime.utcnow()),
                    "messages": json.dumps(conv_data.get("messages", [])),
                    "metadata": json.dumps(conv_data.get("metadata", {}))
                })
                db.commit()
            
            # Mark as archived in Redis
            self.redis.hset(f"conversation:{conversation_id}", "archived", "true")
            
            logger.info(f"Archived conversation {conversation_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive conversation {conversation_id}: {e}")
            return False
    
    def _get_conversation_data(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation data from Redis."""
        try:
            # Get all conversation keys
            pattern = f"*{conversation_id}*"
            keys = self.redis.keys(pattern)
            
            conversation_data = {
                "messages": [],
                "metadata": {}
            }
            
            for key in keys:
                if "message:" in key:
                    # Message data
                    msg_data = self.redis.hgetall(key)
                    if msg_data:
                        conversation_data["messages"].append(msg_data)
                elif "session:" in key:
                    # Session data
                    session_data = self.redis.hgetall(key)
                    if session_data:
                        conversation_data.update(session_data)
            
            # Sort messages by timestamp
            conversation_data["messages"].sort(
                key=lambda x: x.get("timestamp", ""), 
                reverse=False
            )
            
            return conversation_data if conversation_data["messages"] else None
            
        except Exception as e:
            logger.error(f"Failed to get conversation data: {e}")
            return None
    
    async def _get_user_id_from_merchant(self, merchant_id: str) -> Optional[str]:
        """Look up user_id from merchant_id."""
        # Extract shop domain from merchant_id
        shop_domain = f"{merchant_id.replace('merchant_', '')}.myshopify.com"
        
        # Get from Redis merchant data
        merchant_data = self.redis.get(f"merchant:{shop_domain}")
        if merchant_data:
            merchant = json.loads(merchant_data)
            return merchant.get("user_id")
        
        return None
    
    async def find_conversations_to_archive(self) -> List[str]:
        """Find conversations that need archiving."""
        conversations = []
        
        try:
            # Find all conversation keys
            pattern = "conversation:*"
            for key in self.redis.scan_iter(pattern):
                # Check if already archived
                archived = self.redis.hget(key, "archived")
                if archived == "true":
                    continue
                
                # Check TTL
                ttl = self.redis.ttl(key)
                if ttl > 0 and ttl < self.archive_before_ttl.total_seconds():
                    conv_id = key.split(":")[-1]
                    conversations.append(conv_id)
            
        except Exception as e:
            logger.error(f"Failed to find conversations: {e}")
        
        return conversations
    
    async def run_archival_loop(self):
        """Run continuous archival loop."""
        logger.info("Starting conversation archival service")
        
        while True:
            try:
                # Find conversations to archive
                conversations = await self.find_conversations_to_archive()
                
                if conversations:
                    logger.info(f"Found {len(conversations)} conversations to archive")
                    
                    # Archive each conversation
                    for conv_id in conversations:
                        await self.archive_conversation(conv_id)
                
                # Sleep for 30 minutes
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"Archival loop error: {e}")
                await asyncio.sleep(60)  # Short sleep on error

# Singleton instance
archiver = ConversationArchiver()
```

#### Step 2: Add Archival to Main Service

```python
# agents/app/main.py

# Add to startup
@app.on_event("startup")
async def startup_event():
    """Start background tasks."""
    # ... existing startup ...
    
    # Start archival service
    from app.services.conversation_archival import archiver
    asyncio.create_task(archiver.run_archival_loop())
    logger.info("Started conversation archival service")
```

#### Step 3: Test Archival

```python
# tests/test_conversation_archival.py
import pytest
from app.services.conversation_archival import ConversationArchiver

async def test_archive_conversation():
    """Test conversation archival."""
    archiver = ConversationArchiver()
    
    # Create test conversation in Redis
    conv_id = "test-conv-123"
    # ... set up test data ...
    
    # Archive it
    result = await archiver.archive_conversation(conv_id)
    assert result is True
    
    # Verify in PostgreSQL
    # ... verify archived data ...
```

**✅ Phase 4.5.3 Complete When:**
- [ ] Archival service finds conversations near TTL
- [ ] Conversations archived with full message history
- [ ] User ID properly linked
- [ ] Background loop running without errors

---

### Phase 4.5.4: User History API

**Goal**: Add API endpoints to retrieve user conversation history

#### Step 1: Create User API Router

```python
# agents/app/api/users.py
"""User history and profile endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from app.services.identity_db import get_db
from app.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{user_id}/conversations")
async def get_user_conversations(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's conversation history."""
    # Verify user can access this data
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        with get_db() as db:
            # Get conversations
            result = db.execute(text("""
                SELECT 
                    id, workflow_name, started_at, ended_at,
                    jsonb_array_length(messages) as message_count,
                    metadata
                FROM identity.conversations
                WHERE user_id = :user_id
                ORDER BY started_at DESC
                LIMIT :limit OFFSET :offset
            """), {"user_id": user_id, "limit": limit, "offset": offset})
            
            conversations = []
            for row in result:
                conversations.append({
                    "id": str(row.id),
                    "workflow": row.workflow_name,
                    "started_at": row.started_at.isoformat(),
                    "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                    "message_count": row.message_count,
                    "metadata": row.metadata
                })
            
            # Get total count
            count_result = db.execute(
                text("SELECT COUNT(*) as total FROM identity.conversations WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            total = count_result.scalar()
            
            return {
                "conversations": conversations,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        
    except Exception as e:
        logger.error(f"Failed to get user conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")

@router.get("/{user_id}/conversations/{conversation_id}")
async def get_conversation_detail(
    user_id: str,
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get full conversation details."""
    # Verify access
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        with get_db() as db:
            result = db.execute(text("""
                SELECT * FROM identity.conversations
                WHERE id = :conv_id AND user_id = :user_id
            """), {"conv_id": conversation_id, "user_id": user_id})
            
            row = result.first()
            if not row:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            return {
                "id": str(row.id),
                "workflow": row.workflow_name,
                "started_at": row.started_at.isoformat(),
                "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                "messages": row.messages,  # Already JSON
                "metadata": row.metadata
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")

@router.get("/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user profile information."""
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        with get_db() as db:
            # Get user data
            user_result = db.execute(
                text("SELECT * FROM identity.users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            user = user_result.first()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get conversation stats
            stats_result = db.execute(text("""
                SELECT 
                    COUNT(*) as total_conversations,
                    MIN(started_at) as first_conversation,
                    MAX(started_at) as last_conversation
                FROM identity.conversations
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            stats = stats_result.first()
            
            return {
                "user_id": user.id,
                "shop_domain": user.shop_domain,
                "email": user.email,
                "name": user.name,
                "created_at": user.created_at.isoformat(),
                "last_seen": user.last_seen.isoformat(),
                "stats": {
                    "total_conversations": stats.total_conversations,
                    "first_conversation": stats.first_conversation.isoformat() if stats.first_conversation else None,
                    "last_conversation": stats.last_conversation.isoformat() if stats.last_conversation else None
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve profile")
```

#### Step 2: Add Router to Main App

```python
# agents/app/main.py

from app.api import users

# Add router
app.include_router(users.router, prefix="/api/v1")
```

#### Step 3: Test API Endpoints

```bash
# Test user conversations endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users/usr_12345678/conversations

# Test conversation detail
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users/usr_12345678/conversations/$CONV_ID

# Test user profile
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users/usr_12345678/profile
```

**✅ Phase 4.5.4 Complete When:**
- [ ] User conversations endpoint returns paginated history
- [ ] Conversation detail endpoint returns full messages
- [ ] User profile endpoint returns stats
- [ ] Authorization checks prevent unauthorized access

---

### Phase 4.5.5: Frontend Updates

**Goal**: Update frontend to use user_id in sessions

#### Step 1: Update SlackChat Component

```typescript
// homepage/src/components/SlackChat.tsx

interface ChatConfig {
  workflow: string;
  conversationId: string;
  merchantId: string | null;
  userId: string | null;  // NEW
}

// Handle OAuth callback parameters
useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  
  if (params.get('oauth') === 'complete') {
    const userId = params.get('user_id');  // NEW
    const merchantId = params.get('merchant_id');
    const isNew = params.get('is_new') === 'true';
    
    // Update chat config with user ID
    setChatConfig(prev => ({
      ...prev,
      userId,
      merchantId
    }));
    
    // Store user ID in localStorage for future sessions
    if (userId) {
      localStorage.setItem('hirecj_user_id', userId);
    }
    
    // Send OAuth complete message to WebSocket
    sendMessage({
      type: 'oauth_complete',
      oauth_provider: 'shopify',
      is_new: isNew,
      merchant_id: merchantId,
      user_id: userId  // Include in WebSocket message
    });
  }
}, []);

// Include user_id in start message
const startConversation = () => {
  const savedUserId = localStorage.getItem('hirecj_user_id');
  
  sendMessage({
    type: 'start',
    workflow: chatConfig.workflow,
    conversation_id: chatConfig.conversationId,
    merchant_id: chatConfig.merchantId,
    user_id: savedUserId || chatConfig.userId  // Include user ID
  });
};
```

#### Step 2: Add History Button

```typescript
// homepage/src/components/ConversationHistory.tsx
import React from 'react';

interface ConversationHistoryProps {
  userId: string | null;
}

export const ConversationHistory: React.FC<ConversationHistoryProps> = ({ userId }) => {
  if (!userId) return null;
  
  return (
    <button
      onClick={() => window.open(`/history/${userId}`, '_blank')}
      className="text-sm text-gray-500 hover:text-gray-700"
    >
      View conversation history
    </button>
  );
};
```

#### Step 3: Update Session Manager

```python
# agents/app/services/session_manager.py

def create_session(self, data: Dict[str, Any]) -> Session:
    """Enhanced to include user_id."""
    conversation_id = data.get("conversation_id")
    merchant_id = data.get("merchant_id")
    user_id = data.get("user_id")  # NEW
    
    # Create conversation with user_id
    conversation = Conversation(
        id=conversation_id,
        merchant_id=merchant_id,
        user_id=user_id,  # Store in conversation
        workflow=data.get("workflow", "shopify_onboarding"),
        started_at=datetime.utcnow()
    )
    
    # Store user_id in Redis session
    self.redis_client.hset(
        f"session:{conversation_id}",
        mapping={
            "user_id": user_id or "",
            "merchant_id": merchant_id or "",
            # ... other fields ...
        }
    )
    
    return Session(
        id=conversation_id,
        user_id=user_id,
        merchant_id=merchant_id,
        conversation=conversation
    )
```

**✅ Phase 4.5.5 Complete When:**
- [ ] Frontend receives and stores user_id
- [ ] User ID included in WebSocket messages
- [ ] Session manager stores user_id
- [ ] History link shown for authenticated users

---

## 🎉 Phase 4.5 Implementation Complete!

With all phases complete, you now have:
- ✅ Database schema with users, conversations, and events
- ✅ User ID generation during OAuth (usr_xxx format)
- ✅ Automatic conversation archival before Redis TTL
- ✅ API endpoints for user history and profiles
- ✅ Frontend integration with user sessions

## 🧪 End-to-End Testing

### Test Flow

1. **New User Flow**:
   - Start fresh conversation
   - Complete Shopify OAuth
   - Verify user created with usr_xxx ID
   - Check event logged
   - Verify conversation linked to user

2. **Returning User Flow**:
   - Start new conversation
   - Complete OAuth with same shop
   - Verify same user ID returned
   - Check previous conversations accessible

3. **Archival Flow**:
   - Create conversation
   - Wait for archival (or trigger manually)
   - Verify in PostgreSQL
   - Check user can access via API

### Manual Test Commands

```bash
# Check user creation
psql -c "SELECT * FROM identity.users ORDER BY created_at DESC LIMIT 5;"

# Check conversations
psql -c "SELECT id, user_id, workflow_name, started_at FROM identity.conversations ORDER BY started_at DESC LIMIT 5;"

# Check events
psql -c "SELECT user_id, event_type, created_at FROM identity.events ORDER BY created_at DESC LIMIT 10;"

# Test API
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/users/$USER_ID/conversations
```

---

## 🚀 Benefits for Phase 5

With user identity in place, Phase 5 (Quick Value Demo) can now:

1. **Personalized Greetings**: "Welcome back! Last time we discussed..."
2. **Historical Context**: Reference previous conversations
3. **User Preferences**: Store and retrieve user settings
4. **Analytics**: Track user engagement over time
5. **Multi-Session**: Continue conversations across sessions

---

## 📊 Monitoring & Maintenance

### Key Metrics

1. **Archival Health**:
   - Conversations archived per hour
   - Failed archival attempts
   - Average archival latency

2. **User Growth**:
   - New users per day
   - Returning user rate
   - Conversations per user

3. **Storage Usage**:
   - PostgreSQL table sizes
   - JSONB query performance
   - Index effectiveness

### Maintenance Tasks

```sql
-- Weekly: Clean up orphaned conversations
DELETE FROM identity.conversations 
WHERE user_id IS NULL 
AND created_at < NOW() - INTERVAL '7 days';

-- Monthly: Analyze tables for query optimization
ANALYZE identity.users;
ANALYZE identity.conversations;
ANALYZE identity.events;

-- Quarterly: Review and archive old events
INSERT INTO identity.events_archive 
SELECT * FROM identity.events 
WHERE created_at < NOW() - INTERVAL '90 days';
```

---

## 🔑 Key Design Decisions

1. **Why usr_xxx IDs?**
   - Clean, readable format
   - Not tied to external systems
   - Consistent length for indexing

2. **Why JSONB for messages?**
   - Flexibility for future changes
   - No complex migrations needed
   - Native PostgreSQL support

3. **Why archive to PostgreSQL?**
   - Long-term persistence
   - Rich querying capabilities
   - Reliable backup solution

4. **Why link to Shopify?**
   - Single source of identity
   - No separate registration
   - Verified business identity

---

## 📚 Next Steps

1. **Phase 5 Integration**: Use user history for personalized insights
2. **Analytics Dashboard**: Build internal metrics on user behavior
3. **Export Features**: Let users download their conversation history
4. **Team Accounts**: Multiple users per shop (future enhancement)

This minimal implementation provides a solid foundation for user identity without over-engineering, perfectly aligned with our North Star principles.

---

## 🔧 Supabase Integration Summary

### Development Environment

1. **Supabase Project**: Dedicated `hirecj-identity-dev` project
2. **Zero Local Setup**: No PostgreSQL installation required
3. **Environment configuration**: `IDENTITY_SUPABASE_URL` in `.env.local`
4. **Schema Organization**: `identity` schema for clean separation

### Production Environment

1. **Separate Supabase Project**: `hirecj-identity-prod`
2. **Environment variables**: Set via Heroku config
3. **Built-in SSL**: Automatic secure connections
4. **Scalability**: Supabase handles all infrastructure

### Key Design Decisions

1. **Separate Projects**: ETL data and identity data in different Supabase projects
2. **SQLAlchemy ORM**: Consistent with existing patterns
3. **Migration Strategy**: Supabase SQL Editor or CLI
4. **Connection Management**: NullPool for serverless compatibility
5. **Future-Ready**: Can leverage Supabase Auth, Realtime, Row Level Security

### Quick Start Commands

```bash
# Development Setup
# 1. Your Supabase project: hire-cj-dev-amir (us-east-1)
# 2. Add credentials to .env.local:
echo "IDENTITY_SUPABASE_URL=postgresql://postgres:hCqzUNjCg4QKvHyD@db.hire-cj-dev-amir.supabase.co:5432/postgres" >> agents/.env.local

# 3. Run migration in SQL Editor
# 4. Test connection:
cd agents
python -c "from app.services.identity_db import test_connection; print(test_connection())"

# Production Setup
heroku config:set IDENTITY_SUPABASE_URL=postgresql://... --app your-app
heroku config:set IDENTITY_SUPABASE_ANON_KEY=eyJ... --app your-app
```

### Architecture Diagram

```
Production Supabase              Dev Supabase (Identity)
├── ETL/Ticket Data             ├── User Identity Data
│   ├── merchants               │   ├── identity.users
│   ├── etl_shopify_*          │   ├── identity.conversations
│   └── etl_freshdesk_*        │   └── identity.events
└── SUPABASE_CONNECTION_STRING  └── IDENTITY_SUPABASE_URL
```

This elegant integration leverages Supabase's managed infrastructure while maintaining clean separation between production ETL data and user identity data.