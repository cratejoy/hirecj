#!/usr/bin/env python3
"""Run the CSAT detail log tool and show actual output"""

import sys
import os
from datetime import date, timedelta

# Add the agents directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.agents.database_tools import create_database_tools
    from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics
    
    print("🎯 CSAT Detail Log Tool Demo")
    print("=" * 60)
    
    # Create the database tools
    tools = create_database_tools()
    
    # Find the get_csat_detail_log tool
    csat_tool = None
    for tool in tools:
        if tool.name == "get_csat_detail_log":
            csat_tool = tool
            break
    
    if not csat_tool:
        print("❌ Could not find get_csat_detail_log tool!")
        sys.exit(1)
    
    print("✅ Found get_csat_detail_log tool")
    print(f"📝 Description: {csat_tool.description}\n")
    
    # Test 1: Get yesterday's CSAT data
    print("📊 Test 1: Yesterday's CSAT data (default)")
    print("-" * 50)
    try:
        result = csat_tool.func()
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60 + "\n")
    
    # Test 2: Get today's data (might be empty)
    print("📊 Test 2: Today's CSAT data")
    print("-" * 50)
    try:
        today = date.today().isoformat()
        result = csat_tool.func(date_str=today)
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60 + "\n")
    
    # Test 3: Get data with strict threshold
    print("📊 Test 3: Yesterday with strict threshold (only perfect scores)")
    print("-" * 50)
    try:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        result = csat_tool.func({
            "date_str": yesterday,
            "rating_threshold": 103  # Only "Extremely Happy" is positive
        })
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60 + "\n")
    
    # Test 4: Get raw data to show structure
    print("📊 Test 4: Raw data structure (using analytics library directly)")
    print("-" * 50)
    try:
        yesterday = date.today() - timedelta(days=1)
        raw_data = FreshdeskAnalytics.get_csat_detail_log(
            merchant_id=1,
            target_date=yesterday,
            rating_threshold=102
        )
        
        print(f"Total surveys: {raw_data['total_count']}")
        print(f"Below threshold: {raw_data['below_threshold_count']}")
        print(f"Average rating: {raw_data['avg_rating']}")
        
        if raw_data['surveys']:
            print(f"\nFirst survey details:")
            survey = raw_data['surveys'][0]
            for key, value in survey.items():
                print(f"  {key}: {value}")
        else:
            print("\nNo surveys found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you're running this from the agents directory and have all dependencies installed.")
    print("Try: cd /Users/blake/workspace/hirecj/agents && python run_csat_tool_demo.py")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()