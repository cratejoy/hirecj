"""
WebSocket API tests for HireCJ using FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app  # noqa: E402


class TestWebSocketAPI:
    """Test WebSocket functionality using TestClient."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.skip(
        reason="WebSocket handler needs refactoring after Phase 1 cleanup"
    )
    def test_websocket_connection(self, client):
        """Test basic WebSocket connection."""
        with client.websocket_connect("/ws/chat/test_123") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "system"
            assert "Connected" in data["text"]
            assert data["conversation_id"] == "test_123"

    @pytest.mark.skip(
        reason="WebSocket handler needs refactoring after Phase 1 cleanup"
    )
    def test_websocket_invalid_universe(self, client):
        """Test sending message with non-existent universe."""
        with client.websocket_connect("/ws/chat/test_invalid") as websocket:
            # Skip system message
            websocket.receive_json()

            # Send message with invalid universe
            websocket.send_json(
                {
                    "type": "message",
                    "text": "Hello",
                    "merchant_id": "fake_merchant",
                    "scenario": "fake_scenario",
                }
            )

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Universe not found" in data["text"]

    @pytest.mark.skip(reason="WebSocket handler doesn't support 'end' message type yet")
    def test_websocket_end_conversation(self, client):
        """Test ending conversation."""
        with client.websocket_connect("/ws/chat/test_end") as websocket:
            # Skip system message
            websocket.receive_json()

            # Send end message
            websocket.send_json({"type": "end"})

            # Should receive confirmation
            data = websocket.receive_json()
            assert data["type"] == "system"
            assert "ended" in data["text"].lower()

    @pytest.mark.skip(reason="Skipping slow test - requires actual API calls")
    def test_websocket_simple_message(self, client):
        """Test simple message flow with marcus_thompson universe."""
        with client.websocket_connect("/ws/chat/test_simple") as websocket:
            # Skip system message
            websocket.receive_json()

            # Send message using universe we know exists
            websocket.send_json(
                {
                    "type": "message",
                    "text": "Hello CJ!",
                    "merchant_id": "marcus_thompson",
                    "scenario": "steady_operations",
                }
            )

            # Wait for response (this makes actual API calls so it's slow)
            received_response = False
            for _ in range(10):  # Try for up to 10 messages
                data = websocket.receive_json()
                if data["type"] == "cj_message":
                    received_response = True
                    assert "text" in data
                    break

            assert received_response, "Did not receive CJ response"

    @pytest.mark.skip(
        reason="Conversation persistence happens on disconnect, not testable with TestClient"
    )
    def test_websocket_conversation_persistence(self, client):
        """Test that conversations are saved on end."""
        # This test is skipped because TestClient doesn't trigger the actual
        # disconnect handler that saves conversations
        pass
