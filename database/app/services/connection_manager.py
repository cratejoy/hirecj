"""Service for managing connections."""

import logging
from datetime import datetime
from typing import List, Optional

from app.models import (
    Connection,
    ConnectionCreate,
    ConnectionStatus,
    ProviderType
)
from app.storage.memory import storage
from app.connectors.registry import connector_registry
from app.services.credential_manager import credential_manager

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages service connections."""
    
    async def create_connection(self, connection_data: ConnectionCreate) -> Connection:
        """Create a new connection."""
        # Validate provider is supported
        from app.providers import provider_registry
        if not provider_registry["is_supported"](connection_data.provider):
            raise ValueError(f"Provider {connection_data.provider} is not supported")
        
        # Validate credential exists if provided
        if connection_data.credential_id:
            credential = await credential_manager.get_credential(connection_data.credential_id)
            if not credential:
                raise ValueError(f"Credential {connection_data.credential_id} not found")
            if credential.provider != connection_data.provider:
                raise ValueError("Credential provider does not match connection provider")
        
        # Create connection
        connection = Connection(
            provider=connection_data.provider,
            status=ConnectionStatus.PENDING,
            credential_id=connection_data.credential_id,
            metadata=connection_data.metadata
        )
        
        # Try to connect if credential provided
        if connection_data.credential_id:
            try:
                await self._establish_connection(connection)
            except Exception as e:
                logger.error(f"Failed to establish connection: {str(e)}")
                connection.status = ConnectionStatus.ERROR
                connection.error_message = str(e)
        
        # Store connection
        return await storage.create_connection(connection)
    
    async def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Get a connection by ID."""
        return await storage.get_connection(connection_id)
    
    async def list_connections(self) -> List[Connection]:
        """List all connections."""
        return await storage.list_connections()
    
    async def delete_connection(self, connection_id: str) -> bool:
        """Delete a connection."""
        connection = await self.get_connection(connection_id)
        if connection:
            # Disconnect from service
            try:
                connector = self._get_connector(connection.provider)
                await connector.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting: {str(e)}")
        
        return await storage.delete_connection(connection_id)
    
    async def refresh_connection(self, connection_id: str) -> Optional[Connection]:
        """Refresh a connection's credentials."""
        connection = await self.get_connection(connection_id)
        if not connection:
            return None
        
        if not connection.credential_id:
            raise ValueError("Connection has no credentials to refresh")
        
        # Get credential
        credential = await credential_manager.get_credential(connection.credential_id)
        if not credential:
            raise ValueError("Credential not found")
        
        # Update status
        connection.status = ConnectionStatus.REFRESHING
        await storage.update_connection(connection_id, connection)
        
        try:
            # Refresh token
            connector = self._get_connector(connection.provider)
            connector.set_credentials(credential)
            new_credential = await connector.refresh_token()
            
            if new_credential:
                # Update credential in storage
                await credential_manager.update_credential(credential.id, new_credential)
                
                # Re-establish connection
                await self._establish_connection(connection)
            else:
                connection.status = ConnectionStatus.ERROR
                connection.error_message = "Failed to refresh token"
        except Exception as e:
            logger.error(f"Error refreshing connection: {str(e)}")
            connection.status = ConnectionStatus.ERROR
            connection.error_message = str(e)
        
        connection.updated_at = datetime.utcnow()
        return await storage.update_connection(connection_id, connection)
    
    async def check_connection_status(self, connection_id: str) -> ConnectionStatus:
        """Check the live status of a connection."""
        connection = await self.get_connection(connection_id)
        if not connection:
            return ConnectionStatus.DISCONNECTED
        
        try:
            connector = self._get_connector(connection.provider)
            
            # Set credentials if available
            if connection.credential_id:
                credential = await credential_manager.get_credential(connection.credential_id)
                if credential:
                    connector.set_credentials(credential)
            
            # Check connection
            result = await connector.check_connection()
            
            # Update stored connection
            connection.status = result.status
            connection.last_checked = datetime.utcnow()
            connection.error_message = result.error_message
            
            await storage.update_connection(connection_id, connection)
            
            return result.status
        except Exception as e:
            logger.error(f"Error checking connection status: {str(e)}")
            return ConnectionStatus.ERROR
    
    async def _establish_connection(self, connection: Connection) -> None:
        """Establish connection using credentials."""
        if not connection.credential_id:
            raise ValueError("No credentials provided")
        
        credential = await credential_manager.get_credential(connection.credential_id)
        if not credential:
            raise ValueError("Credential not found")
        
        connector = self._get_connector(connection.provider)
        connector.set_credentials(credential)
        
        result = await connector.connect(credential)
        
        connection.status = result.status
        connection.connected_at = result.connected_at
        connection.last_checked = result.last_checked
        connection.error_message = result.error_message
        connection.metadata.update(result.metadata)
    
    def _get_connector(self, provider: ProviderType):
        """Get connector for a provider."""
        # Import here to avoid circular dependency
        from app.connectors.freshdesk import FreshdeskConnector
        from app.connectors.google_analytics import GoogleAnalyticsConnector
        
        # Register connectors if not already done
        if not connector_registry.is_registered(ProviderType.FRESHDESK):
            connector_registry.register(ProviderType.FRESHDESK, FreshdeskConnector)
        if not connector_registry.is_registered(ProviderType.GOOGLE_ANALYTICS):
            connector_registry.register(ProviderType.GOOGLE_ANALYTICS, GoogleAnalyticsConnector)
        
        return connector_registry.get_connector(provider)


# Global instance
connection_manager = ConnectionManager()