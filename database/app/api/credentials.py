"""Credential management API routes."""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.models import (
    Credential,
    CredentialCreate,
    ProviderType
)
from app.services.credential_manager import credential_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.post("/{provider}", response_model=Credential, status_code=status.HTTP_201_CREATED)
async def create_credential(provider: ProviderType, credential_data: CredentialCreate):
    """Create credentials for a provider (for API keys/tokens)."""
    # Ensure provider matches
    if credential_data.provider != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider in URL must match provider in request body"
        )
    
    try:
        credential = await credential_manager.create_credential(credential_data)
        return credential
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[Credential])
async def list_credentials(provider: ProviderType = None):
    """List all credentials, optionally filtered by provider."""
    if provider:
        return await credential_manager.list_credentials_by_provider(provider)
    return await credential_manager.list_credentials()


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(credential_id: str):
    """Delete a credential."""
    deleted = await credential_manager.delete_credential(credential_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential {credential_id} not found"
        )
    
    # Also delete any connections using this credential
    await credential_manager.delete_connections_using_credential(credential_id)