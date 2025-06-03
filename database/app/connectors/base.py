"""Base class for service connectors."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any

from app.models.connection import Connection, ConnectionStatus, ProviderType, Credential


class ServiceConnector(ABC):
    """Abstract base class for service connectors."""
    
    def __init__(self, provider_type: ProviderType):
        self.provider_type = provider_type
        self._credentials: Optional[Credential] = None
        self._connection: Optional[Connection] = None
    
    @abstractmethod
    async def connect(self, credentials: Credential) -> Connection:
        """Establish connection with the service using OAuth credentials."""
        pass
    
    @abstractmethod
    async def check_connection(self) -> Connection:
        """Check the current connection status."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the service."""
        pass
    
    @abstractmethod
    async def refresh_token(self) -> Optional[Credential]:
        """Refresh the OAuth token if supported."""
        pass
    
    def get_connection(self) -> Optional[Connection]:
        """Get the current connection object."""
        return self._connection
    
    def set_credentials(self, credentials: Credential) -> None:
        """Set OAuth credentials."""
        self._credentials = credentials
    
    def _create_connection(
        self, 
        status: ConnectionStatus,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Connection:
        """Helper to create a connection object."""
        now = datetime.utcnow()
        return Connection(
            provider=self.provider_type,
            status=status,
            connected_at=now if status == ConnectionStatus.CONNECTED else None,
            last_checked=now,
            error_message=error_message,
            metadata=metadata or {}
        )