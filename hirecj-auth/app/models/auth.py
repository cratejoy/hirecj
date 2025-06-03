"""Authentication and session models."""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


class AuthProvider(str, Enum):
    """Supported authentication providers."""
    SHOPIFY = "shopify"
    GOOGLE = "google"
    EMAIL = "email"  # Future: email/password auth


class UserSession(BaseModel):
    """User session information."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier from provider")
    provider: AuthProvider = Field(..., description="Authentication provider")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User display name")
    provider_data: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific user data")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_active: bool = True


class OAuthState(BaseModel):
    """OAuth state for security."""
    state: str = Field(..., description="Random state string")
    provider: str = Field(..., description="OAuth provider name")
    redirect_uri: str = Field(..., description="Callback URL")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    """Login request model."""
    provider: AuthProvider
    redirect_url: Optional[str] = None
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class LoginResponse(BaseModel):
    """Login response model."""
    authorization_url: str
    state: str