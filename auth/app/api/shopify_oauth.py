"""Shopify OAuth API routes with full security implementation."""

import logging
import json
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from urllib.parse import urlencode

from app.config import settings
from app.services.merchant_storage import merchant_storage
from app.services.shopify_auth import shopify_auth
from shared.user_identity import get_or_create_user
from app.utils.database import get_db_session
from shared.db_models import OAuthCSRFState

logger = logging.getLogger(__name__)

router = APIRouter()

# Constants
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
async def initiate_oauth(request: Request):
    """
    Initiate OAuth flow by redirecting to Shopify authorization page.
    
    This endpoint is called in two scenarios:
    1. Initial app installation (from Shopify with HMAC)
    2. Re-authorization (from our frontend)
    """
    params = dict(request.query_params)
    shop = params.get("shop")
    hmac = params.get("hmac")
    conversation_id = params.get("conversation_id")

    # For frontend requests, shop might be in different param
    if not shop:
        raise HTTPException(
            status_code=400,
            detail="Missing shop parameter"
        )
    
    logger.info(f"[OAUTH_INSTALL] Initiating OAuth for shop: {shop}")
    logger.info(f"[OAUTH_INSTALL] Frontend URL configured as: {settings.frontend_url}")
    logger.info(f"[OAUTH_INSTALL] OAuth redirect base: {settings.oauth_redirect_base_url}")
    
    # Check if Shopify credentials are configured
    if not settings.shopify_client_id or not settings.shopify_client_secret:
        logger.error("[OAUTH_INSTALL] Shopify credentials not configured!")
        raise HTTPException(
            status_code=500,
            detail="Shopify credentials not configured on the auth server."
        )
    
    # Validate shop domain
    if not shopify_auth.validate_shop_domain(shop):
        logger.error(f"[OAUTH_INSTALL] Invalid shop domain: {shop}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid shop domain format: {shop}"
        )
    
    # If HMAC provided, verify it (initial install from Shopify)
    if hmac:
        if not shopify_auth.verify_hmac(params.copy()):
            logger.error(f"[OAUTH_INSTALL] Invalid HMAC for shop: {shop}")
            raise HTTPException(
                status_code=401,
                detail=f"Invalid HMAC signature for shop {shop}"
            )
    
    # Generate and store state with conversation_id
    nonce = shopify_auth.generate_state()
    state_data = {"nonce": nonce, "conversation_id": conversation_id}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    logger.info(f"[OAUTH_INSTALL] State data to encode: {state_data}")
    logger.info(f"[OAUTH_INSTALL] Encoded state: {state[:20]}...")

    # Store state with shop domain and conversation_id in Database
    try:
        with get_db_session() as session:
            csrf_state = OAuthCSRFState(
                state=state,
                shop=shop,
                conversation_id=conversation_id,
                expires_at=datetime.utcnow() + timedelta(minutes=10)
            )
            session.add(csrf_state)
            session.commit()
    except Exception as e:
        logger.error(f"[OAUTH_INSTALL] Failed to store state in Database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize OAuth flow, could not store state in DB: {e}"
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

    # NEW: allow SPA to request the final URL as JSON to avoid an extra
    # browser navigation hop (mode=json)
    if request.query_params.get("mode") == "json":
        return {"redirect_url": auth_url}

    logger.info(f"[OAUTH_INSTALL] Redirecting shop {shop} to authorization")
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def handle_oauth_callback(request: Request):
    """
    Handle OAuth callback from Shopify with authorization code.
    Exchange code for access token and store it.
    """
    # Get all query parameters from the request for robust HMAC validation
    params = dict(request.query_params)
    shop = params.get("shop")
    code = params.get("code")
    state = params.get("state")

    logger.info(f"[OAUTH_CALLBACK] Received callback for shop: {shop}")
    
    # Verify HMAC
    if not shopify_auth.verify_hmac(params.copy()):
        logger.error(f"[OAUTH_CALLBACK] Invalid HMAC for shop: {shop}")
        # HARD PANIC
        raise HTTPException(
            status_code=401,
            detail=f"Invalid HMAC signature for shop {shop} on callback."
        )
    
    # Verify state if provided
    conversation_id = None
    if state:
        try:
            with get_db_session() as session:
                csrf_record = session.query(OAuthCSRFState).filter(
                    OAuthCSRFState.state == state
                ).first()

                if not csrf_record:
                    logger.error(f"[OAUTH_CALLBACK] State not found in DB for shop: {shop}")
                    raise HTTPException(status_code=400, detail="Invalid state: not found.")
                
                # Clean up used state immediately
                session.delete(csrf_record)
                session.commit()

                if csrf_record.expires_at < datetime.now(timezone.utc):
                    logger.error(f"[OAUTH_CALLBACK] Expired state for shop: {shop}")
                    raise HTTPException(status_code=400, detail="Invalid state: expired.")

                stored_shop = csrf_record.shop
                conversation_id = csrf_record.conversation_id

                logger.info(f"[OAUTH_CALLBACK] State data retrieved from DB: shop={stored_shop}, conversation_id={conversation_id}")

                if not stored_shop or stored_shop != shop:
                    logger.error(f"[OAUTH_CALLBACK] Invalid state for shop: {shop}. Expected {stored_shop}")
                    raise HTTPException(status_code=400, detail="Invalid state: shop mismatch.")
        
        except Exception as e:
            logger.error(f"[OAUTH_CALLBACK] Failed to verify state from DB: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"State verification from DB failed: {e}"
            )
    
    # Check if we have authorization code
    if not code:
        logger.error(f"[OAUTH_CALLBACK] Missing authorization code for shop: {shop}")
        # HARD PANIC
        raise HTTPException(
            status_code=400,
            detail=f"Missing authorization code for shop: {shop}"
        )
    
    # Exchange code for access token
    try:
        access_token, scopes = await exchange_code_for_token(shop, code)
        
        if not access_token:
            # HARD PANIC
            raise HTTPException(
                status_code=500,
                detail="Token exchange failed. No access token received from Shopify."
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
        
        # PHASE 6.3: Call Agent service's internal API to pre-warm session
        if conversation_id:
            try:
                # Prepare payload for the agent service
                handoff_request = {
                    "shop_domain": shop,
                    "is_new": is_new,
                    "conversation_id": conversation_id,
                    "email": None  # We don't have email at this stage, can be added later
                }

                agents_url = f"{settings.agents_service_url}/api/v1/internal/session/initiate"
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(agents_url, json=handoff_request)
                
                if response.status_code == 200:
                    logger.info(f"[OAUTH_HANDOFF] Successfully initiated session for {conversation_id} on agent service.")
                else:
                    # Log the error but don't fail the auth flow.
                    # The user will still be redirected, but the agent won't be pre-warmed.
                    logger.error(
                        f"[OAUTH_HANDOFF] Failed to initiate session. Agent service returned "
                        f"{response.status_code}: {response.text}"
                    )
                    
            except Exception as e:
                # Log the error but don't fail the auth flow.
                logger.error(f"[OAUTH_HANDOFF] Error calling agent service: {e}", exc_info=True)
                # The flow will gracefully degrade to the user connecting and starting a new session.

        # PHASE 3: Redirect to frontend with only conversation_id
        redirect_params = {}
        if conversation_id:
            redirect_params["conversation_id"] = conversation_id
        else:
            logger.warning("[OAUTH_CALLBACK] No conversation_id available for redirect.")
        
        redirect_url = f"{settings.frontend_url}/chat?{urlencode(redirect_params)}"
        logger.info(f"[OAUTH_CALLBACK] Redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        import traceback
        logger.error(f"[OAUTH_CALLBACK] Unexpected error: {e}")
        logger.error(f"[OAUTH_CALLBACK] Traceback: {traceback.format_exc()}")
        # HARD PANIC
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during OAuth callback: {e}"
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

    if settings.debug:
        logger.info("[TOKEN_EXCHANGE] Preparing to exchange code for token:")
        logger.info(f"  - Using Client ID: '{settings.shopify_client_id}'")
        logger.info(f"  - Using Client Secret: '{settings.shopify_client_secret}'")
    
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
