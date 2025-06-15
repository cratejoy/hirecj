"""Prompt loading utilities for version-controlled prompts."""

import yaml
from pathlib import Path
from typing import Dict, Any, List

from app.config import settings
from shared.logging_config import get_logger

logger = get_logger(__name__)


class PromptLoader:
    """Loads and manages version-controlled prompts."""

    def __init__(self, prompts_path: str = None):
        self.prompts_path = Path(prompts_path or settings.prompts_dir)

    def load_merchant_persona(
        self, persona_name: str, version: str = "latest"
    ) -> Dict[str, Any]:
        """Load a merchant persona prompt by name and version."""

        persona_dir = self.prompts_path / "merchants" / "personas" / persona_name

        if version == "latest":
            # Find the latest version
            version = self._get_latest_version(persona_dir)

        prompt_file = persona_dir / f"{version}.yaml"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Persona prompt not found: {prompt_file}")

        with open(prompt_file, "r") as f:
            return yaml.safe_load(f)

    def load_cj_prompt(self, version: str = "latest") -> Dict[str, Any]:
        """Load a CJ prompt by version."""

        cj_dir = self.prompts_path / "cj" / "versions"
        original_version = version

        if version == "latest":
            # Find the latest version
            version = self._get_latest_version(cj_dir)
            logger.info(f"Loading latest CJ prompt version: {version}")
        else:
            # Handle short versions like "v2" by finding the matching full version
            # Check if the version is a short version (e.g., "v2" instead of "v2.0.0")
            if version.count('.') < 2:
                matching_versions = []
                for file in cj_dir.glob(f"{version}.*.yaml"):
                    matching_versions.append(file.stem)
                
                if matching_versions:
                    # Sort and pick the latest matching version
                    def version_key(version_str):
                        parts = version_str[1:].split(".")
                        return [int(part) for part in parts]
                    version = sorted(matching_versions, key=version_key)[-1]
                    logger.info(f"Resolved short version '{original_version}' to '{version}'")

        prompt_file = cj_dir / f"{version}.yaml"

        if not prompt_file.exists():
            logger.error(f"CJ prompt file not found: {prompt_file}")
            # List available versions for debugging
            available = list(cj_dir.glob("*.yaml"))
            logger.error(f"Available CJ prompt files: {[f.name for f in available]}")
            raise FileNotFoundError(f"CJ prompt not found: {prompt_file}")

        logger.info(f"Loading CJ prompt from: {prompt_file}")
        with open(prompt_file, "r") as f:
            return yaml.safe_load(f)

    def list_merchant_personas(self) -> List[str]:
        """List available merchant personas."""

        personas_dir = self.prompts_path / "merchants" / "personas"

        if not personas_dir.exists():
            return []

        return [d.name for d in personas_dir.iterdir() if d.is_dir()]

    def list_cj_versions(self) -> List[str]:
        """List available CJ prompt versions."""

        versions_dir = self.prompts_path / "cj" / "versions"

        if not versions_dir.exists():
            return []

        versions = []
        for file in versions_dir.glob("*.yaml"):
            versions.append(file.stem)

        return sorted(versions)

    def list_persona_versions(self, persona_name: str) -> List[str]:
        """List available versions for a persona."""

        persona_dir = self.prompts_path / "merchants" / "personas" / persona_name

        if not persona_dir.exists():
            return []

        versions = []
        for file in persona_dir.glob("*.yaml"):
            if file.name != "metadata.yaml":
                versions.append(file.stem)

        return sorted(versions)

    def _get_latest_version(self, directory: Path) -> str:
        """Get the latest version from a directory of version files."""

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        versions = []
        for file in directory.glob("v*.yaml"):
            versions.append(file.stem)

        if not versions:
            raise FileNotFoundError(f"No version files found in: {directory}")

        # Sort versions semantically (v1.0.0, v1.1.0, v2.0.0, etc.)
        def version_key(version_str):
            # Remove 'v' prefix and split by '.'
            parts = version_str[1:].split(".")
            return [int(part) for part in parts]

        return sorted(versions, key=version_key)[-1]

    def get_prompt_metadata(
        self, persona_name: str = None, cj_version: str = None
    ) -> Dict[str, Any]:
        """Get metadata about prompts including performance metrics."""

        metadata = {}

        if persona_name:
            try:
                persona_data = self.load_merchant_persona(persona_name, "latest")
                metadata["merchant"] = {
                    "name": persona_name,
                    "version": persona_data.get("version"),
                    "performance": persona_data.get("metadata", {}).get(
                        "performance_metrics", {}
                    ),
                    "tested_scenarios": persona_data.get("metadata", {}).get(
                        "tested_scenarios", []
                    ),
                }
            except FileNotFoundError:
                metadata["merchant"] = {"error": f"Persona {persona_name} not found"}

        if cj_version:
            try:
                cj_data = self.load_cj_prompt(cj_version)
                metadata["cj"] = {
                    "version": cj_data.get("version"),
                    "performance": cj_data.get("metadata", {}).get(
                        "performance_metrics", {}
                    ),
                    "changes": cj_data.get("changes", []),
                }
            except FileNotFoundError:
                metadata["cj"] = {"error": f"CJ version {cj_version} not found"}

        return metadata
    
    def load_prompt(self, prompt_name: str, version: str = "latest") -> Dict[str, Any]:
        """Load a generic prompt by name and version.
        
        Args:
            prompt_name: Name of the prompt to load
            version: Version to load (default: "latest")
            
        Returns:
            Dict containing the prompt data with 'system' and/or 'user' keys
        """
        # Try to load from YAML file
        prompt_file = self.prompts_path / f"{prompt_name}.yaml"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_file, "r") as f:
            data = yaml.safe_load(f)
            
        # Extract the prompt data - it should be under the prompt_name key
        if prompt_name in data:
            return data[prompt_name]
        else:
            # If not found under the key, return the whole data
            return data


# Global prompt loader instance
prompt_loader = PromptLoader()
