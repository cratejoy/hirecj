"""Example demonstrating grounding knowledge integration.

This example shows how to:
1. Create a CJ prompt with grounding directives
2. Create a workflow with grounding configuration
3. Test the grounding functionality
"""

import asyncio
import sys
from pathlib import Path
import yaml
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.grounding_manager import GroundingManager
from app.models import Message


# Example CJ prompt with grounding
EXAMPLE_CJ_PROMPT = """
You are CJ, an AI assistant with specialized knowledge.

{{grounding: npr}}

Use the above knowledge to help answer questions about NPR programs, hosts, and content.
Always cite specific information from the knowledge base when available.

Remember to be helpful and accurate in your responses.
"""

# Example workflow with grounding
EXAMPLE_WORKFLOW = {
    "name": "NPR Support Workflow",
    "workflow": """
Help users with questions about NPR content, programs, and hosts.
Focus on providing accurate information from our knowledge base.
    """,
    "grounding": ["npr"],
    "requirements": {
        "merchant": True,
        "scenario": True,
        "authentication": False
    }
}


async def test_grounding_extraction():
    """Test extracting grounding directives from content."""
    print("=== Testing Grounding Extraction ===")
    
    manager = GroundingManager()
    
    # Test simple extraction
    directives = manager.extract_grounding_directives(EXAMPLE_CJ_PROMPT)
    print(f"\nFound {len(directives)} grounding directives:")
    for d in directives:
        print(f"  - Namespace: {d.namespace}, Limit: {d.limit}, Mode: {d.mode}")
    
    # Test with parameters
    content_with_params = """
    {{grounding: npr, limit: 5}}
    {{grounding: docs, mode: global, limit: 3}}
    """
    
    directives = manager.extract_grounding_directives(content_with_params)
    print(f"\nWith parameters - found {len(directives)} directives:")
    for d in directives:
        print(f"  - Namespace: {d.namespace}, Limit: {d.limit}, Mode: {d.mode}")


async def test_query_building():
    """Test building queries from conversation context."""
    print("\n=== Testing Query Building ===")
    
    manager = GroundingManager()
    
    # Create sample conversation
    messages = [
        Message(
            sender="merchant",
            content="I'm looking for information about Fresh Air",
            timestamp=datetime.now()
        ),
        Message(
            sender="CJ",
            content="I'd be happy to help you learn about Fresh Air!",
            timestamp=datetime.now()
        ),
        Message(
            sender="merchant",
            content="Who hosts the show and when does it air?",
            timestamp=datetime.now()
        ),
    ]
    
    # Build query
    query = manager._build_query_from_context(messages, limit=5)
    print(f"\nBuilt query from context:")
    print(f"  '{query}'")
    print("\nNote: Query prioritizes merchant messages")


async def test_grounding_replacement():
    """Test replacing grounding markers with content."""
    print("\n=== Testing Grounding Replacement ===")
    
    manager = GroundingManager()
    
    # Simulate grounding results
    grounding_results = {
        "npr": "\n\n[Knowledge from NPR database]:\nFresh Air is a radio show hosted by Terry Gross...\n",
        "docs": "\n\n[Knowledge from DOCS database]:\nDocumentation about NPR programs...\n"
    }
    
    # Test replacement
    content = "Let me help you. {{grounding: npr}} Also see: {{grounding: docs}}"
    result = manager.replace_grounding_markers(content, grounding_results)
    
    print("\nOriginal content:")
    print(f"  '{content}'")
    print("\nAfter replacement:")
    print(f"  '{result}'")


async def test_workflow_grounding():
    """Test workflow grounding configuration."""
    print("\n=== Testing Workflow Grounding ===")
    
    # Save example workflow to temp file
    workflow_path = Path("temp_workflow.yaml")
    with open(workflow_path, "w") as f:
        yaml.dump(EXAMPLE_WORKFLOW, f)
    
    print(f"\nExample workflow saved to: {workflow_path}")
    print("\nWorkflow configuration:")
    print(f"  Name: {EXAMPLE_WORKFLOW['name']}")
    print(f"  Grounding namespaces: {EXAMPLE_WORKFLOW['grounding']}")
    
    # Clean up
    workflow_path.unlink()


async def main():
    """Run all examples."""
    print("Grounding Knowledge Integration Examples")
    print("=" * 50)
    
    await test_grounding_extraction()
    await test_query_building()
    await test_grounding_replacement()
    await test_workflow_grounding()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo use in production:")
    print("1. Ensure knowledge service is running on port 8004")
    print("2. Create knowledge graphs using the knowledge service API")
    print("3. Add {{grounding: namespace}} to prompts or workflows")
    print("4. The system will automatically query and inject relevant knowledge")


if __name__ == "__main__":
    asyncio.run(main())