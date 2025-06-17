"""
Conversation catalog with metadata for all available options.
Provides descriptions and characteristics for discovery.
"""

from dataclasses import dataclass
from typing import Dict, List
from enum import Enum
import yaml
import os
from app.scenarios.loader import ScenarioLoader


class StressLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class PersonalityType(str, Enum):
    DIRECT = "direct"  # Marcus - no fluff, numbers-focused
    COLLABORATIVE = "collaborative"  # Sarah - thoughtful, values-driven
    SCATTERED = "scattered"  # Zoe - social media, overwhelmed


@dataclass
class ScenarioMetadata:
    """Metadata about a business scenario."""

    name: str
    display_name: str
    stress_level: StressLevel
    description: str
    key_metrics: Dict[str, str]
    main_challenge: str
    urgency: str  # "immediate", "building", "chronic"


@dataclass
class WorkflowMetadata:
    """Metadata about a conversation workflow."""

    name: str
    display_name: str
    description: str
    typical_turns: int
    initiator: str  # "CJ" or "merchant"
    best_for: List[str]  # scenarios it works well with


class ConversationCatalog:
    """Registry of all available conversation options with rich metadata."""

    _catalog_data = None

    @classmethod
    def _load_catalog(cls) -> dict:
        """Load catalog data from YAML file."""
        if cls._catalog_data is None:
            catalog_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "config",
                "conversation_catalog.yaml",
            )
            with open(catalog_path, "r") as f:
                cls._catalog_data = yaml.safe_load(f)
        return cls._catalog_data

    @staticmethod
    def get_scenarios() -> Dict[str, ScenarioMetadata]:
        """Get all available business scenarios with metadata."""
        # Load scenarios from YAML
        scenarios = {}

        # Load all scenarios from YAML
        try:
            loader = ScenarioLoader()
            yaml_scenarios = loader.scenarios

            # Add all scenarios from YAML
            for scenario_key, scenario_data in yaml_scenarios.items():
                # Create metadata from YAML data
                scenarios[scenario_key] = ScenarioMetadata(
                    name=scenario_key,
                    display_name=scenario_data.get(
                        "name", scenario_key.replace("_", " ").title()
                    ),
                    stress_level=StressLevel.MODERATE,  # Default stress level
                    description=(
                        scenario_data.get("scenario", "")[:200] + "..."
                        if len(scenario_data.get("scenario", "")) > 200
                        else scenario_data.get("scenario", "")
                    ),
                    key_metrics={},  # YAML doesn't include these
                    main_challenge=scenario_key.replace("_", " "),
                    urgency="normal",
                )
        except Exception:
            # If loading fails, just use hardcoded scenarios
            pass

        return scenarios

    @staticmethod
    def get_workflows() -> Dict[str, WorkflowMetadata]:
        """Get all available conversation workflows with metadata."""
        catalog = ConversationCatalog._load_catalog()
        workflows = {}

        for workflow_id, data in catalog.get("workflows", {}).items():
            workflows[workflow_id] = WorkflowMetadata(
                name=data["name"],
                display_name=data["display_name"],
                description=data["description"],
                typical_turns=data["typical_turns"],
                initiator=data["initiator"],
                best_for=data["best_for"],
            )

        return workflows

    @staticmethod
    def get_cj_versions() -> Dict[str, str]:
        """Get available CJ versions with descriptions."""
        catalog = ConversationCatalog._load_catalog()
        return catalog.get("cj_versions", {})

    @staticmethod
    def get_recommended_combinations() -> List[Dict[str, str]]:
        """Get recommended persona/scenario/workflow combinations."""
        catalog = ConversationCatalog._load_catalog()
        return catalog.get("recommended_combinations", [])
