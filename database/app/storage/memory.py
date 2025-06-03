"""In-memory storage implementation."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from app.models import Connection, Credential, ProviderType


class MemoryStorage:
    """Simple in-memory storage for connections and credentials."""
    
    def __init__(self):
        self._connections: Dict[str, Connection] = {}
        self._credentials: Dict[str, Credential] = {}
        self._oauth_states: Dict[str, Dict[str, Any]] = {}  # state -> {provider, timestamp, etc}
    
    # Connection methods
    async def create_connection(self, connection: Connection) -> Connection:
        """Store a new connection."""
        self._connections[connection.id] = connection
        return connection
    
    async def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Get a connection by ID."""
        return self._connections.get(connection_id)
    
    async def list_connections(self) -> List[Connection]:
        """List all connections."""
        return list(self._connections.values())
    
    async def update_connection(self, connection_id: str, connection: Connection) -> Optional[Connection]:
        """Update a connection."""
        if connection_id in self._connections:
            connection.updated_at = datetime.utcnow()
            self._connections[connection_id] = connection
            return connection
        return None
    
    async def delete_connection(self, connection_id: str) -> bool:
        """Delete a connection."""
        if connection_id in self._connections:
            del self._connections[connection_id]
            return True
        return False
    
    # Credential methods
    async def create_credential(self, credential: Credential) -> Credential:
        """Store a new credential."""
        self._credentials[credential.id] = credential
        return credential
    
    async def get_credential(self, credential_id: str) -> Optional[Credential]:
        """Get a credential by ID."""
        return self._credentials.get(credential_id)
    
    async def list_credentials(self) -> List[Credential]:
        """List all credentials."""
        return list(self._credentials.values())
    
    async def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential."""
        if credential_id in self._credentials:
            del self._credentials[credential_id]
            return True
        return False
    
    async def get_credentials_by_provider(self, provider: ProviderType) -> List[Credential]:
        """Get all credentials for a provider."""
        return [c for c in self._credentials.values() if c.provider == provider]
    
    # OAuth state methods
    async def store_oauth_state(self, state: str, data: Dict[str, Any]) -> None:
        """Store OAuth state for verification."""
        self._oauth_states[state] = {
            **data,
            "timestamp": datetime.utcnow()
        }
    
    async def get_oauth_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Get OAuth state data."""
        return self._oauth_states.get(state)
    
    async def delete_oauth_state(self, state: str) -> bool:
        """Delete OAuth state."""
        if state in self._oauth_states:
            del self._oauth_states[state]
            return True
        return False
    
    async def cleanup_expired_oauth_states(self, max_age_seconds: int = 600) -> int:
        """Clean up OAuth states older than max_age_seconds."""
        now = datetime.utcnow()
        expired_states = []
        
        for state, data in self._oauth_states.items():
            age = (now - data["timestamp"]).total_seconds()
            if age > max_age_seconds:
                expired_states.append(state)
        
        for state in expired_states:
            del self._oauth_states[state]
        
        return len(expired_states)


# Global storage instance
storage = MemoryStorage()