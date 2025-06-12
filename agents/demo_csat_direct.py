#!/usr/bin/env python3
"""Direct demo of CSAT detail log functionality"""

import sys
import os
from datetime import date, timedelta

# Add the agents directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics
    
    print("🎯 CSAT Detail Log Direct Demo")
    print("=" * 60)
    
    # Test different scenarios
    scenarios = [
        {
            "name": "Yesterday's CSAT data (default threshold)",
            "date": date.today() - timedelta(days=1),
            "threshold": 102
        },
        {
            "name": "Today's CSAT data",
            "date": date.today(),
            "threshold": 102
        },
        {
            "name": "Strict threshold (only perfect scores)",
            "date": date.today() - timedelta(days=1),
            "threshold": 103
        },
        {
            "name": "Last week's data",
            "date": date.today() - timedelta(days=7),
            "threshold": 102
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📊 {scenario['name']}")
        print(f"   Date: {scenario['date']}")
        print(f"   Threshold: {scenario['threshold']} (ratings below this are negative)")
        print("-" * 50)
        
        try:
            result = FreshdeskAnalytics.get_csat_detail_log(
                merchant_id=1,
                target_date=scenario['date'],
                rating_threshold=scenario['threshold']
            )
            
            # Display summary
            print(f"Total surveys: {result['total_count']}")
            print(f"Average rating: {result['avg_rating']}")
            print(f"Below threshold: {result['below_threshold_count']}", end="")
            if result['total_count'] > 0:
                pct = result['below_threshold_count'] / result['total_count'] * 100
                print(f" ({pct:.1f}%)")
            else:
                print()
            
            # Display surveys
            if result['surveys']:
                print(f"\nSurvey details (showing first 3):")
                for i, survey in enumerate(result['surveys'][:3]):
                    print(f"\n  Survey #{i+1}:")
                    print(f"    Ticket ID: {survey['ticket_id']}")
                    print(f"    Rating: {survey['rating_label']} ({survey['rating']})")
                    print(f"    Customer: {survey['customer_email']}")
                    print(f"    Agent: {survey['agent']}")
                    print(f"    Response time: {survey['first_response_min']} min" if survey['first_response_min'] else "    Response time: N/A")
                    print(f"    Resolution time: {survey['resolution_min']} min" if survey['resolution_min'] else "    Resolution time: N/A")
                    print(f"    Conversations: {survey['conversation_count']}")
                    print(f"    Tags: {', '.join(survey['tags']) if survey['tags'] else 'None'}")
                    print(f"    Feedback: \"{survey['feedback']}\"" if survey['feedback'] else "    Feedback: None")
                
                if len(result['surveys']) > 3:
                    print(f"\n  ... and {len(result['surveys']) - 3} more surveys")
            else:
                print("\n  No surveys found for this date")
                
        except Exception as e:
            print(f"Error: {e}")
            # Only print traceback for unexpected errors
            if "No module named" not in str(e) and "database" not in str(e).lower():
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("\n📝 Note: This demo requires a configured database connection.")
    print("If you see database errors, make sure your .env file is properly configured.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you have all required dependencies installed:")
    print("  pip install -r requirements.txt")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()