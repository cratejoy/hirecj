"""Client for interacting with the Knowledge Service (LightRAG)."""

import httpx
from typing import Optional, Dict, Any
from shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)


class KnowledgeServiceClient:
    """Synchronous HTTP client for Knowledge Service API."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.knowledge_service_url
        self.client = httpx.Client(timeout=30.0)
        logger.info(f"KnowledgeServiceClient initialized with base URL: {self.base_url}")
        
    def query(
        self, 
        namespace: str, 
        query: str, 
        mode: str = "hybrid"
    ) -> Optional[str]:
        """Query a knowledge graph.
        
        Args:
            namespace: Knowledge graph namespace (e.g., "npr")
            query: Query text
            mode: Query mode - "naive", "local", "global", or "hybrid"
            
        Returns:
            Query result or None if error
        """
        try:
            response = self.client.post(
                f"{self.base_url}/api/{namespace}/query",
                json={"query": query, "mode": mode}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("result", "")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Knowledge graph '{namespace}' not found")
            else:
                logger.error(f"HTTP error querying knowledge graph: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Error querying knowledge graph '{namespace}': {e}")
            return None
    
    def check_namespace_exists(self, namespace: str) -> bool:
        """Check if a namespace exists.
        
        Args:
            namespace: Knowledge graph namespace
            
        Returns:
            True if namespace exists, False otherwise
        """
        try:
            response = self.client.get(
                f"{self.base_url}/api/namespaces/{namespace}/statistics"
            )
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error checking namespace '{namespace}': {e}")
            return False
    
    def get_namespace_status(self, namespace: str) -> Optional[Dict[str, Any]]:
        """Get namespace statistics.
        
        Args:
            namespace: Knowledge graph namespace
            
        Returns:
            Statistics dict or None if error
        """
        try:
            response = self.client.get(
                f"{self.base_url}/api/namespaces/{namespace}/statistics"
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting namespace status: {e}")
            return None
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()