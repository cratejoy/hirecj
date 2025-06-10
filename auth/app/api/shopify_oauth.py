"""Shopify OAuth API routes with full security implementation."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx
import redis
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from urllib.parse import urlencode

from app.config import settings
from app.services.merchant_storage import merchant_storage
from app.services.shopify_auth import shopify_auth
from shared.user_identity import get_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter()

try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    redis_client.ping()
    logger.info("Successfully connected to Redis for OAuth state management.")
except Exception as e:
    logger.error(f"Failed to connect to Redis for OAuth state management: {e}")
    # This is a critical failure for OAuth, so we can't proceed.
    # A middleware or dependency injection would be better to handle this.
    # For now, we'll let it fail at runtime if Redis is needed.
    redis_client = None

# Redis keys
STATE_PREFIX = "oauth_state:"
STATE_TTL = 600  # 10 minutes

# Constants
SHOPIFY_API_VERSION = "2025-01"


@router.get("/debug-config")
async def debug_oauth_config():
    """Debug endpoint to check OAuth configuration."""
    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/shopify/callback"
    
    return {
        "oauth_redirect_base_url": settings.oauth_redirect_base_url,
        "computed_redirect_uri": redirect_uri,
        "redirect_uri_length": len(redirect_uri),
        "client_id": settings.shopify_client_id,
        "scopes": settings.shopify_scopes,
        "shopify_config_instructions": {
            "app_url": f"{settings.oauth_redirect_base_url}/api/v1/shopify/install",
            "allowed_redirect_url": redirect_uri,
            "note": "Copy the 'allowed_redirect_url' value exactly into your Shopify app settings"
        }
    }


@router.get("/install")
async def initiate_oauth(
    shop: Optional[str] = Query(None, description="Shop domain"),
    hmac: Optional[str] = Query(None, description="HMAC for verification"),
    timestamp: Optional[str] = Query(None, description="Request timestamp")
):
    """
    Initiate OAuth flow by redirecting to Shopify authorization page.
    
    This endpoint is called in two scenarios:
    1. Initial app installation (from Shopify with HMAC)
    2. Re-authorization (from our frontend)
    """
    # For frontend requests, shop might be in different param
    if not shop:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing shop parameter"}
        )
    
    logger.info(f"[OAUTH_INSTALL] Initiating OAuth for shop: {shop}")
    logger.info(f"[OAUTH_INSTALL] Frontend URL configured as: {settings.frontend_url}")
    logger.info(f"[OAUTH_INSTALL] OAuth redirect base: {settings.oauth_redirect_base_url}")
    
    # Check if Shopify credentials are configured
    if not settings.shopify_client_id or not settings.shopify_client_secret:
        logger.error("[OAUTH_INSTALL] Shopify credentials not configured!")
        logger.error(f"[OAUTH_INSTALL] Will redirect to: {settings.frontend_url}/chat?error=shopify_not_configured")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=shopify_not_configured",
            status_code=302
        )
    
    # Validate shop domain
    if not shopify_auth.validate_shop_domain(shop):
        logger.error(f"[OAUTH_INSTALL] Invalid shop domain: {shop}")
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid shop domain format"}
        )
    
    # If HMAC provided, verify it (initial install from Shopify)
    if hmac:
        params = {"shop": shop, "hmac": hmac}
        if timestamp:
            params["timestamp"] = timestamp
            
        if not shopify_auth.verify_hmac(params.copy()):
            logger.error(f"[OAUTH_INSTALL] Invalid HMAC for shop: {shop}")
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid HMAC signature"}
            )
    
    # Generate and store state
    state = shopify_auth.generate_state()
    state_key = f"{STATE_PREFIX}{state}"
    
    # Store state with shop domain in Redis
    try:
        if not redis_client:
            raise ConnectionError("Redis client not available")
        redis_client.setex(
            state_key,
            STATE_TTL,
            shop
        )
    except Exception as e:
        logger.error(f"[OAUTH_INSTALL] Failed to store state in Redis: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to initialize OAuth flow"}
        )
    
    logger.info(f"[OAUTH_INSTALL] Generated state for shop {shop}: {state[:10]}...")
    
    # Build authorization URL
    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/shopify/callback"
    
    # Log exact redirect URI for debugging
    logger.info(f"[OAUTH_INSTALL] Building auth with redirect_uri: '{redirect_uri}'")
    logger.info(f"[OAUTH_INSTALL] Redirect URI length: {len(redirect_uri)} chars")
    logger.info(f"[OAUTH_INSTALL] Redirect URI encoded: {redirect_uri.encode('utf-8').hex()}")
    
    # Sanity check the expected redirect URI
    expected_uri = "https://amir-auth.hirecj.ai/api/v1/shopify/callback"
    if redirect_uri != expected_uri:
        logger.warning(f"[OAUTH_INSTALL] MISMATCH! Expected: '{expected_uri}', Got: '{redirect_uri}'")
    
    auth_url = shopify_auth.build_auth_url(shop, state, redirect_uri)
    
    logger.info(f"[OAUTH_INSTALL] Redirecting shop {shop} to authorization")
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def handle_oauth_callback(
    code: Optional[str] = Query(None, description="Authorization code"),
    shop: str = Query(..., description="Shop domain"),
    hmac: str = Query(..., description="HMAC for verification"),
    state: Optional[str] = Query(None, description="State for CSRF protection"),
    timestamp: str = Query(..., description="Request timestamp"),
    host: Optional[str] = Query(None, description="Base64 encoded host")
):
    """
    Handle OAuth callback from Shopify with authorization code.
    Exchange code for access token and store it.
    """
    logger.info(f"[OAUTH_CALLBACK] Received callback for shop: {shop}")
    
    # Build params dict for HMAC verification
    params = {
        "shop": shop,
        "hmac": hmac,
        "timestamp": timestamp
    }
    if code:
        params["code"] = code
    if state:
        params["state"] = state
    if host:
        params["host"] = host
    
    # Verify HMAC
    if not shopify_auth.verify_hmac(params.copy()):
        logger.error(f"[OAUTH_CALLBACK] Invalid HMAC for shop: {shop}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=invalid_hmac",
            status_code=302
        )
    
    # Verify state if provided
    if state:
        state_key = f"{STATE_PREFIX}{state}"
        try:
            if not redis_client:
                raise ConnectionError("Redis client not available")
            stored_shop = redis_client.get(state_key)
            
            if not stored_shop or stored_shop != shop:
                logger.error(f"[OAUTH_CALLBACK] Invalid state for shop: {shop}")
                return RedirectResponse(
                    url=f"{settings.frontend_url}/chat?error=invalid_state",
                    status_code=302
                )
            
            # Delete used state
            redis_client.delete(state_key)
        except Exception as e:
            logger.error(f"[OAUTH_CALLBACK] Failed to verify state: {e}")
            return RedirectResponse(
                url=f"{settings.frontend_url}/chat?error=state_verification_failed",
                status_code=302
            )
    
    # Check if we have authorization code
    if not code:
        logger.error(f"[OAUTH_CALLBACK] Missing authorization code for shop: {shop}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=missing_code",
            status_code=302
        )
    
    # Exchange code for access token
    try:
        access_token, scopes = await exchange_code_for_token(shop, code)
        
        if not access_token:
            return RedirectResponse(
                url=f"{settings.frontend_url}/chat?error=token_exchange_failed",
                status_code=302
            )
        
        # Store merchant data
        store_result = store_merchant_token(shop, access_token, scopes)
        merchant_id = store_result["merchant_id"]
        is_new = store_result["is_new"]
        
        # Create or get user identity
        try:
            user_id, user_is_new = get_or_create_user(shop)
            logger.info(f"[OAUTH_CALLBACK] User identity: {user_id}, is_new: {user_is_new}")
        except Exception as e:
            logger.error(f"[OAUTH_CALLBACK] Failed to get/create user identity: {e}")
        
        logger.info(f"[OAUTH_CALLBACK] Successfully authenticated shop: {shop}, is_new: {is_new}")
        
        # Redirect to frontend with success
        redirect_params = {
            "oauth": "complete",
            "is_new": str(is_new).lower(),
            "merchant_id": merchant_id,
            "shop": shop
        }
        
        redirect_url = f"{settings.frontend_url}/chat?{urlencode(redirect_params)}"
        logger.info(f"[OAUTH_CALLBACK] Redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        import traceback
        logger.error(f"[OAUTH_CALLBACK] Unexpected error: {e}")
        logger.error(f"[OAUTH_CALLBACK] Traceback: {traceback.format_exc()}")
        logger.error(f"[OAUTH_CALLBACK] Will redirect to: {settings.frontend_url}/chat?error=internal_error")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=internal_error",
            status_code=302
        )


async def exchange_code_for_token(shop: str, code: str) -> Optional[tuple[str, str]]:
    """
    Exchange authorization code for access token.
    
    Args:
        shop: Shop domain
        code: Authorization code from Shopify
        
    Returns:
        Tuple of (access token, scopes) if successful, None otherwise
    """
    # Check if Shopify credentials are configured
    if not settings.shopify_client_id or not settings.shopify_client_secret:
        logger.error("[TOKEN_EXCHANGE] Shopify credentials not configured!")
        logger.error(f"[TOKEN_EXCHANGE] Client ID present: {bool(settings.shopify_client_id)}")
        logger.error(f"[TOKEN_EXCHANGE] Client Secret present: {bool(settings.shopify_client_secret)}")
        return None, None
    
    token_url = f"https://{shop}/admin/oauth/access_token"
    
    # Build the same redirect URI that was used in the authorization request
    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/shopify/callback"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": settings.shopify_client_id,
                    "client_secret": settings.shopify_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri  # Include redirect_uri to match auth request
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                logger.error(
                    f"[TOKEN_EXCHANGE] Failed for shop {shop}: "
                    f"{response.status_code} - {response.text}"
                )
                return None, None
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            scope = token_data.get("scope", "")
            
            if not access_token:
                logger.error(f"[TOKEN_EXCHANGE] No access token in response for shop: {shop}")
                return None, None
            
            logger.info(f"[TOKEN_EXCHANGE] Success for shop: {shop}, scopes: {scope}")
            return access_token, scope
            
    except httpx.RequestError as e:
        logger.error(f"[TOKEN_EXCHANGE] Network error for shop {shop}: {e}")
        return None, None
    except Exception as e:
        logger.error(f"[TOKEN_EXCHANGE] Unexpected error for shop {shop}: {e}")
        return None, None


def store_merchant_token(shop: str, access_token: str, scopes: str) -> Dict[str, Any]:
    """
    Store merchant access token using the merchant_storage service.
    
    Args:
        shop: Shop domain
        access_token: Access token from Shopify
        scopes: Granted scopes
        
    Returns:
        Dict with merchant_id and is_new status
    """
    return merchant_storage.store_token(shop, access_token, scopes)


@router.get("/test-shop")
async def test_shop_api(shop: str = Query(..., description="Shop domain")):
    """
    Test endpoint to verify access token works by fetching shop data.
    For development/debugging only.
    """
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Get merchant token
    merchant = merchant_storage.get_merchant(shop)
    if not merchant:
        return {"error": "Shop not found"}
    
    access_token = merchant.get("access_token")
    if not access_token:
        return {"error": "No access token for shop"}
    
    # Test API call
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/shop.json",
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                shop_data = response.json()
                return {
                    "success": True,
                    "shop_name": shop_data.get("shop", {}).get("name"),
                    "email": shop_data.get("shop", {}).get("email"),
                    "plan": shop_data.get("shop", {}).get("plan_name")
                }
            else:
                return {
                    "error": f"API call failed: {response.status_code}",
                    "details": response.text
                }
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}
