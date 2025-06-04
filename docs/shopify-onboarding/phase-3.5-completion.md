# Phase 3.5: Completion Checklist

## 🚨 Current Status: FAILURE

This implementation violates our North Star principles and must be completed properly.

## ✅ Definition of Success

According to our North Stars, success is NOT just making it work. Success is:
- **Elegant** and complete solution
- **No shortcuts** or mocked implementations
- **No half-measures** or disabled features
- **No compatibility shims** or dead code
- **Production-ready**, not "good enough"

## 📋 Completion Tasks

### 🔥 Priority 1: Delete Dead Code (30 minutes)

#### Delete OAuth Files
```bash
# From project root
rm -f auth/app/api/oauth.py
rm -rf auth/app/providers/
rm -f auth/tests/test_oauth.py  # if exists
```

#### Clean up main.py
```python
# Remove these lines from auth/app/main.py:
# from app.api import oauth
# # app.include_router(oauth.router, prefix=f"{settings.api_prefix}/oauth")
```

#### Verification
- [ ] `find . -name "*oauth*" -type f | grep -v shopify_custom` returns no auth service files
- [ ] No commented code remains in `main.py`
- [ ] Git shows these files as deleted, not modified

### 🔧 Priority 2: Fix Magic Numbers (1 hour)

#### Create shared/constants.py
```python
"""Shared constants for HireCJ monorepo."""

# Shopify Custom App Installation
SHOPIFY_INSTALL_POLL_INTERVAL_MS = 2000  # 2 seconds
SHOPIFY_INSTALL_TIMEOUT_MS = 600000      # 10 minutes
SHOPIFY_SESSION_EXPIRE_MINUTES = 30      # 30 minutes

# Redis TTLs
REDIS_INSTALL_SESSION_TTL = 1800  # 30 minutes in seconds
REDIS_MERCHANT_SESSION_TTL = 86400  # 24 hours in seconds
```

#### Update Frontend
```typescript
// homepage/src/constants/shopify.ts
export const SHOPIFY_INSTALL_POLL_INTERVAL = 2000;  // 2 seconds
export const SHOPIFY_INSTALL_TIMEOUT = 600000;      // 10 minutes
```

#### Update Usage
- [ ] Replace `2000` with constant in ShopifyOAuthButton.tsx
- [ ] Replace `10 * 60 * 1000` with constant
- [ ] Replace `timedelta(minutes=30)` with constant in backend

### 🔐 Priority 3: Real Session Token Handling (4 hours)

#### Install Dependencies
```bash
# Backend
pip install pyjwt[crypto] httpx

# Frontend
npm install @shopify/app-bridge @shopify/app-bridge-utils
```

#### Implement JWT Verification
```python
# auth/app/services/shopify_jwt.py
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ShopifyJWTVerifier:
    def __init__(self):
        self._public_key = None
        self._last_fetch = None
    
    async def get_public_key(self) -> str:
        """Fetch Shopify's public key for JWT verification."""
        # Cache for 24 hours
        if self._public_key and self._last_fetch:
            # Implementation here
            pass
        
        # Fetch from Shopify
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://shopify.com/.well-known/jwks.json"
            )
            # Parse and cache the key
            # Return PEM format
    
    async def verify_session_token(self, token: str) -> dict:
        """Verify and decode Shopify session token."""
        public_key = await self.get_public_key()
        
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=settings.shopify_client_id,
                issuer="https://shopify.com"
            )
            return payload
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid session token: {e}")
            raise
```

#### Frontend Session Token
```typescript
// homepage/src/hooks/useShopifySession.ts
import { getSessionToken } from '@shopify/app-bridge-utils';
import { createApp } from '@shopify/app-bridge';

export const useShopifySession = () => {
  const getToken = async () => {
    const app = createApp({
      apiKey: import.meta.env.VITE_SHOPIFY_CLIENT_ID,
    });
    
    const token = await getSessionToken(app);
    return token;
  };
  
  return { getToken };
};
```

### 💱 Priority 4: Real Token Exchange (3 hours)

#### Research Required
- [ ] Read Shopify's token exchange documentation
- [ ] Understand offline vs online access tokens
- [ ] Determine scopes needed

#### Implement Token Exchange
```python
# auth/app/services/shopify_token_exchange.py
class ShopifyTokenExchange:
    async def exchange_session_token(
        self, 
        session_token: str,
        shop_domain: str
    ) -> str:
        """Exchange session token for API access token."""
        async with httpx.AsyncClient() as client:
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
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Token exchange failed: {response.text}"
                )
            
            data = response.json()
            return data["access_token"]
```

### 🗄️ Priority 5: Proper Storage (2 hours)

#### Add Redis to docker-compose.yml
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

#### Update .env
```bash
# Root .env
REDIS_URL=redis://localhost:6379/0
```

#### Implement Redis Storage
```python
# auth/app/services/session_storage.py
import redis
import json
from typing import Optional
from datetime import datetime

class SessionStorage:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def store_install_session(
        self, 
        session_id: str, 
        data: dict,
        ttl: int = REDIS_INSTALL_SESSION_TTL
    ):
        """Store installation session with TTL."""
        self.redis.setex(
            f"install:{session_id}",
            ttl,
            json.dumps(data)
        )
    
    async def get_install_session(
        self, 
        session_id: str
    ) -> Optional[dict]:
        """Retrieve installation session."""
        data = self.redis.get(f"install:{session_id}")
        return json.loads(data) if data else None
    
    async def store_merchant_session(
        self,
        shop_domain: str,
        data: dict,
        ttl: int = REDIS_MERCHANT_SESSION_TTL
    ):
        """Store merchant session with TTL."""
        self.redis.setex(
            f"merchant:{shop_domain}",
            ttl,
            json.dumps(data)
        )
```

### 🧪 Priority 6: Testing (2 hours)

#### Unit Tests
- [ ] Test JWT verification with real Shopify tokens
- [ ] Test token exchange with mocked HTTP calls
- [ ] Test Redis storage with test Redis instance
- [ ] Test error handling for all edge cases

#### Integration Tests
- [ ] Full flow test with real Shopify test store
- [ ] Test session expiry handling
- [ ] Test concurrent installations
- [ ] Test Redis failure recovery

## 📊 Completion Metrics

| Task | Time Est | Status | Blocker |
|------|----------|--------|---------|
| Delete OAuth Code | 30 min | ⬜ | None |
| Fix Magic Numbers | 1 hr | ⬜ | None |
| Session Token Handling | 4 hrs | ⬜ | Need Shopify App Bridge docs |
| Token Exchange | 3 hrs | ⬜ | Need API documentation |
| Redis Storage | 2 hrs | ⬜ | None |
| Testing | 2 hrs | ⬜ | Depends on above |

**Total: ~12.5 hours**

## 🎯 Success Criteria

- [ ] `grep -r "mock-session-token" .` returns no results
- [ ] `grep -r "verify_signature.*False" .` returns no results
- [ ] `grep -r "2000\|600000" .` returns no results (except in constants)
- [ ] OAuth files completely deleted from git history
- [ ] All tests pass with real implementations
- [ ] Code review shows no "TODO" or "FIXME" comments
- [ ] Production deployment checklist complete

## 🚀 Only After ALL Checkboxes Are Checked

Then and only then can Phase 3.5 be marked as COMPLETE and meet our North Star standards.