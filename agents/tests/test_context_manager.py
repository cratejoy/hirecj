"""Tests for ConversationContextManager."""

from datetime import datetime
from unittest.mock import patch, mock_open
import yaml

from app.context_manager import ConversationContextManager, get_context_manager
from app.models import Conversation, Message, ConversationState


class TestConversationContextManager:
    """Test ConversationContextManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_messages = [
            Message(
                timestamp=datetime.utcnow(),
                sender="merchant",
                content="I need help with shipping",
            ),
            Message(
                timestamp=datetime.utcnow(),
                sender="cj",
                content="I'd be happy to help with shipping. What's the issue?",
            ),
            Message(
                timestamp=datetime.utcnow(),
                sender="merchant",
                content="Customers are complaining about delays",
            ),
            Message(
                timestamp=datetime.utcnow(),
                sender="cj",
                content="Let me check the shipping data for you.",
            ),
        ]

        self.test_conversation = Conversation(
            id="test-123",
            created_at=datetime.utcnow(),
            scenario_name="test_scenario",
            merchant_name="test_merchant",
            messages=self.test_messages,
        )

    @patch("app.context_manager.Path.exists")
    def test_load_config_file_exists(self, mock_exists):
        """Test loading config from YAML file."""
        mock_exists.return_value = True
        config_data = {"window_size": 5}

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))):
            manager = ConversationContextManager()

            assert manager.window_size == 5

    @patch("app.context_manager.Path.exists")
    def test_load_config_file_missing(self, mock_exists):
        """Test using default config when file is missing."""
        mock_exists.return_value = False

        with patch("app.config.settings") as mock_settings:
            mock_settings.context_window_size = 10
            manager = ConversationContextManager()

            assert manager.window_size == 10

    @patch("app.context_manager.Path.exists")
    def test_get_context_for_cj_empty(self, mock_exists):
        """Test getting context for empty conversation."""
        mock_exists.return_value = False
        manager = ConversationContextManager()

        empty_conv = Conversation(
            id="empty",
            created_at=datetime.utcnow(),
            scenario_name="test",
            merchant_name="test",
        )

        context = manager.get_context_for_cj(empty_conv)
        assert context == "No previous messages."

    @patch("app.context_manager.Path.exists")
    def test_get_context_for_cj_with_messages(self, mock_exists):
        """Test getting context with messages."""
        mock_exists.return_value = False
        manager = ConversationContextManager()
        manager.window_size = 3

        context = manager.get_context_for_cj(self.test_conversation)

        # Should only include last 3 messages
        assert "MERCHANT: Customers are complaining about delays" in context
        assert "CJ: Let me check the shipping data for you." in context
        assert "I need help with shipping" not in context  # First message excluded

    @patch("app.context_manager.Path.exists")
    def test_get_context_for_cj_respects_window_size(self, mock_exists):
        """Test that context respects window size."""
        mock_exists.return_value = False
        manager = ConversationContextManager()
        manager.window_size = 2

        context = manager.get_context_for_cj(self.test_conversation)
        lines = context.strip().split("\n")

        assert len(lines) == 2
        assert "MERCHANT: Customers are complaining about delays" in lines[0]
        assert "CJ: Let me check the shipping data for you." in lines[1]

    @patch("app.context_manager.Path.exists")
    def test_get_conversation_state(self, mock_exists):
        """Test getting conversation state."""
        mock_exists.return_value = False
        manager = ConversationContextManager()
        manager.window_size = 2

        state = manager.get_conversation_state(self.test_conversation)

        assert isinstance(state, ConversationState)
        assert len(state.context_window) == 2
        assert (
            state.context_window[0].content == "Customers are complaining about delays"
        )
        assert (
            state.context_window[1].content == "Let me check the shipping data for you."
        )

    @patch("app.context_manager.Path.exists")
    def test_singleton_pattern(self, mock_exists):
        """Test that get_instance returns singleton."""
        mock_exists.return_value = False

        manager1 = ConversationContextManager.get_instance()
        manager2 = ConversationContextManager.get_instance()

        assert manager1 is manager2

    @patch("app.context_manager.Path.exists")
    def test_get_context_manager_helper(self, mock_exists):
        """Test the helper function returns singleton."""
        mock_exists.return_value = False

        manager1 = get_context_manager()
        manager2 = get_context_manager()

        assert manager1 is manager2

    @patch("app.context_manager.Path.exists")
    def test_custom_config_path(self, mock_exists):
        """Test using custom config path."""
        mock_exists.return_value = True
        config_data = {"window_size": 15}

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))):
            # Reset singleton for this test
            ConversationContextManager._instance = None

            manager = ConversationContextManager.get_instance("custom/path.yaml")
            assert manager.window_size == 15
