"""Universe discovery and validation utilities."""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import yaml


class UniverseDiscovery:
    """Discover and validate available universes."""

    def __init__(self, universe_dir: str = "data/universes"):
        self.universe_dir = Path(universe_dir)
        self._universes = self._scan_universes()

    def _scan_universes(self) -> Dict[Tuple[str, str], Path]:
        """Scan directory for available universes.

        Returns:
            Dict mapping (merchant, scenario) tuples to file paths
        """
        universes = {}

        if not self.universe_dir.exists():
            return universes

        for file_path in self.universe_dir.glob("*.yaml"):
            try:
                # Quick parse to get metadata
                with open(file_path, "r") as f:
                    # Only read first few lines for efficiency
                    content = ""
                    for _ in range(10):
                        line = f.readline()
                        if not line:
                            break
                        content += line

                    data = yaml.safe_load(content)
                    if data and "metadata" in data:
                        merchant = data["metadata"].get("merchant")
                        scenario = data["metadata"].get("scenario")
                        if merchant and scenario:
                            universes[(merchant, scenario)] = file_path
            except (yaml.YAMLError, KeyError, IOError):
                # Skip invalid files
                pass

        return universes

    def has_universe(self, merchant: str, scenario: str) -> bool:
        """Check if a universe exists for merchant/scenario combination."""
        return (merchant, scenario) in self._universes

    def get_available_combinations(self) -> List[Tuple[str, str]]:
        """Get all available merchant/scenario combinations."""
        return list(self._universes.keys())

    def get_available_merchants(self) -> List[str]:
        """Get unique merchants that have universes."""
        return sorted(list(set(m for m, _ in self._universes.keys())))

    def get_scenarios_for_merchant(self, merchant: str) -> List[str]:
        """Get scenarios available for a specific merchant."""
        return sorted([s for m, s in self._universes.keys() if m == merchant])

    def get_universe_path(self, merchant: str, scenario: str) -> Optional[Path]:
        """Get the path to a universe file if it exists."""
        return self._universes.get((merchant, scenario))

    def get_universe_info(self, merchant: str, scenario: str) -> Optional[Dict]:
        """Get basic info about a universe if it exists."""
        path = self.get_universe_path(merchant, scenario)
        if not path:
            return None

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
                metadata = data.get("metadata", {})
                return {
                    "path": str(path),
                    "generated_at": metadata.get("generated_at"),
                    "timeline_days": metadata.get("timeline_days"),
                    "current_day": metadata.get("current_day"),
                    "total_customers": len(data.get("customers", [])),
                    "total_tickets": len(data.get("support_tickets", [])),
                }
        except (yaml.YAMLError, IOError):
            return None

    def refresh(self):
        """Rescan for universes (useful after generation)."""
        self._universes = self._scan_universes()
