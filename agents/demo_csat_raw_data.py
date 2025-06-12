#!/usr/bin/env python3
"""
Demonstration of raw CSAT data structure from the get_csat_detail_log tool.

This script shows the actual data structure returned by the tool,
which is useful for understanding how to parse and use the results.
"""

import sys
import os
import json
from datetime import date, timedelta

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics
from app.utils.supabase_util import get_db_session


def demo_raw_csat_data():
    """Show the raw data structure from get_csat_detail_log."""
    
    print("🔍 Raw CSAT Detail Log Data Structure Demo\n")
    
    # Set parameters
    merchant_id = 1
    target_date = date.today() - timedelta(days=1)  # Yesterday
    rating_threshold = 102
    
    print(f"Parameters:")
    print(f"  - Merchant ID: {merchant_id}")
    print(f"  - Target Date: {target_date}")
    print(f"  - Rating Threshold: {rating_threshold}")
    print(f"  - Ratings below {rating_threshold} are considered negative\n")
    
    try:
        # Get the raw data
        csat_data = FreshdeskAnalytics.get_csat_detail_log(
            merchant_id=merchant_id,
            target_date=target_date,
            rating_threshold=rating_threshold
        )
        
        # Pretty print the entire structure
        print("📊 Raw Data Structure:")
        print(json.dumps(csat_data, indent=2, default=str))
        
        print("\n" + "="*80 + "\n")
        
        # Explain the structure
        print("📝 Data Structure Explanation:\n")
        
        print("1. Top-level fields:")
        print(f"   - total_count: {csat_data['total_count']} (total surveys on this date)")
        print(f"   - below_threshold_count: {csat_data['below_threshold_count']} (negative ratings)")
        print(f"   - avg_rating: {csat_data['avg_rating']} (average rating score)")
        print(f"   - surveys: List of {len(csat_data['surveys'])} individual survey objects\n")
        
        print("2. Each survey object contains:")
        if csat_data['surveys']:
            survey_example = csat_data['surveys'][0]
            for key, value in survey_example.items():
                value_type = type(value).__name__
                print(f"   - {key}: {value_type}")
        
        print("\n3. Rating score mapping:")
        print("   - 103: Extremely Happy 😊😊😊")
        print("   - 102: Very Happy 😊😊")
        print("   - 101: Happy 😊")
        print("   - 100: Neutral 😐")
        print("   - -100: Unhappy 😞")
        print("   - -101: Very Unhappy 😞😞")
        print("   - -102: Extremely Unhappy 😞😞😞")
        
        print("\n" + "="*80 + "\n")
        
        # Show how to work with the data
        print("💡 Example: Processing the data\n")
        
        if csat_data['surveys']:
            # Group by rating
            ratings_by_score = {}
            for survey in csat_data['surveys']:
                score = survey['rating']
                if score not in ratings_by_score:
                    ratings_by_score[score] = []
                ratings_by_score[score].append(survey)
            
            print("Surveys grouped by rating:")
            for score in sorted(ratings_by_score.keys()):
                surveys = ratings_by_score[score]
                print(f"\n{surveys[0]['rating_label']} ({score}): {len(surveys)} surveys")
                
                # Show first survey in each group
                first_survey = surveys[0]
                print(f"  Example ticket: #{first_survey['ticket_id']}")
                print(f"  Customer: {first_survey['customer_email']}")
                print(f"  Agent: {first_survey['agent']}")
                print(f"  Response time: {first_survey['first_response_min']} min")
                if first_survey['feedback']:
                    print(f"  Feedback: \"{first_survey['feedback'][:100]}...\"")
        
        print("\n" + "="*80 + "\n")
        
        # Show filtering examples
        print("🔍 Filtering Examples:\n")
        
        # Find surveys with slow response times
        slow_responses = [s for s in csat_data['surveys'] 
                         if s['first_response_min'] and s['first_response_min'] > 60]
        print(f"Surveys with response time > 60 min: {len(slow_responses)}")
        
        # Find surveys with feedback
        with_feedback = [s for s in csat_data['surveys'] if s['feedback']]
        print(f"Surveys with customer feedback: {len(with_feedback)}")
        
        # Find unassigned tickets
        unassigned = [s for s in csat_data['surveys'] if s['agent'] == 'unassigned']
        print(f"Surveys from unassigned tickets: {len(unassigned)}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_raw_csat_data()