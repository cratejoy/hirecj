"""Configuration settings for the HireCJ auth service."""

import os
import sys
import logging
from typing import Optional
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Add parent directories to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.env_loader import load_env_for_service

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_ignore_empty=True  # Ignore empty string values from env
    )
    
    # Server Configuration
    app_host: str = Field("0.0.0.0", env="APP_HOST")
    app_port: int = Field(8103, env="AUTH_SERVICE_PORT")  # Use service-specific port
    
    # Service URLs (from shared config)
    auth_service_url: str = Field("http://localhost:8103", env="AUTH_SERVICE_URL")
    agents_service_url: str = Field("http://localhost:8000", env="AGENTS_SERVICE_URL")
    homepage_url: str = Field("http://localhost:3456", env="HOMEPAGE_URL")
    
    # Database Configuration
    database_url: str = Field(
        "postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj_auth",
        env="AUTH_DATABASE_URL"
    )
    
    # Supabase connection for shared tables
    supabase_connection_string: str = Field(
        env="SUPABASE_CONNECTION_STRING"
    )
    
    # Security Configuration
    jwt_secret: str = Field(
        "dev-secret-change-in-production",
        env="JWT_SECRET"
    )
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(24, env="JWT_EXPIRATION_HOURS")
    
    encryption_key: str = Field(
        "dev-encryption-key-change-in-production",
        env="ENCRYPTION_KEY"
    )
    
    # OAuth Configuration - Login Providers
    shopify_client_id: Optional[str] = Field(None, env="SHOPIFY_CLIENT_ID")
    shopify_client_secret: Optional[str] = Field(None, env="SHOPIFY_CLIENT_SECRET")
    shopify_scopes: str = Field(
        "read_products,read_orders,read_customers",
        env="SHOPIFY_SCOPES"
    )
    shopify_custom_install_link: Optional[str] = Field(None, env="SHOPIFY_CUSTOM_INSTALL_LINK")
    
    # OAuth Configuration - Data Providers
    klaviyo_client_id: Optional[str] = Field(None, env="KLAVIYO_CLIENT_ID")
    klaviyo_client_secret: Optional[str] = Field(None, env="KLAVIYO_CLIENT_SECRET")
    
    google_client_id: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    
    freshdesk_client_id: Optional[str] = Field(None, env="FRESHDESK_CLIENT_ID")
    freshdesk_client_secret: Optional[str] = Field(None, env="FRESHDESK_CLIENT_SECRET")
    
    # OAuth Redirect Configuration
    # Single source of truth - must be explicitly set, no magic fallbacks
    oauth_redirect_base_url: str = Field(
        env="OAUTH_REDIRECT_BASE_URL"
    )
    
    # Public URL Configuration
    public_url: str = Field("", env="PUBLIC_URL")
    
    # Frontend URLs (for redirects after auth)
    frontend_url: str = Field(
        "http://localhost:3456",
        env="HOMEPAGE_URL"  # Use HOMEPAGE_URL which is set by tunnel detector
    )
    frontend_success_path: str = Field(
        "/auth/success",
        env="FRONTEND_SUCCESS_PATH"
    )
    frontend_error_path: str = Field(
        "/auth/error",
        env="FRONTEND_ERROR_PATH"
    )
    
    # API Configuration
    api_prefix: str = Field("/api/v1", env="API_PREFIX")
    debug: bool = Field(False, env="DEBUG")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    
    # CORS Configuration
    allowed_origins: list[str] = Field(
        default_factory=list,
        env="ALLOWED_ORIGINS"
    )
    
    # Ngrok tunnel configuration
    ngrok_enabled: bool = Field(False, env="NGROK_ENABLED")
    ngrok_domain: Optional[str] = Field(None, env="NGROK_DOMAIN")
    
    model_config = SettingsConfigDict(
        env_file=load_env_for_service("auth"),
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from .env files
        env_ignore_empty=True,  # Don't let empty strings override values
    )
    
    @field_validator("oauth_redirect_base_url", mode="after")
    @classmethod
    def validate_oauth_redirect_url(cls, v: Optional[str], info) -> str:
        """Validate OAuth redirect base URL is set."""
        if not v:
            raise ValueError(
                "OAUTH_REDIRECT_BASE_URL must be set. "
                "Use 'https://amir-auth.hirecj.ai' for production or appropriate tunnel URL for development."
            )
        
        # Log what we're using for clarity
        logger.info(f"🔐 OAuth redirect base URL: {v}")
        return v
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def build_allowed_origins(cls, v, info) -> list[str]:
        """Build allowed origins list including tunnel URLs."""
        # Normalize env value → Python set[str]
        if not v:
            origins: set[str] = set()
        elif isinstance(v, str):
            # Value may be a JSON list or a comma-separated string
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, (list, tuple)):
                    origins = set(parsed)
                else:
                    origins = set(s.strip() for s in v.split(",") if s.strip())
            except json.JSONDecodeError:
                origins = set(s.strip() for s in v.split(",") if s.strip())
        elif isinstance(v, (list, tuple, set)):
            origins = set(v)
        else:
            origins = set()

        # Always include localhost origins
        origins.update({
            "http://localhost:3456",
            "http://localhost:8000",
            "http://localhost:8103",
            "http://localhost:8002",
        })
        
        # Get values from ValidationInfo
        values = info.data if hasattr(info, 'data') else {}
        
        # Add frontend & homepage URLs if set
        for url_key in ("frontend_url", "homepage_url"):
            url = values.get(url_key)
            if url:
                origins.add(url)
        
        # Add public URL if set
        public_url = values.get("public_url")
        if public_url:
            origins.add(public_url)
        
        # Add OAuth redirect URL if set
        oauth_url = values.get("oauth_redirect_base_url")
        if oauth_url and not oauth_url.startswith("http://localhost"):
            origins.add(oauth_url)
        
        # Add reserved domains if detected
        if frontend_url and "hirecj.ai" in frontend_url:
            origins.update([
                "https://amir.hirecj.ai",
                "https://amir-auth.hirecj.ai",
            ])
        
        # Filter out empty strings and return as list
        return list(filter(None, origins))
    
    def get_oauth_callback_url(self, provider: str) -> str:
        """Get the full OAuth callback URL for a provider."""
        base_url = self.oauth_redirect_base_url.rstrip("/")
        # The path should be /api/v1/{provider}/callback to match router prefixes
        return f"{base_url}{self.api_prefix}/{provider}/callback"
    
    def log_oauth_urls(self):
        """Log all OAuth callback URLs for easy copying."""
        if self.debug:
            logger.info("🔐 OAuth Callback URLs:")
            logger.info(f"  Base URL: {self.oauth_redirect_base_url}")
            # Removed "google" from the list of providers
            for provider in ["shopify", "klaviyo", "freshdesk"]:
                logger.info(f"  {provider.title()}: {self.get_oauth_callback_url(provider)}")
    
    def __init__(self, **kwargs):
        """Initialize settings and ensure proper frontend URL."""
        super().__init__(**kwargs)
        
        # If homepage_url is set and looks like a tunnel URL, use it for frontend_url
        if self.homepage_url and ("ngrok" in self.homepage_url or "hirecj.ai" in self.homepage_url):
            self.frontend_url = self.homepage_url
            logger.info(f"🔧 Using homepage_url for frontend_url: {self.frontend_url}")


# Create global settings instance with hierarchical loading
settings = Settings()
