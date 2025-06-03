"""Universe loading and validation."""

import yaml
from pathlib import Path
from typing import Dict, Any


class UniverseLoader:
    """Loads and validates universe files."""

    def __init__(self, universes_path: str = "data/universes"):
        """Initialize with path to universes directory."""
        self.universes_path = Path(universes_path)

    def load(self, universe_id: str) -> Dict[str, Any]:
        """Load a universe by ID."""

        universe_file = self.universes_path / f"{universe_id}.yaml"
        if not universe_file.exists():
            raise FileNotFoundError(f"Universe not found: {universe_file}")

        with open(universe_file, "r") as f:
            universe = yaml.safe_load(f)

        self.validate(universe)
        return universe

    def load_by_merchant_scenario(
        self, merchant_name: str, scenario_name: str
    ) -> Dict[str, Any]:
        """Load universe by merchant and scenario names."""

        universe_id = f"{merchant_name}_{scenario_name}_v1"
        return self.load(universe_id)

    def exists(self, universe_id: str) -> bool:
        """Check if universe exists."""

        universe_file = self.universes_path / f"{universe_id}.yaml"
        return universe_file.exists()

    def list_universes(self) -> list:
        """List all available universes."""

        if not self.universes_path.exists():
            return []

        universes = []
        for file in self.universes_path.glob("*.yaml"):
            universes.append(file.stem)

        return sorted(universes)

    def validate(self, universe: Dict[str, Any]) -> bool:
        """Validate universe structure."""

        # Check required sections
        required_sections = ["metadata", "customers", "support_tickets"]
        for section in required_sections:
            if section not in universe:
                raise ValueError(f"Missing required section: {section}")

        # Validate metadata
        metadata = universe["metadata"]
        required_metadata = ["universe_id", "merchant", "scenario", "current_day"]
        for field in required_metadata:
            if field not in metadata:
                raise ValueError(f"Missing required metadata field: {field}")

        # Validate customer references in tickets
        customer_ids = set(c["customer_id"] for c in universe["customers"])
        for ticket in universe["support_tickets"]:
            if ticket["customer_id"] not in customer_ids:
                raise ValueError(
                    f"Ticket references unknown customer: {ticket['customer_id']}"
                )

        return True
