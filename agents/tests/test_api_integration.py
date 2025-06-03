"""Integration tests for the unified API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAPIIntegration:
    """Test complete API flows end-to-end."""

    def test_root_endpoint(self, client):
        """Test root endpoint provides API information."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "HireCJ API Server"
        assert "endpoints" in data
        assert (
            data["endpoints"]["conversation_generation"]
            == "/api/v1/conversations/generate"
        )
        assert data["endpoints"]["websocket_chat"] == "/ws/chat/{conversation_id}"

    def test_health_check_flow(self, client):
        """Test health check provides service status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert data["services"]["conversation_generation"] == "operational"

    def test_list_scenarios_flow(self, client):
        """Test listing scenarios."""
        response = client.get("/api/v1/scenarios")
        assert response.status_code == 200

        data = response.json()
        assert "scenarios" in data
        assert "count" in data
        assert isinstance(data["scenarios"], list)
        assert data["count"] == len(data["scenarios"])
        assert "steady_operations" in data["scenarios"]

    def test_list_merchants_flow(self, client):
        """Test listing merchants."""
        response = client.get("/api/v1/merchants")
        assert response.status_code == 200

        data = response.json()
        assert "merchants" in data
        assert "count" in data
        assert "zoe_martinez" in data["merchants"]
        assert "marcus_thompson" in data["merchants"]

    def test_catalog_endpoints(self, client):
        """Test catalog API endpoints."""
        # Test universes endpoint
        response = client.get("/api/v1/catalog/universes")
        assert response.status_code == 200
        data = response.json()
        assert "universes" in data

        # Test recommendations endpoint
        response = client.get(
            "/api/v1/catalog/recommendations?merchant=marcus_thompson"
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data

        # Test CJ versions
        response = client.get("/api/v1/catalog/cj-versions")
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        # Check that v5.0.0 exists in the versions list
        versions = [v["version"] for v in data["versions"]]
        assert "v5.0.0" in versions

    def test_list_conversations_with_filtering(self, client):
        """Test listing conversations with filters."""
        # Test basic endpoint availability
        # The actual conversation files exist in data/conversations/

        # Test without filters
        response = client.get("/api/v1/conversations/")
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert "total" in data
        assert isinstance(data["conversations"], list)

        # Test with merchant filter
        response = client.get("/api/v1/conversations/?merchant=marcus_thompson")
        assert response.status_code == 200

        # Test with scenario filter
        response = client.get("/api/v1/conversations/?scenario=steady_operations")
        assert response.status_code == 200

        # Test with pagination
        response = client.get("/api/v1/conversations/?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) <= 10

    def test_conversation_annotation_flow(self, client):
        """Test conversation annotation endpoints."""
        conversation_id = "test-conv-123"

        # Mock conversation file
        with patch("app.api.routes.conversations.get_conversation_path") as mock_path:
            mock_path.return_value = None

            # Try to get non-existent conversation
            response = client.get(f"/api/v1/conversations/{conversation_id}")
            assert response.status_code == 404

    def test_universe_endpoints(self, client):
        """Test universe management endpoints."""
        # List universes
        response = client.get("/api/v1/universes/")
        assert response.status_code == 200

        # Check specific universe (will fail if not exists)
        response = client.get("/api/v1/universes/marcus_thompson/steady_operations")
        # Could be 200 or 404 depending on whether universe exists
        assert response.status_code in [200, 404]

        # Test universe check endpoint
        response = client.get("/api/v1/universes/check/test_merchant/test_scenario")
        assert response.status_code == 200
        data = response.json()
        assert "exists" in data
        assert isinstance(data["exists"], bool)

    def test_websocket_test_page(self, client):
        """Test WebSocket test page is served."""
        response = client.get("/ws-test")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "HireCJ WebSocket Test" in response.text

    def test_api_error_handling(self, client):
        """Test API error handling."""
        # Test invalid pagination parameters
        response = client.get("/api/v1/conversations/?limit=0")
        assert response.status_code == 422  # Validation error

        response = client.get("/api/v1/conversations/?limit=1000")
        assert response.status_code == 422  # Exceeds max limit

    @patch("app.api.routes.universe.UniverseLoader")
    def test_universe_generation_placeholder(self, mock_loader, client):
        """Test universe generation endpoint (placeholder)."""
        response = client.post(
            "/api/v1/universes/generate",
            json={"merchant": "test_merchant", "scenario": "test_scenario"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "not_implemented"
        assert "CLI" in data["message"]

    def test_missing_required_parameters(self, client):
        """Test endpoints with missing required parameters."""
        # Missing merchant and scenario
        response = client.post("/api/v1/universes/generate", json={})
        assert response.status_code == 400

        data = response.json()
        assert "merchant and scenario are required" in data["detail"]

    def test_legacy_scenarios_endpoint(self, client):
        """Test legacy scenarios endpoint compatibility."""
        response = client.get("/api/v1/scenarios")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["scenarios"], list)
        # Legacy endpoint returns list of strings
        if len(data["scenarios"]) > 0:
            assert isinstance(data["scenarios"][0], str)
