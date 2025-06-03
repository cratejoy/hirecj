"""Base classes for OAuth providers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum

from pydantic import BaseModel


class ProviderType(str, Enum):
    """Type of OAuth provider."""
    LOGIN = "login"  # For user authentication (e.g., Shopify login)
    DATA = "data"    # For data integration (e.g., Klaviyo, Google Analytics)
    HYBRID = "hybrid"  # Can be used for both (e.g., Google)


class OAuthToken(BaseModel):
    """OAuth token information."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    extra_data: Dict[str, Any] = {}  # Provider-specific data


class OAuthProvider(ABC):
    """Base class for all OAuth providers."""
    
    def __init__(
        self,
        name: str,
        provider_type: ProviderType,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        token_url: str,
        scopes: List[str],
        extra_params: Dict[str, Any] = None
    ):
        self.name = name
        self.provider_type = provider_type
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.scopes = scopes
        self.extra_params = extra_params or {}
    
    @abstractmethod
    async def get_authorization_url(self, redirect_uri: str, state: str, **kwargs) -> str:
        """
        Generate the OAuth authorization URL.
        
        Args:
            redirect_uri: The callback URL
            state: Security state parameter
            **kwargs: Provider-specific parameters
            
        Returns:
            The authorization URL to redirect the user to
        """
        pass
    
    @abstractmethod
    async def exchange_code_for_token(self, code: str, redirect_uri: str, **kwargs) -> OAuthToken:
        """
        Exchange authorization code for access token.
        
        Args:
            code: The authorization code
            redirect_uri: The callback URL (must match)
            **kwargs: Provider-specific parameters
            
        Returns:
            OAuthToken with access token and related data
        """
        pass
    
    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> OAuthToken:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            New OAuthToken
        """
        pass
    
    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access or refresh token.
        
        Args:
            token: The token to revoke
            
        Returns:
            True if successful
        """
        pass
    
    def get_scopes_string(self) -> str:
        """Get scopes as a string for OAuth request."""
        return " ".join(self.scopes)


class LoginProvider(OAuthProvider):
    """Base class for login/authentication providers."""
    
    def __init__(self, **kwargs):
        super().__init__(provider_type=ProviderType.LOGIN, **kwargs)
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information using the access token.
        
        Args:
            access_token: Valid OAuth access token
            
        Returns:
            User information dict with at least 'id' and 'email'
        """
        pass


class DataProvider(OAuthProvider):
    """Base class for data integration providers."""
    
    def __init__(self, **kwargs):
        super().__init__(provider_type=ProviderType.DATA, **kwargs)
    
    @abstractmethod
    async def test_connection(self, access_token: str) -> Dict[str, Any]:
        """
        Test if the data connection is working.
        
        Args:
            access_token: Valid OAuth access token
            
        Returns:
            Connection test results
        """
        pass
    
    @abstractmethod
    async def get_available_resources(self, access_token: str) -> List[str]:
        """
        Get list of available data resources.
        
        Args:
            access_token: Valid OAuth access token
            
        Returns:
            List of resource identifiers
        """
        pass