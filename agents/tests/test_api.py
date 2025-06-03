"""
REST API tests for HireCJ using FastAPI best practices.
Uses TestClient for faster, more reliable testing.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app  # noqa: E402


class TestRestAPI:
    """Test REST API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_list_merchants(self, client):
        """Test merchant catalog endpoint."""
        response = client.get("/api/v1/catalog/merchants")
        assert response.status_code == 200
        data = response.json()
        assert "merchants" in data
        assert isinstance(data["merchants"], list)
        assert len(data["merchants"]) > 0

    def test_list_scenarios(self, client):
        """Test scenario catalog endpoint."""
        response = client.get("/api/v1/catalog/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert isinstance(data["scenarios"], list)
        assert len(data["scenarios"]) > 0

    def test_list_workflows(self, client):
        """Test workflow catalog endpoint."""
        response = client.get("/api/v1/catalog/workflows")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)
        assert len(data["workflows"]) > 0

    def test_catalog_universes(self, client):
        """Test catalog universes endpoint."""
        response = client.get("/api/v1/catalog/universes")
        assert response.status_code == 200
        data = response.json()
        assert "total_available" in data
        assert "merchants_with_data" in data
        assert "universes" in data
        assert isinstance(data["universes"], list)
        assert len(data["merchants_with_data"]) > 0
        # Check structure of universe data
        if len(data["universes"]) > 0:
            universe = data["universes"][0]
            assert "merchant" in universe
            assert "scenario" in universe
            assert "generated_at" in universe
            assert "total_customers" in universe
            assert "total_tickets" in universe

    def test_catalog_recommendations(self, client):
        """Test catalog recommendations endpoint."""
        response = client.get("/api/v1/catalog/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0
        # Check structure of recommendations
        rec = data["recommendations"][0]
        assert "merchant" in rec
        assert "scenario" in rec
        assert "workflow" in rec
        assert "description" in rec

    def test_catalog_cj_versions(self, client):
        """Test catalog CJ versions endpoint."""
        response = client.get("/api/v1/catalog/cj-versions")
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert isinstance(data["versions"], list)
        assert len(data["versions"]) > 0
        # Check structure of version data
        version = data["versions"][0]
        assert "version" in version
        assert "description" in version
        assert "is_default" in version

    def test_list_universes(self, client):
        """Test universe list endpoint."""
        response = client.get("/api/v1/universes/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # We know we have these two universes
        universe_keys = [(u["merchant"], u["scenario"]) for u in data]
        assert ("marcus_thompson", "steady_operations") in universe_keys
        assert ("zoe_martinez", "memorial_day_weekend") in universe_keys

    def test_get_universe_details(self, client):
        """Test getting universe details for marcus_thompson."""
        response = client.get("/api/v1/universes/marcus_thompson/steady_operations")
        assert response.status_code == 200
        data = response.json()
        assert data["merchant"] == "marcus_thompson"
        assert data["scenario"] == "steady_operations"
        assert "exists" in data
        assert data["exists"] is True
        assert "metadata" in data
        assert "business_context" in data

    def test_get_universe_not_found(self, client):
        """Test getting non-existent universe."""
        response = client.get("/api/v1/universes/fake_merchant/fake_scenario")
        assert response.status_code == 404

    def test_check_universe_exists(self, client):
        """Test checking universe existence."""
        # Test existing universe
        response = client.get(
            "/api/v1/universes/check/marcus_thompson/steady_operations"
        )
        assert response.status_code == 200
        assert response.json()["exists"] is True

        # Test non-existent universe
        response = client.get("/api/v1/universes/check/fake_merchant/fake_scenario")
        assert response.status_code == 200
        assert response.json()["exists"] is False

    def test_generate_universe_placeholder(self, client):
        """Test universe generation endpoint (placeholder)."""
        response = client.post(
            "/api/v1/universes/generate",
            json={"merchant": "marcus_thompson", "scenario": "growth_stall"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_implemented"

    def test_generate_universe_missing_params(self, client):
        """Test universe generation with missing parameters."""
        response = client.post(
            "/api/v1/universes/generate",
            json={
                "merchant": "marcus_thompson"
                # missing scenario
            },
        )
        assert response.status_code == 400  # Bad request

    def test_demo_endpoint(self, client):
        """Test that demo endpoint has been removed."""
        response = client.get("/api/demo")
        assert response.status_code == 404

    def test_list_scenarios_legacy(self, client):
        """Test legacy scenarios endpoint."""
        response = client.get("/api/v1/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert "count" in data
        assert isinstance(data["scenarios"], list)
        assert len(data["scenarios"]) > 0
        # Legacy endpoint returns list of scenario names as strings
        assert isinstance(data["scenarios"][0], str)
