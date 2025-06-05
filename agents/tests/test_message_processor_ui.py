import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import asyncio

from app.services.message_processor import MessageProcessor
from app.services.session_manager import Session
from app.models import Conversation, ConversationState, Message


@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    session = Mock(spec=Session)
    session.id = "test-session-123"
    session.conversation = Mock(spec=Conversation)
    session.conversation.merchant_name = "Test Merchant"
    session.conversation.scenario_name = "test_scenario"
    session.conversation.workflow = "shopify_onboarding"
    session.conversation.messages = []
    session.conversation.state = ConversationState()
    session.conversation.state.context_window = []
    session.conversation.add_message = Mock()
    session.data_agent = None
    session.merchant_memory = None
    session.last_activity = datetime.utcnow()
    session.metrics = {
        "messages": 0,
        "response_time_total": 0,
        "errors": 0
    }
    return session


@pytest.fixture
def mock_session_other_workflow():
    """Create a mock session with a different workflow."""
    session = Mock(spec=Session)
    session.id = "test-session-456"
    session.conversation = Mock(spec=Conversation)
    session.conversation.merchant_name = "Test Merchant"
    session.conversation.scenario_name = "test_scenario"
    session.conversation.workflow = "other_workflow"
    session.conversation.messages = []
    session.conversation.state = ConversationState()
    session.conversation.state.context_window = []
    session.conversation.add_message = Mock()
    session.data_agent = None
    session.merchant_memory = None
    session.last_activity = datetime.utcnow()
    session.metrics = {
        "messages": 0,
        "response_time_total": 0,
        "errors": 0
    }
    return session


class TestMessageProcessorUI:
    """Test UI component parsing in message processor."""

    @pytest.mark.asyncio
    async def test_message_processor_parses_ui_elements(self, mock_session):
        """Test that message processor extracts UI elements from CJ response."""
        processor = MessageProcessor()
        
        # Mock _get_cj_response to return structured response with UI elements
        with patch.object(processor, '_get_cj_response') as mock_get_response:
            mock_get_response.return_value = {
                "type": "message_with_ui",
                "content": "Let's connect your store: __OAUTH_BUTTON_1__",
                "ui_elements": [{
                    'id': 'oauth_1',
                    'type': 'oauth_button',
                    'provider': 'shopify',
                    'placeholder': '__OAUTH_BUTTON_1__'
                }]
            }
            
            # Process message
            response = await processor.process_message(
                mock_session,
                "I'd like to connect my store",
                sender="merchant"
            )
                
        # Verify response structure
        assert isinstance(response, dict)
        assert response['type'] == 'message_with_ui'
        assert '__OAUTH_BUTTON_1__' in response['content']
        assert len(response['ui_elements']) == 1
        assert response['ui_elements'][0]['type'] == 'oauth_button'
        assert response['ui_elements'][0]['provider'] == 'shopify'
        assert response['ui_elements'][0]['placeholder'] == '__OAUTH_BUTTON_1__'
        
        # Verify clean content was stored in conversation
        mock_session.conversation.add_message.assert_called()
        added_message = mock_session.conversation.add_message.call_args[0][0]
        assert added_message.content == response['content']
        assert '__OAUTH_BUTTON_1__' in added_message.content
        assert '{{oauth:shopify}}' not in added_message.content

    @pytest.mark.asyncio
    async def test_message_processor_no_ui_for_other_workflows(self, mock_session_other_workflow):
        """Test that other workflows don't get UI parsing."""
        processor = MessageProcessor()
        
        # Mock _get_cj_response to return plain string (for non-shopify workflow)
        with patch.object(processor, '_get_cj_response') as mock_get_response:
            mock_get_response.return_value = "Text with {{oauth:shopify}}"
            
            # Process message
            response = await processor.process_message(
                mock_session_other_workflow,
                "test message",
                sender="merchant"
            )
                
        # Should return raw response
        assert isinstance(response, str)
        assert response == "Text with {{oauth:shopify}}"
        assert "{{oauth:shopify}}" in response

    @pytest.mark.asyncio
    async def test_message_processor_multiple_ui_elements(self, mock_session):
        """Test parsing multiple UI elements."""
        processor = MessageProcessor()
        
        # Mock _get_cj_response to return structured response with multiple UI elements
        with patch.object(processor, '_get_cj_response') as mock_get_response:
            mock_get_response.return_value = {
                "type": "message_with_ui",
                "content": "First: __OAUTH_BUTTON_1__ and second: __OAUTH_BUTTON_2__",
                "ui_elements": [
                    {
                        'id': 'oauth_1',
                        'type': 'oauth_button',
                        'provider': 'shopify',
                        'placeholder': '__OAUTH_BUTTON_1__'
                    },
                    {
                        'id': 'oauth_2',
                        'type': 'oauth_button',
                        'provider': 'shopify',
                        'placeholder': '__OAUTH_BUTTON_2__'
                    }
                ]
            }
            
            # Process message
            response = await processor.process_message(
                mock_session,
                "test message",
                sender="merchant"
            )
                
        # Verify response structure
        assert isinstance(response, dict)
        assert response['type'] == 'message_with_ui'
        assert '__OAUTH_BUTTON_1__' in response['content']
        assert '__OAUTH_BUTTON_2__' in response['content']
        assert len(response['ui_elements']) == 2

    @pytest.mark.asyncio
    async def test_message_processor_no_ui_elements(self, mock_session):
        """Test response without UI elements."""
        processor = MessageProcessor()
        
        # Mock _get_cj_response to return plain string (no UI elements)
        with patch.object(processor, '_get_cj_response') as mock_get_response:
            mock_get_response.return_value = "Regular response without any UI elements"
            
            # Process message
            response = await processor.process_message(
                mock_session,
                "test message",
                sender="merchant"
            )
                
        # Should return plain string
        assert isinstance(response, str)
        assert response == "Regular response without any UI elements"

    @pytest.mark.asyncio
    async def test_get_cj_response_directly(self, mock_session):
        """Test _get_cj_response method directly."""
        processor = MessageProcessor()
        
        # Mock the crew result
        mock_result = Mock()
        mock_result.output = "Connect here: {{oauth:shopify}}"
        
        with patch('app.services.message_processor.create_cj_agent') as mock_create_cj:
            with patch('app.services.message_processor.Crew') as mock_crew_class:
                with patch('app.services.message_processor.Task') as mock_task_class:
                    # Setup mocks
                    mock_cj_agent = Mock()
                    mock_create_cj.return_value = mock_cj_agent
                    
                    mock_crew = Mock()
                    mock_crew.kickoff.return_value = mock_result
                    mock_crew_class.return_value = mock_crew
                    
                    mock_task = Mock()
                    mock_task_class.return_value = mock_task
                    
                    # Call _get_cj_response directly
                    response = await processor._get_cj_response(
                        mock_session,
                        "test message",
                        is_system=False
                    )
                
        # Verify structured response
        assert isinstance(response, dict)
        assert response['type'] == 'message_with_ui'
        assert response['content'] == "Connect here: __OAUTH_BUTTON_1__"
        assert len(response['ui_elements']) == 1

    @pytest.mark.asyncio
    async def test_system_message_with_ui(self, mock_session):
        """Test system message handling with UI elements."""
        processor = MessageProcessor()
        
        # Mock _get_cj_response to return structured response with UI elements
        with patch.object(processor, '_get_cj_response') as mock_get_response:
            mock_get_response.return_value = {
                "type": "message_with_ui",
                "content": "OAuth complete! __OAUTH_BUTTON_1__",
                "ui_elements": [{
                    'id': 'oauth_1',
                    'type': 'oauth_button',
                    'provider': 'shopify',
                    'placeholder': '__OAUTH_BUTTON_1__'
                }]
            }
            
            # Process system message
            response = await processor.process_message(
                mock_session,
                "OAuth completed successfully",
                sender="system"
            )
                
        # Verify response has UI elements
        assert isinstance(response, dict)
        assert response['type'] == 'message_with_ui'
        assert '__OAUTH_BUTTON_1__' in response['content']