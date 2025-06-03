#!/usr/bin/env python3
"""Generate universe files following existing script patterns."""

import argparse
import os
import sys

# Add project directory to path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from app.universe.generator import UniverseGenerator  # noqa: E402
from app.universe.loader import UniverseLoader  # noqa: E402


def main():
    """Main entry point following existing script patterns."""

    parser = argparse.ArgumentParser(
        description="Generate universe files for merchant-scenario combinations"
    )
    parser.add_argument(
        "--merchant",
        default="marcus_thompson",
        help="Merchant name (default: marcus_thompson)",
    )
    parser.add_argument(
        "--scenario",
        default="steady_operations",
        help="Scenario name (default: steady_operations)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/universes",
        help="Output directory (default: data/universes)",
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate generated universe"
    )
    parser.add_argument(
        "--all", action="store_true", help="Generate all merchant-scenario combinations"
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress output")

    args = parser.parse_args()

    generator = UniverseGenerator()

    if args.all:
        generate_all_universes(generator, args)
    else:
        generate_single_universe(generator, args)


def generate_single_universe(generator: UniverseGenerator, args):
    """Generate a single universe."""

    if not args.quiet:
        print(f"🔄 Generating universe: {args.merchant} + {args.scenario}")

    try:
        # Generate universe
        universe = generator.generate(args.merchant, args.scenario)

        # Save to file
        output_path = generator.save_universe(universe)

        if not args.quiet:
            print(f"✅ Generated universe: {output_path}")

        # Validate if requested
        if args.validate:
            loader = UniverseLoader()
            loader.validate(universe)
            if not args.quiet:
                print("✅ Universe validation passed")

    except Exception as e:
        print(f"❌ Error generating universe: {e}")
        sys.exit(1)


def generate_all_universes(generator: UniverseGenerator, args):
    """Generate all merchant-scenario combinations."""

    # Available merchants and scenarios
    merchants = ["marcus_thompson", "sarah_chen", "zoe_martinez"]
    scenarios = [
        # Normal operations
        "steady_operations",
        "summer_lull",
        "pre_holiday_prep",
        "mothers_day_prep",
        "memorial_day_weekend",
        "post_black_friday",
        "january_reset",
        # Crisis/problem scenarios
        "growth_stall",
        "churn_spike",
        "return_to_growth",
        "scaling_chaos",
        "competitor_threat",
    ]

    total_combinations = len(merchants) * len(scenarios)
    completed = 0

    if not args.quiet:
        print(f"🔄 Generating {total_combinations} universes...")

    for merchant in merchants:
        for scenario in scenarios:
            try:
                if not args.quiet:
                    print(f"  📝 {merchant} + {scenario}")

                universe = generator.generate(merchant, scenario)
                generator.save_universe(universe)

                if args.validate:
                    loader = UniverseLoader()
                    loader.validate(universe)

                completed += 1

            except Exception as e:
                print(f"❌ Error with {merchant} + {scenario}: {e}")

    if not args.quiet:
        print(f"✅ Completed {completed}/{total_combinations} universes")


if __name__ == "__main__":
    main()
