"""Tests for Freshdesk Analytics Library

Tests the analytics functions with mock data to ensure correct calculations.
"""

import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics


class TestGetDailySnapshot:
    """Test cases for get_daily_snapshot function."""
    
    def create_mock_ticket(self, **kwargs):
        """Helper to create a mock ticket with default values."""
        defaults = {
            'merchant_id': 1,
            'freshdesk_ticket_id': '12345',
            'created_at': datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            'closed_at': None,
            'resolved_at': None,
            'first_responded_at': None,
            'status': 2,  # Open
            'has_rating': False,
            'rating_score': None,
            'rating_created_at': None,
            'fr_escalated': False,
            'is_escalated': False,
        }
        defaults.update(kwargs)
        
        mock_ticket = Mock()
        for key, value in defaults.items():
            setattr(mock_ticket, key, value)
        return mock_ticket
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_basic_daily_metrics(self, mock_get_db_session):
        """Test basic counting metrics for a single day."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        # Create test data
        target_date = date(2024, 1, 10)
        tickets = [
            # New ticket created on target date
            self.create_mock_ticket(
                freshdesk_ticket_id='1',
                created_at=datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
                status=2
            ),
            # Another new ticket, closed same day
            self.create_mock_ticket(
                freshdesk_ticket_id='2',
                created_at=datetime(2024, 1, 10, 11, 0, 0, tzinfo=timezone.utc),
                closed_at=datetime(2024, 1, 10, 15, 0, 0, tzinfo=timezone.utc),
                status=5  # Closed
            ),
            # Old ticket closed on target date
            self.create_mock_ticket(
                freshdesk_ticket_id='3',
                created_at=datetime(2024, 1, 8, 10, 0, 0, tzinfo=timezone.utc),
                closed_at=datetime(2024, 1, 10, 14, 0, 0, tzinfo=timezone.utc),
                status=5  # Closed
            ),
        ]
        
        # Configure mock query chain
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Set up different return values for different queries
        count_results = [2, 2, 1]  # new_tickets, closed_tickets, open_eod
        mock_query.count.side_effect = count_results
        mock_query.all.side_effect = [
            [tickets[0], tickets[1]],  # target_date_tickets
            []  # csat_ratings
        ]
        
        # Execute
        result = FreshdeskAnalytics.get_daily_snapshot(merchant_id=1, target_date=target_date)
        
        # Assert basic counts
        assert result['date'] == '2024-01-10'
        assert result['new_tickets'] == 2
        assert result['closed_tickets'] == 2
        assert result['open_eod'] == 1
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_response_time_calculations(self, mock_get_db_session):
        """Test median response time calculations."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        target_date = date(2024, 1, 10)
        base_time = datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
        
        # Create tickets with various response times
        tickets = [
            # 5 minute first response, 30 minute resolution
            self.create_mock_ticket(
                freshdesk_ticket_id='1',
                created_at=base_time,
                first_responded_at=base_time + timedelta(minutes=5),
                resolved_at=base_time + timedelta(minutes=30)
            ),
            # 10 minute first response, 60 minute resolution
            self.create_mock_ticket(
                freshdesk_ticket_id='2',
                created_at=base_time,
                first_responded_at=base_time + timedelta(minutes=10),
                resolved_at=base_time + timedelta(minutes=60)
            ),
            # 15 minute first response, no resolution yet
            self.create_mock_ticket(
                freshdesk_ticket_id='3',
                created_at=base_time,
                first_responded_at=base_time + timedelta(minutes=15),
                resolved_at=None
            ),
            # No response yet
            self.create_mock_ticket(
                freshdesk_ticket_id='4',
                created_at=base_time,
                first_responded_at=None,
                resolved_at=None
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.side_effect = [
            tickets,  # target_date_tickets
            []  # csat_ratings
        ]
        
        # Execute
        result = FreshdeskAnalytics.get_daily_snapshot(merchant_id=1, target_date=target_date)
        
        # Assert medians
        # First response times: [5, 10, 15] -> median = 10
        assert result['median_first_response_min'] == 10.0
        # Resolution times: [30, 60] -> median = 45
        assert result['median_resolution_min'] == 45.0
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_quick_close_detection(self, mock_get_db_session):
        """Test detection of tickets closed in under 10 minutes."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        target_date = date(2024, 1, 10)
        base_time = datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
        
        # Create tickets with various resolution times
        tickets = [
            # 5 minute resolution - should count as quick close
            self.create_mock_ticket(
                created_at=base_time,
                resolved_at=base_time + timedelta(minutes=5)
            ),
            # 9.5 minute resolution - should count as quick close
            self.create_mock_ticket(
                created_at=base_time,
                resolved_at=base_time + timedelta(minutes=9.5)
            ),
            # 10 minute resolution - should NOT count as quick close
            self.create_mock_ticket(
                created_at=base_time,
                resolved_at=base_time + timedelta(minutes=10)
            ),
            # 30 minute resolution - should NOT count
            self.create_mock_ticket(
                created_at=base_time,
                resolved_at=base_time + timedelta(minutes=30)
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.side_effect = [
            tickets,  # target_date_tickets
            []  # csat_ratings
        ]
        
        # Execute
        result = FreshdeskAnalytics.get_daily_snapshot(merchant_id=1, target_date=target_date)
        
        # Assert quick close count
        assert result['quick_close_count'] == 2
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_csat_calculations(self, mock_get_db_session):
        """Test CSAT metrics calculation and rating conversion."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        target_date = date(2024, 1, 10)
        rating_time = datetime(2024, 1, 10, 15, 0, 0, tzinfo=timezone.utc)
        
        # Create tickets with various ratings
        csat_tickets = [
            # Extremely Happy (5.0)
            self.create_mock_ticket(
                has_rating=True,
                rating_score=103,
                rating_created_at=rating_time
            ),
            # Very Happy (4.0)
            self.create_mock_ticket(
                has_rating=True,
                rating_score=102,
                rating_created_at=rating_time
            ),
            # Happy (3.0) - counts as bad
            self.create_mock_ticket(
                has_rating=True,
                rating_score=101,
                rating_created_at=rating_time
            ),
            # Unhappy (2.0) - counts as bad
            self.create_mock_ticket(
                has_rating=True,
                rating_score=-101,
                rating_created_at=rating_time
            ),
            # Extremely Unhappy (1.0) - counts as bad
            self.create_mock_ticket(
                has_rating=True,
                rating_score=-103,
                rating_created_at=rating_time
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.side_effect = [
            [],  # target_date_tickets
            csat_tickets  # csat_ratings
        ]
        
        # Execute
        result = FreshdeskAnalytics.get_daily_snapshot(merchant_id=1, target_date=target_date)
        
        # Assert CSAT metrics
        assert result['new_csat_count'] == 5
        # CSAT: 1 perfect score (103) out of 5 total = 20%
        assert result['csat_percentage'] == 20.0
        assert result['bad_csat_count'] == 3  # Ratings below 102 (Very Happy)
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_sla_breach_detection(self, mock_get_db_session):
        """Test SLA breach counting."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        target_date = date(2024, 1, 10)
        
        # Create tickets with SLA breaches
        tickets = [
            # First response SLA breach
            self.create_mock_ticket(
                fr_escalated=True,
                is_escalated=False
            ),
            # Resolution SLA breach
            self.create_mock_ticket(
                fr_escalated=False,
                is_escalated=True
            ),
            # Both breaches (should only count once)
            self.create_mock_ticket(
                fr_escalated=True,
                is_escalated=True
            ),
            # No breaches
            self.create_mock_ticket(
                fr_escalated=False,
                is_escalated=False
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.side_effect = [
            tickets,  # target_date_tickets
            []  # csat_ratings
        ]
        
        # Execute
        result = FreshdeskAnalytics.get_daily_snapshot(merchant_id=1, target_date=target_date)
        
        # Assert SLA breaches
        assert result['sla_breaches'] == 3
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_empty_data_handling(self, mock_get_db_session):
        """Test handling of days with no data."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        # Configure mock for no data
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        # Execute
        result = FreshdeskAnalytics.get_daily_snapshot(merchant_id=1, target_date=date(2024, 1, 10))
        
        # Assert all metrics are zero/empty
        assert result['new_tickets'] == 0
        assert result['closed_tickets'] == 0
        assert result['open_eod'] == 0
        assert result['median_first_response_min'] == 0.0
        assert result['median_resolution_min'] == 0.0
        assert result['quick_close_count'] == 0
        assert result['new_csat_count'] == 0
        assert result['csat_percentage'] == 0.0
        assert result['bad_csat_count'] == 0
        assert result['sla_breaches'] == 0


class TestGetCSATDetailLog:
    """Test cases for get_csat_detail_log function."""
    
    def create_mock_ticket(self, **kwargs):
        """Helper to create a mock ticket with default values."""
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
    def test_basic_csat_detail_log(self, mock_get_db_session):
        """Test basic CSAT detail log functionality."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        target_date = date(2024, 1, 10)
        base_time = datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
        rating_time = datetime(2024, 1, 10, 15, 0, 0, tzinfo=timezone.utc)
        
        # Create test tickets with various ratings
        tickets = [
            # Extremely Happy with feedback
            self.create_mock_ticket(
                freshdesk_ticket_id='101',
                rating_score=103,
                rating_feedback='Excellent service!',
                created_at=base_time,
                first_responded_at=base_time + timedelta(minutes=5),
                resolved_at=base_time + timedelta(minutes=30),
                rating_created_at=rating_time
            ),
            # Very Happy
            self.create_mock_ticket(
                freshdesk_ticket_id='102',
                rating_score=102,
                rating_feedback='',
                created_at=base_time,
                first_responded_at=base_time + timedelta(minutes=10),
                resolved_at=base_time + timedelta(minutes=60),
                rating_created_at=rating_time
            ),
            # Unhappy with feedback
            self.create_mock_ticket(
                freshdesk_ticket_id='103',
                rating_score=-101,
                rating_feedback='Took too long to resolve',
                created_at=base_time,
                first_responded_at=base_time + timedelta(minutes=120),
                resolved_at=base_time + timedelta(minutes=240),
                rating_created_at=rating_time
            ),
        ]
        
        # Configure mock query
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Mock conversation data for each ticket
        conversation_data = [
            ([{"id": 1}, {"id": 2}, {"id": 3}],),  # 3 conversations for ticket 101
            ([{"id": 4}, {"id": 5}],),  # 2 conversations for ticket 102
            ([{"id": 6}, {"id": 7}, {"id": 8}, {"id": 9}, {"id": 10}],),  # 5 conversations for ticket 103
        ]
        mock_query.first.side_effect = conversation_data
        
        # Execute
        result = FreshdeskAnalytics.get_csat_detail_log(merchant_id=1, target_date=target_date)
        
        # Assert summary
        assert result['total_count'] == 3
        assert result['below_threshold_count'] == 1  # Only the -101 rating
        assert result['avg_rating'] == pytest.approx(34.7, 0.1)  # (103 + 102 + (-101)) / 3
        
        # Assert survey details
        assert len(result['surveys']) == 3
        
        # Check sorting (lowest rating first)
        assert result['surveys'][0]['rating'] == -101
        assert result['surveys'][0]['ticket_id'] == 103
        assert result['surveys'][0]['rating_label'] == 'Very Unhappy'
        assert result['surveys'][0]['feedback'] == 'Took too long to resolve'
        assert result['surveys'][0]['first_response_min'] == 120.0
        assert result['surveys'][0]['resolution_min'] == 240.0
        assert result['surveys'][0]['conversation_count'] == 5
        
        # Check highest rating
        assert result['surveys'][-1]['rating'] == 103
        assert result['surveys'][-1]['rating_label'] == 'Extremely Happy'
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_csat_detail_with_custom_threshold(self, mock_get_db_session):
        """Test CSAT detail log with custom rating threshold."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        target_date = date(2024, 1, 10)
        rating_time = datetime(2024, 1, 10, 15, 0, 0, tzinfo=timezone.utc)
        
        # Create tickets with various ratings
        tickets = [
            self.create_mock_ticket(freshdesk_ticket_id='1', rating_score=103, rating_created_at=rating_time),
            self.create_mock_ticket(freshdesk_ticket_id='2', rating_score=102, rating_created_at=rating_time),
            self.create_mock_ticket(freshdesk_ticket_id='3', rating_score=101, rating_created_at=rating_time),
            self.create_mock_ticket(freshdesk_ticket_id='4', rating_score=100, rating_created_at=rating_time),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        mock_query.first.return_value = ([{"id": 1}],)  # 1 conversation for each ticket
        
        # Execute with custom threshold (103 = only perfect scores are good)
        result = FreshdeskAnalytics.get_csat_detail_log(
            merchant_id=1, 
            target_date=target_date,
            rating_threshold=103
        )
        
        # Assert
        assert result['below_threshold_count'] == 3  # 102, 101, 100 are all below 103
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_csat_detail_with_missing_data(self, mock_get_db_session):
        """Test CSAT detail log handling of missing response times."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        target_date = date(2024, 1, 10)
        base_time = datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
        
        # Create ticket with missing response times
        tickets = [
            self.create_mock_ticket(
                freshdesk_ticket_id='105',
                rating_score=103,
                created_at=base_time,
                first_responded_at=None,  # No response time
                resolved_at=None,  # Not resolved
                responder_email=None,  # Unassigned
                tags=None,  # No tags
                rating_feedback=None  # No feedback
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        mock_query.first.return_value = None  # No conversations
        
        # Execute
        result = FreshdeskAnalytics.get_csat_detail_log(merchant_id=1, target_date=target_date)
        
        # Assert handling of missing data
        survey = result['surveys'][0]
        assert survey['first_response_min'] is None
        assert survey['resolution_min'] is None
        assert survey['agent'] == 'unassigned'
        assert survey['tags'] == []
        assert survey['feedback'] == ''
        assert survey['conversation_count'] == 0
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_empty_csat_detail_log(self, mock_get_db_session):
        """Test CSAT detail log with no ratings for the day."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        # Configure mock for no data
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        # Execute
        result = FreshdeskAnalytics.get_csat_detail_log(
            merchant_id=1, 
            target_date=date(2024, 1, 10)
        )
        
        # Assert empty results
        assert result['total_count'] == 0
        assert result['below_threshold_count'] == 0
        assert result['avg_rating'] == 0.0
        assert result['surveys'] == []


class TestGetOpenTicketDistribution:
    """Test cases for get_open_ticket_distribution function."""
    
    def create_mock_ticket(self, **kwargs):
        """Helper to create a mock ticket with default values."""
        defaults = {
            'merchant_id': 1,
            'freshdesk_ticket_id': '12345',
            'created_at': datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=2),
            'updated_at': datetime.utcnow().replace(tzinfo=timezone.utc),
            'status': 2,  # Open
            'priority': 2,
            'subject': 'Test ticket',
            'requester_email': 'customer@example.com',
            'tags': ['support'],
        }
        defaults.update(kwargs)
        
        mock_ticket = Mock()
        for key, value in defaults.items():
            setattr(mock_ticket, key, value)
        return mock_ticket
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_ticket_age_distribution(self, mock_get_db_session):
        """Test correct distribution of tickets into age buckets."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Create tickets of various ages
        tickets = [
            # 0-4h bucket (3 tickets)
            self.create_mock_ticket(freshdesk_ticket_id='1', created_at=now - timedelta(hours=1)),
            self.create_mock_ticket(freshdesk_ticket_id='2', created_at=now - timedelta(hours=2)),
            self.create_mock_ticket(freshdesk_ticket_id='3', created_at=now - timedelta(hours=3.5)),
            
            # 4-24h bucket (2 tickets)
            self.create_mock_ticket(freshdesk_ticket_id='4', created_at=now - timedelta(hours=5)),
            self.create_mock_ticket(freshdesk_ticket_id='5', created_at=now - timedelta(hours=20)),
            
            # 1-2d bucket (1 ticket)
            self.create_mock_ticket(freshdesk_ticket_id='6', created_at=now - timedelta(days=1.5)),
            
            # 3-7d bucket (1 ticket)
            self.create_mock_ticket(freshdesk_ticket_id='7', created_at=now - timedelta(days=5)),
            
            # >7d bucket (2 tickets)
            self.create_mock_ticket(freshdesk_ticket_id='8', created_at=now - timedelta(days=10)),
            self.create_mock_ticket(freshdesk_ticket_id='9', created_at=now - timedelta(days=30)),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Execute
        result = FreshdeskAnalytics.get_open_ticket_distribution(merchant_id=1)
        
        # Assert distribution
        assert result['total_open'] == 9
        assert result['age_buckets']['0-4h']['count'] == 3
        assert result['age_buckets']['0-4h']['percentage'] == pytest.approx(33.3, 0.1)
        assert result['age_buckets']['4-24h']['count'] == 2
        assert result['age_buckets']['1-2d']['count'] == 1
        assert result['age_buckets']['3-7d']['count'] == 1
        assert result['age_buckets']['>7d']['count'] == 2
        assert result['age_buckets']['>7d']['percentage'] == pytest.approx(22.2, 0.1)
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_oldest_tickets_details(self, mock_get_db_session):
        """Test that oldest tickets are correctly identified and formatted."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Create tickets with specific ages
        tickets = [
            self.create_mock_ticket(
                freshdesk_ticket_id='100',
                created_at=now - timedelta(days=15),
                subject='Very old ticket',
                status=2,  # Open
                priority=4,  # Urgent
                tags=['escalation', 'urgent']
            ),
            self.create_mock_ticket(
                freshdesk_ticket_id='101',
                created_at=now - timedelta(days=7, hours=3),
                subject='Week old ticket',
                status=6,  # Waiting on Customer
                priority=2
            ),
            self.create_mock_ticket(
                freshdesk_ticket_id='102',
                created_at=now - timedelta(hours=2),
                subject='Recent ticket',
                status=3,  # Pending
                priority=1
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Execute
        result = FreshdeskAnalytics.get_open_ticket_distribution(merchant_id=1)
        
        # Assert oldest tickets
        assert len(result['oldest_tickets']) == 3
        
        # Check oldest ticket
        oldest = result['oldest_tickets'][0]
        assert oldest['ticket_id'] == 100
        assert oldest['subject'] == 'Very old ticket'
        assert oldest['age_display'] == '15d'
        assert oldest['status'] == 'Open'
        assert oldest['priority'] == 4
        assert oldest['tags'] == ['escalation', 'urgent']
        
        # Check second oldest
        second = result['oldest_tickets'][1]
        assert second['ticket_id'] == 101
        # 7 days 3 hours = 171 hours, which is > 168, so should show just days
        assert second['age_display'] == '7d'
        assert second['status'] == 'Waiting on Customer'
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_age_display_formatting(self, mock_get_db_session):
        """Test various age display formats."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Create tickets with specific ages to test formatting
        tickets = [
            self.create_mock_ticket(
                freshdesk_ticket_id='1',
                created_at=now - timedelta(minutes=30)  # 30 minutes
            ),
            self.create_mock_ticket(
                freshdesk_ticket_id='2',
                created_at=now - timedelta(hours=1.5)  # 1h 30m
            ),
            self.create_mock_ticket(
                freshdesk_ticket_id='3',
                created_at=now - timedelta(days=2, hours=6)  # 2d 6h
            ),
            self.create_mock_ticket(
                freshdesk_ticket_id='4',
                created_at=now - timedelta(days=10)  # 10d
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Execute
        result = FreshdeskAnalytics.get_open_ticket_distribution(merchant_id=1)
        
        # Check age displays
        age_displays = [t['age_display'] for t in result['oldest_tickets']]
        assert '10d' in age_displays
        assert '2d 6h' in age_displays
        assert '1h 30m' in age_displays
        assert '30m' in age_displays
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_empty_backlog(self, mock_get_db_session):
        """Test handling of empty backlog."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        # Configure mock for no tickets
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        # Execute
        result = FreshdeskAnalytics.get_open_ticket_distribution(merchant_id=1)
        
        # Assert empty results
        assert result['total_open'] == 0
        assert all(bucket['count'] == 0 for bucket in result['age_buckets'].values())
        assert all(bucket['percentage'] == 0 for bucket in result['age_buckets'].values())
        assert result['oldest_tickets'] == []
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_status_filtering(self, mock_get_db_session):
        """Test that only open statuses are included."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        # Create mix of open and closed tickets
        tickets = [
            self.create_mock_ticket(freshdesk_ticket_id='1', status=2),  # Open
            self.create_mock_ticket(freshdesk_ticket_id='2', status=3),  # Pending
            self.create_mock_ticket(freshdesk_ticket_id='3', status=4),  # Resolved (should not appear)
            self.create_mock_ticket(freshdesk_ticket_id='4', status=5),  # Closed (should not appear)
            self.create_mock_ticket(freshdesk_ticket_id='5', status=6),  # Waiting on Customer
            self.create_mock_ticket(freshdesk_ticket_id='6', status=7),  # Waiting on Third Party
        ]
        
        # Configure mock to return only open tickets
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        
        # Mock the filter to simulate SQL IN clause behavior
        def filter_side_effect(*args, **kwargs):
            # Return only tickets with status in [2, 3, 6, 7]
            mock_filtered = MagicMock()
            mock_filtered.all.return_value = [t for t in tickets if t.status in [2, 3, 6, 7]]
            return mock_filtered
        
        mock_query.filter.side_effect = filter_side_effect
        
        # Execute
        result = FreshdeskAnalytics.get_open_ticket_distribution(merchant_id=1)
        
        # Should only count open statuses
        assert result['total_open'] == 4  # Only statuses 2, 3, 6, 7


class TestGetResponseTimeMetrics:
    """Test cases for get_response_time_metrics function."""
    
    def create_mock_ticket(self, **kwargs):
        """Helper to create a mock ticket with default values."""
        defaults = {
            'merchant_id': 1,
            'freshdesk_ticket_id': '12345',
            'created_at': datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=2),
            'first_responded_at': None,
            'resolved_at': None,
            'has_rating': False,
            'rating_score': None,
        }
        defaults.update(kwargs)
        
        mock_ticket = Mock()
        for key, value in defaults.items():
            setattr(mock_ticket, key, value)
        return mock_ticket
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    @patch('app.lib.freshdesk_analytics_lib.np')
    def test_response_time_statistics(self, mock_np, mock_get_db_session):
        """Test calculation of response time statistics."""
        # Setup numpy mocks
        mock_np.array.side_effect = lambda x: x
        mock_np.median.side_effect = lambda x: sorted(x)[len(x)//2] if x else 0
        mock_np.mean.side_effect = lambda x: sum(x)/len(x) if x else 0
        mock_np.percentile.side_effect = lambda x, p: sorted(x)[int(len(x) * p / 100)] if x else 0
        mock_np.std.side_effect = lambda x: 10.0  # Fixed std for predictable outliers
        
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        base_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Create tickets with various response times
        tickets = [
            # Fast response: 5 minutes
            self.create_mock_ticket(
                freshdesk_ticket_id='1',
                created_at=base_time - timedelta(days=1),
                first_responded_at=base_time - timedelta(days=1) + timedelta(minutes=5),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=30)
            ),
            # Medium response: 30 minutes
            self.create_mock_ticket(
                freshdesk_ticket_id='2',
                created_at=base_time - timedelta(days=2),
                first_responded_at=base_time - timedelta(days=2) + timedelta(minutes=30),
                resolved_at=base_time - timedelta(days=2) + timedelta(minutes=120)
            ),
            # Slow response: 60 minutes
            self.create_mock_ticket(
                freshdesk_ticket_id='3',
                created_at=base_time - timedelta(days=3),
                first_responded_at=base_time - timedelta(days=3) + timedelta(minutes=60),
                resolved_at=base_time - timedelta(days=3) + timedelta(minutes=180)
            ),
            # Very slow response: 120 minutes (outlier)
            self.create_mock_ticket(
                freshdesk_ticket_id='4',
                created_at=base_time - timedelta(days=4),
                first_responded_at=base_time - timedelta(days=4) + timedelta(minutes=120),
                resolved_at=None  # Not resolved yet
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Execute
        date_range = {
            'start_date': (base_time - timedelta(days=7)).date(),
            'end_date': base_time.date()
        }
        result = FreshdeskAnalytics.get_response_time_metrics(merchant_id=1, date_range=date_range)
        
        # Assert first response statistics
        assert 'first_response' in result
        fr = result['first_response']
        assert fr['median_min'] == 30.0  # Middle value of [5, 30, 60, 120]
        assert fr['mean_min'] == pytest.approx(53.75, 0.1)  # (5+30+60+120)/4
        
        # Assert resolution statistics
        assert 'resolution' in result
        res = result['resolution']
        # Only 3 tickets have resolution times: [30, 120, 180]
        assert res['median_min'] == 120.0
        assert res['mean_min'] == pytest.approx(110.0, 0.1)  # (30+120+180)/3
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    @patch('app.lib.freshdesk_analytics_lib.np')
    def test_quick_resolution_buckets(self, mock_np, mock_get_db_session):
        """Test categorization of quick resolutions."""
        # Setup numpy mocks
        mock_np.array.side_effect = lambda x: x
        mock_np.median.return_value = 15.0
        mock_np.mean.return_value = 20.0
        mock_np.percentile.return_value = 30.0
        mock_np.std.return_value = 10.0
        
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        base_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Create tickets with specific resolution times
        tickets = [
            # <5min bucket
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=3),
                has_rating=True,
                rating_score=103  # Extremely Happy
            ),
            # <10min bucket (but not <5min)
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=7),
                has_rating=True,
                rating_score=102  # Very Happy
            ),
            # <30min bucket (but not <10min)
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=25),
                has_rating=True,
                rating_score=101  # Happy
            ),
            # <60min bucket (but not <30min)
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=45),
                has_rating=True,
                rating_score=100  # Neutral
            ),
            # >60min (not in any quick bucket)
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=90),
                has_rating=False
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Execute
        date_range = {
            'start_date': (base_time - timedelta(days=7)).date(),
            'end_date': base_time.date()
        }
        result = FreshdeskAnalytics.get_response_time_metrics(merchant_id=1, date_range=date_range)
        
        # Assert quick resolution buckets
        assert result['total_resolved'] == 5
        
        qr = result['quick_resolutions']
        assert qr['<5min']['count'] == 1
        assert qr['<5min']['percentage'] == 20.0
        assert qr['<5min']['avg_csat'] > 4.5  # Should be high (103 rating)
        
        assert qr['<10min']['count'] == 2  # Includes both <5min and 5-10min
        assert qr['<30min']['count'] == 3  # Includes <5, <10, and 10-30min
        assert qr['<60min']['count'] == 4  # All except the 90min one
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    @patch('app.lib.freshdesk_analytics_lib.np')
    def test_csat_by_speed_correlation(self, mock_np, mock_get_db_session):
        """Test CSAT correlation with response/resolution speed."""
        # Setup numpy mocks
        mock_np.array.side_effect = lambda x: x
        mock_np.median.return_value = 30.0
        mock_np.mean.return_value = 40.0
        mock_np.percentile.return_value = 60.0
        mock_np.std.return_value = 15.0
        
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        base_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Create tickets with resolution times and ratings
        tickets = [
            # Ultra fast (<5min) with high rating
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=3),
                has_rating=True,
                rating_score=103
            ),
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=4),
                has_rating=True,
                rating_score=102
            ),
            # Fast (5-30min) with good rating
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=15),
                has_rating=True,
                rating_score=102
            ),
            # Normal (30-180min) with ok rating
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=90),
                has_rating=True,
                rating_score=101
            ),
            # Slow (>180min) with poor rating
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=240),
                has_rating=True,
                rating_score=-101
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Execute
        date_range = {
            'start_date': (base_time - timedelta(days=7)).date(),
            'end_date': base_time.date()
        }
        result = FreshdeskAnalytics.get_response_time_metrics(merchant_id=1, date_range=date_range)
        
        # Assert CSAT by speed
        csat_speed = result['csat_by_speed']
        
        # Ultra fast should have highest rating
        assert csat_speed['ultra_fast_<5min']['count'] == 2
        assert csat_speed['ultra_fast_<5min']['avg_rating'] == 102.5  # (103+102)/2
        
        # Fast should have good rating
        assert csat_speed['fast_5-30min']['count'] == 1
        assert csat_speed['fast_5-30min']['avg_rating'] == 102.0
        
        # Normal should have ok rating
        assert csat_speed['normal_30-180min']['count'] == 1
        assert csat_speed['normal_30-180min']['avg_rating'] == 101.0
        
        # Slow should have poor rating
        assert csat_speed['slow_>180min']['count'] == 1
        assert csat_speed['slow_>180min']['avg_rating'] == -101.0
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    @patch('app.lib.freshdesk_analytics_lib.np')
    def test_outlier_detection(self, mock_np, mock_get_db_session):
        """Test detection of response time outliers."""
        # Setup numpy mocks with specific values for outlier detection
        response_times = [5.0, 10.0, 15.0, 20.0, 200.0]  # 200 is an outlier
        mock_np.array.side_effect = lambda x: x
        mock_np.median.return_value = 15.0
        mock_np.mean.return_value = 50.0  # Mean is high due to outlier
        mock_np.percentile.side_effect = lambda x, p: 20.0
        mock_np.std.return_value = 50.0  # High std due to outlier
        
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        base_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Create tickets including outliers
        tickets = []
        for i, resp_time in enumerate(response_times):
            tickets.append(self.create_mock_ticket(
                freshdesk_ticket_id=str(i+1),
                created_at=base_time - timedelta(days=1),
                first_responded_at=base_time - timedelta(days=1) + timedelta(minutes=resp_time)
            ))
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Execute
        date_range = {
            'start_date': (base_time - timedelta(days=7)).date(),
            'end_date': base_time.date()
        }
        result = FreshdeskAnalytics.get_response_time_metrics(merchant_id=1, date_range=date_range)
        
        # Assert outliers are detected
        # Outlier threshold = mean + 2*std = 50 + 2*50 = 150
        # So ticket with 200 min response time should be an outlier
        assert len(result['first_response']['outliers']) > 0
        outlier = result['first_response']['outliers'][0]
        assert outlier['ticket_id'] == 5  # The ticket with 200 min response
        assert outlier['response_min'] == 200.0
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    def test_empty_metrics(self, mock_get_db_session):
        """Test handling when no tickets have response/resolution times."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        # Create tickets with no response/resolution times
        tickets = [
            self.create_mock_ticket(
                created_at=datetime.utcnow().replace(tzinfo=timezone.utc),
                first_responded_at=None,
                resolved_at=None
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Execute
        date_range = {
            'start_date': date.today() - timedelta(days=7),
            'end_date': date.today()
        }
        result = FreshdeskAnalytics.get_response_time_metrics(merchant_id=1, date_range=date_range)
        
        # Assert empty results are handled gracefully
        assert result['first_response'] == {}
        assert result['resolution'] == {}
        assert result['total_resolved'] == 0
        assert all(bucket['count'] == 0 for bucket in result['quick_resolutions'].values())
    
    @patch('app.lib.freshdesk_analytics_lib.get_db_session')
    @patch('app.lib.freshdesk_analytics_lib.np')
    def test_negative_time_sanity_check(self, mock_np, mock_get_db_session):
        """Test that negative response times are filtered out."""
        # Setup numpy mocks
        mock_np.array.side_effect = lambda x: x
        mock_np.median.return_value = 10.0
        mock_np.mean.return_value = 10.0
        mock_np.percentile.return_value = 15.0
        mock_np.std.return_value = 5.0
        
        # Setup mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        base_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Create tickets including one with invalid timestamps
        tickets = [
            # Valid ticket
            self.create_mock_ticket(
                created_at=base_time - timedelta(days=1),
                first_responded_at=base_time - timedelta(days=1) + timedelta(minutes=10),
                resolved_at=base_time - timedelta(days=1) + timedelta(minutes=30)
            ),
            # Invalid: response before creation (data error)
            self.create_mock_ticket(
                created_at=base_time,
                first_responded_at=base_time - timedelta(minutes=10),  # Before creation!
                resolved_at=base_time + timedelta(minutes=20)
            ),
        ]
        
        # Configure mock
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = tickets
        
        # Execute
        date_range = {
            'start_date': (base_time - timedelta(days=7)).date(),
            'end_date': base_time.date()
        }
        result = FreshdeskAnalytics.get_response_time_metrics(merchant_id=1, date_range=date_range)
        
        # Assert only valid times are included
        # Should only have 1 valid response time (10 minutes)
        assert result['first_response']['median_min'] == 10.0
        assert result['first_response']['mean_min'] == 10.0