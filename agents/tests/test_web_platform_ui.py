import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime
import json

from app.platforms.web_platform import WebPlatform
from app.platforms.base import OutgoingMessage


@pytest.fixture
def web_platform():
    """Create a web platform instance."""
    config = {"max_message_length": 1000}
    platform = WebPlatform(config)
    return platform


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    session_manager = Mock()
    session = Mock()
    session.id = "test-session-123"
    session.merchant_name = "test_merchant"
    session.scenario_name = "test_scenario"
    session.conversation = Mock()
    session.conversation.workflow = "shopify_onboarding"
    session.conversation.messages = []
    session.conversation.state = Mock()
    session.conversation.state.context_window = []
    session_manager.get_session.return_value = session
    session_manager.create_session.return_value = session
    session_manager._sessions = {"test-conv-123": session}
    return session_manager


class TestWebPlatformUI:
    """Test UI element handling in web platform."""

    @pytest.mark.asyncio
    async def test_send_message_with_ui_elements(self, web_platform, mock_websocket):
        """Test sending message with UI elements via send_message method."""
        # Set up connection
        conversation_id = "test-conv-123"
        web_platform.connections[conversation_id] = mock_websocket
        
        # Create message with UI elements in metadata
        message = OutgoingMessage(
            conversation_id=conversation_id,
            text="Connect your store: __OAUTH_BUTTON_1__",
            thread_id="thread-123",
            metadata={
                "ui_elements": [{
                    'id': 'oauth_1',
                    'type': 'oauth_button',
                    'provider': 'shopify',
                    'placeholder': '__OAUTH_BUTTON_1__'
                }]
            }
        )
        
        # Send message
        result = await web_platform.send_message(message)
        
        # Verify success
        assert result is True
        
        # Verify WebSocket call
        mock_websocket.send_json.assert_called_once()
        sent_data = mock_websocket.send_json.call_args[0][0]
        
        # Check message structure
        assert sent_data["type"] == "message"
        assert sent_data["text"] == "Connect your store: __OAUTH_BUTTON_1__"
        assert "ui_elements" in sent_data
        assert len(sent_data["ui_elements"]) == 1
        assert sent_data["ui_elements"][0]["type"] == "oauth_button"

    @pytest.mark.asyncio
    async def test_handle_cj_response_with_ui_elements(self, web_platform, mock_websocket, mock_session_manager):
        """Test handling CJ response with UI elements."""
        # Set up
        web_platform.session_manager = mock_session_manager
        web_platform.connections["test-conv-123"] = mock_websocket
        
        # Mock message processor to return structured response
        mock_message_processor = AsyncMock()
        mock_message_processor.process_message.return_value = {
            "type": "message_with_ui",
            "content": "Let's connect: __OAUTH_BUTTON_1__",
            "ui_elements": [{
                'id': 'oauth_1',
                'type': 'oauth_button',
                'provider': 'shopify',
                'placeholder': '__OAUTH_BUTTON_1__'
            }]
        }
        web_platform.message_processor = mock_message_processor
        
        # Simulate incoming message
        await web_platform._handle_websocket_message(
            mock_websocket,
            "test-conv-123",
            {
                "type": "message",
                "text": "I want to connect my store"
            }
        )
        
        # Verify WebSocket received message with UI elements
        calls = mock_websocket.send_json.call_args_list
        cj_message_call = None
        
        for call_obj in calls:
            data = call_obj[0][0]
            if data.get("type") == "cj_message":
                cj_message_call = data
                break
        
        assert cj_message_call is not None
        assert cj_message_call["data"]["content"] == "Let's connect: __OAUTH_BUTTON_1__"
        assert "ui_elements" in cj_message_call["data"]
        assert len(cj_message_call["data"]["ui_elements"]) == 1
        assert cj_message_call["data"]["ui_elements"][0]["type"] == "oauth_button"

    @pytest.mark.asyncio
    async def test_handle_initial_greeting_with_ui_elements(self, web_platform, mock_websocket, mock_session_manager):
        """Test initial greeting with UI elements for shopify_onboarding."""
        # Set up
        web_platform.session_manager = mock_session_manager
        web_platform.connections["test-conv-123"] = mock_websocket
        
        # Mock message processor to return structured response
        mock_message_processor = AsyncMock()
        mock_message_processor.process_message.return_value = {
            "type": "message_with_ui",
            "content": "Welcome! Let's connect: __OAUTH_BUTTON_1__",
            "ui_elements": [{
                'id': 'oauth_1',
                'type': 'oauth_button',
                'provider': 'shopify',
                'placeholder': '__OAUTH_BUTTON_1__'
            }]
        }
        web_platform.message_processor = mock_message_processor
        
        # Simulate start conversation with shopify_onboarding
        await web_platform._handle_websocket_message(
            mock_websocket,
            "test-conv-123",
            {
                "type": "start_conversation",
                "data": {
                    "workflow": "shopify_onboarding",
                    "merchant_id": "onboarding_user",
                    "scenario": "onboarding"
                }
            }
        )
        
        # Find the CJ message with UI elements
        calls = mock_websocket.send_json.call_args_list
        cj_message_call = None
        
        for call_obj in calls:
            data = call_obj[0][0]
            if data.get("type") == "cj_message":
                cj_message_call = data
                break
        
        assert cj_message_call is not None
        assert "ui_elements" in cj_message_call["data"]
        assert cj_message_call["data"]["ui_elements"][0]["type"] == "oauth_button"

    @pytest.mark.asyncio
    async def test_handle_oauth_complete_with_ui_elements(self, web_platform, mock_websocket, mock_session_manager):
        """Test OAuth completion response with UI elements."""
        # Set up
        web_platform.session_manager = mock_session_manager
        web_platform.connections["test-conv-123"] = mock_websocket
        
        # Mock message processor to return structured response
        mock_message_processor = AsyncMock()
        mock_message_processor.process_message.return_value = {
            "type": "message_with_ui",
            "content": "Great! Now let's connect support: __OAUTH_BUTTON_1__",
            "ui_elements": [{
                'id': 'oauth_1',
                'type': 'oauth_button',
                'provider': 'freshdesk',
                'placeholder': '__OAUTH_BUTTON_1__'
            }]
        }
        web_platform.message_processor = mock_message_processor
        
        # Simulate OAuth completion
        await web_platform._handle_websocket_message(
            mock_websocket,
            "test-conv-123",
            {
                "type": "oauth_complete",
                "data": {
                    "provider": "shopify",
                    "is_new": True,
                    "merchant_id": "test-merchant",
                    "shop_domain": "test.myshopify.com"
                }
            }
        )
        
        # Find the CJ message response
        calls = mock_websocket.send_json.call_args_list
        cj_message_call = None
        
        for call_obj in calls:
            data = call_obj[0][0]
            if data.get("type") == "cj_message":
                cj_message_call = data
                break
        
        assert cj_message_call is not None
        assert "ui_elements" in cj_message_call["data"]
        assert cj_message_call["data"]["ui_elements"][0]["provider"] == "freshdesk"

    @pytest.mark.asyncio
    async def test_regular_response_without_ui_elements(self, web_platform, mock_websocket, mock_session_manager):
        """Test that regular responses work without UI elements."""
        # Set up
        web_platform.session_manager = mock_session_manager
        web_platform.connections["test-conv-123"] = mock_websocket
        
        # Mock message processor to return plain string
        mock_message_processor = AsyncMock()
        mock_message_processor.process_message.return_value = "Thanks for your message!"
        web_platform.message_processor = mock_message_processor
        
        # Simulate incoming message
        await web_platform._handle_websocket_message(
            mock_websocket,
            "test-conv-123",
            {
                "type": "message",
                "text": "Hello"
            }
        )
        
        # Verify response
        calls = mock_websocket.send_json.call_args_list
        cj_message_call = None
        
        for call_obj in calls:
            data = call_obj[0][0]
            if data.get("type") == "cj_message":
                cj_message_call = data
                break
        
        assert cj_message_call is not None
        assert cj_message_call["data"]["content"] == "Thanks for your message!"
        assert "ui_elements" not in cj_message_call["data"]

    @pytest.mark.asyncio
    async def test_non_shopify_workflow_no_ui_parsing(self, web_platform, mock_websocket, mock_session_manager):
        """Test that non-shopify workflows don't get UI elements."""
        # Update session to use different workflow
        mock_session_manager.get_session.return_value.conversation.workflow = "daily_briefing"
        
        # Set up
        web_platform.session_manager = mock_session_manager
        web_platform.connections["test-conv-123"] = mock_websocket
        
        # Mock message processor - even if it returns UI structure, platform should pass it through
        mock_message_processor = AsyncMock()
        mock_message_processor.process_message.return_value = "Daily briefing content"
        web_platform.message_processor = mock_message_processor
        
        # Simulate message for daily briefing
        await web_platform._handle_websocket_message(
            mock_websocket,
            "test-conv-123",
            {
                "type": "message",
                "text": "Give me the daily briefing"
            }
        )
        
        # Verify response has no UI elements
        calls = mock_websocket.send_json.call_args_list
        cj_message_call = None
        
        for call_obj in calls:
            data = call_obj[0][0]
            if data.get("type") == "cj_message":
                cj_message_call = data
                break
        
        assert cj_message_call is not None
        assert "ui_elements" not in cj_message_call["data"]

    def test_websocket_message_format(self):
        """Test the WebSocket message format with UI elements."""
        # Expected format for message with UI elements
        expected = {
            "type": "cj_message",
            "data": {
                "content": "Let's connect: __OAUTH_BUTTON_1__",
                "factCheckStatus": "available",
                "timestamp": "2024-01-01T00:00:00",
                "ui_elements": [{
                    'id': 'oauth_1',
                    'type': 'oauth_button',
                    'provider': 'shopify',
                    'placeholder': '__OAUTH_BUTTON_1__'
                }]
            }
        }
        
        # Verify JSON serializable
        json_str = json.dumps(expected)
        parsed = json.loads(json_str)
        
        assert parsed["data"]["ui_elements"][0]["type"] == "oauth_button"
        assert len(parsed["data"]["ui_elements"]) == 1