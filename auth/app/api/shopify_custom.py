"""Shopify Custom App API routes."""

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
import httpx
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse
from urllib.parse import urlencode

from app.config import settings
from shared.constants import SHOPIFY_SESSION_EXPIRE_MINUTES
from app.services.merchant_storage import merchant_storage
from app.services.shopify_token_exchange import token_exchange

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/connected")
async def handle_shopify_redirect(
    shop: str = Query(..., description="Shop domain"),
    host: Optional[str] = Query(None, description="Base64 encoded host"),
    id_token: Optional[str] = Query(None, description="Session token to exchange"),
    conversation_id: Optional[str] = Query(None, description="Original conversation ID")
):
    """
    Handle redirect from Shopify after custom app installation.
    
    Shopify sends users here after they install the app with:
    - shop: The shop domain
    - host: Base64 encoded host
    - id_token: Session token to exchange for access token
    """
    if not id_token:
        logger.error(f"[SHOPIFY_CONNECTED] Missing id_token for shop: {shop}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=missing_token",
            status_code=302
        )
    
    try:
        # Exchange id_token for permanent access token
        logger.info(f"[SHOPIFY_CONNECTED] Exchanging token for shop: {shop}")
        token_data = await token_exchange.exchange_id_token(
            id_token,
            shop
        )
        access_token = token_data["access_token"]
        
        # Check if merchant is new or returning
        merchant = await merchant_storage.get_merchant(shop)
        is_new = merchant is None
        
        if is_new:
            # Create new merchant record
            merchant_id = f"merchant_{shop.replace('.myshopify.com', '')}"
            await merchant_storage.create_merchant({
                "merchant_id": merchant_id,
                "shop_domain": shop,
                "access_token": access_token,
                "created_at": datetime.utcnow()
            })
            logger.info(f"[SHOPIFY_CONNECTED] New merchant created: {shop}")
        else:
            # Update existing merchant
            await merchant_storage.update_token(shop, access_token)
            merchant_id = merchant.get("merchant_id", f"merchant_{shop.replace('.myshopify.com', '')}")
            logger.info(f"[SHOPIFY_CONNECTED] Existing merchant updated: {shop}")
        
        logger.info(f"[SHOPIFY_CONNECTED] Successfully connected shop: {shop}, is_new: {is_new}")
        
        # Redirect to chat with success parameters
        redirect_params = {
            "oauth": "complete",
            "is_new": str(is_new).lower(),
            "merchant_id": merchant_id,
            "shop": shop
        }
        
        if conversation_id:
            redirect_params["conversation_id"] = conversation_id
        
        redirect_url = f"{settings.frontend_url}/chat?{urlencode(redirect_params)}"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except HTTPException as e:
        logger.error(f"[SHOPIFY_CONNECTED_ERROR] HTTP error: {e.detail}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=connection_failed&details={e.detail}",
            status_code=302
        )
    except Exception as e:
        logger.error(f"[SHOPIFY_CONNECTED_ERROR] Failed to process connection: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/chat?error=connection_failed",
            status_code=302
        )