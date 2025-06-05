"""
Manual test script to verify CJ sees UI instructions.

Run this script to check that the shopify_onboarding workflow
includes UI component instructions when loaded.
"""

import sys
sys.path.append('.')

from app.workflows.loader import WorkflowLoader
from app.agents.cj_agent import CJAgent


def test_workflow_has_ui_instructions():
    """Test that UI instructions are present in workflow."""
    print("=== Testing Workflow Loader ===")
    
    loader = WorkflowLoader()
    workflow_data = loader.get_workflow("shopify_onboarding")
    
    print(f"\nWorkflow name: {workflow_data.get('name', 'Unknown')}")
    print(f"UI components enabled: {workflow_data.get('ui_components', {}).get('enabled', False)}")
    print(f"Components: {workflow_data.get('ui_components', {}).get('components', [])}")
    
    # Check if UI instructions are in the workflow
    workflow_text = workflow_data.get('workflow', '')
    has_ui_instructions = "UI COMPONENT AVAILABLE" in workflow_text
    has_oauth_marker = "{{oauth:shopify}}" in workflow_text
    
    print(f"\nHas UI instructions: {has_ui_instructions}")
    print(f"Has OAuth marker example: {has_oauth_marker}")
    
    if has_ui_instructions:
        # Extract just the UI instructions part
        ui_start = workflow_text.find("UI COMPONENT AVAILABLE")
        if ui_start != -1:
            # Find the end of the UI instructions (next double newline or end)
            ui_end = workflow_text.find("\n\n", ui_start)
            if ui_end == -1:
                ui_end = len(workflow_text)
            ui_section = workflow_text[ui_start:ui_end]
            print("\n=== UI Instructions Added to Workflow ===")
            print(ui_section)
    
    return has_ui_instructions and has_oauth_marker


def test_cj_agent_workflow():
    """Test that CJ agent receives the workflow with UI instructions."""
    print("\n\n=== Testing CJ Agent ===")
    
    # Create a mock context manager to avoid database dependencies
    class MockContextManager:
        def get_conversation_context(self, *args, **kwargs):
            return {}
    
    # Create CJ agent with shopify_onboarding workflow
    cj = CJAgent(
        merchant_name="Test Merchant",
        scenario_name="shopify_onboarding",  # This becomes the workflow name
        merchant_id="test-merchant",
        conversation_id="test-conversation",
        session_id="test-session",
        workflow_name="shopify_onboarding",
        message_processor=None,  # Not needed for this test
        context_manager=MockContextManager()
    )
    
    # Check if workflow data includes UI instructions
    workflow_text = cj.workflow_data.get('workflow', '') if cj.workflow_data else ''
    has_ui_instructions = "UI COMPONENT AVAILABLE" in workflow_text
    has_oauth_marker = "{{oauth:shopify}}" in workflow_text
    
    print(f"CJ workflow includes UI instructions: {has_ui_instructions}")
    print(f"CJ workflow includes OAuth marker: {has_oauth_marker}")
    
    # Also check that UI components are enabled in the data
    ui_enabled = cj.workflow_data.get('ui_components', {}).get('enabled', False) if cj.workflow_data else False
    print(f"UI components enabled in workflow data: {ui_enabled}")
    
    # Show a snippet of the workflow with UI instructions
    if has_ui_instructions:
        ui_start = workflow_text.find("UI COMPONENT AVAILABLE")
        if ui_start != -1:
            snippet_end = min(ui_start + 300, len(workflow_text))
            print(f"\nWorkflow snippet:\n...{workflow_text[ui_start:snippet_end]}...")
    
    return has_ui_instructions and has_oauth_marker


if __name__ == "__main__":
    print("Manual Test: Verify CJ Sees UI Instructions")
    print("=" * 50)
    
    # Test workflow loader
    workflow_test_passed = test_workflow_has_ui_instructions()
    
    # Test CJ agent
    cj_test_passed = test_cj_agent_workflow()
    
    print("\n" + "=" * 50)
    print(f"Workflow Loader Test: {'PASSED' if workflow_test_passed else 'FAILED'}")
    print(f"CJ Agent Test: {'PASSED' if cj_test_passed else 'FAILED'}")
    print("=" * 50)
    
    if workflow_test_passed and cj_test_passed:
        print("\n✅ Phase 4.2 Manual Test: PASSED")
        print("CJ will now see UI component instructions and can use {{oauth:shopify}} markers!")
    else:
        print("\n❌ Phase 4.2 Manual Test: FAILED")
        print("Check the implementation and debug the issues.")