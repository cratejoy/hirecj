"""OAuth API routes for Shopify authentication."""

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config import settings
from app.providers.shopify import ShopifyProvider

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory state storage for demo
# In production, use Redis or database
_oauth_states = {}
_merchant_sessions = {}  # shop_domain -> merchant_info


class OAuthState(BaseModel):
    """OAuth state data."""
    conversation_id: str
    redirect_uri: str
    created_at: datetime
    
    def is_expired(self) -> bool:
        """Check if state is expired (10 minutes)."""
        return datetime.utcnow() - self.created_at > timedelta(minutes=10)


class MerchantSession(BaseModel):
    """Merchant session data."""
    merchant_id: str
    shop_domain: str
    shop_name: str
    owner_email: str
    created_at: datetime
    last_seen: datetime
    access_token: str
    

@router.get("/shopify/authorize")
async def shopify_authorize(
    conversation_id: str = Query(..., description="Conversation ID to link with OAuth"),
    redirect_uri: str = Query(..., description="Frontend redirect URI"),
    shop: Optional[str] = Query(None, description="Shopify shop domain")
):
    """
    Initiate Shopify OAuth flow.
    
    If shop domain is not provided, show a shop entry form.
    """
    if not shop:
        # TODO: Return HTML form for shop entry
        # For now, return error
        raise HTTPException(
            status_code=400,
            detail="Shop domain required. Add ?shop=yourshop to the URL"
        )
    
    # Generate secure state
    state = secrets.token_urlsafe(32)
    
    # Store state data
    _oauth_states[state] = OAuthState(
        conversation_id=conversation_id,
        redirect_uri=redirect_uri,
        created_at=datetime.utcnow()
    )
    
    # Clean expired states
    expired_states = [k for k, v in _oauth_states.items() if v.is_expired()]
    for k in expired_states:
        del _oauth_states[k]
    
    # Get Shopify authorization URL
    provider = ShopifyProvider()
    auth_url = await provider.get_authorization_url(
        redirect_uri=f"{settings.oauth_redirect_base_url}/api/v1/oauth/shopify/callback",
        state=state,
        shop=shop
    )
    
    logger.info(f"[OAUTH_START] Starting OAuth for shop={shop}, conversation={conversation_id}")
    
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/shopify/callback")
async def shopify_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    shop: str = Query(..., description="Shop domain"),
    hmac: str = Query(None, alias="hmac", description="HMAC signature"),
    timestamp: str = Query(None, description="Timestamp")
):
    """
    Handle Shopify OAuth callback.
    
    This endpoint:
    1. Validates the state parameter
    2. Exchanges code for access token
    3. Fetches shop info
    4. Determines if merchant is new or returning
    5. Redirects back to frontend with results
    """
    # Validate state
    state_data = _oauth_states.get(state)
    if not state_data:
        logger.error(f"[OAUTH_CALLBACK] Invalid state: {state}")
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    if state_data.is_expired():
        del _oauth_states[state]
        logger.error(f"[OAUTH_CALLBACK] Expired state: {state}")
        raise HTTPException(status_code=400, detail="State parameter expired")
    
    # Clean up state
    del _oauth_states[state]
    
    # TODO: Validate HMAC signature for security
    # For now, we'll skip this in development
    
    try:
        # Exchange code for token
        provider = ShopifyProvider()
        token = await provider.exchange_code_for_token(
            code=code,
            redirect_uri=f"{settings.oauth_redirect_base_url}/api/v1/oauth/shopify/callback",
            shop=shop
        )
        
        # Get shop info
        # TODO: This needs shop domain in token - fix provider
        # For now, create mock data
        shop_info = {
            "id": hashlib.md5(shop.encode()).hexdigest()[:12],
            "email": f"owner@{shop}",
            "name": f"Owner of {shop}",
            "shop_name": shop.replace(".myshopify.com", "").replace("-", " ").title(),
            "shop_domain": shop
        }
        
        # Check if merchant is new or returning
        is_new = shop not in _merchant_sessions
        
        # Create/update merchant session
        merchant_id = f"merchant_{shop_info['id']}"
        _merchant_sessions[shop] = MerchantSession(
            merchant_id=merchant_id,
            shop_domain=shop,
            shop_name=shop_info["shop_name"],
            owner_email=shop_info["email"],
            created_at=datetime.utcnow() if is_new else _merchant_sessions.get(shop, {}).get("created_at", datetime.utcnow()),
            last_seen=datetime.utcnow(),
            access_token=token.access_token
        )
        
        logger.info(f"[OAUTH_SUCCESS] OAuth completed for shop={shop}, is_new={is_new}, merchant_id={merchant_id}")
        
        # Build redirect URL with parameters
        redirect_params = {
            "oauth": "complete",
            "conversation_id": state_data.conversation_id,
            "is_new": str(is_new).lower(),
            "merchant_id": merchant_id,
            "shop": shop
        }
        
        redirect_url = f"{state_data.redirect_uri}?{urlencode(redirect_params)}"
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        logger.error(f"[OAUTH_ERROR] OAuth failed for shop={shop}: {str(e)}")
        
        # Redirect with error
        error_params = {
            "oauth": "error",
            "conversation_id": state_data.conversation_id,
            "error": str(e)
        }
        
        error_url = f"{state_data.redirect_uri}?{urlencode(error_params)}"
        
        return RedirectResponse(url=error_url, status_code=302)


@router.get("/shopify/status/{shop_domain}")
async def check_merchant_status(shop_domain: str):
    """
    Check if a merchant has authenticated before.
    
    This is used to determine if we should show "Welcome back" messaging.
    """
    is_authenticated = shop_domain in _merchant_sessions
    
    if is_authenticated:
        session = _merchant_sessions[shop_domain]
        return {
            "authenticated": True,
            "merchant_id": session.merchant_id,
            "shop_name": session.shop_name,
            "last_seen": session.last_seen.isoformat()
        }
    else:
        return {
            "authenticated": False
        }