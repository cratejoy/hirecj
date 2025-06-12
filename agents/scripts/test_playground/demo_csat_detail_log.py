"""Demo script showing usage of get_csat_detail_log tool

This demonstrates how the CSAT detail log function works with real data.
"""

from datetime import date, timedelta
from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics
from app.agents.database_tools import create_database_tools

def demo_analytics_function():
    """Direct usage of the analytics function"""
    print("=== Direct Function Usage ===\n")
    
    # Use yesterday's date as an example
    yesterday = date.today() - timedelta(days=1)
    
    # Call the function directly
    result = FreshdeskAnalytics.get_csat_detail_log(
        merchant_id=1,
        target_date=yesterday,
        rating_threshold=102  # Consider anything below "Very Happy" as negative
    )
    
    print(f"CSAT Detail Log for {yesterday}")
    print(f"Total Surveys: {result['total_count']}")
    print(f"Average Rating: {result['avg_rating']}")
    print(f"Below Threshold: {result['below_threshold_count']}")
    
    if result['surveys']:
        print("\nSurvey Details:")
        for survey in result['surveys'][:3]:  # Show first 3
            print(f"\n  Ticket #{survey['ticket_id']} - {survey['rating_label']} ({survey['rating']})")
            print(f"  Customer: {survey['customer_email']}")
            print(f"  Agent: {survey['agent']}")
            print(f"  Response Time: {survey['first_response_min']} min")
            print(f"  Tags: {', '.join(survey['tags']) if survey['tags'] else 'None'}")
            print(f"  Feedback: '{survey['feedback']}'")


def demo_crewai_tool():
    """Usage as a CrewAI tool"""
    print("\n\n=== CrewAI Tool Usage ===\n")
    
    # Create the tools
    tools = create_database_tools()
    
    # Find the get_csat_detail_log tool
    csat_tool = None
    for tool in tools:
        if tool.name == "get_csat_detail_log":
            csat_tool = tool
            break
    
    if csat_tool:
        # Call it with yesterday's date
        yesterday = date.today() - timedelta(days=1)
        result = csat_tool.func(date_str=yesterday.isoformat())
        print(result)
    else:
        print("CSAT detail log tool not found!")


def demo_specific_date():
    """Demo with a specific date and custom threshold"""
    print("\n\n=== Custom Date and Threshold ===\n")
    
    # Use a specific date
    target_date = date(2024, 1, 10)
    
    # Only consider "Extremely Happy" (103) as positive
    result = FreshdeskAnalytics.get_csat_detail_log(
        merchant_id=1,
        target_date=target_date,
        rating_threshold=103  # Only 103 is considered positive
    )
    
    print(f"CSAT Analysis for {target_date} (Only Perfect Scores)")
    print(f"Total Surveys: {result['total_count']}")
    
    if result['total_count'] > 0:
        perfect_scores = sum(1 for s in result['surveys'] if s['rating'] == 103)
        print(f"Perfect Scores: {perfect_scores} ({perfect_scores/result['total_count']*100:.1f}%)")
        print(f"Non-Perfect: {result['below_threshold_count']} ({result['below_threshold_count']/result['total_count']*100:.1f}%)")


def demo_workflow_context():
    """Show how it would be used in a workflow"""
    print("\n\n=== Workflow Context Usage ===\n")
    
    # This is how CJ would use it in the support_daily workflow
    print("Example prompt for CJ agent:")
    print("""
    "Please analyze yesterday's customer satisfaction ratings in detail. 
    I need to understand why customers were unhappy and identify any patterns."
    """)
    
    print("\nCJ would then call get_csat_detail_log and format the response:")
    
    # Simulate the response
    yesterday = date.today() - timedelta(days=1)
    tools = create_database_tools()
    
    # Find and call the tool
    for tool in tools:
        if tool.name == "get_csat_detail_log":
            print("\n[CJ's Response]:")
            print(tool.func(date_str=yesterday.isoformat()))
            break


if __name__ == "__main__":
    print("CSAT Detail Log Tool Demo")
    print("=" * 50)
    
    try:
        # Run the demos
        demo_analytics_function()
        demo_crewai_tool()
        demo_specific_date()
        demo_workflow_context()
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nNote: This demo requires a database connection with data.")
        print("Make sure your .env file is configured and the database is populated.")