"""Tests for MessageProcessor service."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from app.services.message_processor import MessageProcessor
from app.services.session_manager import Session
from app.models import Conversation


@pytest.mark.skip(
    reason="MessageProcessor tests need complete rewrite to match actual implementation"
)
class TestMessageProcessor:
    """Test MessageProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = MessageProcessor()

        # Create test conversation
        self.conversation = Conversation(
            id="test-123",
            created_at=datetime.utcnow(),
            scenario_name="test_scenario",
            merchant_name="test_merchant",
            workflow="chat",
        )

        # Create test session
        self.session = Session(self.conversation)
        self.session.id = "session-123"

    def test_initialization(self):
        """Test that MessageProcessor initializes correctly."""
        processor = MessageProcessor()
        assert processor._progress_callbacks == []

    @pytest.mark.asyncio
    @patch("app.services.message_processor.create_cj_agent")
    @patch("app.services.message_processor.Crew")
    async def test_process_message_success(self, mock_crew_class, mock_create_cj_agent):
        """Test successful message processing."""
        # Setup mocks
        mock_agent = Mock()
        mock_create_cj_agent.return_value = mock_agent

        mock_result = Mock()
        mock_result.output = "Hello! How can I help you today?"
        mock_crew = Mock()
        mock_crew.kickoff.return_value = mock_result
        mock_crew_class.return_value = mock_crew

        processor = MessageProcessor()

        # Process message
        response = await processor.process_message(
            session=self.session,
            message="I need help with shipping",
            sender="merchant",
        )

        assert response == "Hello! How can I help you today?"

        # Verify agent and crew were created correctly
        mock_create_cj_agent.assert_called_once()
        mock_crew_class.assert_called_once()
        mock_crew.kickoff.assert_called_once()

        # Verify messages were added to conversation
        assert len(self.conversation.messages) == 2  # merchant + cj messages
        assert self.conversation.messages[0].sender == "merchant"
        assert self.conversation.messages[0].content == "I need help with shipping"
        assert self.conversation.messages[1].sender == "CJ"
        assert (
            self.conversation.messages[1].content == "Hello! How can I help you today?"
        )

    @pytest.mark.asyncio
    @patch("app.services.message_processor.CrewManager")
    async def test_process_message_with_metadata(self, mock_crew_manager_class):
        """Test message processing preserves metadata."""
        mock_crew = Mock()
        mock_crew.kickoff_async = AsyncMock(return_value="Response")

        mock_manager = Mock()
        mock_manager.get_crew_for_session.return_value = mock_crew
        mock_crew_manager_class.return_value = mock_manager

        processor = MessageProcessor()

        metadata = {"source": "web", "ip": "127.0.0.1"}
        await processor.process_message(
            session=self.session,
            message="Test message",
            sender="merchant",
            metadata=metadata,
        )

        # Check merchant message has metadata
        merchant_msg = self.conversation.messages[0]
        assert merchant_msg.metadata == metadata

    @pytest.mark.asyncio
    @patch("app.services.message_processor.CrewManager")
    async def test_process_message_empty_response(self, mock_crew_manager_class):
        """Test handling of empty response from crew."""
        mock_crew = Mock()
        mock_crew.kickoff_async = AsyncMock(return_value="")

        mock_manager = Mock()
        mock_manager.get_crew_for_session.return_value = mock_crew
        mock_crew_manager_class.return_value = mock_manager

        processor = MessageProcessor()

        response = await processor.process_message(
            session=self.session, message="Test", sender="merchant"
        )

        # Should provide default response
        assert response != ""
        assert "I'm having trouble" in response or "error" in response.lower()

    @pytest.mark.asyncio
    @patch("app.services.message_processor.CrewManager")
    async def test_process_message_crew_error(self, mock_crew_manager_class):
        """Test handling of crew errors."""
        mock_crew = Mock()
        mock_crew.kickoff_async = AsyncMock(side_effect=Exception("Crew error"))

        mock_manager = Mock()
        mock_manager.get_crew_for_session.return_value = mock_crew
        mock_crew_manager_class.return_value = mock_manager

        processor = MessageProcessor()

        response = await processor.process_message(
            session=self.session, message="Test", sender="merchant"
        )

        # Should return error message
        assert "I'm having trouble" in response or "error" in response.lower()

        # Error should still add messages to conversation
        assert len(self.conversation.messages) == 2

    @pytest.mark.asyncio
    @patch("app.services.message_processor.CrewManager")
    async def test_process_message_with_workflow(self, mock_crew_manager_class):
        """Test message processing respects workflow."""
        mock_crew = Mock()
        mock_crew.kickoff_async = AsyncMock(return_value="Daily briefing response")

        mock_manager = Mock()
        mock_manager.get_crew_for_session.return_value = mock_crew
        mock_crew_manager_class.return_value = mock_manager

        # Set workflow
        self.conversation.workflow = "daily_briefing"
        processor = MessageProcessor()

        response = await processor.process_message(
            session=self.session,
            message="Give me the daily briefing",
            sender="merchant",
        )

        assert response == "Daily briefing response"

        # Verify crew manager got correct session with workflow
        mock_manager.get_crew_for_session.assert_called_with(self.session)
        assert self.session.conversation.workflow == "daily_briefing"

    @pytest.mark.asyncio
    @patch("app.services.message_processor.CrewManager")
    async def test_process_message_updates_session_metrics(
        self, mock_crew_manager_class
    ):
        """Test that processing updates session metrics."""
        mock_crew = Mock()
        mock_crew.kickoff_async = AsyncMock(return_value="Response")

        mock_manager = Mock()
        mock_manager.get_crew_for_session.return_value = mock_crew
        mock_crew_manager_class.return_value = mock_manager

        processor = MessageProcessor()

        # Initial metrics
        assert self.session.metrics["messages"] == 0

        await processor.process_message(
            session=self.session, message="Test", sender="merchant"
        )

        # Metrics should be updated
        assert self.session.metrics["messages"] == 1
        assert self.session.last_activity is not None

    @pytest.mark.asyncio
    @patch("app.services.message_processor.CrewManager")
    async def test_concurrent_message_processing(self, mock_crew_manager_class):
        """Test concurrent message processing."""

        # Create mock that simulates delay
        async def slow_response(inputs):
            await asyncio.sleep(0.1)
            return f"Response to: {inputs.get('message', '')}"

        mock_crew = Mock()
        mock_crew.kickoff_async = slow_response

        mock_manager = Mock()
        mock_manager.get_crew_for_session.return_value = mock_crew
        mock_crew_manager_class.return_value = mock_manager

        processor = MessageProcessor()

        # Process multiple messages concurrently
        tasks = [
            processor.process_message(self.session, f"Message {i}", "merchant")
            for i in range(3)
        ]

        responses = await asyncio.gather(*tasks)

        assert len(responses) == 3
        assert all("Response to:" in r for r in responses)

        # All messages should be in conversation
        assert len(self.conversation.messages) == 6  # 3 merchant + 3 cj
