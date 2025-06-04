"""Shopify Custom App API routes."""

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from shared.constants import SHOPIFY_SESSION_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory session storage (use Redis in production)
_merchant_sessions = {}  # shop_domain -> merchant_info
_install_sessions = {}   # session_id -> install_info


class InstallSession(BaseModel):
    """Installation session tracking."""
    session_id: str
    conversation_id: str
    created_at: datetime
    shop_domain: Optional[str] = None
    installed: bool = False
    access_token: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() - self.created_at > timedelta(minutes=SHOPIFY_SESSION_EXPIRE_MINUTES)


class MerchantSession(BaseModel):
    """Merchant session data."""
    merchant_id: str
    shop_domain: str
    shop_name: str
    owner_email: str
    created_at: datetime
    last_seen: datetime
    access_token: str


class CustomInstallRequest(BaseModel):
    """Request to initiate custom app installation."""
    conversation_id: str


class SessionTokenValidationRequest(BaseModel):
    """Request to validate a session token."""
    session_token: str
    session_id: str


@router.post("/install")
async def initiate_custom_install(request: CustomInstallRequest):
    """
    Initiate custom app installation.
    
    Returns the custom install link for the frontend to open.
    """
    if not settings.shopify_custom_install_link:
        raise HTTPException(
            status_code=500,
            detail="Custom app install link not configured"
        )
    
    # Generate session ID to track this installation
    session_id = secrets.token_urlsafe(16)
    
    # Store installation session
    _install_sessions[session_id] = InstallSession(
        session_id=session_id,
        conversation_id=request.conversation_id,
        created_at=datetime.utcnow()
    )
    
    logger.info(f"[CUSTOM_INSTALL] Starting custom app installation for conversation={request.conversation_id}")
    
    return {
        "install_url": settings.shopify_custom_install_link,
        "session_id": session_id
    }


@router.post("/verify")
async def verify_custom_installation(request: SessionTokenValidationRequest):
    """
    Verify custom app installation by validating session token.
    
    Called after merchant installs the custom app to exchange
    the session token for an access token.
    """
    # Check if we have this session
    install_session = _install_sessions.get(request.session_id)
    if not install_session:
        raise HTTPException(status_code=404, detail="Installation session not found")
    
    if install_session.is_expired():
        del _install_sessions[request.session_id]
        raise HTTPException(status_code=400, detail="Installation session expired")
    
    try:
        # Validate the session token (Shopify JWT)
        # In a real implementation, you'd verify the JWT signature
        # using Shopify's public key
        payload = jwt.decode(
            request.session_token, 
            options={"verify_signature": False}  # TODO: Implement proper verification
        )
        
        shop_domain = payload.get("dest", "").replace("https://", "")
        
        # Exchange session token for access token
        # TODO: Implement actual token exchange with Shopify
        # For now, we'll simulate it
        access_token = f"shpat_{secrets.token_urlsafe(32)}"
        
        # Check if merchant is new or returning
        is_new = shop_domain not in _merchant_sessions
        
        # Create/update merchant session
        merchant_id = f"merchant_{shop_domain.replace('.myshopify.com', '')}"
        _merchant_sessions[shop_domain] = MerchantSession(
            merchant_id=merchant_id,
            shop_domain=shop_domain,
            shop_name=shop_domain.replace(".myshopify.com", "").replace("-", " ").title(),
            owner_email=f"owner@{shop_domain}",
            created_at=datetime.utcnow() if is_new else _merchant_sessions.get(shop_domain, {}).get("created_at", datetime.utcnow()),
            last_seen=datetime.utcnow(),
            access_token=access_token
        )
        
        # Update install session
        install_session.installed = True
        install_session.shop_domain = shop_domain
        install_session.access_token = access_token
        
        logger.info(f"[CUSTOM_INSTALL_SUCCESS] Custom app installed for shop={shop_domain}, is_new={is_new}")
        
        return {
            "success": True,
            "installed": True,
            "is_new": is_new,
            "merchant_id": merchant_id,
            "shop_domain": shop_domain,
            "conversation_id": install_session.conversation_id
        }
        
    except jwt.InvalidTokenError as e:
        logger.error(f"[CUSTOM_INSTALL_ERROR] Invalid session token: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid session token"
        )
    except Exception as e:
        logger.error(f"[CUSTOM_INSTALL_ERROR] Failed to verify installation: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to verify installation"
        )


@router.get("/status/{session_id}")
async def check_installation_status(session_id: str):
    """
    Check the status of a custom app installation.
    
    Used by frontend to poll for installation completion.
    """
    install_session = _install_sessions.get(session_id)
    
    if not install_session:
        return {"installed": False, "error": "Session not found"}
    
    if install_session.is_expired():
        del _install_sessions[session_id]
        return {"installed": False, "error": "Session expired"}
    
    return {
        "installed": install_session.installed,
        "shop_domain": install_session.shop_domain,
        "session_id": session_id
    }


@router.get("/merchant/{shop_domain}")
async def check_merchant_status(shop_domain: str):
    """
    Check if a merchant has authenticated before.
    
    This is used to determine if we should show "Welcome back" messaging.
    """
    merchant = _merchant_sessions.get(shop_domain)
    
    if merchant:
        return {
            "authenticated": True,
            "merchant_id": merchant.merchant_id,
            "shop_name": merchant.shop_name,
            "last_seen": merchant.last_seen.isoformat()
        }
    else:
        return {
            "authenticated": False
        }