"""Tests for prompt management endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_prompts():
    """Test listing prompt versions."""
    response = client.get("/api/v1/prompts/")
    assert response.status_code == 200
    data = response.json()
    assert "versions" in data
    assert isinstance(data["versions"], list)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "editor-backend"


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "HireCJ Editor Backend"
    assert "endpoints" in data


def test_cors_endpoint():
    """Test CORS test endpoint."""
    response = client.get("/api/v1/test-cors")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "editor-backend"