"""Configuration settings for the service connections backend."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server Configuration
    app_host: str = Field("0.0.0.0", env="APP_HOST")
    app_port: int = Field(8002, env="APP_PORT")
    
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


# Create global settings instance
settings = Settings()