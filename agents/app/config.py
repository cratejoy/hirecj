"""Central configuration management for HireCJ.

All configurable values should be defined here, with sensible defaults
and environment variable overrides for deployment flexibility.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import logging

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Add parent directories to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.env_loader import load_env_for_service

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # API Configuration
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    # Database Configuration
    supabase_connection_string: Optional[str] = Field(None, env="SUPABASE_CONNECTION_STRING")

    # Public URL Configuration
    public_url: str = Field("", env="PUBLIC_URL")
    frontend_url: str = Field("http://localhost:3456", env="HOMEPAGE_URL")
    
    # Service URLs (from shared config)
    auth_service_url: str = Field("http://localhost:8103", env="AUTH_SERVICE_URL")
    agents_service_url: str = Field("http://localhost:8100", env="AGENTS_SERVICE_URL")
    homepage_url: str = Field("http://localhost:3456", env="HOMEPAGE_URL")
    knowledge_service_url: str = Field("http://localhost:8004", env="KNOWLEDGE_SERVICE_URL")
    
    # Legacy alias for compatibility
    auth_url: str = Field("http://localhost:8103", env="AUTH_SERVICE_URL")

    # Server Configuration
    app_host: str = Field("0.0.0.0", env="APP_HOST")
    app_port: int = Field(8100, env="AGENTS_SERVICE_PORT")
    websocket_port: int = Field(8001, env="WEBSOCKET_PORT")


    # Paths
    base_dir: str = Field(".", env="BASE_DIR")
    data_dir: str = Field("data", env="DATA_DIR")
    conversations_dir: str = Field("data/conversations", env="CONVERSATIONS_DIR")
    universes_dir: str = Field("data/universes", env="UNIVERSES_DIR")
    prompts_dir: str = Field("prompts", env="PROMPTS_DIR")
    logs_dir: str = Field("logs", env="LOGS_DIR")

    # File Extensions
    json_ext: str = ".json"
    yaml_ext: str = ".yaml"
    yml_ext: str = ".yml"

    # Timeouts (in seconds)
    default_timeout: int = Field(30, env="DEFAULT_TIMEOUT")
    api_timeout: int = Field(30, env="API_TIMEOUT")
    websocket_timeout: int = Field(10, env="WEBSOCKET_TIMEOUT")
    message_timeout: int = Field(15, env="MESSAGE_TIMEOUT")

    # Cache Configuration
    cache_ttl: int = Field(3600, env="CACHE_TTL")  # 1 hour
    cache_ttl_short: int = Field(600, env="CACHE_TTL_SHORT")  # 10 minutes

    # Conversation Limits
    max_conversation_turns: int = Field(10, env="MAX_CONVERSATION_TURNS")
    context_window_size: int = Field(10, env="CONTEXT_WINDOW_SIZE")
    recent_history_limit: int = Field(5, env="RECENT_HISTORY_LIMIT")
    max_message_length: int = Field(200, env="MAX_MESSAGE_LENGTH")

    # Model Configuration
    default_temperature: float = Field(0.3, env="DEFAULT_TEMPERATURE")
    universe_temperature: float = Field(0.2, env="UNIVERSE_TEMPERATURE")
    max_tokens_evaluation: int = Field(1000, env="MAX_TOKENS_EVALUATION")
    max_retries: int = Field(3, env="MAX_RETRIES")
    fact_extraction_model: str = Field("gpt-4o-mini", env="FACT_EXTRACTION_MODEL")

    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_max_bytes: int = Field(10_485_760, env="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(5, env="LOG_BACKUP_COUNT")

    # Performance Configuration
    batch_size: int = Field(5, env="BATCH_SIZE")
    max_concurrent_requests: int = Field(50, env="MAX_CONCURRENT_REQUESTS")
    rate_limit_delay: float = Field(0.1, env="RATE_LIMIT_DELAY")
    cache_warm_concurrency: int = Field(3, env="CACHE_WARM_CONCURRENCY")
    slow_response_threshold: float = Field(5.0, env="SLOW_RESPONSE_THRESHOLD")

    # API Configuration
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_ws_url: str = Field("ws://localhost:8100", env="HIRECJ_API_URL")

    # WebSocket Configuration
    websocket_ping_interval: int = Field(20, env="WEBSOCKET_PING_INTERVAL")
    websocket_ping_timeout: int = Field(10, env="WEBSOCKET_PING_TIMEOUT")
    websocket_response_timeout: float = Field(30.0, env="WEBSOCKET_RESPONSE_TIMEOUT")
    websocket_check_interval: float = Field(0.5, env="WEBSOCKET_CHECK_INTERVAL")

    # Session Configuration
    session_cleanup_timeout: int = Field(
        300, env="SESSION_CLEANUP_TIMEOUT"
    )  # 5 minutes

    # Search and Display Limits
    max_search_results: int = Field(10, env="MAX_SEARCH_RESULTS")
    max_conversation_turns_display: int = Field(4, env="MAX_CONVERSATION_TURNS_DISPLAY")

    # Model Token Limits
    max_tokens_standard: int = Field(1000, env="MAX_TOKENS_STANDARD")
    max_tokens_universe: int = Field(100000, env="MAX_TOKENS_UNIVERSE")

    # Universe Generation Settings
    universe_timeline_days: int = Field(90, env="UNIVERSE_TIMELINE_DAYS")
    universe_current_day: int = Field(45, env="UNIVERSE_CURRENT_DAY")
    universe_events_min: int = Field(8, env="UNIVERSE_EVENTS_MIN")
    universe_events_max: int = Field(12, env="UNIVERSE_EVENTS_MAX")
    universe_customers_min: int = Field(12, env="UNIVERSE_CUSTOMERS_MIN")
    universe_customers_max: int = Field(15, env="UNIVERSE_CUSTOMERS_MAX")
    universe_tickets_min: int = Field(35, env="UNIVERSE_TICKETS_MIN")
    universe_tickets_max: int = Field(50, env="UNIVERSE_TICKETS_MAX")

    # UI/Display Settings
    default_pagination_limit: int = Field(50, env="DEFAULT_PAGINATION_LIMIT")
    max_pagination_limit: int = Field(100, env="MAX_PAGINATION_LIMIT")
    trending_issues_display_count: int = Field(3, env="TRENDING_ISSUES_DISPLAY_COUNT")
    search_results_display_count: int = Field(5, env="SEARCH_RESULTS_DISPLAY_COUNT")
    universe_data_preview_length: int = Field(1000, env="UNIVERSE_DATA_PREVIEW_LENGTH")

    # Business Metrics Configuration
    trending_window_days: int = Field(7, env="TRENDING_WINDOW_DAYS")
    top_trending_count: int = Field(3, env="TOP_TRENDING_COUNT")

    # API URLs
    openai_api_url: str = Field(
        "https://api.openai.com/v1/chat/completions", env="OPENAI_API_URL"
    )

    # Feature Flags
    enable_prompt_caching: bool = Field(False, env="ENABLE_PROMPT_CACHING")
    enable_litellm_cache: bool = Field(False, env="ENABLE_LITELLM_CACHE")
    enable_cache_warming: bool = Field(False, env="ENABLE_CACHE_WARMING")
    enable_fact_checking: bool = Field(True, env="ENABLE_FACT_CHECKING")
    enable_performance_metrics: bool = Field(True, env="ENABLE_PERFORMANCE_METRICS")
    enable_verbose_logging: bool = Field(False, env="ENABLE_VERBOSE_LOGGING")

    # Version Information
    default_cj_version: str = Field("v6.0.1", env="DEFAULT_CJ_VERSION")
    default_persona_version: str = Field("v1.0.0", env="DEFAULT_PERSONA_VERSION")

    model_config = SettingsConfigDict(
        env_file=load_env_for_service("agents"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # IMPORTANT: env_ignore_empty ensures empty strings don't override
        env_ignore_empty=True,
    )

    @field_validator("public_url", mode="before")
    @classmethod
    def detect_tunnel_url(cls, v: Optional[str]) -> str:
        """Auto-detect tunnel URL from .env.tunnel if not set."""
        if v:
            return v
        
        # Check for tunnel URL from root .env.tunnel
        root_dir = Path(__file__).parent.parent.parent
        tunnel_env_path = root_dir / ".env.tunnel"
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
        return f"http://localhost:8100"

    def get_conversation_path(self, filename: str) -> str:
        """Get full path for a conversation file."""
        return os.path.join(self.conversations_dir, filename)

    def get_universe_path(self, filename: str) -> str:
        """Get full path for a universe file."""
        return os.path.join(self.universes_dir, filename)

    def get_prompt_path(self, *parts: str) -> str:
        """Get full path for a prompt file."""
        return os.path.join(self.prompts_dir, *parts)

    def get_log_path(self, filename: str) -> str:
        """Get full path for a log file."""
        return os.path.join(self.logs_dir, filename)


# Global settings instance
settings = Settings()

# Export commonly used values as constants for convenience
CACHE_TTL = settings.cache_ttl
DEFAULT_TIMEOUT = settings.default_timeout
MAX_RETRIES = settings.max_retries
CONTEXT_WINDOW_SIZE = settings.context_window_size
