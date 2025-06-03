"""Tests for ConversationStorage service."""

import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open, Mock

from app.services.conversation_storage import ConversationStorage
from app.services.session_manager import Session
from app.models import Conversation, Message


class TestConversationStorage:
    """Test ConversationStorage class."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("app.services.conversation_storage.Path.mkdir"):
            self.storage = ConversationStorage()

        self.test_conversation = Conversation(
            id="test-conv-123",
            created_at=datetime.utcnow(),
            scenario_name="test_scenario",
            merchant_name="test_merchant",
            messages=[
                Message(
                    timestamp=datetime.utcnow(), sender="merchant", content="Hello CJ"
                ),
                Message(
                    timestamp=datetime.utcnow(),
                    sender="cj",
                    content="Hello! How can I help you today?",
                ),
            ],
        )

        # Create test session
        self.test_session = Session(self.test_conversation)
        self.test_session.id = "session-123"

    def test_initialization_creates_directory(self):
        """Test that ConversationStorage creates directory on init."""
        with patch("app.services.conversation_storage.Path.mkdir") as mock_mkdir:
            ConversationStorage()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_custom_base_dir(self):
        """Test initialization with custom base directory."""
        with patch("app.services.conversation_storage.Path.mkdir"):
            storage = ConversationStorage(base_dir="/custom/path")
            assert str(storage.base_dir) == "/custom/path"

    @patch("builtins.open", new_callable=mock_open)
    @patch("app.services.conversation_storage.datetime")
    def test_save_session(self, mock_datetime, mock_file):
        """Test saving a session to disk."""
        # Mock datetime to get consistent filename
        mock_now = Mock()
        mock_now.strftime.return_value = "20240101_120000"
        mock_datetime.now.return_value = mock_now

        filepath = self.storage.save_session(self.test_session)

        # Check filename format
        expected_filename = "test_merchant_test_scenario_20240101_120000.json"
        assert filepath.name == expected_filename

        # Check that file was written
        mock_file.assert_called_once()

        # Check JSON structure
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed = json.loads(written_data)

        assert parsed["session_id"] == "session-123"
        assert parsed["conversation"]["id"] == "test-conv-123"
        assert parsed["conversation"]["merchant_name"] == "test_merchant"
        assert parsed["conversation"]["scenario_name"] == "test_scenario"
        assert len(parsed["conversation"]["messages"]) == 2

    @patch("builtins.open", new_callable=mock_open)
    def test_save_session_with_special_characters(self, mock_file):
        """Test saving session with special characters in names."""
        # Create conversation with spaces and special chars
        self.test_conversation.merchant_name = "Test Merchant"
        self.test_conversation.scenario_name = "Test Scenario!"

        filepath = self.storage.save_session(self.test_session)

        # Check that spaces are replaced with underscores
        assert "test_merchant" in filepath.name
        assert "test_scenario!" in filepath.name

    def test_load_conversation_success(self):
        """Test loading conversation from file."""
        test_data = {
            "session_id": "session-123",
            "created_at": datetime.utcnow().isoformat(),
            "conversation": {
                "id": "test-123",
                "created_at": datetime.utcnow().isoformat(),
                "scenario_name": "test_scenario",
                "merchant_name": "test_merchant",
                "workflow": "daily_briefing",
                "messages": [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "sender": "merchant",
                        "content": "Hello",
                        "metadata": {"source": "web"},
                    }
                ],
            },
            "metrics": {"messages": 1},
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(test_data))):
            conversation = self.storage.load_conversation(Path("test.json"))

            assert conversation is not None
            assert conversation.id == "test-123"
            assert conversation.merchant_name == "test_merchant"
            assert conversation.scenario_name == "test_scenario"
            assert conversation.workflow == "daily_briefing"
            assert len(conversation.messages) == 1
            assert conversation.messages[0].content == "Hello"
            assert conversation.messages[0].metadata == {"source": "web"}

    def test_load_conversation_file_not_found(self):
        """Test loading non-existent conversation."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            conversation = self.storage.load_conversation(Path("nonexistent.json"))
            assert conversation is None

    def test_load_conversation_invalid_json(self):
        """Test loading conversation with invalid JSON."""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            conversation = self.storage.load_conversation(Path("invalid.json"))
            assert conversation is None

    @patch.object(Path, "glob")
    def test_list_conversations(self, mock_glob):
        """Test listing saved conversations."""
        # Mock file paths
        mock_files = [
            Path("data/conversations/conv1.json"),
            Path("data/conversations/conv2.json"),
            Path("data/conversations/conv3.json"),
        ]
        mock_glob.return_value = mock_files

        conversations = self.storage.list_conversations()

        assert len(conversations) == 3
        assert all(isinstance(p, Path) for p in conversations)
        assert conversations[0].name == "conv1.json"

    @patch.object(Path, "glob")
    def test_list_conversations_empty(self, mock_glob):
        """Test listing conversations when directory is empty."""
        mock_glob.return_value = []

        conversations = self.storage.list_conversations()

        assert len(conversations) == 0

    @patch("builtins.open", new_callable=mock_open)
    def test_save_session_with_workflow(self, mock_file):
        """Test saving session with workflow information."""
        self.test_conversation.workflow = "daily_briefing"

        self.storage.save_session(self.test_session)

        # Check that workflow was saved
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed = json.loads(written_data)

        assert parsed["conversation"]["workflow"] == "daily_briefing"
