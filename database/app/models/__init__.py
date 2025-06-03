"""Data models for service connections."""

from .connection import (
    Connection,
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionStatus,
    Credential,
    CredentialCreate,
    ProviderType,
    AuthType,
    OAuthAuthorizeResponse,
    OAuthExchangeRequest,
    ProviderConfig
)

__all__ = [
    "Connection",
    "ConnectionCreate", 
    "ConnectionUpdate",
    "ConnectionStatus",
    "Credential",
    "CredentialCreate",
    "ProviderType",
    "AuthType",
    "OAuthAuthorizeResponse",
    "OAuthExchangeRequest",
    "ProviderConfig"
]