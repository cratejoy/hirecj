"""Tests for Freshdesk Analytics Library

Tests the analytics functions with mock data to ensure correct calculations.
"""

import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
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