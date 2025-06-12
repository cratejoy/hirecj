"""Simple example of using the CSAT detail log function"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch

# Import the analytics library
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics

def create_mock_ticket(**kwargs):
    """Helper to create a mock ticket"""
    defaults = {
        'merchant_id': 1,
        'freshdesk_ticket_id': '12345',
        'created_at': datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
        'resolved_at': None,
        'first_responded_at': None,
        'has_rating': True,
        'rating_score': 103,
        'rating_created_at': datetime(2024, 1, 10, 15, 0, 0, tzinfo=timezone.utc),
        'rating_feedback': None,
        'requester_email': 'customer@example.com',
        'responder_email': 'agent@example.com',
        'tags': ['support', 'general'],
    }
    defaults.update(kwargs)
    
    mock_ticket = Mock()
    for key, value in defaults.items():
        setattr(mock_ticket, key, value)
    return mock_ticket

@patch('app.lib.freshdesk_analytics_lib.get_db_session')
def demo_with_mock_data(mock_get_db_session):
    """Demo the CSAT detail log with mock data"""
    
    # Setup mock session
    mock_session = MagicMock()
    mock_get_db_session.return_value.__enter__.return_value = mock_session
    
    # Create mock tickets with various ratings
    target_date = date(2024, 1, 10)
    base_time = datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
    rating_time = datetime(2024, 1, 10, 15, 0, 0, tzinfo=timezone.utc)
    
    mock_tickets = [
        # Extremely Happy customer with great feedback
        create_mock_ticket(
            freshdesk_ticket_id='101',
            rating_score=103,
            rating_feedback='Outstanding service! Agent went above and beyond!',
            created_at=base_time,
            first_responded_at=base_time + timedelta(minutes=3),
            resolved_at=base_time + timedelta(minutes=15),
            rating_created_at=rating_time,
            requester_email='happy.customer@example.com',
            tags=['shipping', 'quick-resolution']
        ),
        
        # Very Happy customer
        create_mock_ticket(
            freshdesk_ticket_id='102',
            rating_score=102,
            rating_feedback='Good service, thanks!',
            created_at=base_time,
            first_responded_at=base_time + timedelta(minutes=10),
            resolved_at=base_time + timedelta(minutes=45),
            rating_created_at=rating_time,
            requester_email='satisfied.customer@example.com',
            tags=['product-question']
        ),
        
        # Happy customer (below default threshold)
        create_mock_ticket(
            freshdesk_ticket_id='103',
            rating_score=101,
            rating_feedback='It was okay, but took a while',
            created_at=base_time,
            first_responded_at=base_time + timedelta(minutes=60),
            resolved_at=base_time + timedelta(minutes=180),
            rating_created_at=rating_time,
            requester_email='neutral.customer@example.com',
            tags=['refund', 'slow-response']
        ),
        
        # Very Unhappy customer
        create_mock_ticket(
            freshdesk_ticket_id='104',
            rating_score=-101,
            rating_feedback='Terrible experience! Agent was rude and unhelpful.',
            created_at=base_time,
            first_responded_at=base_time + timedelta(minutes=120),
            resolved_at=None,  # Still unresolved
            rating_created_at=rating_time,
            requester_email='angry.customer@example.com',
            responder_email='problematic.agent@example.com',
            tags=['complaint', 'escalation']
        ),
        
        # Extremely Unhappy customer
        create_mock_ticket(
            freshdesk_ticket_id='105',
            rating_score=-103,
            rating_feedback='Worst support ever! Still waiting for my refund after 2 weeks!',
            created_at=base_time - timedelta(days=14),
            first_responded_at=base_time - timedelta(days=14) + timedelta(hours=3),
            resolved_at=None,
            rating_created_at=rating_time,
            requester_email='furious.customer@example.com',
            tags=['refund', 'unresolved', 'escalation']
        ),
    ]
    
    # Configure mock query
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = mock_tickets
    
    # Mock conversation data - need enough for both test runs
    conversation_data = [
        # First test run
        ([{"id": 1}, {"id": 2}],),  # 2 conversations
        ([{"id": 3}, {"id": 4}, {"id": 5}],),  # 3 conversations
        ([{"id": 6}, {"id": 7}, {"id": 8}, {"id": 9}],),  # 4 conversations
        ([{"id": 10}, {"id": 11}, {"id": 12}, {"id": 13}, {"id": 14}],),  # 5 conversations
        ([{"id": 15}] * 12,),  # 12 conversations (lots of back and forth)
        # Second test run (same data)
        ([{"id": 1}, {"id": 2}],),  # 2 conversations
        ([{"id": 3}, {"id": 4}, {"id": 5}],),  # 3 conversations
        ([{"id": 6}, {"id": 7}, {"id": 8}, {"id": 9}],),  # 4 conversations
        ([{"id": 10}, {"id": 11}, {"id": 12}, {"id": 13}, {"id": 14}],),  # 5 conversations
        ([{"id": 15}] * 12,),  # 12 conversations (lots of back and forth)
    ]
    mock_query.first.side_effect = conversation_data
    
    # Call the function
    print("🔍 CSAT Detail Log Demo")
    print("=" * 60)
    
    # Test 1: Default threshold (102 - Very Happy)
    print("\n📊 Test 1: Default Threshold (ratings below 'Very Happy' are negative)")
    result = FreshdeskAnalytics.get_csat_detail_log(
        merchant_id=1,
        target_date=target_date
    )
    
    print(f"\nDate: {target_date}")
    print(f"Total Surveys: {result['total_count']}")
    print(f"Average Rating: {result['avg_rating']}")
    print(f"Below Threshold (<102): {result['below_threshold_count']} ({result['below_threshold_count']/result['total_count']*100:.1f}%)")
    
    print("\n📉 Negative Ratings (sorted worst first):")
    for survey in result['surveys']:
        if survey['rating'] < 102:
            print(f"\n  Ticket #{survey['ticket_id']} - {survey['rating_label']} ({survey['rating']})")
            print(f"  Customer: {survey['customer_email']}")
            print(f"  Agent: {survey['agent']}")
            print(f"  Response Time: {survey['first_response_min']} min")
            print(f"  Resolution Time: {survey['resolution_min'] or 'Not resolved'} min")
            print(f"  Conversations: {survey['conversation_count']}")
            print(f"  Tags: {', '.join(survey['tags'])}")
            print(f"  Feedback: \"{survey['feedback']}\"")
    
    print("\n📈 Positive Ratings:")
    positive_count = sum(1 for s in result['surveys'] if s['rating'] >= 102)
    print(f"  Total: {positive_count} ({positive_count/result['total_count']*100:.1f}%)")
    for survey in result['surveys']:
        if survey['rating'] >= 102:
            print(f"  - Ticket #{survey['ticket_id']}: {survey['rating_label']} - \"{survey['feedback']}\"")
    
    # Test 2: Strict threshold (only 103 is good)
    print("\n\n📊 Test 2: Strict Threshold (only 'Extremely Happy' is positive)")
    result2 = FreshdeskAnalytics.get_csat_detail_log(
        merchant_id=1,
        target_date=target_date,
        rating_threshold=103
    )
    
    print(f"\nWith strict threshold:")
    print(f"Below Threshold (<103): {result2['below_threshold_count']} ({result2['below_threshold_count']/result2['total_count']*100:.1f}%)")
    print(f"Perfect Scores (103): {result2['total_count'] - result2['below_threshold_count']} ({(result2['total_count'] - result2['below_threshold_count'])/result2['total_count']*100:.1f}%)")


if __name__ == "__main__":
    try:
        demo_with_mock_data()
        
        print("\n\n💡 Key Insights from this Analysis:")
        print("- Response time correlates with satisfaction (faster = happier)")
        print("- Unresolved tickets always have negative ratings")
        print("- Long conversation counts indicate complex issues")
        print("- Tags help identify problem areas (e.g., 'refund', 'escalation')")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()