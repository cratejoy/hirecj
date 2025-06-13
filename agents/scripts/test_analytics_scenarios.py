#!/usr/bin/env python3
"""
Test script to demonstrate analytics tool usage with real examples.
This script simulates various user queries and shows the corresponding tool calls.
"""

import sys
import os
from datetime import date, timedelta

# Example scenarios that demonstrate each analytics capability
SCENARIOS = [
    {
        "name": "Daily Morning Briefing",
        "query": "Give me yesterday's support metrics",
        "tools": ["get_daily_snapshot"],
        "description": "Manager checking daily support health"
    },
    {
        "name": "CSAT Deep Dive",
        "query": "Show me all bad CSAT ratings from yesterday with full conversations",
        "tools": ["get_csat_detail_log"],
        "params": {"include_conversations": True, "rating_threshold": 102},
        "description": "Investigating customer dissatisfaction"
    },
    {
        "name": "Backlog Health Check",
        "query": "How does our ticket backlog look? Show me the oldest tickets",
        "tools": ["get_open_ticket_distribution"],
        "description": "Monitoring aging tickets and backlog"
    },
    {
        "name": "Performance Analysis",
        "query": "Analyze our response times for the past week",
        "tools": ["get_response_time_metrics"],
        "params": {"days": 7},
        "description": "Team performance review"
    },
    {
        "name": "Volume Trend Analysis",
        "query": "Have we had any ticket spikes in the past 60 days?",
        "tools": ["get_volume_trends"],
        "params": {"days": 60},
        "description": "Identifying unusual patterns"
    },
    {
        "name": "SLA Compliance Check",
        "query": "Show me all tickets breaching our 1-hour response SLA",
        "tools": ["get_sla_exceptions"],
        "params": {"first_response_min": 60, "resolution_min": 1440},
        "description": "Ensuring service level compliance"
    },
    {
        "name": "Spike Investigation",
        "query": "What caused the spike in tickets on May 26th?",
        "tools": ["get_root_cause_analysis"],
        "params": {"date_str": "2024-05-26"},
        "description": "Understanding spike drivers"
    },
    {
        "name": "Comprehensive Health Check",
        "query": "Give me a complete support health check for this week",
        "tools": ["get_daily_snapshot", "get_open_ticket_distribution", 
                 "get_response_time_metrics", "get_sla_exceptions"],
        "description": "Weekly support review meeting"
    }
]

def print_scenario(scenario):
    """Print a formatted scenario example."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"{'='*80}")
    print(f"User Query: \"{scenario['query']}\"")
    print(f"Description: {scenario['description']}")
    print(f"\nTools Called: {', '.join(scenario['tools'])}")
    
    if 'params' in scenario:
        print(f"Parameters: {scenario['params']}")
    
    print(f"\nThis scenario demonstrates:")
    print(f"- When to use: {scenario['description']}")
    print(f"- What it provides: Real-time analytics from the database")
    print(f"- Value: Automated insights without manual analysis")

def generate_tool_call_examples():
    """Generate example tool calls for documentation."""
    print("\n" + "="*80)
    print("ANALYTICS TOOL CALL EXAMPLES")
    print("="*80)
    
    # Example 1: Daily Snapshot
    print("\n1. Daily Snapshot Tool Call:")
    print("```python")
    print("# User asks: 'What were our support metrics yesterday?'")
    print("result = get_daily_snapshot(date_str='2024-01-10')")
    print("# Returns comprehensive daily metrics including:")
    print("# - Volume metrics (new, closed, open tickets)")
    print("# - Response times (median first response, resolution)")
    print("# - CSAT scores and feedback")
    print("# - SLA breach count")
    print("```")
    
    # Example 2: CSAT with Conversations
    print("\n2. CSAT Analysis with Conversations:")
    print("```python")
    print("# User asks: 'Show me what went wrong with unhappy customers'")
    print("result = get_csat_detail_log(")
    print("    date_str='2024-01-10',")
    print("    rating_threshold=102,")
    print("    include_conversations=True  # Key parameter!")
    print(")")
    print("# Returns full conversation history for bad ratings")
    print("# Helps identify exactly where interactions failed")
    print("```")
    
    # Example 3: SLA Monitoring
    print("\n3. Custom SLA Monitoring:")
    print("```python")
    print("# User asks: 'Which tickets exceed 2-hour response time?'")
    print("result = get_sla_exceptions(")
    print("    first_response_min=120,  # 2 hours")
    print("    resolution_min=2880,     # 48 hours")
    print("    include_pending=True")
    print(")")
    print("# Returns tickets breaching custom SLA thresholds")
    print("# Shows patterns and common factors in breaches")
    print("```")

def main():
    """Run the analytics scenario demonstrations."""
    print("SUPPORT ANALYTICS AGENT - CAPABILITY DEMONSTRATION")
    print("="*80)
    print("\nThis script demonstrates the analytics capabilities available")
    print("in the support_daily workflow. Each scenario shows a real-world")
    print("use case and the corresponding analytics tools.\n")
    
    # Print all scenarios
    for scenario in SCENARIOS:
        print_scenario(scenario)
    
    # Generate tool call examples
    generate_tool_call_examples()
    
    # Print integration notes
    print("\n" + "="*80)
    print("INTEGRATION WITH SUPPORT_DAILY WORKFLOW")
    print("="*80)
    print("\nThe support_daily workflow automatically uses these tools to:")
    print("- Generate daily support briefings")
    print("- Monitor SLA compliance")
    print("- Detect and investigate spikes")
    print("- Analyze customer satisfaction trends")
    print("- Prioritize urgent issues")
    print("\nAll analytics are merchant-isolated and real-time.")

if __name__ == "__main__":
    main()