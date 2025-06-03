#!/usr/bin/env python3
"""Setup script for the HireCJ synthetic conversation generator."""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔧 {description}...")
    try:
        subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False


def main():
    """Main setup function."""

    print("🚀 Setting up HireCJ Synthetic Conversation Generator")
    print("=" * 60)

    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 or higher is required")
        sys.exit(1)

    print(f"✅ Python version: {sys.version.split()[0]}")

    # Create virtual environment if it doesn't exist
    if not Path("venv").exists():
        if not run_command("python -m venv venv", "Creating virtual environment"):
            sys.exit(1)
    else:
        print("✅ Virtual environment already exists")

    # Determine activation command based on OS
    if os.name == "nt":  # Windows
        activate_cmd = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
        python_cmd = "venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
        python_cmd = "venv/bin/python"

    # Install dependencies
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        sys.exit(1)

    if not run_command(
        f"{pip_cmd} install -r requirements-dev.txt", "Installing dependencies"
    ):
        sys.exit(1)

    # Initialize database
    if not run_command(f"{python_cmd} scripts/init_db.py", "Initializing database"):
        sys.exit(1)

    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        print("🔧 Creating .env file from template...")
        try:
            with open(".env.example", "r") as src, open(".env", "w") as dst:
                content = src.read()
                dst.write(content)
            print("✅ Created .env file - please add your API keys")
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
    else:
        print("✅ .env file already exists")

    # Install pre-commit hooks
    if not run_command(
        f"{pip_cmd} install pre-commit && {python_cmd} -m pre_commit install",
        "Installing pre-commit hooks",
    ):
        print("⚠️  Pre-commit hook installation failed (optional)")

    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("\nNext steps:")
    print(f"1. Activate virtual environment: {activate_cmd}")
    print("2. Add your OpenAI API key to .env file")
    print("3. Test the setup: make test-conversation")
    print("4. Start development server: make dev")
    print("\nFor help: make help")


if __name__ == "__main__":
    main()
