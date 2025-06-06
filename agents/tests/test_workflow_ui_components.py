import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import yaml

from app.workflows.loader import WorkflowLoader


@pytest.fixture
def mock_workflows_path(tmp_path):
    """Create temporary workflows directory."""
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    
    # Create shopify_onboarding workflow with UI components
    shopify_workflow = {
        "name": "Shopify Onboarding",
        "description": "Test workflow with UI components",
        "version": "1.0.0",
        "active": True,
        "ui_components": {
            "enabled": True,
            "components": ["oauth"]
        },
        "workflow": "WORKFLOW: Shopify Onboarding\nBasic workflow content"
    }
    
    with open(workflows_dir / "shopify_onboarding.yaml", "w") as f:
        yaml.dump(shopify_workflow, f)
    
    # Create basic workflow without UI components
    basic_workflow = {
        "name": "Basic Workflow",
        "description": "Test workflow without UI components",
        "version": "1.0.0",
        "active": True,
        "workflow": "WORKFLOW: Basic\nBasic workflow content"
    }
    
    with open(workflows_dir / "basic_workflow.yaml", "w") as f:
        yaml.dump(basic_workflow, f)
    
    return workflows_dir


def test_workflow_loads_ui_instructions(mock_workflows_path):
    """Test that UI instructions are added to workflow."""
    loader = WorkflowLoader(workflows_path=str(mock_workflows_path))
    workflow_data = loader.get_workflow("shopify_onboarding")
    
    # Verify UI instructions were added
    assert "UI COMPONENT AVAILABLE" in workflow_data['workflow']
    assert "{{oauth:shopify}}" in workflow_data['workflow']
    assert "When ready to connect Shopify" in workflow_data['workflow']
    
    # Verify original content is preserved
    assert "WORKFLOW: Shopify Onboarding" in workflow_data['workflow']
    assert "Basic workflow content" in workflow_data['workflow']


def test_workflow_without_ui_components(mock_workflows_path):
    """Test workflows without UI components aren't modified."""
    loader = WorkflowLoader(workflows_path=str(mock_workflows_path))
    workflow_data = loader.get_workflow("basic_workflow")
    
    # Should not contain UI instructions
    assert "UI COMPONENT AVAILABLE" not in workflow_data['workflow']
    assert "{{oauth:shopify}}" not in workflow_data['workflow']
    
    # Should contain original content
    assert "WORKFLOW: Basic" in workflow_data['workflow']
    assert "Basic workflow content" in workflow_data['workflow']


def test_workflow_with_disabled_ui_components(tmp_path):
    """Test workflow with explicitly disabled UI components."""
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    
    disabled_workflow = {
        "name": "Disabled UI Workflow",
        "workflow": "WORKFLOW: Disabled\nContent here",
        "ui_components": {
            "enabled": False,
            "components": ["oauth"]
        }
    }
    
    with open(workflows_dir / "disabled_ui.yaml", "w") as f:
        yaml.dump(disabled_workflow, f)
    
    loader = WorkflowLoader(workflows_path=str(workflows_dir))
    workflow_data = loader.get_workflow("disabled_ui")
    
    # Should not add UI instructions when disabled
    assert "UI COMPONENT AVAILABLE" not in workflow_data['workflow']


def test_workflow_cached_version_not_modified(mock_workflows_path):
    """Test that cached workflow version isn't modified."""
    loader = WorkflowLoader(workflows_path=str(mock_workflows_path))
    
    # First load
    workflow_data1 = loader.get_workflow("shopify_onboarding")
    assert "UI COMPONENT AVAILABLE" in workflow_data1['workflow']
    
    # Second load should also have UI instructions
    workflow_data2 = loader.get_workflow("shopify_onboarding")
    assert "UI COMPONENT AVAILABLE" in workflow_data2['workflow']
    
    # Cached version should not be modified
    cached_workflow = loader.workflows["shopify_onboarding"]
    assert "UI COMPONENT AVAILABLE" not in cached_workflow['workflow']


def test_get_ui_instructions_method():
    """Test the _get_ui_instructions method directly."""
    loader = WorkflowLoader()
    
    # Test with oauth component
    ui_config = {"components": ["oauth"]}
    instructions = loader._get_ui_instructions(ui_config)
    
    assert "UI COMPONENT AVAILABLE" in instructions
    assert "{{oauth:shopify}}" in instructions
    assert "Let's connect your store: {{oauth:shopify}}" in instructions
    
    # Test with empty components
    ui_config = {"components": []}
    instructions = loader._get_ui_instructions(ui_config)
    assert instructions == ""
    
    # Test with no components key
    ui_config = {}
    instructions = loader._get_ui_instructions(ui_config)
    assert instructions == ""