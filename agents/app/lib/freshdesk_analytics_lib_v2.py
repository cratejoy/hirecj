"""Freshdesk Analytics Library V2 - Refactored

Key changes:
1. All functions now accept a session parameter instead of creating their own
2. Fixed rating comparisons to be consistent 
3. Added proper rating constants and documentation

This library provides comprehensive analytics functions for support team metrics,
designed to power the support_daily workflow with actionable insights.
"""

from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import func, and_, or_, case, distinct
from sqlalchemy.orm import Session

from app.dbmodels.view_models import FreshdeskUnifiedTicketView
from app.dbmodels.etl_tables import FreshdeskTicket, FreshdeskConversation, FreshdeskRating
from app.config import logger


# Freshdesk rating constants for clarity
class FreshdeskRatings:
    """Freshdesk 7-point rating scale constants.
    
    CSAT Calculation: Only EXTREMELY_HAPPY (103) counts as "satisfied"
    Bad/Negative: Anything below VERY_HAPPY (102)
    """
    EXTREMELY_HAPPY = 103
    VERY_HAPPY = 102
    HAPPY = 101
    NEUTRAL = 100
    UNHAPPY = -101
    VERY_UNHAPPY = -102
    EXTREMELY_UNHAPPY = -103
    
    # Thresholds
    SATISFIED_THRESHOLD = 103  # Only "Extremely Happy" counts for CSAT
    NEGATIVE_THRESHOLD = 102   # Below "Very Happy" is considered negative


class FreshdeskAnalytics:
    """Analytics engine for Freshdesk support metrics.
    
    All methods accept a session parameter to avoid creating database connections
    within the analytics layer. The calling code is responsible for session management.
    """
    
    @staticmethod
    def get_daily_snapshot(session: Session, merchant_id: int, target_date: date) -> Dict[str, Any]:
        """Get comprehensive daily health metrics for a merchant.
        
        Args:
            session: SQLAlchemy session for database queries
            merchant_id: The merchant ID to filter by (NEVER look up by name)
            target_date: The date to analyze
            
        Returns:
            Dict containing:
                - new_tickets: Count of tickets created on target_date
                - closed_tickets: Count of tickets closed on target_date
                - open_eod: Count of tickets still open at end of target_date
                - median_first_response_min: Median time to first response in minutes
                - median_resolution_min: Median time to resolution in minutes
                - quick_close_count: Count of tickets closed in <10 minutes
                - new_csat_count: Count of new CSAT ratings received
                - csat_percentage: % of ratings that are "Extremely Happy" (103)
                - bad_csat_count: Count of ratings below "Very Happy" (<102)
                - sla_breaches: Count of tickets that breached SLA
        """
        # Convert date to datetime range for the target day
        start_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Base query filtered by merchant
        base_query = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id
        )
        
        # New tickets created on target date
        new_tickets = base_query.filter(
            FreshdeskUnifiedTicketView.created_at.between(start_dt, end_dt)
        ).count()
        
        # Tickets closed on target date
        closed_tickets = base_query.filter(
            FreshdeskUnifiedTicketView.closed_at.between(start_dt, end_dt)
        ).count()
        
        # Open tickets at end of day (created before end of day and not closed by end of day)
        open_eod = base_query.filter(
            FreshdeskUnifiedTicketView.created_at <= end_dt,
            or_(
                FreshdeskUnifiedTicketView.closed_at.is_(None),
                FreshdeskUnifiedTicketView.closed_at > end_dt
            ),
            FreshdeskUnifiedTicketView.status.in_([2, 3, 6, 7])  # Open, Pending, Waiting statuses
        ).count()
        
        # Get tickets created on target date for response/resolution metrics
        target_date_tickets = base_query.filter(
            FreshdeskUnifiedTicketView.created_at.between(start_dt, end_dt)
        ).all()
        
        # Calculate response times
        first_response_times = []
        resolution_times = []
        quick_close_count = 0
        
        for ticket in target_date_tickets:
            # First response time
            if ticket.first_responded_at and ticket.created_at:
                response_time = (ticket.first_responded_at - ticket.created_at).total_seconds() / 60
                first_response_times.append(response_time)
            
            # Resolution time
            if ticket.resolved_at and ticket.created_at:
                resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 60
                resolution_times.append(resolution_time)
                
                # Quick close (< 10 minutes)
                if resolution_time < 10:
                    quick_close_count += 1
        
        # Calculate medians
        def calculate_median(values: List[float]) -> float:
            if not values:
                return 0.0
            sorted_values = sorted(values)
            n = len(sorted_values)
            if n % 2 == 0:
                return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
            return sorted_values[n//2]
        
        median_first_response_min = calculate_median(first_response_times)
        median_resolution_min = calculate_median(resolution_times)
        
        # CSAT metrics - ratings received on target date
        csat_ratings = base_query.filter(
            FreshdeskUnifiedTicketView.rating_created_at.between(start_dt, end_dt),
            FreshdeskUnifiedTicketView.has_rating == True
        ).all()
        
        new_csat_count = len(csat_ratings)
        
        # CSAT calculation: percentage of perfect scores (103 = Extremely Happy ONLY)
        # Bad ratings: anything below 102 (Very Happy)
        perfect_scores = 0
        bad_csat_count = 0
        
        for ticket in csat_ratings:
            if ticket.rating_score == FreshdeskRatings.EXTREMELY_HAPPY:
                perfect_scores += 1
            if ticket.rating_score < FreshdeskRatings.NEGATIVE_THRESHOLD:
                bad_csat_count += 1
        
        # Calculate CSAT percentage
        csat_percentage = (perfect_scores / new_csat_count * 100) if new_csat_count > 0 else 0.0
        
        # SLA breaches - tickets created on target date that breached SLA
        sla_breaches = 0
        for ticket in target_date_tickets:
            # Check first response SLA breach
            if ticket.fr_escalated:
                sla_breaches += 1
            # Check resolution SLA breach (only if not already counted for first response)
            elif ticket.is_escalated:
                sla_breaches += 1
        
        return {
            "date": target_date.isoformat(),
            "new_tickets": new_tickets,
            "closed_tickets": closed_tickets,
            "open_eod": open_eod,
            "median_first_response_min": round(median_first_response_min, 1),
            "median_resolution_min": round(median_resolution_min, 1),
            "quick_close_count": quick_close_count,
            "new_csat_count": new_csat_count,
            "csat_percentage": round(csat_percentage, 1),
            "bad_csat_count": bad_csat_count,
            "sla_breaches": sla_breaches
        }
    
    @staticmethod
    def get_tickets_by_rating(session: Session, rating_type: str, merchant_id: int, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get tickets with specific rating type.
        
        IMPORTANT: Rating definitions have been corrected:
        - "happy": Only includes Extremely Happy (103) - consistent with CSAT calculation
        - "unhappy": Everything below Very Happy (<102)
        
        Args:
            session: Database session
            rating_type: Either "happy" or "unhappy"
            merchant_id: Merchant to filter by
            days: Optional days to look back
        """
        # Build base query
        query = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.has_rating == True
        )
        
        # Filter by rating type
        if rating_type == "happy":
            # CORRECTED: Only "Extremely Happy" is truly happy for consistency with CSAT
            query = query.filter(FreshdeskUnifiedTicketView.rating_score == FreshdeskRatings.EXTREMELY_HAPPY)
        else:  # unhappy
            query = query.filter(FreshdeskUnifiedTicketView.rating_score < FreshdeskRatings.NEGATIVE_THRESHOLD)
        
        # Add time filter
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(FreshdeskUnifiedTicketView.rating_created_at >= cutoff_date)
        
        # Get tickets
        tickets = query.order_by(FreshdeskUnifiedTicketView.rating_created_at.desc()).limit(20).all()
        
        results = []
        for ticket in tickets:
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.subject,
                "rating_score": ticket.rating_score,
                "rating_created_at": ticket.rating_created_at.isoformat() if ticket.rating_created_at else None,
                "requester": {
                    "name": ticket.requester_name,
                    "email": ticket.requester_email
                }
            })
            
        return results