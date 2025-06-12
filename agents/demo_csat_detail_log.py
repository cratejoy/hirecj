#!/usr/bin/env python3
"""
Demonstration script for the CSAT Detail Log tool.

This script shows how to use the get_csat_detail_log tool from the database_tools module
to retrieve detailed customer satisfaction survey data.
"""

import sys
import os
from datetime import date, datetime, timedelta
from pprint import pprint

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Import necessary modules
from app.agents.database_tools import create_database_tools
from app.logging_config import setup_logging

# Setup logging
setup_logging()


def print_separator():
    """Print a visual separator."""
    print("\n" + "="*80 + "\n")


def demonstrate_csat_detail_log():
    """Demonstrate various uses of the get_csat_detail_log tool."""
    
    print("🚀 CSAT Detail Log Tool Demonstration")
    print_separator()
    
    # Create the database tools
    print("📦 Creating database tools...")
    tools = create_database_tools(merchant_name="Demo Merchant")
    
    # Find the get_csat_detail_log tool
    csat_detail_tool = None
    for tool in tools:
        if tool.name == "get_csat_detail_log":
            csat_detail_tool = tool
            break
    
    if not csat_detail_tool:
        print("❌ Error: Could not find get_csat_detail_log tool!")
        return
    
    print(f"✅ Found tool: {csat_detail_tool.name}")
    print(f"📝 Description: {csat_detail_tool.description}")
    print_separator()
    
    # Example 1: Get CSAT details for yesterday (default behavior)
    print("📊 Example 1: Get CSAT details for yesterday (default)")
    print("-" * 40)
    try:
        result = csat_detail_tool.run()
        print(result)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    print_separator()
    
    # Example 2: Get CSAT details for a specific date
    print("📊 Example 2: Get CSAT details for a specific date")
    print("-" * 40)
    specific_date = (date.today() - timedelta(days=7)).isoformat()
    print(f"📅 Querying for date: {specific_date}")
    try:
        result = csat_detail_tool.run({"date_str": specific_date})
        print(result)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    print_separator()
    
    # Example 3: Get CSAT details with custom rating threshold
    print("📊 Example 3: Get CSAT details with custom threshold")
    print("-" * 40)
    print("🎯 Using threshold of 103 (only Extremely Happy is positive)")
    try:
        result = csat_detail_tool.run({
            "date_str": specific_date,
            "rating_threshold": 103
        })
        print(result)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    print_separator()
    
    # Example 4: Get today's CSAT details (might be empty)
    print("📊 Example 4: Get today's CSAT details")
    print("-" * 40)
    today = date.today().isoformat()
    print(f"📅 Querying for today: {today}")
    try:
        result = csat_detail_tool.run({"date_str": today})
        print(result)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    print_separator()
    
    # Example 5: Demonstrate error handling with invalid date
    print("📊 Example 5: Error handling with invalid date")
    print("-" * 40)
    print("🔧 Testing with invalid date format...")
    try:
        result = csat_detail_tool.run({"date_str": "not-a-date"})
        print(result)
    except Exception as e:
        print(f"❌ Expected error: {str(e)}")
    print_separator()
    
    # Show raw function usage (without CrewAI wrapper)
    print("🔧 Bonus: Direct library usage example")
    print("-" * 40)
    print("You can also use the analytics library directly:")
    print("""
from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics
from datetime import date

# Get CSAT detail log for a specific merchant and date
merchant_id = 1
target_date = date.today() - timedelta(days=1)
rating_threshold = 102  # Default threshold

csat_data = FreshdeskAnalytics.get_csat_detail_log(
    merchant_id=merchant_id,
    target_date=target_date,
    rating_threshold=rating_threshold
)

# The result contains:
# - surveys: List of individual survey details
# - total_count: Total surveys on that date
# - below_threshold_count: Count of negative ratings
# - avg_rating: Average rating score
""")
    
    print_separator()
    print("✅ Demonstration complete!")


def main():
    """Main entry point."""
    try:
        demonstrate_csat_detail_log()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demonstration interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()