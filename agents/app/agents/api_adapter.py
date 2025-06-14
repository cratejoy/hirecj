"""
API Adapter for CrewAI compatibility.

This module provides adapter classes that mimic the CrewAI interface but route
all calls through the ConversationAPI WebSocket backend. This allows existing
scripts to work unchanged while using the API for proper session management.
"""

import time
from typing import List, Dict, Any, Optional
from collections import defaultdict

from app.clients.conversation_api import ConversationAPI
from shared.logging_config import get_logger

logger = get_logger(__name__)


class APIClientManager:
    """Manages API client instances without globals."""

    _instance: Optional["APIClientManager"] = None

    def __init__(self):
        self.client: Optional[ConversationAPI] = None
        self.enable_fact_checking = True
        self.performance_metrics = defaultdict(lambda: defaultdict(float))
        self.performance_metrics["response_times"] = []
        self.performance_metrics["success_count"] = 0
        self.performance_metrics["error_count"] = 0
        self.performance_metrics["total_time"] = 0.0

    @classmethod
    def get_instance(cls) -> "APIClientManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_client(self) -> ConversationAPI:
        """Get or create API client."""
        if not self.client:
            from app.config import settings

            base_url = settings.api_ws_url
            self.client = ConversationAPI(base_url=base_url)
            logger.info(f"Created API client connecting to {base_url}")
        return self.client

    def reset(self):
        """Reset client and metrics."""
        if self.client:
            self.client.reset_session()
        self.performance_metrics.clear()
        self.performance_metrics["response_times"] = []
        self.performance_metrics["success_count"] = 0
        self.performance_metrics["error_count"] = 0


# Singleton instance
_manager = APIClientManager.get_instance()


def get_api_client() -> ConversationAPI:
    """Get or create the API client."""
    return _manager.get_client()


def create_cj_agent(
    merchant_name: str,
    scenario_name: str,
    workflow_name: str = None,
    prompt_version: str = None,
    enable_fact_checking: bool = True,
    **kwargs,
):
    """Drop-in replacement for the original create_cj_agent.

    Args:
        merchant_name: Name of the merchant persona
        scenario_name: Name of the business scenario
        workflow_name: Optional workflow (e.g., 'daily_briefing')
        prompt_version: CJ version to use (e.g., 'v6.0.1')
        enable_fact_checking: Whether to enable fact checking
        **kwargs: Additional arguments (reserved for future use)

    Returns:
        Agent: An API-backed agent that routes through WebSocket
    """
    _manager.enable_fact_checking = enable_fact_checking
    return Agent(
        merchant_name=merchant_name,
        scenario_name=scenario_name,
        workflow_name=workflow_name,
        prompt_version=prompt_version,
        enable_fact_checking=enable_fact_checking,
    )


class Agent:
    """Mimics CrewAI Agent interface but routes through API."""

    def __init__(self, **kwargs):
        self.config = kwargs
        # Store configuration that would normally go to agent
        self.role = f"CJ Agent for {kwargs.get('merchant_name', 'unknown')}"
        self.goal = "Help merchants succeed"
        self.backstory = (
            f"Working with scenario: {kwargs.get('scenario_name', 'unknown')}"
        )

    def __repr__(self):
        return f"Agent(role='{self.role}')"


class Task:
    """Mimics CrewAI Task interface."""

    def __init__(self, description: str, agent: Agent, expected_output: str = None):
        self.description = description
        self.agent = agent
        self.expected_output = expected_output or "A helpful response"

    def __repr__(self):
        return f"Task(description='{self.description[:50]}...')"


class Crew:
    """Mimics CrewAI Crew interface but routes through API."""

    def __init__(self, agents: List[Agent], tasks: List[Task], verbose: bool = False):
        self.agents = agents
        self.tasks = tasks
        self.verbose = verbose
        # Extract config from first agent (they should all have same config)
        if agents:
            self.config = agents[0].config
        else:
            self.config = {}

    def kickoff(self) -> str:
        """Execute the crew's tasks through the API."""
        if not self.tasks:
            return "No tasks to execute"

        # Track performance
        start_time = time.time()

        try:
            # Get the first task's description as the prompt
            prompt = self.tasks[0].description

            # Extract config from crew
            api_client = get_api_client()
            response = api_client.kickoff(
                merchant=self.config.get("merchant_name", "marcus_thompson"),
                scenario=self.config.get("scenario_name", "steady_operations"),
                workflow=self.config.get("workflow_name", "chat"),
                message=prompt,
            )

            # Track success metrics
            elapsed = time.time() - start_time
            _manager.performance_metrics["response_times"].append(elapsed)
            _manager.performance_metrics["success_count"] += 1
            _manager.performance_metrics["total_time"] += elapsed

            if self.verbose:
                logger.info(f"API response received in {elapsed:.2f}s")

            return response

        except Exception as e:
            # Track error metrics
            elapsed = time.time() - start_time
            _manager.performance_metrics["error_count"] += 1
            _manager.performance_metrics["total_time"] += elapsed

            logger.error(f"API call failed: {str(e)}")
            raise


# Helper functions for API management
def reset_api_client():
    """Reset the API client (useful for testing)."""
    _manager.reset()


def reset_conversation(
    merchant: str = None, scenario: str = None, workflow: str = None
):
    """Reset a specific conversation or all conversations."""
    client = get_api_client()
    client.reset_session(merchant=merchant, scenario=scenario, workflow=workflow)


def set_fact_checking(enabled: bool):
    """Set fact checking on/off globally."""
    _manager.enable_fact_checking = enabled


def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics."""
    metrics = dict(_manager.performance_metrics)
    if metrics.get("response_times"):
        avg_time = sum(metrics["response_times"]) / len(metrics["response_times"])
        metrics["average_response_time"] = avg_time
    return metrics
