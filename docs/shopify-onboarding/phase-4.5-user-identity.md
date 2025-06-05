# Phase 4.5: User Identity & Persistence - Implementation Guide

## 🎯 Phase Objectives

Implement a minimal user identity system that preserves conversation history without complex schemas, enabling personalized experiences across sessions while maintaining simplicity.

**North Star Principles Applied:**
- **Simplify**: Just 3 tables with JSONB for flexibility
- **No Cruft**: No complex user management, Shopify OAuth is our identity
- **Backend-Driven**: All identity logic in backend services
- **Single Source of Truth**: usr_xxx ID links everything
- **No Over-Engineering**: Only what Phase 5 needs for "your store" insights

## ✅ Implementation Checklist

Phase 4.5 is complete when all sub-phases are complete:

- [ ] **Phase 4.5.1**: Database schema creation and migration
- [ ] **Phase 4.5.2**: User ID generation in auth service
- [ ] **Phase 4.5.3**: Conversation archival service
- [ ] **Phase 4.5.4**: User history API endpoints
- [ ] **Phase 4.5.5**: Frontend session updates
- [ ] **End-to-End**: Complete flow tested manually

## 🏗️ Architecture Overview

### Identity Flow

```
Shopify OAuth → User Creation → Session Enhancement → Conversation Archive
      ↓              ↓                ↓                      ↓
 (Shop Domain)   (usr_xxx ID)    (Redis Session)      (PostgreSQL)
```

### Why This Design?

1. **Shopify OAuth = Identity**: No separate registration, shop domain is unique
2. **Internal User IDs**: Clean usr_xxx format, not tied to external systems
3. **Flexible Storage**: JSONB allows evolution without migrations
4. **Automatic Archival**: Conversations preserved before Redis TTL
5. **Simple Queries**: User history by ID, no complex joins

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

## 🚀 PostgreSQL Integration

### Local Development Setup (Native, No Docker)

Our development system uses native PostgreSQL on port **5435** to avoid conflicts with default PostgreSQL installations.

#### Step 1: Install PostgreSQL Locally

```bash
# macOS (using Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Linux (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-contrib

# Start PostgreSQL on custom port
postgres -D /usr/local/var/postgres -p 5435 &
```

#### Step 2: Create Development Database

```bash
# Create database and user
createdb -p 5435 hirecj_identity
createuser -p 5435 -s hirecj

# Set password (optional for local dev)
psql -p 5435 -d hirecj_identity -c "ALTER USER hirecj PASSWORD 'hirecj_dev_password';"
```

#### Step 3: Configure Environment

```bash
# agents/.env.local
IDENTITY_DATABASE_URL=postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj_identity

# For development without password
IDENTITY_DATABASE_URL=postgresql://hirecj@localhost:5435/hirecj_identity
```

### Heroku Production Setup

Heroku provides PostgreSQL as an add-on with automatic configuration.

#### Step 1: Add PostgreSQL to Heroku

```bash
# Add Heroku Postgres (mini plan for identity data)
heroku addons:create heroku-postgresql:mini --app your-app-name

# This creates DATABASE_URL environment variable
# We'll use a separate database for identity
heroku addons:create heroku-postgresql:mini --as IDENTITY_DATABASE --app your-app-name
```

#### Step 2: Configure Production Environment

```bash
# Heroku automatically provides:
# DATABASE_URL=postgres://user:pass@host:port/dbname
# IDENTITY_DATABASE_URL=postgres://user:pass@host:port/dbname

# Our config automatically handles postgres:// → postgresql:// conversion
```

### Database Configuration Class

Update the agents service configuration to support identity database:

```python
# agents/app/config.py

class Settings(BaseSettings):
    """Enhanced with identity database support."""
    
    # Existing configuration...
    
    # Identity Database (Phase 4.5)
    identity_database_url: str = Field(
        default="postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj_identity",
        description="PostgreSQL URL for user identity data"
    )
    
    @field_validator('identity_database_url')
    def validate_identity_database_url(cls, v):
        """Handle Heroku's postgres:// URLs."""
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v
    
    # Connection pool settings for identity DB
    identity_db_pool_size: int = Field(default=5, ge=1, le=20)
    identity_db_max_overflow: int = Field(default=10, ge=0, le=20)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )
```

### Database Connection Manager

Create a connection manager for the identity database:

```python
# agents/app/services/identity_db.py
"""Identity database connection management."""

from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create engine with appropriate pooling
if "localhost" in settings.identity_database_url:
    # Local development: use connection pooling
    engine = create_engine(
        settings.identity_database_url,
        pool_size=settings.identity_db_pool_size,
        max_overflow=settings.identity_db_max_overflow,
        pool_pre_ping=True
    )
else:
    # Production/Heroku: use NullPool for serverless compatibility
    engine = create_engine(
        settings.identity_database_url,
        poolclass=NullPool,
        connect_args={
            "sslmode": "require",
            "connect_timeout": 30
        }
    )

SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_db():
    """Get database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def test_connection():
    """Test database connectivity."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("Identity database connection successful")
            return True
    except Exception as e:
        logger.error(f"Identity database connection failed: {e}")
        return False
```

### Migration Strategy

We'll use the same pattern as the agents service - SQL migration scripts:

```bash
# Directory structure
agents/
  app/
    migrations/
      001_create_all_tables.sql         # Existing ETL tables
      002_create_daily_ticket_summaries.sql.old  # Old migration
      003_user_identity.sql             # Our new migration (Phase 4.5)
  scripts/
      run_migration.py                  # Enhanced migration runner
```

Note: We use migration number `003` to follow the existing sequence in the agents service.

Enhanced migration runner:

```python
# agents/scripts/run_migration.py
"""Run SQL migrations for identity database."""

import sys
import psycopg2
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration(migration_file: str, database_url: str = None):
    """Run a SQL migration file."""
    db_url = database_url or settings.identity_database_url
    
    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Read migration file
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        # Execute migration
        cur.execute(sql)
        conn.commit()
        
        logger.info(f"Migration {migration_file} completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        migration_file = sys.argv[1]
        database_url = sys.argv[2] if len(sys.argv) > 2 else None
        run_migration(migration_file, database_url)
    else:
        # Run all identity migrations
        run_migration("app/migrations/003_user_identity.sql")
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
"""Test identity database setup."""

import pytest
from app.services.identity_db import test_connection, get_db
from sqlalchemy import text

def test_database_connection():
    """Test we can connect to identity database."""
    assert test_connection() is True

def test_database_tables():
    """Test our tables exist."""
    with get_db() as db:
        # Check users table
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            )
        """))
        assert result.scalar() is True
        
        # Check conversations table
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'conversations'
            )
        """))
        assert result.scalar() is True
```

### Deployment Commands

```bash
# Local Development
make dev                    # Starts all services
python scripts/run_migration.py app/migrations/003_user_identity.sql

# Heroku Production
heroku run python scripts/run_migration.py app/migrations/003_user_identity.sql --app your-app
heroku config:set IDENTITY_DATABASE_URL=$IDENTITY_DATABASE_URL --app your-app
```

## 📋 Phased Implementation Approach

### Phase 4.5.1: Database Setup

**Goal**: Create database schema and test connectivity

#### Step 1: Create Migration File

```sql
-- agents/app/migrations/003_user_identity.sql
BEGIN;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    shop_domain VARCHAR(255) UNIQUE NOT NULL,
    shopify_id VARCHAR(100),
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_users_shop_domain ON users(shop_domain);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Conversations archive
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id),
    merchant_id VARCHAR(100),
    workflow_name VARCHAR(100),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    messages JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_started_at ON conversations(started_at);

-- Events table
CREATE TABLE IF NOT EXISTS events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id),
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

COMMIT;
```

#### Step 2: Run Migration

```bash
# Using the migration script
cd agents
python scripts/run_migration.py app/migrations/003_user_identity.sql

# Or manually via psql
psql -U hirecj -d hirecj_identity -h localhost -p 5435

# Run migration
\i app/migrations/003_user_identity.sql

# Verify tables
\dt
```

#### Step 3: Test Queries

```sql
-- Test user creation
INSERT INTO users (id, shop_domain, email, name) 
VALUES ('usr_test123', 'test.myshopify.com', 'test@example.com', 'Test User');

-- Test conversation archive
INSERT INTO conversations (id, user_id, workflow_name, started_at, messages)
VALUES (
    gen_random_uuid(),
    'usr_test123',
    'shopify_onboarding',
    NOW(),
    '[{"sender": "user", "content": "Hello"}, {"sender": "cj", "content": "Hi there!"}]'::jsonb
);

-- Test event logging
INSERT INTO events (user_id, event_type, event_data)
VALUES ('usr_test123', 'oauth_complete', '{"shop": "test.myshopify.com"}'::jsonb);

-- Verify data
SELECT * FROM users;
SELECT * FROM conversations WHERE user_id = 'usr_test123';
SELECT * FROM events WHERE user_id = 'usr_test123';
```

**✅ Phase 4.5.1 Complete When:**
- [ ] Migration file created
- [ ] Tables created successfully
- [ ] Test data inserts work
- [ ] Indexes are in place

---

### Phase 4.5.2: User ID Generation

**Goal**: Update auth service to create/retrieve user IDs during OAuth

#### Step 1: Update Merchant Storage

```python
# auth/app/services/merchant_storage.py

import hashlib
from typing import Optional, Dict, Any, Tuple

class MerchantStorage:
    """Enhanced with user ID generation."""
    
    def generate_user_id(self, shop_domain: str) -> str:
        """Generate consistent user ID from shop domain."""
        # Use first 8 chars of SHA256 for readable IDs
        hash_obj = hashlib.sha256(shop_domain.encode())
        short_hash = hash_obj.hexdigest()[:8]
        return f"usr_{short_hash}"
    
    def get_or_create_user(self, shop_domain: str) -> Tuple[str, bool]:
        """Get existing user ID or create new one.
        
        Returns:
            Tuple of (user_id, is_new)
        """
        # Check if merchant exists
        merchant = self.get_merchant(shop_domain)
        
        if merchant and merchant.get("user_id"):
            return merchant["user_id"], False
        
        # Generate new user ID
        user_id = self.generate_user_id(shop_domain)
        
        # Update or create merchant with user ID
        if merchant:
            merchant["user_id"] = user_id
            self.update_merchant(shop_domain, merchant)
        else:
            # Will be created later with full data
            pass
            
        return user_id, True
    
    def create_merchant(self, merchant_data: Dict[str, Any]) -> None:
        """Enhanced to include user_id."""
        shop_domain = merchant_data["shop_domain"]
        
        # Ensure user_id is set
        if "user_id" not in merchant_data:
            merchant_data["user_id"] = self.generate_user_id(shop_domain)
        
        # ... rest of existing create_merchant logic ...
        super().create_merchant(merchant_data)
```

#### Step 2: Update OAuth Callback

```python
# auth/app/api/shopify_oauth.py

def store_merchant_token(shop: str, access_token: str) -> Tuple[str, str]:
    """
    Store merchant token and return user info.
    
    Returns:
        Tuple of (merchant_id, user_id)
    """
    # Get or create user ID
    user_id, is_new = merchant_storage.get_or_create_user(shop)
    
    # Check if merchant exists
    merchant = merchant_storage.get_merchant(shop)
    
    if merchant is None:
        # Create new merchant with user ID
        merchant_id = f"merchant_{shop.replace('.myshopify.com', '')}"
        merchant_storage.create_merchant({
            "merchant_id": merchant_id,
            "user_id": user_id,
            "shop_domain": shop,
            "access_token": access_token,
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Log event
        log_user_event(user_id, "user_created", {"shop": shop})
        log_user_event(user_id, "oauth_complete", {"shop": shop, "first_time": True})
        
        logger.info(f"[STORE_TOKEN] Created new merchant: {shop}, user: {user_id}")
        return f"new_{merchant_id}", user_id
    else:
        # Update existing merchant
        merchant_storage.update_token(shop, access_token)
        merchant_id = merchant.get("merchant_id", f"merchant_{shop.replace('.myshopify.com', '')}")
        
        # Log event
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
                INSERT INTO events (user_id, event_type, event_data, created_at)
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

**Goal**: Archive conversations from Redis to PostgreSQL before TTL

#### Step 1: Create Archival Service

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
                    INSERT INTO conversations 
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
                FROM conversations
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
                text("SELECT COUNT(*) as total FROM conversations WHERE user_id = :user_id"),
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
                SELECT * FROM conversations
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
                text("SELECT * FROM users WHERE id = :user_id"),
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
                FROM conversations
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
psql -c "SELECT * FROM users ORDER BY created_at DESC LIMIT 5;"

# Check conversations
psql -c "SELECT id, user_id, workflow_name, started_at FROM conversations ORDER BY started_at DESC LIMIT 5;"

# Check events
psql -c "SELECT user_id, event_type, created_at FROM events ORDER BY created_at DESC LIMIT 10;"

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
DELETE FROM conversations 
WHERE user_id IS NULL 
AND created_at < NOW() - INTERVAL '7 days';

-- Monthly: Analyze tables for query optimization
ANALYZE users;
ANALYZE conversations;
ANALYZE events;

-- Quarterly: Review and archive old events
INSERT INTO events_archive 
SELECT * FROM events 
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

## 🔧 PostgreSQL Integration Summary

### Development Environment

1. **Native PostgreSQL** on port 5435 (avoids conflicts)
2. **Single identity database**: `hirecj_identity`
3. **Environment configuration**: `IDENTITY_DATABASE_URL` in `.env.local`
4. **Connection pooling**: Optimized for local development

### Production Environment (Heroku)

1. **Heroku Postgres add-on**: Automatic provisioning
2. **Environment variable**: `IDENTITY_DATABASE_URL`
3. **Automatic SSL**: Required for production connections
4. **NullPool**: Serverless-friendly connection management

### Key Design Decisions

1. **Separate Database**: Identity data isolated from other services
2. **SQLAlchemy ORM**: Consistent with existing patterns
3. **Migration Strategy**: Sequential SQL scripts (003_user_identity.sql)
4. **Connection Management**: Context managers for safety
5. **Environment Flexibility**: Works seamlessly in both environments

### Quick Start Commands

```bash
# Local Development
createdb -p 5435 hirecj_identity
cd agents && python scripts/run_migration.py app/migrations/003_user_identity.sql

# Heroku Production
heroku addons:create heroku-postgresql:mini --as IDENTITY_DATABASE --app your-app
heroku run python scripts/run_migration.py app/migrations/003_user_identity.sql --app your-app
```

This elegant integration maintains simplicity while providing robust identity persistence across environments.