# Phase 3.5: Shopify Custom App Flow - Complete Documentation

## 📋 Table of Contents
1. [Problem Statement](#problem-statement)
2. [Solution Design](#solution-design)
3. [What Was Implemented](#what-was-implemented)
4. [Audit Findings](#audit-findings)
5. [What Still Needs to Be Done](#what-still-needs-to-be-done)
6. [Testing Guide](#testing-guide)
7. [Success Criteria](#success-criteria)

---

## 🎯 Problem Statement

We're using Shopify custom apps, which don't support standard OAuth flow. The current OAuth implementation causes "Unauthorized Access" errors because:
- Custom apps use a pre-approved install link
- They require session token authentication
- Standard OAuth `/authorize` endpoint doesn't work

**User Experience**: When merchants try to connect, they get an error instead of being able to install the app.

## 💡 Solution Design

Replace the broken OAuth flow entirely with Shopify's custom app flow:

```
Custom App Flow:
├── Frontend opens custom install link
├── Merchant installs app in Shopify
├── Backend validates session token (JWT)
└── Exchange session token for API access token
```

### Benefits
- Simpler: No shop domain input needed
- Works: Uses Shopify's intended flow for custom apps
- Better UX: One click to connect

---

## ✅ What Was Implemented

### 1. Environment Configuration
**File**: `auth/app/config.py`
```python
shopify_custom_install_link: Optional[str] = Field(None, env="SHOPIFY_CUSTOM_INSTALL_LINK")
```
- ✅ Added configuration for custom install link
- ✅ Updated `.env.secrets` with actual link

### 2. Backend Endpoints
**File**: `auth/app/api/shopify_custom.py`

Created new endpoints:
- ✅ `POST /api/v1/shopify/install` - Returns custom install link
- ✅ `POST /api/v1/shopify/verify` - Validates session token
- ✅ `GET /api/v1/shopify/status/{session_id}` - Check installation status
- ✅ `GET /api/v1/shopify/merchant/{shop_domain}` - Check merchant status

**Note**: OAuth endpoints were commented out (not deleted) in `main.py`

### 3. Frontend Changes
**File**: `homepage/src/components/ShopifyOAuthButton.tsx`
- ✅ Removed shop domain input dialog
- ✅ Opens custom install link directly
- ✅ Polls for installation completion
- ✅ Redirects back to chat on success

### 4. UI Improvements
- ✅ Added Shopify brand colors to Tailwind
- ✅ Button shows "Connecting..." during process
- ✅ Error messages displayed to user

---

## 🚨 Audit Findings

### Current Status: **FAILURE by North Star Standards**

According to our principles:
- ❌ **Shortcuts = FAILURE** (mocked session tokens)
- ❌ **Half-measures = FAILURE** (disabled JWT verification)
- ❌ **Compatibility shims = FAILURE** (kept OAuth code)
- ❌ **"Good enough" = FAILURE** (demo quality, not production)

### North Star Violations

| Principle | Score | Violation |
|-----------|-------|-----------|
| **Simplify** | ✅ 9/10 | Good - much simpler flow |
| **No Cruft** | ❌ 4/10 | OAuth code still exists (6KB dead code) |
| **Break It & Fix It Right** | ❌ 5/10 | Mocked tokens, disabled security |
| **Long-term Elegance** | ❌ 3/10 | In-memory storage won't scale |
| **Backend-Driven** | ✅ 10/10 | Good separation of concerns |
| **Single Source of Truth** | ⚠️ 6/10 | Two auth patterns coexist |
| **No Over-Engineering** | ✅ 9/10 | Simple implementation |
| **Thoughtful Logging** | ✅ 8/10 | Good structured logging |

### Specific Issues Found

#### 1. Dead Code Not Deleted
```python
# auth/app/main.py
# app.include_router(oauth.router, prefix=f"{settings.api_prefix}/oauth")  # COMMENTED, NOT DELETED
```
- `auth/app/api/oauth.py` - 6,984 bytes of unused code
- `auth/app/providers/` - entire directory still exists

#### 2. Security Bypassed
```python
# auth/app/api/shopify_custom.py
payload = jwt.decode(
    request.session_token, 
    options={"verify_signature": False}  # TODO: Implement proper verification
)
```

#### 3. Mocked Implementation
```typescript
// homepage/src/components/ShopifyOAuthButton.tsx
const sessionToken = 'mock-session-token'; // TODO: Get real session token
```

#### 4. Magic Numbers
```typescript
}, 2000); // Poll every 2 seconds - SHOULD BE CONSTANT
}, 10 * 60 * 1000); // 10 minutes timeout - SHOULD BE CONSTANT
```

#### 5. In-Memory Storage
```python
# Will lose all sessions on restart!
_merchant_sessions = {}  # shop_domain -> merchant_info
_install_sessions = {}   # session_id -> install_info
```

---

## 🔧 What Still Needs to Be Done

### ✅ Priority 1: Delete Dead Code (30 minutes) - COMPLETE

```bash
# Delete these files completely
rm -f auth/app/api/oauth.py
rm -rf auth/app/providers/
rm -f auth/tests/test_oauth.py

# Remove from auth/app/main.py:
# - from app.api import oauth
# - # app.include_router(oauth.router, prefix=f"{settings.api_prefix}/oauth")
```

**✅ COMPLETED:**
- Deleted `auth/app/api/oauth.py` (OAuth API endpoints)
- Deleted `auth/app/models/oauth.py` (OAuth models)
- Deleted `auth/app/providers/` directory (OAuth provider implementations)
- Cleaned up `auth/app/main.py` (removed OAuth imports and references)

### ✅ Priority 2: Fix Magic Numbers (1 hour) - COMPLETE

Create `shared/constants.py`:
```python
# Shopify Custom App Installation
SHOPIFY_INSTALL_POLL_INTERVAL_MS = 2000  # 2 seconds
SHOPIFY_INSTALL_TIMEOUT_MS = 600000      # 10 minutes
SHOPIFY_SESSION_EXPIRE_MINUTES = 30

# Redis TTLs
REDIS_INSTALL_SESSION_TTL = 1800   # 30 minutes
REDIS_MERCHANT_SESSION_TTL = 86400 # 24 hours
```

Create `homepage/src/constants/shopify.ts`:
```typescript
export const SHOPIFY_INSTALL_POLL_INTERVAL = 2000;
export const SHOPIFY_INSTALL_TIMEOUT = 600000;
```

**✅ COMPLETED:**
- Created `shared/constants.py` with all backend constants
- Created `homepage/src/constants/shopify.ts` with frontend constants
- Updated `ShopifyOAuthButton.tsx` to use `SHOPIFY_INSTALL_POLL_INTERVAL` and `SHOPIFY_INSTALL_TIMEOUT`
- Updated `auth/app/api/shopify_custom.py` to use `SHOPIFY_SESSION_EXPIRE_MINUTES`
- Verified no magic numbers remain in codebase

### 🔐 Priority 3: Real Session Token Handling (4 hours)

#### Install Dependencies
```bash
pip install pyjwt[crypto] httpx
npm install @shopify/app-bridge @shopify/app-bridge-utils
```

#### Implement JWT Verification
Create `auth/app/services/shopify_jwt.py`:
```python
class ShopifyJWTVerifier:
    async def verify_session_token(self, token: str) -> dict:
        """Verify and decode Shopify session token."""
        public_key = await self.get_public_key()
        
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.shopify_client_id,
            issuer="https://shopify.com"
        )
        return payload
```

#### Get Real Session Tokens
Update frontend to use Shopify App Bridge:
```typescript
import { getSessionToken } from '@shopify/app-bridge-utils';

const sessionToken = await getSessionToken(app);
```

### 💱 Priority 4: Real Token Exchange (3 hours)

Implement actual Shopify API call:
```python
async def exchange_session_token(self, session_token: str, shop_domain: str) -> str:
    """Exchange session token for API access token."""
    response = await client.post(
        f"https://{shop_domain}/admin/oauth/access_token",
        json={
            "client_id": settings.shopify_client_id,
            "client_secret": settings.shopify_client_secret,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": session_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
            "requested_token_type": "urn:shopify:params:oauth:token-type:offline-access-token",
        }
    )
    return response.json()["access_token"]
```

### 🗄️ Priority 5: Proper Storage (2 hours)

Add Redis:
```python
# auth/app/services/session_storage.py
class SessionStorage:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def store_install_session(self, session_id: str, data: dict):
        self.redis.setex(
            f"install:{session_id}",
            REDIS_INSTALL_SESSION_TTL,
            json.dumps(data)
        )
```

### 🧪 Priority 6: Testing (2 hours)

Write tests for:
- JWT verification with real tokens
- Token exchange with mocked HTTP
- Redis storage with test instance
- Error handling edge cases

**Total Time: ~12.5 hours**

---

## 🧪 Testing Guide

### Pre-Testing Checklist
```bash
# Verify custom install link is configured
grep SHOPIFY_CUSTOM_INSTALL_LINK auth/.env.secrets
```

### Manual Testing Steps

1. **Start Services**
   ```bash
   # Terminal 1: Auth service
   cd auth && make dev
   
   # Terminal 2: Agents service  
   cd agents && make dev
   
   # Terminal 3: Homepage
   cd homepage && npm run dev
   ```

2. **Test Installation**
   - Navigate to https://amir.hirecj.ai
   - Click "Connect Shopify" (no dialog should appear)
   - Popup opens with Shopify install page
   - Click "Install app"
   - Popup closes automatically
   - Redirected to chat with parameters

3. **Verify URL Parameters**
   - `oauth=complete`
   - `is_new=true/false`
   - `merchant_id=merchant_xxx`
   - `shop=store.myshopify.com`

### Expected Logs

Auth Service:
```
[CUSTOM_INSTALL] Starting custom app installation for conversation=xxx
[CUSTOM_INSTALL_SUCCESS] Custom app installed for shop=xxx, is_new=true
```

Frontend Console:
- Polling requests every 2 seconds
- No CORS errors
- Successful verification

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Custom app install link not configured" | Missing env var | Add to auth/.env.secrets |
| Popup blocked | Browser settings | Allow popups |
| Installation timeout | Link expired | Get new link from Shopify |
| "Session not found" | Waited too long | Try again quickly |

---

## ✅ Success Criteria

### Definition of Done
- [ ] Zero OAuth code remains in codebase
- [ ] No mocked implementations (`grep -r "mock-session-token"` returns nothing)
- [ ] No disabled security (`grep -r "verify_signature.*False"` returns nothing)
- [ ] No magic numbers (except in constants file)
- [ ] Proper Redis storage implemented
- [ ] All tests pass
- [ ] Production deployment checklist complete

### Verification Commands
```bash
# No mock tokens
grep -r "mock-session-token" . --exclude-dir=node_modules

# No disabled verification
grep -r "verify_signature.*False" . --exclude-dir=node_modules

# No magic numbers
grep -r "2000\|600000" . --exclude-dir=node_modules --exclude=constants

# OAuth files deleted
find . -name "*oauth*" -type f | grep -v shopify_custom
```

---

## 📊 Summary

**Current State**: Working demo with serious production issues
**Required State**: Production-ready implementation
**Effort Required**: 11 hours remaining (Priorities 1-2 complete)
**Blocker**: Need Shopify App Bridge documentation and API details

### Progress Update
- ✅ **Priority 1: Delete Dead Code** - COMPLETE
  - All OAuth code deleted (no commented code, no cruft)
  - Aligns with "No Cruft" North Star principle
- ✅ **Priority 2: Fix Magic Numbers** - COMPLETE
  - Created shared constants files for both backend and frontend
  - All hardcoded values replaced with named constants
  - Aligns with "No Magic Values" operational guideline

This consolidates all Phase 3.5 documentation into one place, providing a complete picture of where we are and where we need to be.