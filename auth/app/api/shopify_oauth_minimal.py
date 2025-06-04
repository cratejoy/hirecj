"""Minimal Shopify OAuth endpoints for testing the flow."""

import logging
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/install")
async def initiate_oauth(shop: str = Query(..., description="Shop domain")):
    """
    Minimal OAuth initiation - just redirect to Shopify.
    No HMAC verification, no state parameter.
    """
    logger.info(f"[OAUTH_TEST] Install requested for shop: {shop}")
    
    # Basic validation
    if not shop or not shop.endswith('.myshopify.com'):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid shop domain. Must end with .myshopify.com"}
        )
    
    # Build minimal auth URL
    client_id = settings.shopify_client_id
    scopes = "read_products,read_orders"
    redirect_uri = "https://amir-auth.hirecj.ai/api/v1/shopify/callback"
    
    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={client_id}"
        f"&scope={scopes}"
        f"&redirect_uri={redirect_uri}"
    )
    
    logger.info(f"[OAUTH_TEST] Redirecting to: {auth_url}")
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def handle_oauth_callback(
    code: str = Query(None, description="Authorization code"),
    shop: str = Query(None, description="Shop domain"),
    hmac: str = Query(None, description="HMAC signature"),
    timestamp: str = Query(None, description="Timestamp"),
    state: str = Query(None, description="State parameter"),
    host: str = Query(None, description="Host parameter")
):
    """
    Minimal OAuth callback - just log what we receive.
    No token exchange, no HMAC verification.
    """
    logger.info(f"[OAUTH_TEST] Callback received!")
    logger.info(f"[OAUTH_TEST] shop: {shop}")
    logger.info(f"[OAUTH_TEST] code: {code[:20]}..." if code else "[OAUTH_TEST] NO CODE RECEIVED")
    logger.info(f"[OAUTH_TEST] hmac: {hmac[:20]}..." if hmac else "[OAUTH_TEST] NO HMAC")
    logger.info(f"[OAUTH_TEST] timestamp: {timestamp}")
    logger.info(f"[OAUTH_TEST] state: {state}")
    logger.info(f"[OAUTH_TEST] host: {host}")
    
    # Return JSON response showing what we got
    return JSONResponse(content={
        "status": "oauth_callback_received",
        "shop": shop,
        "has_code": bool(code),
        "has_hmac": bool(hmac),
        "params_received": {
            "code": f"{code[:20]}..." if code else None,
            "hmac": f"{hmac[:20]}..." if hmac else None,
            "timestamp": timestamp,
            "state": state,
            "host": host
        },
        "next_step": "In real implementation, we would exchange the code for an access token"
    })