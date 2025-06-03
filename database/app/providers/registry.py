"""Provider configuration registry."""

from typing import Dict, List, Optional

from app.models import ProviderType, ProviderConfig, AuthType


# Provider configurations
PROVIDER_CONFIGS: Dict[ProviderType, ProviderConfig] = {
    ProviderType.FRESHDESK: ProviderConfig(
        provider=ProviderType.FRESHDESK,
        name="Freshdesk",
        auth_types=[AuthType.OAUTH2, AuthType.API_KEY],
        oauth_config={
            "authorization_url": "https://{domain}.freshdesk.com/oauth/authorize",
            "token_url": "https://{domain}.freshdesk.com/oauth/token",
            "scopes": ["read", "write", "delete"],
            "requires_domain": True
        },
        required_fields={
            AuthType.OAUTH2: ["domain"],
            AuthType.API_KEY: ["domain", "api_key"]
        },
        optional_fields={
            AuthType.OAUTH2: ["scopes"],
            AuthType.API_KEY: []
        },
        features=["tickets", "contacts", "companies", "conversations"],
        icon_url="https://example.com/icons/freshdesk.png"
    ),
    
    ProviderType.GOOGLE_ANALYTICS: ProviderConfig(
        provider=ProviderType.GOOGLE_ANALYTICS,
        name="Google Analytics",
        auth_types=[AuthType.OAUTH2],
        oauth_config={
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": [
                "https://www.googleapis.com/auth/analytics.readonly",
                "https://www.googleapis.com/auth/analytics"
            ]
        },
        required_fields={
            AuthType.OAUTH2: []
        },
        optional_fields={
            AuthType.OAUTH2: ["account_id", "property_id", "view_id"]
        },
        features=["reporting", "realtime", "management", "user_activity"],
        icon_url="https://example.com/icons/google-analytics.png"
    ),
    
    ProviderType.SLACK: ProviderConfig(
        provider=ProviderType.SLACK,
        name="Slack",
        auth_types=[AuthType.OAUTH2],
        oauth_config={
            "authorization_url": "https://slack.com/oauth/v2/authorize",
            "token_url": "https://slack.com/api/oauth.v2.access",
            "scopes": [
                "channels:read",
                "channels:write",
                "chat:write",
                "users:read"
            ]
        },
        required_fields={
            AuthType.OAUTH2: []
        },
        optional_fields={
            AuthType.OAUTH2: ["team_id", "channel"]
        },
        features=["messaging", "channels", "users", "files"],
        icon_url="https://example.com/icons/slack.png"
    ),
    
    ProviderType.HUBSPOT: ProviderConfig(
        provider=ProviderType.HUBSPOT,
        name="HubSpot",
        auth_types=[AuthType.OAUTH2, AuthType.API_KEY],
        oauth_config={
            "authorization_url": "https://app.hubspot.com/oauth/authorize",
            "token_url": "https://api.hubapi.com/oauth/v1/token",
            "scopes": ["contacts", "forms", "tickets"]
        },
        required_fields={
            AuthType.OAUTH2: [],
            AuthType.API_KEY: ["api_key"]
        },
        optional_fields={
            AuthType.OAUTH2: ["portal_id"],
            AuthType.API_KEY: ["portal_id"]
        },
        features=["contacts", "companies", "deals", "tickets", "marketing"],
        icon_url="https://example.com/icons/hubspot.png"
    ),
    
    ProviderType.SALESFORCE: ProviderConfig(
        provider=ProviderType.SALESFORCE,
        name="Salesforce",
        auth_types=[AuthType.OAUTH2],
        oauth_config={
            "authorization_url": "https://login.salesforce.com/services/oauth2/authorize",
            "token_url": "https://login.salesforce.com/services/oauth2/token",
            "scopes": ["api", "refresh_token", "offline_access"]
        },
        required_fields={
            AuthType.OAUTH2: []
        },
        optional_fields={
            AuthType.OAUTH2: ["instance_url", "organization_id"]
        },
        features=["leads", "contacts", "opportunities", "accounts", "reports"],
        icon_url="https://example.com/icons/salesforce.png"
    )
}


def get_provider_config(provider: ProviderType) -> Optional[ProviderConfig]:
    """Get configuration for a provider."""
    return PROVIDER_CONFIGS.get(provider)


def list_providers() -> List[ProviderConfig]:
    """List all available provider configurations."""
    return list(PROVIDER_CONFIGS.values())


def is_provider_supported(provider: ProviderType) -> bool:
    """Check if a provider is supported."""
    return provider in PROVIDER_CONFIGS


# Export registry functions
provider_registry = {
    "get_config": get_provider_config,
    "list_providers": list_providers,
    "is_supported": is_provider_supported
}