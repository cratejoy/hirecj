"""Registry for managing service connectors."""

from typing import Dict, Type, Optional

from app.models.connection import ProviderType
from app.connectors.base import ServiceConnector


class ConnectorRegistry:
    """Registry for service connectors."""
    
    def __init__(self):
        self._connectors: Dict[ProviderType, Type[ServiceConnector]] = {}
        self._instances: Dict[ProviderType, ServiceConnector] = {}
    
    def register(self, provider_type: ProviderType, connector_class: Type[ServiceConnector]) -> None:
        """Register a connector class for a provider type."""
        if provider_type in self._connectors:
            raise ValueError(f"Connector for {provider_type} already registered")
        self._connectors[provider_type] = connector_class
    
    def get_connector(self, provider_type: ProviderType) -> ServiceConnector:
        """Get or create a connector instance for a provider type."""
        if provider_type not in self._instances:
            if provider_type not in self._connectors:
                raise ValueError(f"No connector registered for {provider_type}")
            
            connector_class = self._connectors[provider_type]
            self._instances[provider_type] = connector_class()
        
        return self._instances[provider_type]
    
    def get_all_connectors(self) -> Dict[ProviderType, ServiceConnector]:
        """Get all connector instances."""
        # Ensure all registered connectors have instances
        for provider_type in self._connectors:
            self.get_connector(provider_type)
        
        return self._instances.copy()
    
    def is_registered(self, provider_type: ProviderType) -> bool:
        """Check if a provider type has a registered connector."""
        return provider_type in self._connectors


# Global registry instance
connector_registry = ConnectorRegistry()