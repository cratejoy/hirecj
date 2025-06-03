"""Tests for SessionManager service."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from app.services.session_manager import Session, SessionManager
from app.models import Conversation
from app.agents.universe_data_agent import UniverseDataAgent


class TestSession:
    """Test Session class."""

    def test_session_creation(self):
        """Test creating a new session."""
        conversation = Conversation(
            id="test-123",
            created_at=datetime.utcnow(),
            scenario_name="test_scenario",
            merchant_name="test_merchant",
            workflow="daily_briefing",
        )

        session = Session(conversation)

        assert session.id is not None
        assert session.conversation == conversation
        assert session.merchant_name == "test_merchant"
        assert session.scenario_name == "test_scenario"
        assert session.is_active is True
        assert session.metrics["messages"] == 0
        assert session.metrics["errors"] == 0

    def test_session_with_data_agent(self):
        """Test session creation with data agent."""
        conversation = Conversation(
            id="test-123",
            created_at=datetime.utcnow(),
            scenario_name="test_scenario",
            merchant_name="test_merchant",
        )
        data_agent = Mock(spec=UniverseDataAgent)

        session = Session(conversation, data_agent)

        assert session.data_agent == data_agent


class TestSessionManager:
    """Test SessionManager class."""

    def test_create_session_basic(self):
        """Test creating a basic session."""
        manager = SessionManager()

        session = manager.create_session(
            merchant_name="test_merchant", scenario_name="test_scenario"
        )

        assert session is not None
        assert session.merchant_name == "test_merchant"
        assert session.scenario_name == "test_scenario"
        assert session.conversation.workflow is None
        assert session.id in manager._sessions

    def test_create_session_with_workflow(self):
        """Test creating a session with workflow."""
        manager = SessionManager()

        session = manager.create_session(
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            workflow_name="daily_briefing",
        )

        assert session.conversation.workflow == "daily_briefing"
        assert session.conversation.state.workflow == "daily_briefing"

    @patch("app.services.session_manager.UniverseDataAgent")
    def test_create_session_with_universe(self, mock_agent_class):
        """Test session creation loads universe data."""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        manager = SessionManager()
        session = manager.create_session(
            merchant_name="test_merchant", scenario_name="test_scenario"
        )

        mock_agent_class.assert_called_once_with("test_merchant", "test_scenario")
        assert session.data_agent == mock_agent

    @patch("app.services.session_manager.UniverseDataAgent")
    def test_create_session_universe_not_found(self, mock_agent_class):
        """Test session creation continues when universe file not found."""
        mock_agent_class.side_effect = FileNotFoundError("Universe not found")

        manager = SessionManager()
        session = manager.create_session(
            merchant_name="test_merchant", scenario_name="test_scenario"
        )

        assert session is not None
        assert session.data_agent is None
        
    @patch("app.services.session_manager.UniverseDataAgent")
    def test_create_session_universe_real_error(self, mock_agent_class):
        """Test session creation fails fast on real errors."""
        mock_agent_class.side_effect = Exception("Database connection failed")

        manager = SessionManager()
        with pytest.raises(Exception) as exc_info:
            manager.create_session(
                merchant_name="test_merchant", scenario_name="test_scenario"
            )
        assert "Database connection failed" in str(exc_info.value)

    def test_get_session(self):
        """Test retrieving a session."""
        manager = SessionManager()
        session = manager.create_session(
            merchant_name="test_merchant", scenario_name="test_scenario"
        )

        retrieved = manager.get_session(session.id)
        assert retrieved == session

    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session returns None."""
        manager = SessionManager()
        assert manager.get_session("nonexistent") is None

    def test_suspend_session(self):
        """Test suspending a session."""
        manager = SessionManager()
        session = manager.create_session(
            merchant_name="test_merchant", scenario_name="test_scenario"
        )

        manager.suspend_session(session.id)
        assert session.is_active is False

    def test_resume_session(self):
        """Test resuming a suspended session."""
        manager = SessionManager()
        session = manager.create_session(
            merchant_name="test_merchant", scenario_name="test_scenario"
        )

        manager.suspend_session(session.id)
        assert session.is_active is False

        result = manager.resume_session(session.id)
        assert result is True
        assert session.is_active is True

    def test_resume_nonexistent_session(self):
        """Test resuming non-existent session returns False."""
        manager = SessionManager()
        assert manager.resume_session("nonexistent") is False

    def test_end_session(self):
        """Test ending a session removes it."""
        manager = SessionManager()
        session = manager.create_session(
            merchant_name="test_merchant", scenario_name="test_scenario"
        )
        session_id = session.id

        ended = manager.end_session(session_id)
        assert ended == session
        assert manager.get_session(session_id) is None

    def test_end_nonexistent_session(self):
        """Test ending non-existent session returns None."""
        manager = SessionManager()
        assert manager.end_session("nonexistent") is None
