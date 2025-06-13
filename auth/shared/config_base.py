"""
Base configuration class for all HireCJ services.

Provides common configuration patterns using Pydantic.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceConfig(BaseSettings):
    """Base configuration for all services."""
    
    # Service identification
    service_name: str
    port: int
    host: str = "0.0.0.0"
    
    # Common settings
    log_level: str = "INFO"
    debug: bool = False
    
    # Database (optional - not all services need it)
    database_url: Optional[str] = None
    
    # Redis (optional)
    redis_url: Optional[str] = None
    
    # API Keys (optional)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow environment variables to override .env file
        env_nested_delimiter="__",
        # Validate on assignment
        validate_assignment=True,
    )
    
    def get_bind_address(self) -> str:
        """Get the address to bind the service to."""
        return f"{self.host}:{self.port}"