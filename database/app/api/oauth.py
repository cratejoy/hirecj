"""OAuth flow API routes."""

import logging
import secrets
from typing import Dict

from fastapi import APIRouter, HTTPException, status, Query

from app.models import (
    ProviderType,
    OAuthAuthorizeResponse,
    OAuthExchangeRequest,
    Credential
)
from app.services.oauth_manager import oauth_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/{provider}/authorize", response_model=OAuthAuthorizeResponse)
async def get_authorization_url(
    provider: ProviderType,
    redirect_uri: str = Query(..., description="Redirect URI for OAuth callback"),
    scopes: str = Query(None, description="Comma-separated list of scopes")
):
    """Get OAuth authorization URL for a provider."""
    try:
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Parse scopes if provided
        scope_list = scopes.split(",") if scopes else None
        
        # Get authorization URL
        auth_url = await oauth_manager.get_authorization_url(
            provider=provider,
            redirect_uri=redirect_uri,
            state=state,
            scopes=scope_list
        )
        
        return OAuthAuthorizeResponse(
            authorization_url=auth_url,
            state=state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: ProviderType,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    error: str = Query(None, description="OAuth error parameter"),
    error_description: str = Query(None, description="OAuth error description")
):
    """Handle OAuth callback from provider."""
    # Check for OAuth errors
    if error:
        logger.error(f"OAuth error for {provider}: {error} - {error_description}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authorization failed: {error_description or error}"
        )
    
    # Verify state
    is_valid = await oauth_manager.verify_state(state, provider)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state parameter"
        )
    
    return {
        "provider": provider,
        "code": code,
        "state": state,
        "message": "Authorization successful. Use /oauth/{provider}/exchange to get tokens."
    }


@router.post("/{provider}/exchange", response_model=Credential)
async def exchange_code_for_tokens(
    provider: ProviderType,
    exchange_data: OAuthExchangeRequest
):
    """Exchange authorization code for access tokens."""
    try:
        # Verify state again
        is_valid = await oauth_manager.verify_state(exchange_data.state, provider)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state parameter"
            )
        
        # Exchange code for tokens
        credential = await oauth_manager.exchange_code(
            provider=provider,
            code=exchange_data.code,
            redirect_uri=exchange_data.redirect_uri
        )
        
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code"
            )
        
        return credential
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error exchanging code for {provider}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to exchange authorization code"
        )