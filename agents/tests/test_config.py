"""Tests for configuration system."""

import os
from unittest.mock import patch
from app.config import Settings


class TestSettings:
    """Test Settings configuration class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        s = Settings()

        # API Configuration
        assert s.app_host == "0.0.0.0"
        assert s.app_port == 8000
        assert s.websocket_port == 8001

        # Paths
        assert s.base_dir == "."
        assert s.data_dir == "data"
        assert s.conversations_dir == "data/conversations"

        # Timeouts
        assert s.default_timeout == 30
        assert s.websocket_timeout == 10

        # Feature flags
        assert s.enable_prompt_caching is False
        assert s.enable_litellm_cache is False
        assert s.enable_fact_checking is True

    @patch.dict(os.environ, {"APP_HOST": "127.0.0.1", "APP_PORT": "9000"})
    def test_env_override(self):
        """Test that environment variables override defaults."""
        s = Settings()

        assert s.app_host == "127.0.0.1"
        assert s.app_port == 9000

    @patch.dict(
        os.environ, {"ENABLE_PROMPT_CACHING": "true", "ENABLE_LITELLM_CACHE": "TRUE"}
    )
    def test_boolean_env_vars(self):
        """Test that boolean environment variables work."""
        s = Settings()

        assert s.enable_prompt_caching is True
        assert s.enable_litellm_cache is True

    def test_path_helpers(self):
        """Test path helper methods."""
        s = Settings()

        assert s.get_conversation_path("test.json") == "data/conversations/test.json"
        assert s.get_universe_path("universe.yaml") == "data/universes/universe.yaml"
        assert s.get_prompt_path("cj", "main.yaml") == "prompts/cj/main.yaml"
        assert s.get_log_path("app.log") == "logs/app.log"

    def test_new_display_settings(self):
        """Test newly added display settings."""
        s = Settings()

        # UI/Display Settings
        assert s.default_pagination_limit == 50
        assert s.max_pagination_limit == 100
        assert s.trending_issues_display_count == 3
        assert s.search_results_display_count == 5
        assert s.universe_data_preview_length == 1000

    def test_conversation_limits(self):
        """Test conversation limit settings."""
        s = Settings()

        assert s.max_conversation_turns == 10
        assert s.context_window_size == 10
        assert s.recent_history_limit == 5
        assert s.max_message_length == 200

    def test_universe_generation_settings(self):
        """Test universe generation settings."""
        s = Settings()

        assert s.universe_timeline_days == 90
        assert s.universe_current_day == 45
        assert s.universe_events_min == 8
        assert s.universe_events_max == 12
        assert s.universe_customers_min == 12
        assert s.universe_customers_max == 15
        assert s.universe_tickets_min == 35
        assert s.universe_tickets_max == 50

    def test_model_config_settings(self):
        """Test model configuration settings."""
        s = Settings()

        assert s.default_temperature == 0.3
        assert s.universe_temperature == 0.2
        assert s.max_tokens_evaluation == 1000
        assert s.max_retries == 3

    def test_websocket_settings(self):
        """Test WebSocket configuration settings."""
        s = Settings()

        assert s.websocket_ping_interval == 20
        assert s.websocket_ping_timeout == 10
        assert s.websocket_response_timeout == 30.0
        assert s.websocket_check_interval == 0.5

    def test_api_configuration(self):
        """Test API configuration settings."""
        s = Settings()

        assert s.api_host == "0.0.0.0"
        assert s.api_port == 8000
        assert s.api_ws_url == "ws://localhost:8000"
        assert s.openai_api_url == "https://api.openai.com/v1/chat/completions"

    def test_settings_singleton(self):
        """Test that the global settings instance is available."""
        from app.config import (
            settings,
            CACHE_TTL,
            DEFAULT_TIMEOUT,
            MAX_RETRIES,
            CONTEXT_WINDOW_SIZE,
        )

        assert settings is not None
        assert isinstance(settings, Settings)

        # Test exported constants
        assert CACHE_TTL == settings.cache_ttl
        assert DEFAULT_TIMEOUT == settings.default_timeout
        assert MAX_RETRIES == settings.max_retries
        assert CONTEXT_WINDOW_SIZE == settings.context_window_size

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "MAX_RETRIES": "5"})
    def test_complex_env_overrides(self):
        """Test various types of environment overrides."""
        s = Settings()

        assert s.log_level == "DEBUG"
        assert s.max_retries == 5
