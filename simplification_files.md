# Files Involved in OAuth Simplification Architecture

## 1. Shared/Centralized Components

### Database Models (Single Source of Truth)
- `/shared/db_models.py` - All centralized database models:
  - `OAuthCSRFState` - OAuth CSRF protection
  - `WebSession` - HTTP cookie-based authentication
  - `Merchant` - Merchant accounts
  - `MerchantIntegration` - Platform integrations (Shopify, etc)
  - `User` - User accounts linked to shops
  - `MerchantToken` - Links users to merchants with OAuth tokens

### Shared Models
- `/shared/models/api.py` - API request/response models (including OAuthHandoffRequest)
- `/shared/models/__init__.py` - Model exports
- `/shared/user_identity.py` - User identity management functions
- `/shared/env_loader.py` - Centralized environment loading

## 2. Auth Service

### API Routes
- `/auth/app/api/shopify_oauth.py` - Main OAuth flow:
  - `/install` endpoint - initiates OAuth
  - `/callback` endpoint - handles OAuth callback
  - Creates User + Merchant + MerchantToken records
  - Redirects with minimal `oauth=complete` parameter

### Services
- `/auth/app/services/merchant_storage.py` - Stores merchant data and tokens
- `/auth/app/services/session_cookie.py` - Issues HTTP session cookies
- `/auth/app/services/shopify_auth.py` - Shopify OAuth utilities

### Configuration
- `/auth/app/config.py` - Auth service configuration
- `/auth/app/utils/database.py` - Database connection utilities

### Removed Files
- `/auth/app/models/db.py` - ❌ REMOVED (using shared models)

## 3. Agents Service

### WebSocket/Platform Handlers
- `/agents/app/platforms/web/websocket_handler.py` - WebSocket connection management:
  - Reads session cookie to get user_id
  - Creates conversation IDs based on user/session
  
- `/agents/app/platforms/web/session_handlers.py` - Session message handling:
  - `handle_start_conversation` - Main entry point
  - Queries MerchantToken to find user's merchants
  - Determines workflow based on OAuth recency
  - No longer uses post_oauth_handler

- `/agents/app/platforms/web/message_handlers.py` - Routes messages to handlers
- `/agents/app/platforms/web/session_handler.py` - Creates conversation sessions
- `/agents/app/platforms/web/workflow_handlers.py` - Workflow-specific logic

### API Routes
- `/agents/app/api/routes/internal.py` - Now empty (OAuth endpoint removed)

### Database/Migrations
- `/agents/app/migrations/010_create_merchant_tokens.sql` - Creates merchant_tokens table
- `/agents/app/utils/supabase_util.py` - Database connection utilities

### Configuration
- `/agents/app/config.py` - Agents service configuration

### Removed Files
- `/agents/app/services/post_oauth_handler.py` - ❌ REMOVED
- `/agents/app/platforms/web/oauth_handler.py` - ❌ REMOVED

## 4. Frontend (Homepage)

### React Components
- `/homepage/src/pages/SlackChat.tsx`:
  - No longer parses merchantId/scenario from URL
  - Sends empty data in start_conversation
  - Handles `oauth=complete` redirect

- `/homepage/src/hooks/useWebSocketChat.ts`:
  - Connects to `/ws/chat` (no conversation_id in URL)
  - Sends minimal `start_conversation` with empty data
  - Server determines everything

- `/homepage/src/hooks/useUserSession.ts` - Client-side user session management
- `/homepage/src/components/ShopifyOAuthButton.tsx` - OAuth initiation button

### Constants
- `/homepage/src/constants/workflow.ts` - Workflow type definitions

## 5. Migration Scripts

### Run Scripts
- `/agents/scripts/run_migration.py` - Main migration runner

### Migration Files
- `/agents/app/migrations/001_create_all_tables.sql` - Base tables
- `/agents/app/migrations/003_user_identity.sql` - Users table
- `/agents/app/migrations/007_create_oauth_tables.sql` - OAuth CSRF state
- `/agents/app/migrations/008_create_web_sessions.sql` - Web sessions
- `/agents/app/migrations/010_create_merchant_tokens.sql` - Merchant tokens

## 6. Documentation

- `/CLAUDE.md` - Project-wide instructions
- `/agents/CLAUDE.md` - Agents service specific instructions
- `/auth/CLAUDE.md` - Auth service specific instructions

## Summary of Changes

### Before (Complex)
- URL parameters: `merchantId`, `scenario`, `workflow`, `conversation_id`
- Cross-service API calls for OAuth completion
- Complex state management with post_oauth_handler
- Multiple sources of truth

### After (Simple)
- URL parameter: just `oauth=complete`
- No cross-service notifications
- Server determines everything from database
- Single source of truth (centralized database)

### Key Principles Applied
1. **Backend-Driven**: Server determines workflow/merchant from database
2. **Single Source of Truth**: All models in `/shared/db_models.py`
3. **Simplify**: Removed unnecessary parameters and cross-service calls
4. **No Over-Engineering**: Direct database queries instead of complex state management