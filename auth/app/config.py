"""Configuration settings for the HireCJ auth service."""

import os
import logging
from typing import Optional
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server Configuration
    app_host: str = Field("0.0.0.0", env="APP_HOST")
    app_port: int = Field(8103, env="APP_PORT")
    
    # Database Configuration
    database_url: str = Field(
        "postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj_auth",
        env="DATABASE_URL"
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
    
    # OAuth Configuration - Data Providers
    klaviyo_client_id: Optional[str] = Field(None, env="KLAVIYO_CLIENT_ID")
    klaviyo_client_secret: Optional[str] = Field(None, env="KLAVIYO_CLIENT_SECRET")
    
    google_client_id: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    
    freshdesk_client_id: Optional[str] = Field(None, env="FRESHDESK_CLIENT_ID")
    freshdesk_client_secret: Optional[str] = Field(None, env="FRESHDESK_CLIENT_SECRET")
    
    # OAuth Redirect Configuration
    oauth_redirect_base_url: str = Field(
        "http://localhost:8003",
        env="OAUTH_REDIRECT_BASE_URL"
    )
    
    # Public URL Configuration
    public_url: str = Field("", env="PUBLIC_URL")
    
    # Frontend URLs (for redirects after auth)
    frontend_url: str = Field(
        "http://localhost:3456",
        env="FRONTEND_URL"
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from .env files
    
    @field_validator("oauth_redirect_base_url", mode="before")
    @classmethod
    def detect_tunnel_url(cls, v: Optional[str], values) -> str:
        """Automatically detect and use ngrok tunnel URL if available."""
        # If explicitly set, use that
        if v:
            return v
        
        # Check for tunnel URL from .env.tunnel (created by tunnel detector)
        tunnel_env_path = Path(".env.tunnel")
        if tunnel_env_path.exists():
            try:
                with open(tunnel_env_path) as f:
                    for line in f:
                        # Also check OAUTH_REDIRECT_BASE_URL for auth service
                        if line.startswith("OAUTH_REDIRECT_BASE_URL="):
                            tunnel_url = line.split("=", 1)[1].strip()
                            if tunnel_url:
                                logger.info(f"📡 Using detected tunnel URL: {tunnel_url}")
                                return tunnel_url
                        elif line.startswith("PUBLIC_URL="):
                            tunnel_url = line.split("=", 1)[1].strip()
                            if tunnel_url:
                                logger.info(f"📡 Using detected tunnel URL: {tunnel_url}")
                                return tunnel_url
            except Exception as e:
                logger.warning(f"Failed to read tunnel URL: {e}")
        
        # Default to localhost
        default_url = f"http://localhost:{values.get('app_port', 8003)}"
        logger.info(f"Using default redirect URL: {default_url}")
        return default_url
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def build_allowed_origins(cls, v, info) -> list[str]:
        """Build allowed origins list including tunnel URLs."""
        origins = set(v) if v else set()
        
        # Always include localhost origins
        origins.update([
            "http://localhost:3456",
            "http://localhost:8000",
            "http://localhost:8103",
            "http://localhost:8002",
        ])
        
        # Get values from ValidationInfo
        values = info.data if hasattr(info, 'data') else {}
        
        # Add frontend URL if set
        frontend_url = values.get("frontend_url")
        if frontend_url:
            origins.add(frontend_url)
        
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
        # Determine if it's a login provider or data provider
        login_providers = ["shopify", "google"]
        if provider.lower() in login_providers:
            return f"{base_url}{self.api_prefix}/auth/callback/{provider}"
        else:
            return f"{base_url}{self.api_prefix}/oauth/callback/{provider}"
    
    def log_oauth_urls(self):
        """Log all OAuth callback URLs for easy copying."""
        if self.debug:
            logger.info("🔐 OAuth Callback URLs:")
            logger.info(f"  Base URL: {self.oauth_redirect_base_url}")
            for provider in ["shopify", "google", "klaviyo", "freshdesk"]:
                logger.info(f"  {provider.title()}: {self.get_oauth_callback_url(provider)}")


# Create global settings instance
settings = Settings()

# Load additional env files if they exist
env_files = [".env", ".env.local", ".env.tunnel"]
for env_file in env_files:
    if Path(env_file).exists():
        settings = Settings(_env_file=env_file)