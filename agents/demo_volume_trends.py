#!/usr/bin/env python3
"""Demo of the volume trends analysis tool"""

import sys
import os

# Add the agents directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Import and create the tools
    from app.agents.database_tools import create_database_tools
    
    print("📊 Volume Trends Analysis Demo")
    print("=" * 60)
    
    # Create all tools
    tools = create_database_tools()
    
    # Find the volume trends tool
    volume_trends_tool = None
    for tool in tools:
        if tool.name == "get_volume_trends":
            volume_trends_tool = tool
            break
    
    if volume_trends_tool:
        # Call the tool with default 60 days
        print("\n1. Analyzing last 60 days (default):")
        print("-" * 60)
        result = volume_trends_tool.func()
        print(result)
        
        # Call with shorter period to see more detail
        print("\n\n2. Analyzing last 14 days (recent detail):")
        print("-" * 60)
        result_14d = volume_trends_tool.func(days=14)
        print(result_14d)
    else:
        print("❌ Volume trends tool not found!")

except ImportError as e:
    # If CrewAI import fails, call the function directly
    print("CrewAI import failed, calling analytics function directly...")
    print("=" * 60)
    
    from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics
    import json
    
    # Get raw data for 30 days
    print("\n📊 Raw Volume Trends Data (30 days):")
    raw_result = FreshdeskAnalytics.get_volume_trends(merchant_id=1, days=30)
    
    # Show summary
    print("\nSummary:")
    print(json.dumps(raw_result['summary'], indent=2))
    
    # Show last 10 days of daily volumes
    print("\nLast 10 days:")
    for day in raw_result['daily_volumes'][-10:]:
        spike = " 🚨 SPIKE!" if day['is_spike'] else ""
        print(f"  {day['date']}: {day['new_tickets']} tickets (deviation: {day['deviation']:.1f}σ){spike}")
    
    # Show rolling averages
    print("\nLast 7 days rolling average:")
    for avg in raw_result['rolling_7d_avg'][-7:]:
        print(f"  {avg['date']}: {avg['avg']:.1f} tickets/day average")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()