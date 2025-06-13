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
    """Run the knowledge service."""
    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "ingest":
            # Run the ingestion pipeline
            from src.ingest import main as ingest_main
            sys.argv = sys.argv[1:]  # Remove 'ingest' from args for ingest.py
            ingest_main()
            return
        elif command == "demo":
            # Run the demo explicitly
            from src.scripts.lightrag_transcripts_demo import main as demo_main
            print("Starting HireCJ Knowledge service (LightRAG demo mode)")
            demo_main()
            return
        else:
            print("Usage:")
            print("  python -m src              # Run interactive demo")
            print("  python -m src demo         # Run interactive demo")
            print("  python -m src ingest       # Run content ingestion")
            print("")
            print("Ingestion commands:")
            print("  python -m src ingest add URL [--limit N]  # Add content")
            print("  python -m src ingest process              # Process pipeline")
            print("  python -m src ingest status               # Show status")
            return
    
    # Default: run demo
    from src.scripts.lightrag_transcripts_demo import main as demo_main
    
    print("Starting HireCJ Knowledge service (LightRAG demo mode)")
    print(f"Environment: {os.environ.get('APP_ENV', 'development')}")
    
    # Check for API key
    if not os.environ.get('OPENAI_API_KEY'):
        print("WARNING: OPENAI_API_KEY not set")
    
    demo_main()


if __name__ == "__main__":
    main()