#!/usr/bin/env python3
"""Demo of the clean data architecture with two layers."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.universe_data_agent import UniverseDataAgent  # noqa: E402


def demonstrate_data_architecture():
    """Show how the data architecture works."""

    print("=== DATA ARCHITECTURE DEMO ===\n")

    # 1. Create UniverseDataAgent (uses pre-generated universe data)
    print(
        "1. Creating UniverseDataAgent for marcus_thompson in churn_spike scenario..."
    )
    data_agent = UniverseDataAgent(
        merchant_name="marcus_thompson", scenario_name="churn_spike"
    )

    print(f"   Base metrics generated: {data_agent.base_metrics}\n")

    # 2. Get daily briefing view
    print("2. Getting daily briefing view...")
    daily_view = data_agent.get_daily_briefing()
    print(
        f"   MRR: ${daily_view.mrr.current_value:,.0f} ({daily_view.mrr.formatted_change})"
    )
    print(f"   Churn: {daily_view.churn_rate.current_value:.1%}")
    print(f"   Urgent issues: {daily_view.urgent_issues}\n")

    # 3. Show formatted output
    print("3. Formatted for CJ's daily flash:")
    print(daily_view.to_flash_report())
    print()

    # 4. Get crisis metrics
    print("4. Getting crisis analysis...")
    crisis_view = data_agent.get_crisis_metrics()
    print(f"   Crisis type: {crisis_view.crisis_type} ({crisis_view.severity})")
    print(f"   MRR at risk: ${crisis_view.mrr_at_risk:,.0f}")
    print(f"   Top reason: {list(crisis_view.cancellation_reasons.keys())[0]}")
    print()

    # 5. Show how consistent data is maintained
    print("5. Data consistency demonstration:")
    print("   Creating another UniverseDataAgent with same inputs...")
    data_agent2 = UniverseDataAgent("marcus_thompson", "churn_spike")
    daily_view2 = data_agent2.get_daily_briefing()
    print(
        f"   MRR matches: {daily_view.mrr.current_value == daily_view2.mrr.current_value}"
    )
    print()

    # 6. Show different scenario
    print("6. Different scenario (growth_stall):")
    stall_agent = UniverseDataAgent("sarah_chen", "growth_stall")
    stall_view = stall_agent.get_daily_briefing()
    print(
        f"   MRR: ${stall_view.mrr.current_value:,.0f} ({stall_view.mrr.formatted_change})"
    )
    print("   Growth is indeed stalled!")
    print()

    # 7. Universe system benefits
    print("7. Universe System Benefits:")
    print("   ✅ Immutable data prevents CJ from hallucinating fake issues")
    print("   ✅ Pre-generated universe ensures consistent, realistic data")
    print("   ✅ Same interface works with existing CJ tools and workflows")
    print("   ✅ Solves the 'unicorn problem' - CJ can't generate fake support tickets")
    print("   ✅ Production migration: replace universe files with real data feeds")


if __name__ == "__main__":
    demonstrate_data_architecture()
