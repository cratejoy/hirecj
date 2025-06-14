"""Shopify OAuth API routes with full security implementation."""

import logging
import json
import base64
import secrets, jwt                              # NEW
from jwt import InvalidTokenError                # NEW
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
from shared.db_models import WebSession            # NEW
from sqlalchemy import update                       # NEW

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


@router.get("/state")
async def get_signed_state(conversation_id: str | None = Query(None)) -> dict:
    """
    Front-end fetches this to obtain the Shopify `state` value.
    It is a self-contained, 10-minute JWT – no DB write needed.
    """
    payload = {
        "nonce": secrets.token_hex(16),
        "exp": datetime.utcnow() + timedelta(minutes=10),
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id
    token = jwt.encode(payload, settings.state_jwt_secret, algorithm="HS256")
    return {"state": token}

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
    
    # Generate and store state
    nonce = shopify_auth.generate_state()
    state_data = {"nonce": nonce}
    if conversation_id:
        state_data["conversation_id"] = conversation_id
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
    
    # Verify state (JWT preferred, DB fallback)
    conversation_id = None
    state_valid = False
    if state:
        try:
            jwt_payload = jwt.decode(state, settings.state_jwt_secret, algorithms=["HS256"])
            conversation_id = jwt_payload.get("conversation_id")
            nonce          = jwt_payload.get("nonce")
            state_valid    = True
            logger.info(f"[OAUTH_CALLBACK] JWT state verified (nonce={nonce}) conversation_id={conversation_id}")
        except InvalidTokenError:
            logger.warning("[OAUTH_CALLBACK] State is not valid JWT – attempting legacy DB lookup")
            state_valid = False

    # Legacy DB lookup only when JWT failed
    if not state_valid:
        try:
            with get_db_session() as session:
                csrf_record = session.query(OAuthCSRFState).filter(
                    OAuthCSRFState.state == state
                ).first()
                if not csrf_record:
                    raise HTTPException(status_code=400, detail="Invalid state")
                if csrf_record.expires_at < datetime.now(timezone.utc):
                    raise HTTPException(status_code=400, detail="State expired")
                conversation_id = csrf_record.conversation_id
                shop_db = csrf_record.shop
                if shop_db != shop:
                    raise HTTPException(status_code=400, detail="State shop mismatch")
                # cleanup
                session.delete(csrf_record)
                session.commit()
                state_valid = True
                logger.info("[OAUTH_CALLBACK] Legacy DB state verified")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[OAUTH_CALLBACK] DB state verification error: {e}")
            raise HTTPException(status_code=500, detail="State verification failed")
    
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
        
        # Create or get user identity first
        try:
            user_id, user_is_new = get_or_create_user(shop)
            logger.info(f"[OAUTH_CALLBACK] User identity: {user_id}, is_new: {user_is_new}")
        except Exception as e:
            logger.error(f"[OAUTH_CALLBACK] Failed to get/create user identity: {e}")
            user_id = None
        
        # Store merchant data with user association
        store_result = store_merchant_token(shop, access_token, scopes, user_id)
        merchant_id = store_result["merchant_id"]
        is_new = store_result["is_new"]
        
        logger.info(f"[OAUTH_CALLBACK] Successfully authenticated shop: {shop}, is_new: {is_new}")
        
        # With centralized database, agents service will determine OAuth completion
        # from MerchantToken creation timestamp - no notification needed

        # PHASE 3: Redirect to frontend with oauth complete marker
        # Server will determine everything from session
        redirect_params = {
            "oauth": "complete",
            "workflow": "shopify_post_auth",   # tell frontend which workflow to open
        }
        
        redirect_url = f"{settings.frontend_url}/chat?{urlencode(redirect_params)}"
        logger.info(f"[OAUTH_CALLBACK] Redirecting to: {redirect_url}")
        
        # Create redirect response
        response = RedirectResponse(url=redirect_url, status_code=302)
        
        # Issue session cookie if we have a user_id
        if user_id:
            from app.services.session_cookie import issue_session
            session_id = issue_session(user_id)

            # Store OAuth metadata in session for agents service
            try:
                with get_db_session() as db:
                    db.execute(
                        update(WebSession)
                        .where(WebSession.session_id == session_id)
                        .values(data={
                            'next_workflow': 'shopify_post_auth',
                            'oauth_metadata': {
                                'provider': 'shopify',
                                'shop_domain': shop,
                                'merchant_id': merchant_id,
                                'is_new': is_new
                            }
                        })
                    )
                    db.commit()
                    logger.info(f"[OAUTH_CALLBACK] Stored OAuth metadata for session {session_id}")
            except Exception as e:
                logger.error(f"[OAUTH_CALLBACK] Failed to store OAuth metadata: {e}")

            # Determine cookie domain based on environment
            cookie_domain = None
            if "hirecj.ai" in settings.frontend_url:
                # Production: allow cookie across all subdomains
                cookie_domain = ".hirecj.ai"
                logger.info(f"[OAUTH_CALLBACK] Setting cookie domain to {cookie_domain} for cross-subdomain access")
            
            # Set HTTP-only secure cookie
            response.set_cookie(
                key="hirecj_session",
                value=session_id,
                max_age=86400,  # 24 hours in seconds
                httponly=True,
                secure=True,  # Only send over HTTPS
                samesite="lax",  # CSRF protection
                domain=cookie_domain  # None for localhost, ".hirecj.ai" for production
            )
            logger.info(f"[OAUTH_CALLBACK] Set session cookie for user {user_id} (domain: {cookie_domain})")
        else:
            logger.warning(f"[OAUTH_CALLBACK] No user_id available, not setting session cookie")
        
        return response
        
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


def store_merchant_token(shop: str, access_token: str, scopes: str, user_id: str = None) -> Dict[str, Any]:
    """
    Store merchant access token using the merchant_storage service.
    
    Args:
        shop: Shop domain
        access_token: Access token from Shopify
        scopes: Granted scopes
        user_id: User ID to associate with this merchant
        
    Returns:
        Dict with merchant_id and is_new status
    """
    return merchant_storage.store_token(shop, access_token, scopes, user_id)


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
