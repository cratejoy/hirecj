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
        
        workflow_data = self.workflows[name].copy()  # Don't modify cached version
        
        # Ensure requirements exist with sensible defaults
        if 'requirements' not in workflow_data:
            # Default: require everything (safer default)
            workflow_data['requirements'] = {
                'merchant': True,
                'scenario': True,
                'authentication': True
            }
        
        # Check if workflow enables UI components
        if workflow_data.get('ui_components', {}).get('enabled', False):
            # Add UI instructions to workflow
            ui_instructions = self._get_ui_instructions(
                workflow_data['ui_components']
            )
            workflow_data['workflow'] += f"\n\n{ui_instructions}"
        
        return workflow_data

    def list_workflows(self) -> List[str]:
        """List all available workflow names."""
        return list(self.workflows.keys())
    
    def workflow_exists(self, name: str) -> bool:
        """Check if a workflow exists."""
        return name in self.workflows
    
    def load_workflow(self, name: str) -> Dict[str, Any]:
        """Load a workflow by name. Alias for get_workflow for compatibility."""
        return self.get_workflow(name)

    def get_workflow_description(self, name: str) -> str:
        """Get just the workflow description."""
        workflow = self.get_workflow(name)
        return workflow.get("workflow", "")

    def get_workflow_display_name(self, name: str) -> str:
        """Get the display name for a workflow."""
        workflow = self.get_workflow(name)
        return workflow.get("name", name)

    def get_workflow_requirements(self, name: str) -> Dict[str, bool]:
        """Get just the requirements for a workflow."""
        workflow = self.get_workflow(name)
        return workflow.get('requirements', {
            'merchant': True,
            'scenario': True,
            'authentication': True
        })
    
    def get_workflow_behavior(self, name: str) -> Dict[str, Any]:
        """Get workflow behavior configuration."""
        workflow = self.get_workflow(name)
        return workflow.get('behavior', {
            'initiator': 'merchant',  # Default: merchant starts
            'initial_action': None,
            'transitions': {}
        })

    def _get_ui_instructions(self, ui_config: Dict) -> str:
        """Generate UI instructions based on workflow config."""
        instructions = []

        if 'oauth' in ui_config.get('components', []):
            instructions.append("""
UI COMPONENT AVAILABLE:
- When ready to connect Shopify, insert {{oauth:shopify}} where the button should appear
- Don't say "click the button below" - just include the marker naturally
- Example: "Let's connect your store: {{oauth:shopify}}"
""")

        return "\n".join(instructions)
