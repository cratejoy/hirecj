"""
Test fact-checking API endpoints.
"""

import pytest
import json
import time
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# Test data setup
TEST_CONVERSATION_ID = "test_fact_check_conv"
TEST_CONVERSATION_PATH = Path("data/conversations") / f"{TEST_CONVERSATION_ID}.json"

# Sample conversation with CJ messages
SAMPLE_CONVERSATION = {
    "id": TEST_CONVERSATION_ID,
    "created_at": "2025-05-27T10:00:00Z",
    "scenario_name": "steady_operations",
    "merchant_name": "marcus_thompson",
    "cj_version": "v5.0.0",
    "workflow": "chat",
    "messages": [
        {
            "timestamp": "2025-05-27T10:00:00Z",
            "sender": "merchant",
            "content": "whats our cac looking like",
            "metadata": {},
        },
        {
            "timestamp": "2025-05-27T10:00:01Z",
            "sender": "cj",
            "content": "Your CAC is currently at $45, up from $38 last month. The main driver is increased competition in paid search.",
            "metadata": {"metrics": {"prompts": 3, "tools": 1, "time": 2.5}},
        },
        {
            "timestamp": "2025-05-27T10:00:02Z",
            "sender": "merchant",
            "content": "what about churn",
            "metadata": {},
        },
        {
            "timestamp": "2025-05-27T10:00:03Z",
            "sender": "cj",
            "content": "Churn rate is holding steady at 5.5%, which is good news. No concerning trends there.",
            "metadata": {"metrics": {"prompts": 2, "tools": 1, "time": 1.8}},
        },
    ],
    "state": {
        "workflow": "chat",
        "workflow_details": "Ad-hoc conversation",
        "context_window": [],
    },
    "fact_checks": {},  # Explicitly set empty fact_checks
}


def setup_module():
    """Create test conversation file."""
    TEST_CONVERSATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TEST_CONVERSATION_PATH, "w") as f:
        json.dump(SAMPLE_CONVERSATION, f)


def teardown_module():
    """Clean up test conversation file."""
    if TEST_CONVERSATION_PATH.exists():
        TEST_CONVERSATION_PATH.unlink()

    # Also clean up any fact-checked version
    fact_checked_path = (
        TEST_CONVERSATION_PATH.parent / f"{TEST_CONVERSATION_ID}_with_facts.json"
    )
    if fact_checked_path.exists():
        fact_checked_path.unlink()


def setup_function():
    """Set up before each test function."""
    # Recreate the test file fresh for each test with empty fact_checks
    clean_conversation = SAMPLE_CONVERSATION.copy()
    clean_conversation["fact_checks"] = {}  # Ensure empty fact_checks
    with open(TEST_CONVERSATION_PATH, "w") as f:
        json.dump(clean_conversation, f)

    # Clear in-memory caches in fact_checking module
    from app.api.routes import fact_checking

    # Clear all fact check results for our test conversation
    if TEST_CONVERSATION_ID in fact_checking._fact_check_results:
        fact_checking._fact_check_results[TEST_CONVERSATION_ID].clear()
    fact_checking._active_checkers.clear()

    # Clear any cached conversation data (removed - not present in server)


@pytest.mark.skip(reason="Fact-checking endpoints not implemented yet")
class TestFactCheckingAPI:
    """Test fact-checking REST API endpoints."""

    def test_get_fact_check_not_available(self):
        """Test getting fact-check status when none exists."""
        response = client.get(
            f"/api/v1/conversations/{TEST_CONVERSATION_ID}/fact-checks/1"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "not_available"
        assert data["message_index"] == 1

    def test_get_fact_check_invalid_conversation(self):
        """Test getting fact-check for non-existent conversation."""
        response = client.get("/api/v1/conversations/nonexistent/fact-checks/0")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_start_fact_check_merchant_message(self):
        """Test that fact-checking merchant messages returns error."""
        response = client.post(
            f"/api/v1/conversations/{TEST_CONVERSATION_ID}/fact-checks/0",
            json={
                "merchant_name": "marcus_thompson",
                "scenario_name": "steady_operations",
            },
        )
        assert response.status_code == 400
        assert "Can only fact-check CJ messages" in response.json()["detail"]

    def test_start_fact_check_invalid_index(self):
        """Test fact-checking with invalid message index."""
        response = client.post(
            f"/api/v1/conversations/{TEST_CONVERSATION_ID}/fact-checks/99",
            json={
                "merchant_name": "marcus_thompson",
                "scenario_name": "steady_operations",
            },
        )
        assert response.status_code == 400
        assert "Invalid message index" in response.json()["detail"]

    def test_start_fact_check_missing_universe(self):
        """Test fact-checking with non-existent universe."""
        response = client.post(
            f"/api/v1/conversations/{TEST_CONVERSATION_ID}/fact-checks/1",
            json={
                "merchant_name": "nonexistent_merchant",
                "scenario_name": "fake_scenario",
            },
        )
        assert response.status_code == 400
        assert "Universe not found" in response.json()["detail"]

    @pytest.mark.skip(reason="Requires actual API calls")
    def test_start_fact_check_success(self):
        """Test successfully starting a fact-check."""
        response = client.post(
            f"/api/v1/conversations/{TEST_CONVERSATION_ID}/fact-checks/1",
            json={
                "merchant_name": "marcus_thompson",
                "scenario_name": "steady_operations",
                "force_refresh": False,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "checking"
        assert data["message_index"] == 1
        assert "checking_progress" in data

        # Wait a bit for async processing
        time.sleep(2)

        # Check if fact-check completed
        response = client.get(
            f"/api/v1/conversations/{TEST_CONVERSATION_ID}/fact-checks/1"
        )
        data = response.json()

        # Should either be checking or complete
        assert data["status"] in ["checking", "complete"]
        if data["status"] == "complete":
            assert "result" in data
            assert "overall_status" in data["result"]
            assert "claims" in data["result"]

    def test_get_all_fact_checks_empty(self):
        """Test getting all fact-checks for conversation with none."""
        # Use a unique conversation ID for this test
        test_id = "test_empty_fact_checks"
        test_path = Path("data/conversations") / f"{test_id}.json"

        # Create test conversation
        empty_conv = SAMPLE_CONVERSATION.copy()
        empty_conv["id"] = test_id
        empty_conv["fact_checks"] = {}
        with open(test_path, "w") as f:
            json.dump(empty_conv, f)

        try:
            response = client.get(f"/api/v1/conversations/{test_id}/fact-checks")
            assert response.status_code == 200

            data = response.json()
            assert data["conversation_id"] == test_id
            assert data["fact_checks"] == {}
            assert data["total_messages"] == 4
            assert data["cj_messages"] == 2
        finally:
            # Clean up
            if test_path.exists():
                test_path.unlink()

    def test_delete_fact_check_not_found(self):
        """Test deleting non-existent fact-check."""
        # Use a unique conversation ID for this test
        test_id = "test_delete_not_found"
        test_path = Path("data/conversations") / f"{test_id}.json"

        # Create test conversation
        delete_conv = SAMPLE_CONVERSATION.copy()
        delete_conv["id"] = test_id
        delete_conv["fact_checks"] = {}
        with open(test_path, "w") as f:
            json.dump(delete_conv, f)

        try:
            response = client.delete(f"/api/v1/conversations/{test_id}/fact-checks/1")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "not_found"
            assert "No fact check found" in data["message"]
        finally:
            # Clean up
            if test_path.exists():
                test_path.unlink()

    @pytest.mark.skip(reason="Requires actual API calls")
    def test_fact_check_persistence(self):
        """Test that fact-checks are persisted in conversation file."""
        # Create a fresh conversation for this test
        test_conv_id = "test_persist_fact_check"
        test_path = Path("data/conversations") / f"{test_conv_id}.json"

        # Create conversation
        conv_data = {**SAMPLE_CONVERSATION, "id": test_conv_id}
        with open(test_path, "w") as f:
            json.dump(conv_data, f)

        try:
            # Start fact-check
            response = client.post(
                f"/api/v1/conversations/{test_conv_id}/fact-checks/1",
                json={
                    "merchant_name": "marcus_thompson",
                    "scenario_name": "steady_operations",
                },
            )
            assert response.status_code == 200

            # Wait for processing
            time.sleep(3)

            # Load conversation file and check for fact_checks
            with open(test_path, "r") as f:
                saved_conv = json.load(f)

            # Should have fact_checks field if completed
            if "fact_checks" in saved_conv:
                assert "1" in saved_conv["fact_checks"]
                fact_check = saved_conv["fact_checks"]["1"]
                assert "overall_status" in fact_check
                assert "claims" in fact_check

        finally:
            # Clean up
            if test_path.exists():
                test_path.unlink()

    @pytest.mark.skip(reason="Requires actual API calls")
    def test_force_refresh(self):
        """Test force refresh parameter."""
        response = client.post(
            f"/api/v1/conversations/{TEST_CONVERSATION_ID}/fact-checks/1",
            json={
                "merchant_name": "marcus_thompson",
                "scenario_name": "steady_operations",
                "force_refresh": True,
            },
        )

        # Should accept force_refresh parameter
        assert response.status_code in [200, 400]  # 400 if universe missing

    def test_concurrent_fact_checks(self):
        """Test handling concurrent fact-check requests."""
        # This would test that multiple fact-checks don't interfere
        # For now, just verify the endpoint handles multiple requests

        for i in range(3):
            response = client.get(
                f"/api/v1/conversations/{TEST_CONVERSATION_ID}/fact-checks/1"
            )
            assert response.status_code == 200


@pytest.mark.skip(reason="Fact-checking endpoints not implemented yet")
class TestFactCheckingEdgeCases:
    """Test edge cases and error handling."""

    def test_malformed_conversation_file(self):
        """Test handling of malformed conversation files."""
        bad_conv_id = "test_malformed"
        bad_path = Path("data/conversations") / f"{bad_conv_id}.json"

        # Create malformed JSON
        with open(bad_path, "w") as f:
            f.write("{invalid json")

        try:
            response = client.get(f"/api/v1/conversations/{bad_conv_id}/fact-checks/0")
            assert response.status_code == 500
        finally:
            if bad_path.exists():
                bad_path.unlink()

    def test_conversation_without_messages(self):
        """Test fact-checking conversation with no messages."""
        empty_conv_id = "test_empty"
        empty_path = Path("data/conversations") / f"{empty_conv_id}.json"

        empty_conv = {
            "id": empty_conv_id,
            "messages": [],
            "created_at": "2025-05-27T10:00:00Z",
        }

        with open(empty_path, "w") as f:
            json.dump(empty_conv, f)

        try:
            response = client.post(
                f"/api/v1/conversations/{empty_conv_id}/fact-checks/0",
                json={
                    "merchant_name": "marcus_thompson",
                    "scenario_name": "steady_operations",
                },
            )
            assert response.status_code == 400
            assert "Invalid message index" in response.json()["detail"]
        finally:
            if empty_path.exists():
                empty_path.unlink()
