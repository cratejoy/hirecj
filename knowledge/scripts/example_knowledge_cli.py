#!/usr/bin/env python3
"""
Example usage of the Knowledge CLI tool
"""
import subprocess
import sys
import os

def run_command(cmd):
    """Run a command and print the output"""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    print()
    return result.returncode

def main():
    """Demonstrate Knowledge CLI usage"""
    python = "venv/bin/python"
    cli = "scripts/knowledge.py"
    
    print("Knowledge CLI Example Usage")
    print("="*60)
    
    # Show help
    run_command([python, cli, "--help"])
    
    # List namespaces
    run_command([python, cli, "list"])
    
    # Create a test namespace
    run_command([python, cli, "create", "test_namespace", 
                 "--name", "Test Namespace", 
                 "--description", "Example namespace for testing",
                 "--set-default"])
    
    # List namespaces again to see the new one
    run_command([python, cli, "list"])
    
    # Show namespace statistics
    run_command([python, cli, "stats", "test_namespace"])
    
    # Create a test file to ingest
    test_file = "test_document.txt"
    with open(test_file, "w") as f:
        f.write("""# Test Document

This is a test document for the Knowledge CLI example.

## Features

The Knowledge CLI supports:
- File ingestion
- URL ingestion
- Directory ingestion with patterns
- Parallel uploads
- Progress tracking
- Configuration management

## Usage

You can ingest documents using various methods:
1. Single files
2. Multiple files with glob patterns
3. URLs
4. Directories (recursive or not)

This makes it easy to manage your knowledge base from the command line.
""")
    
    # Ingest the test file
    run_command([python, cli, "ingest", test_file, 
                 "-n", "test_namespace",
                 "-m", '{"source": "example", "type": "documentation"}'])
    
    # Show updated statistics
    run_command([python, cli, "stats", "test_namespace"])
    
    # Show configuration
    run_command([python, cli, "config", "--list"])
    
    # Clean up
    os.remove(test_file)
    print("\nExample completed! The test file has been cleaned up.")
    print("You now have a 'test_namespace' with one document.")

if __name__ == "__main__":
    main()