"""
Main entry point for the HireCJ Knowledge service.

This module provides a standardized way to run the service with:
    python -m src
"""
import os
import sys

# Ensure the parent directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Run the knowledge service demo."""
    # For now, run the demo script as the main entry point
    # In the future, this could be a proper API service
    from src.scripts.lightrag_transcripts_demo import main as demo_main
    
    print("Starting HireCJ Knowledge service (LightRAG demo mode)")
    print(f"Environment: {os.environ.get('APP_ENV', 'development')}")
    
    # Check for API key
    if not os.environ.get('OPENAI_API_KEY'):
        print("WARNING: OPENAI_API_KEY not set")
    
    demo_main()


if __name__ == "__main__":
    main()