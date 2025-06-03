"""Loads text-based scenarios from YAML."""

import yaml
from pathlib import Path
from typing import Dict, Any, List


class ScenarioLoader:
    """Loads text-based scenarios from YAML."""

    def __init__(self, scenarios_file: str = None):
        # If no file specified, load both normal and extreme scenarios
        if scenarios_file:
            self.scenarios_files = [Path(scenarios_file)]
        else:
            # Get the project root directory (two levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            self.scenarios_files = [
                project_root / "prompts/scenarios/business_scenarios.yaml",
                project_root / "prompts/scenarios/normal_business_scenarios.yaml",
            ]
        self._scenarios = None

    @property
    def scenarios(self) -> Dict[str, Any]:
        """Lazy load scenarios from YAML."""
        if self._scenarios is None:
            self._scenarios = {}
            for scenarios_file in self.scenarios_files:
                if scenarios_file.exists():
                    with open(scenarios_file, "r") as f:
                        data = yaml.safe_load(f)
                        # Merge scenarios from this file
                        self._scenarios.update(data.get("scenarios", {}))

            if not self._scenarios:
                raise ValueError("No scenarios found in any scenario files")
        return self._scenarios

    def get_scenario(self, name: str) -> Dict[str, Any]:
        """Get a scenario by name."""
        if name not in self.scenarios:
            available = ", ".join(self.list_scenarios())
            raise ValueError(f"Scenario '{name}' not found. Available: {available}")
        return self.scenarios[name]

    def list_scenarios(self) -> List[str]:
        """List all available scenario names."""
        return list(self.scenarios.keys())

    def get_scenario_text(self, name: str) -> str:
        """Get just the scenario text for a given scenario."""
        scenario = self.get_scenario(name)
        return scenario.get("scenario", "")

    def get_scenario_display_name(self, name: str) -> str:
        """Get the display name for a scenario."""
        scenario = self.get_scenario(name)
        return scenario.get("name", name)
