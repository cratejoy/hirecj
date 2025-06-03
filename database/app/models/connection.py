"""Service connection models."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class ConnectionStatus(str, Enum):
    """Status of a service connection."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"
    REFRESHING = "refreshing"


class ProviderType(str, Enum):
    """Supported provider types."""
    FRESHDESK = "freshdesk"
    GOOGLE_ANALYTICS = "google_analytics"
    SLACK = "slack"
    HUBSPOT = "hubspot"
    SALESFORCE = "salesforce"


class AuthType(str, Enum):
    """Authentication types."""
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC = "basic"


class Connection(BaseModel):
    """Model representing a service connection."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique connection ID")
    provider: ProviderType = Field(..., description="Service provider type")
    status: ConnectionStatus = Field(..., description="Current connection status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    connected_at: Optional[datetime] = Field(None, description="When the service was connected")
    last_checked: Optional[datetime] = Field(None, description="Last status check timestamp")
    error_message: Optional[str] = Field(None, description="Error message if status is ERROR")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific metadata")
    credential_id: Optional[str] = Field(None, description="Associated credential ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ConnectionCreate(BaseModel):
    """Request model for creating a connection."""
    
    provider: ProviderType = Field(..., description="Service provider type")
    credential_id: Optional[str] = Field(None, description="Existing credential ID to use")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific metadata")


class ConnectionUpdate(BaseModel):
    """Request model for updating a connection."""
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class Credential(BaseModel):
    """Model for storing service credentials."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique credential ID")
    provider: ProviderType = Field(..., description="Service provider type")
    auth_type: AuthType = Field(..., description="Authentication type")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    expires_at: Optional[datetime] = Field(None, description="Credential expiration time")
    
    # OAuth fields
    access_token: Optional[str] = Field(None, description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_type: Optional[str] = Field("Bearer", description="Token type")
    scope: Optional[str] = Field(None, description="OAuth scope")
    
    # API Key fields
    api_key: Optional[str] = Field(None, description="API key")
    
    # Basic auth fields
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional credential metadata")


class CredentialCreate(BaseModel):
    """Request model for creating credentials."""
    
    provider: ProviderType = Field(..., description="Service provider type")
    auth_type: AuthType = Field(..., description="Authentication type")
    
    # OAuth fields
    access_token: Optional[str] = Field(None, description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_type: Optional[str] = Field("Bearer", description="Token type")
    scope: Optional[str] = Field(None, description="OAuth scope")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    
    # API Key fields
    api_key: Optional[str] = Field(None, description="API key")
    
    # Basic auth fields
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class OAuthAuthorizeResponse(BaseModel):
    """Response for OAuth authorization URL."""
    
    authorization_url: str = Field(..., description="URL to redirect user for authorization")
    state: str = Field(..., description="OAuth state parameter for security")


class OAuthExchangeRequest(BaseModel):
    """Request for exchanging OAuth code for tokens."""
    
    code: str = Field(..., description="Authorization code from OAuth callback")
    state: str = Field(..., description="OAuth state parameter for verification")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI used in authorization")


class ProviderConfig(BaseModel):
    """Configuration for a service provider."""
    
    provider: ProviderType = Field(..., description="Provider type")
    name: str = Field(..., description="Human-readable provider name")
    auth_types: List[AuthType] = Field(..., description="Supported authentication types")
    oauth_config: Optional[Dict[str, Any]] = Field(None, description="OAuth configuration")
    required_fields: Dict[str, List[str]] = Field(..., description="Required fields by auth type")
    optional_fields: Dict[str, List[str]] = Field(default_factory=dict, description="Optional fields by auth type")
    features: List[str] = Field(default_factory=list, description="Supported features")
    icon_url: Optional[str] = Field(None, description="Provider icon URL")