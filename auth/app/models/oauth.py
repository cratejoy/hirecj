"""OAuth connection models for data integrations."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field


class DataProvider(str, Enum):
    """Supported data integration providers."""
    KLAVIYO = "klaviyo"
    GOOGLE_ANALYTICS = "google_analytics"
    FRESHDESK = "freshdesk"
    STRIPE = "stripe"
    SENDGRID = "sendgrid"


class OAuthConnection(BaseModel):
    """OAuth connection for data integration."""
    connection_id: str = Field(..., description="Unique connection identifier")
    account_id: str = Field(..., description="Account/merchant identifier")
    provider: DataProvider = Field(..., description="Data provider")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    scopes: List[str] = Field(default_factory=list, description="Granted OAuth scopes")
    provider_account_id: Optional[str] = Field(None, description="Account ID at provider")
    provider_account_name: Optional[str] = Field(None, description="Account name at provider")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional connection metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class ConnectRequest(BaseModel):
    """Request to connect a data provider."""
    provider: DataProvider
    redirect_url: Optional[str] = None
    requested_scopes: Optional[List[str]] = None


class ConnectResponse(BaseModel):
    """Response for connection request."""
    authorization_url: str
    state: str


class ConnectionStatus(BaseModel):
    """Status of a data connection."""
    provider: DataProvider
    is_connected: bool
    connected_at: Optional[datetime] = None
    account_name: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    last_refreshed: Optional[datetime] = None