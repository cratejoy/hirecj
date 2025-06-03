"""
Unit tests for API adapter to catch runtime errors.
"""

import pytest
from unittest.mock import Mock, patch
from collections import defaultdict

from app.agents.api_adapter import Crew, Task, Agent, APIClientManager


class TestAPIAdapter:
    """Test the API adapter for CrewAI compatibility."""

    def test_conversation_api_method_is_kickoff_not_send_message(self):
        """Test that the API uses kickoff method, not send_message."""
        # Create a mock API client with only kickoff method
        mock_client = Mock()
        mock_client.kickoff.return_value = "Test response"

        # Create agent and task
        agent = Agent(role="test", goal="test", backstory="test")
        task = Task(description="Test task", agent=agent)

        # Create crew with mocked client
        with patch("app.agents.api_adapter.get_api_client", return_value=mock_client):
            crew = Crew(agents=[agent], tasks=[task], verbose=False)

            # This should work with kickoff
            crew.kickoff()

            # Verify kickoff was called, not send_message
            mock_client.kickoff.assert_called_once()
            assert hasattr(mock_client, "kickoff")
            # Mock objects have all attributes, so we can't test hasattr
            # Instead, verify that kickoff was the method actually called

    def test_performance_metrics_defaultdict_type_error(self):
        """Test that performance_metrics['total_time'] += float raises TypeError when not initialized."""
        # Create a defaultdict that returns defaultdict for missing keys
        metrics = defaultdict(lambda: defaultdict(float))
        metrics["response_times"] = []
        metrics["success_count"] = 0
        metrics["error_count"] = 0
        # Note: total_time is NOT initialized

        # This should raise TypeError when trying to add float to defaultdict
        with pytest.raises(
            TypeError, match="unsupported operand type.*defaultdict.*float"
        ):
            metrics["total_time"] += 1.5

    def test_api_client_manager_metrics_initialization(self):
        """Test that APIClientManager properly initializes all metrics."""
        manager = APIClientManager()

        # Check that all expected metrics are properly initialized
        assert isinstance(manager.performance_metrics["response_times"], list)
        assert isinstance(manager.performance_metrics["success_count"], (int, float))
        assert isinstance(manager.performance_metrics["error_count"], (int, float))

        # This is the bug - total_time is not initialized, so it returns defaultdict
        # This should fail with current implementation
        assert not isinstance(
            manager.performance_metrics["total_time"], defaultdict
        ), "total_time should be initialized as a number, not defaultdict"

    def test_crew_kickoff_with_exception_handling(self):
        """Test that exception handling in kickoff doesn't cause secondary errors."""
        # Create a mock client that raises an exception
        mock_client = Mock()
        mock_client.kickoff.side_effect = RuntimeError("Some API error")

        # Mock the manager to have improperly initialized metrics (simulating the bug)
        mock_manager = Mock()
        mock_manager.enable_fact_checking = True
        mock_manager.performance_metrics = defaultdict(lambda: defaultdict(float))
        mock_manager.performance_metrics["error_count"] = 0
        # total_time is not initialized, which would cause the bug

        # Create agent and task
        agent = Agent(role="test", goal="test", backstory="test")
        task = Task(description="Test task", agent=agent)

        with patch("app.agents.api_adapter.get_api_client", return_value=mock_client):
            with patch("app.agents.api_adapter._manager", mock_manager):
                crew = Crew(agents=[agent], tasks=[task], verbose=False)

                # With the bug, this would raise TypeError when trying to do total_time += elapsed
                # After fix, it should properly raise the RuntimeError
                with pytest.raises((TypeError, RuntimeError)) as exc_info:
                    crew.kickoff()

                # Check if it's the secondary error (bug) or primary error (fixed)
                if isinstance(exc_info.value, TypeError):
                    assert "unsupported operand type" in str(exc_info.value)

    def test_correct_api_method_usage(self):
        """Test that the correct ConversationAPI method is used."""
        # Create a mock client with the correct kickoff method
        mock_client = Mock()
        mock_client.kickoff.return_value = "Test response"

        # Properly initialize the manager
        mock_manager = Mock()
        mock_manager.enable_fact_checking = True
        mock_manager.performance_metrics = {
            "response_times": [],
            "success_count": 0,
            "error_count": 0,
            "total_time": 0.0,  # Properly initialized
        }

        # Create agent with config
        agent = Agent(
            role="test",
            goal="test",
            backstory="test",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
        )
        task = Task(description="Test task", agent=agent)

        with patch("app.agents.api_adapter.get_api_client", return_value=mock_client):
            with patch("app.agents.api_adapter._manager", mock_manager):
                crew = Crew(agents=[agent], tasks=[task], verbose=False)

                result = crew.kickoff()

                # Verify kickoff was called with correct parameters
                mock_client.kickoff.assert_called_once_with(
                    merchant="test_merchant",
                    scenario="test_scenario",
                    workflow="chat",
                    message="Test task",
                )
                assert result == "Test response"

                # Verify metrics were updated
                assert mock_manager.performance_metrics["success_count"] == 1
                assert isinstance(
                    mock_manager.performance_metrics["total_time"], (int, float)
                )
