"""Configuration for the editor backend service."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os
from pathlib import Path

# Import shared configuration
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "shared"))
from config_base import ServiceConfig
from env_loader import load_env_for_service

# Load environment variables including tunnel config
load_env_for_service("editor-backend")


class Settings(ServiceConfig):
    """Editor backend specific settings."""
    
    # Service identification
    service_name: str = "editor-backend"
    port: int = 8001
    host: str = "0.0.0.0"
    
    # API settings (aliases for compatibility)
    @property
    def api_host(self) -> str:
        return self.host
    
    @property
    def api_port(self) -> int:
        return self.port
    
    # Editor-specific paths
    prompts_dir: Path = Path("../agents/prompts")
    personas_dir: Path = Path("../agents/prompts/merchants/personas")
    workflows_dir: Path = Path("../agents/prompts/workflows")
    scenarios_dir: Path = Path("../agents/prompts/scenarios")
    
    # CORS settings
    frontend_url: str = "http://localhost:3458"
    public_url: Optional[str] = Field(None, env="PUBLIC_URL")
    editor_url: Optional[str] = Field(None, env="EDITOR_URL")  # From tunnel detection
    environment: str = "development"
    
    @property
    def allowed_origins(self) -> list[str]:
        """Get allowed CORS origins."""
        origins = [
            self.frontend_url,
            "http://localhost:3458",  # Editor frontend default
        ]
        
        # Add ngrok URLs if detected
        if self.public_url:
            origins.append(self.public_url)
            
        # Add editor URL from tunnel detection
        if self.editor_url:
            origins.append(self.editor_url)
            
        # Add custom domain if configured
        if "hirecj.ai" in self.frontend_url:
            origins.extend([
                "https://editor.hirecj.ai",
                "https://amir-editor.hirecj.ai",
            ])
            
        return list(set(filter(None, origins)))
    
    model_config = SettingsConfigDict(
        env_file = "../.env",
        env_file_encoding = "utf-8",
        extra = "ignore"  # Ignore extra fields from .env
    )


# Create settings instance
settings = Settings()