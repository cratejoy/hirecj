"""
Test playground for freshdesk_insight_lib.py
This file contains stub functions to test each method in the FreshdeskInsights class.
"""

# Standard library imports
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# Database imports (adjust path as needed for your setup)
from sqlalchemy.orm import Session
from app.utils.supabase_util import get_db_session

# Import the insights library
from app.lib.freshdesk_insight_lib import FreshdeskInsights, Rating


def test_get_support_dashboard(session: Session):
    """
    Test FreshdeskInsights.get_support_dashboard()
    
    Call: FreshdeskInsights.get_support_dashboard(session, merchant_id=1)
    Expected Response: Dict with dashboard metrics
    {
        "merchant_id": 1,
        "total_tickets": 150,
        "status_counts": {
            "open": 12,
            "in_progress": 8,
            "resolved": 120,
            "closed": 10,
            "pending": 0
        }
    }
    """
    result = FreshdeskInsights.get_support_dashboard(session, merchant_id=1)
    print(f"Dashboard data: {result}")


def test_calculate_csat(session: Session):
    """
    Test FreshdeskInsights.calculate_csat()
    
    Call options:
    - FreshdeskInsights.calculate_csat(session, days=30)
    - FreshdeskInsights.calculate_csat(session, start_date=datetime(2024,1,1), end_date=datetime(2024,1,31))
    
    Expected Response: Dict with CSAT metrics
    {
        "csat_percentage": 85.5,
        "total_unique_ratings": 100,
        "satisfied_ratings": 85,  # Only rating 103 counts as satisfied
        "unsatisfied_ratings": 15,  # All ratings < 102
        "time_range": "last 30 days",
        "merchant_info": "Merchant ID: 1",
        "has_data": True
    }
    """
    result = FreshdeskInsights.calculate_csat(session, days=30)
    print(f"CSAT: {result['csat_percentage']}% ({result['satisfied_ratings']}/{result['total_unique_ratings']})")


def test_get_ticket_by_id(session: Session):
    """
    Test FreshdeskInsights.get_ticket_by_id()
    
    Call: FreshdeskInsights.get_ticket_by_id(session, "12345", merchant_id=1)
    Expected Response: Dict with full ticket details including conversations and ratings
    {
        "ticket_id": "12345",
        "merchant_id": 1,
        "created_at": "2024-01-15T10:30:00+00:00",
        "updated_at": "2024-01-15T14:20:00+00:00",
        "data": {...},
        "conversations": [
            {
                "conversation_id": "conv_123",
                "created_at": "2024-01-15T10:30:00+00:00",
                "from_email": "customer@example.com",
                "body_text": "I have an issue...",
                "data": {...}
            }
        ],
        "ratings": [
            {
                "rating_id": "rating_456",
                "created_at": "2024-01-15T16:00:00+00:00",
                "ratings": {"default_question": 103},
                "data": {...}
            }
        ]
    }
    """
    # result = FreshdeskInsights.get_ticket_by_id(session, "12345", merchant_id=1)
    # print(f"Ticket details: {result['ticket_id'] if result else 'Not found'}")
    print("Stub: get_ticket_by_id - Returns full ticket with conversations and ratings")


def test_get_tickets_by_email(session: Session):
    """
    Test FreshdeskInsights.get_tickets_by_email()
    
    Call: FreshdeskInsights.get_tickets_by_email(session, "customer@example.com", merchant_id=1)
    Expected Response: List of tickets for the customer
    [
        {
            "ticket_id": "12345",
            "subject": "Payment issue",
            "status": "closed",
            "priority": "normal",
            "created_at": "2024-01-15T10:30:00+00:00",
            "requester": {...},
            "data": {...}
        }
    ]
    """
    # result = FreshdeskInsights.get_tickets_by_email(session, "customer@example.com", merchant_id=1)
    # print(f"Customer tickets: {len(result)} found")
    print("Stub: get_tickets_by_email - Returns all tickets for a customer email")


def test_get_tickets_by_rating(session: Session):
    """
    Test FreshdeskInsights.get_tickets_by_rating()
    
    Call options:
    - FreshdeskInsights.get_tickets_by_rating(session, rating_value=103, days=30, limit=10)
    - FreshdeskInsights.get_tickets_by_rating(session, rating_type="extremely_happy", days=30)
    - FreshdeskInsights.get_tickets_by_rating(session, rating_type="satisfied")  # CSAT satisfied
    - FreshdeskInsights.get_tickets_by_rating(session, rating_type="unsatisfied")  # CSAT unsatisfied
    
    Expected Response: List of tickets with specified rating
    [
        {
            "ticket_id": "12345",
            "subject": "Great service!",
            "status": "closed",
            "priority": "normal",
            "created_at": "2024-01-15T10:30:00+00:00",
            "rating_created_at": "2024-01-15T16:00:00+00:00",
            "rating_value": 103,
            "rating_name": "extremely_happy",
            "requester": {...},
            "feedback": "Excellent support!",
            "data": {...}
        }
    ]
    """
    # result = FreshdeskInsights.get_tickets_by_rating(session, rating_value=Rating.EXTREMELY_HAPPY, days=30, limit=10)
    # print(f"Happy tickets: {len(result)} found")
    print("Stub: get_tickets_by_rating - Returns tickets filtered by rating value/type")


def test_get_recent_bad_csat_tickets(session: Session):
    """
    Test FreshdeskInsights.get_recent_bad_csat_tickets()
    
    Call: FreshdeskInsights.get_recent_bad_csat_tickets(session, limit=10, merchant_id=1)
    Expected Response: List of recent tickets with bad ratings (<102) including full context
    [
        {
            "ticket_id": "12345",
            "merchant_id": 1,
            "created_at": "2024-01-15T10:30:00+00:00",
            "data": {...},
            "conversations": [...],
            "ratings": [...],
            "bad_rating_date": "2024-01-15T16:00:00+00:00",
            "rating_comment": "Service was slow"
        }
    ]
    """
    result = FreshdeskInsights.get_recent_bad_csat_tickets(session, limit=5, merchant_id=1)
    print(f"Recent bad CSAT tickets: {len(result)} found")
    print("Stub: get_recent_bad_csat_tickets - Returns recent tickets with bad ratings + full context")


def test_get_rating_statistics(session: Session):
    """
    Test FreshdeskInsights.get_rating_statistics()
    
    Call options:
    - FreshdeskInsights.get_rating_statistics(session, days=30)
    - FreshdeskInsights.get_rating_statistics(session, start_date=datetime(2024,1,1), end_date=datetime(2024,1,31))
    
    Expected Response: Dict with rating statistics
    {
        "total_ratings": 100,
        "by_rating": {
            "extremely_happy": {"value": 103, "count": 45, "percentage": 45.0},
            "very_happy": {"value": 102, "count": 20, "percentage": 20.0},
            "happy": {"value": 101, "count": 15, "percentage": 15.0},
            "neutral": {"value": 100, "count": 10, "percentage": 10.0},
            "unhappy": {"value": -101, "count": 8, "percentage": 8.0},
            "very_unhappy": {"value": -102, "count": 2, "percentage": 2.0}
        },
        "csat_percentage": 45.0,  # Only 103 counts for CSAT
        "period": {
            "days": 30,
            "start_date": null,
            "end_date": null
        }
    }
    """
    # result = FreshdeskInsights.get_rating_statistics(session, days=30)
    # print(f"Rating stats: {result['total_ratings']} total, CSAT: {result['csat_percentage']}%")
    print("Stub: get_rating_statistics - Returns comprehensive rating breakdown and CSAT")


def run_all_tests(session: Session):
    """Run all test stubs"""
    print("=== Freshdesk Insights Library Test Stubs ===\n")
    
    test_get_support_dashboard(session)
    test_calculate_csat(session)
    test_get_ticket_by_id(session)
    test_get_tickets_by_email(session)
    test_get_tickets_by_rating(session)
    test_get_recent_bad_csat_tickets(session)
    test_get_rating_statistics(session)
    
    print("=== To run actual tests, uncomment the result lines in each function ===")


if __name__ == "__main__":
    # Create database session using context manager
    with get_db_session() as session:
        run_all_tests(session)
