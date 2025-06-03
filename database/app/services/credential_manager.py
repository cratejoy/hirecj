"""Service for managing credentials."""

import logging
from datetime import datetime
from typing import List, Optional

from app.models import (
    Credential,
    CredentialCreate,
    ProviderType,
    AuthType
)
from app.storage.memory import storage

logger = logging.getLogger(__name__)


class CredentialManager:
    """Manages credential lifecycle."""
    
    def __init__(self):
        self.storage = storage
    
    async def create_credential(self, credential_data: CredentialCreate) -> Credential:
        """Create a new credential."""
        credential = Credential(
            provider=credential_data.provider,
            auth_type=credential_data.auth_type,
            access_token=credential_data.access_token,
            refresh_token=credential_data.refresh_token,
            token_type=credential_data.token_type,
            scope=credential_data.scope,
            expires_at=credential_data.expires_at,
            api_key=credential_data.api_key,
            username=credential_data.username,
            password=credential_data.password,
            metadata=credential_data.metadata
        )
        
        return await self.storage.create_credential(credential)
    
    async def get_credential(self, credential_id: str) -> Optional[Credential]:
        """Get a credential by ID."""
        return await self.storage.get_credential(credential_id)
    
    async def update_credential(self, credential_id: str, **updates) -> Optional[Credential]:
        """Update a credential."""
        credential = await self.get_credential(credential_id)
        if not credential:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(credential, key):
                setattr(credential, key, value)
        
        credential.updated_at = datetime.utcnow()
        return await self.storage.update_credential(credential)
    
    async def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential."""
        return await self.storage.delete_credential(credential_id)
    
    async def list_credentials(self, provider: Optional[ProviderType] = None) -> List[Credential]:
        """List all credentials, optionally filtered by provider."""
        credentials = await self.storage.list_credentials()
        
        if provider:
            credentials = [c for c in credentials if c.provider == provider]
        
        return credentials


# Global instance
credential_manager = CredentialManager()