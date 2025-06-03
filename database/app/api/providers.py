"""Provider configuration API routes."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from app.models import ProviderType, ProviderConfig
from app.providers import provider_registry

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/", response_model=List[ProviderConfig])
async def list_providers():
    """List all available providers."""
    return provider_registry["list_providers"]()


@router.get("/{provider}/config", response_model=ProviderConfig)
async def get_provider_config(provider: ProviderType):
    """Get configuration for a specific provider."""
    config = provider_registry["get_config"](provider)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider} not found"
        )
    
    return config