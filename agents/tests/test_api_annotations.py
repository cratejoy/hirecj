"""
Tests for annotation API endpoints.
"""

import pytest
import json
import time
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app  # noqa: E402


class TestAnnotationAPI:
    """Test annotation functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def test_conversation(self):
        """Create a test conversation file."""
        conversation_id = f"test_annotations_{int(time.time())}"
        conversation_data = {
            "conversation_id": conversation_id,
            "merchant": {"id": "marcus_thompson", "name": "Marcus Thompson"},
            "scenario": {"id": "steady_operations", "name": "Steady Operations"},
            "messages": [
                {
                    "sender": "merchant",
                    "content": "whats our cac looking like",
                    "timestamp": "2025-05-27T08:00:00Z",
                },
                {
                    "sender": "cj",
                    "content": "Your CAC is currently at $45, up from $38 last month.",
                    "timestamp": "2025-05-27T08:00:01Z",
                },
                {
                    "sender": "merchant",
                    "content": "why the jump",
                    "timestamp": "2025-05-27T08:00:02Z",
                },
                {
                    "sender": "cj",
                    "content": "The increase is primarily due to higher ad costs on Meta...",
                    "timestamp": "2025-05-27T08:00:03Z",
                },
            ],
            "created_at": "2025-05-27T08:00:00Z",
            "updated_at": "2025-05-27T08:00:00Z",
        }

        # Save to data/conversations
        conversation_dir = Path("data/conversations")
        conversation_dir.mkdir(parents=True, exist_ok=True)

        file_path = conversation_dir / f"{conversation_id}.json"
        with open(file_path, "w") as f:
            json.dump(conversation_data, f, indent=2)

        yield conversation_id

        # Cleanup
        if file_path.exists():
            file_path.unlink()

    def test_get_conversation(self, client, test_conversation):
        """Test getting a conversation."""
        response = client.get(f"/api/v1/conversations/{test_conversation}")
        assert response.status_code == 200

        data = response.json()
        assert data["conversation_id"] == test_conversation
        assert len(data["messages"]) == 4
        assert "annotations" in data  # Should have empty annotations dict

    def test_get_nonexistent_conversation(self, client):
        """Test getting a conversation that doesn't exist."""
        response = client.get("/api/v1/conversations/nonexistent_123")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_add_annotation(self, client, test_conversation):
        """Test adding an annotation."""
        # Add annotation to second message (index 1)
        response = client.post(
            f"/api/v1/conversations/{test_conversation}/annotations/1",
            json={"sentiment": "dislike", "text": "Too formal for Marcus"},
        )
        assert response.status_code == 200

        result = response.json()
        assert result["message"] == "Annotation added successfully"
        assert result["annotation"]["sentiment"] == "dislike"
        assert result["annotation"]["text"] == "Too formal for Marcus"
        assert "timestamp" in result["annotation"]

        # Verify annotation was saved
        response = client.get(f"/api/v1/conversations/{test_conversation}")
        data = response.json()
        assert "1" in data["annotations"]
        assert data["annotations"]["1"]["sentiment"] == "dislike"

    def test_update_annotation(self, client, test_conversation):
        """Test updating an existing annotation."""
        # First add an annotation
        client.post(
            f"/api/v1/conversations/{test_conversation}/annotations/1",
            json={"sentiment": "dislike", "text": "Too formal"},
        )

        # Then update it
        response = client.post(
            f"/api/v1/conversations/{test_conversation}/annotations/1",
            json={"sentiment": "like", "text": "Actually, this is good"},
        )
        assert response.status_code == 200

        # Verify update
        response = client.get(f"/api/v1/conversations/{test_conversation}")
        data = response.json()
        assert data["annotations"]["1"]["sentiment"] == "like"
        assert data["annotations"]["1"]["text"] == "Actually, this is good"

    def test_add_annotation_invalid_sentiment(self, client, test_conversation):
        """Test adding annotation with invalid sentiment."""
        response = client.post(
            f"/api/v1/conversations/{test_conversation}/annotations/1",
            json={"sentiment": "maybe", "text": "Not sure"},
        )
        assert response.status_code == 400
        assert "must be 'like' or 'dislike'" in response.json()["detail"]

    def test_add_annotation_invalid_index(self, client, test_conversation):
        """Test adding annotation with invalid message index."""
        # Try to annotate message that doesn't exist
        response = client.post(
            f"/api/v1/conversations/{test_conversation}/annotations/10",
            json={"sentiment": "like"},
        )
        assert response.status_code == 400
        assert "Invalid message index" in response.json()["detail"]

    def test_delete_annotation(self, client, test_conversation):
        """Test deleting an annotation."""
        # First add an annotation
        client.post(
            f"/api/v1/conversations/{test_conversation}/annotations/1",
            json={"sentiment": "like"},
        )

        # Then delete it
        response = client.delete(
            f"/api/v1/conversations/{test_conversation}/annotations/1"
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Annotation deleted successfully"

        # Verify deletion
        response = client.get(f"/api/v1/conversations/{test_conversation}")
        data = response.json()
        assert "1" not in data["annotations"]

    def test_delete_nonexistent_annotation(self, client, test_conversation):
        """Test deleting annotation that doesn't exist."""
        response = client.delete(
            f"/api/v1/conversations/{test_conversation}/annotations/1"
        )
        assert response.status_code == 404
        assert "No annotation found" in response.json()["detail"]

    def test_list_conversations(self, client, test_conversation):
        """Test listing conversations."""
        response = client.get("/api/v1/conversations/")
        assert response.status_code == 200

        data = response.json()
        assert "conversations" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        # Our test conversation should be in the list
        conv_ids = [c["conversation_id"] for c in data["conversations"]]
        assert test_conversation in conv_ids

    def test_list_conversations_with_filters(self, client, test_conversation):
        """Test listing conversations with filters."""
        # Add an annotation to our test conversation
        client.post(
            f"/api/v1/conversations/{test_conversation}/annotations/1",
            json={"sentiment": "like"},
        )

        # Test annotated filter
        response = client.get("/api/v1/conversations/?annotated=true")
        data = response.json()
        conv_ids = [c["conversation_id"] for c in data["conversations"]]
        assert test_conversation in conv_ids

        # Test merchant filter
        response = client.get("/api/v1/conversations/?merchant=marcus_thompson")
        data = response.json()
        conv_ids = [c["conversation_id"] for c in data["conversations"]]
        assert test_conversation in conv_ids

        # Test scenario filter
        response = client.get("/api/v1/conversations/?scenario=steady_operations")
        data = response.json()
        conv_ids = [c["conversation_id"] for c in data["conversations"]]
        assert test_conversation in conv_ids

    def test_annotation_without_text(self, client, test_conversation):
        """Test adding annotation with just sentiment."""
        response = client.post(
            f"/api/v1/conversations/{test_conversation}/annotations/3",
            json={"sentiment": "like"},
        )
        assert response.status_code == 200

        result = response.json()
        assert result["annotation"]["sentiment"] == "like"
        assert result["annotation"]["text"] == ""
