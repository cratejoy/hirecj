"""Configuration settings for the service connections backend."""

from pathlib import Path
from typing import Optional
import logging

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server Configuration
    app_host: str = Field("0.0.0.0", env="APP_HOST")
    app_port: int = Field(8002, env="APP_PORT")
    
    # Public URL Configuration
    public_url: str = Field("", env="PUBLIC_URL")
    frontend_url: str = Field("http://localhost:3456", env="FRONTEND_URL")
    auth_url: str = Field("http://localhost:8103", env="AUTH_URL")
    
    # Database Configuration
    database_url: str = Field(
        "postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj_connections",
        env="DATABASE_URL"
    )
    
    # OAuth Configuration (placeholders for now)
    freshdesk_client_id: Optional[str] = Field(None, env="FRESHDESK_CLIENT_ID")
    freshdesk_client_secret: Optional[str] = Field(None, env="FRESHDESK_CLIENT_SECRET")
    freshdesk_domain: Optional[str] = Field(None, env="FRESHDESK_DOMAIN")
    
    google_client_id: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID") 
    google_client_secret: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    
    # Storage Configuration (now using postgres)
    storage_backend: str = Field("postgres", env="STORAGE_BACKEND")
    
    # API Configuration
    api_prefix: str = Field("/api/v1", env="API_PREFIX")
    debug: bool = Field(False, env="DEBUG")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("public_url", mode="before")
    @classmethod
    def detect_tunnel_url(cls, v: Optional[str]) -> str:
        """Auto-detect tunnel URL from .env.tunnel if not set."""
        if v:
            return v
        
        tunnel_env_path = Path(".env.tunnel")
        if tunnel_env_path.exists():
            try:
                with open(tunnel_env_path) as f:
                    for line in f:
                        if line.startswith("PUBLIC_URL="):
                            tunnel_url = line.split("=", 1)[1].strip()
                            if tunnel_url:
                                logger.info(f"📡 Using detected tunnel URL: {tunnel_url}")
                                return tunnel_url
            except Exception:
                pass
        
        # Return service-specific default
        return f"http://localhost:8002"


# Create global settings instance
settings = Settings()