"""Loads workflow definitions from YAML files."""

import yaml
from pathlib import Path
from typing import Dict, Any, List


class WorkflowLoader:
    """Loads workflow definitions from YAML files."""

    def __init__(self, workflows_path: str = None):
        self.workflows_path = Path(workflows_path or "prompts/workflows")
        self._workflows = None

    @property
    def workflows(self) -> Dict[str, Any]:
        """Lazy load workflows from YAML files."""
        if self._workflows is None:
            self._workflows = {}
            if self.workflows_path.exists():
                for yaml_file in self.workflows_path.glob("*.yaml"):
                    with open(yaml_file, "r") as f:
                        workflow_data = yaml.safe_load(f)
                        workflow_name = yaml_file.stem
                        self._workflows[workflow_name] = workflow_data
        return self._workflows

    def get_workflow(self, name: str) -> Dict[str, Any]:
        """Get a workflow by name."""
        if name not in self.workflows:
            available = ", ".join(self.list_workflows())
            raise ValueError(f"Workflow '{name}' not found. Available: {available}")
        return self.workflows[name]

    def list_workflows(self) -> List[str]:
        """List all available workflow names."""
        return list(self.workflows.keys())

    def get_workflow_description(self, name: str) -> str:
        """Get just the workflow description."""
        workflow = self.get_workflow(name)
        return workflow.get("workflow", "")

    def get_workflow_display_name(self, name: str) -> str:
        """Get the display name for a workflow."""
        workflow = self.get_workflow(name)
        return workflow.get("name", name)
