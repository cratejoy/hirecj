#!/usr/bin/env python3
"""Validate universe files."""

import argparse
import os
import sys

# Add project directory to path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from app.universe.loader import UniverseLoader  # noqa: E402


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(description="Validate universe files")
    parser.add_argument("universe", help="Universe ID or file path to validate")
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed validation results"
    )

    args = parser.parse_args()

    loader = UniverseLoader()

    try:
        if args.universe.endswith(".yaml"):
            # Load from file path
            import yaml

            with open(args.universe, "r") as f:
                universe = yaml.safe_load(f)
            loader.validate(universe)
        else:
            # Load by ID
            universe = loader.load(args.universe)

        print(f"✅ Universe validation passed: {args.universe}")

        if args.verbose:
            metadata = universe["metadata"]
            print(f"  Universe ID: {metadata['universe_id']}")
            print(f"  Merchant: {metadata['merchant']}")
            print(f"  Scenario: {metadata['scenario']}")
            print(f"  Customers: {len(universe.get('customers', []))}")
            print(f"  Tickets: {len(universe.get('support_tickets', []))}")

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
