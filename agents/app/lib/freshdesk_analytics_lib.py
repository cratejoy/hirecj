"""Freshdesk Analytics Library

This library provides comprehensive analytics functions for support team metrics,
designed to power the support_daily workflow with actionable insights.
"""

from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import func, and_, or_, case, distinct
from sqlalchemy.orm import Session

from app.dbmodels.view_models import FreshdeskUnifiedTicketView
from app.dbmodels.etl_tables import FreshdeskTicket, FreshdeskConversation, FreshdeskRating
from app.utils.supabase_util import get_db_session
from app.config import logger


class FreshdeskAnalytics:
    """Analytics engine for Freshdesk support metrics."""
    
    @staticmethod
    def get_daily_snapshot(merchant_id: int, target_date: date) -> Dict[str, Any]:
        """Get comprehensive daily health metrics for a merchant.
        
        Args:
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
                - avg_csat: Average CSAT score (1-5 scale conversion)
                - bad_csat_count: Count of ratings ≤3 (on 1-5 scale)
                - sla_breaches: Count of tickets that breached SLA
        """
        with get_db_session() as session:
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
            
            # CSAT calculation: percentage of perfect scores (103 = Extremely Happy)
            # Bad ratings: anything below 102 (Very Happy)
            perfect_scores = 0
            bad_csat_count = 0
            
            for ticket in csat_ratings:
                if ticket.rating_score == 103:  # Extremely Happy
                    perfect_scores += 1
                if ticket.rating_score < 102:  # Below Very Happy
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
    def get_recent_ticket(session: Session, merchant_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent open ticket."""
        # Query the unified view for the most recent open ticket
        ticket = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.status.in_([2, 3, 6, 7])  # Open, Pending, Waiting statuses
        ).order_by(
            FreshdeskUnifiedTicketView.updated_at.desc()
        ).first()
        
        if not ticket:
            return None
            
        return {
            "ticket_id": ticket.freshdesk_ticket_id,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "requester": {
                "name": ticket.requester_name,
                "email": ticket.requester_email
            }
        }
    
    @staticmethod
    def get_support_dashboard(session: Session, merchant_id: int) -> Dict[str, Any]:
        """Get support dashboard overview."""
        # Count tickets by status
        status_counts = session.query(
            FreshdeskUnifiedTicketView.status,
            func.count(FreshdeskUnifiedTicketView.freshdesk_ticket_id)
        ).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id
        ).group_by(
            FreshdeskUnifiedTicketView.status
        ).all()
        
        # Convert to dict
        status_map = {
            2: "open",
            3: "pending", 
            4: "resolved",
            5: "closed",
            6: "waiting_on_customer",
            7: "waiting_on_third_party"
        }
        
        ticket_counts = {status_map.get(status, f"status_{status}"): count for status, count in status_counts}
        
        # Get total count
        total_tickets = sum(ticket_counts.values())
        
        return {
            "merchant_id": merchant_id,
            "total_tickets": total_tickets,
            "ticket_counts": ticket_counts,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def search_tickets(session: Session, query: str, merchant_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Search tickets by keyword."""
        # Search in subject and description
        tickets = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            or_(
                FreshdeskUnifiedTicketView.subject.ilike(f"%{query}%"),
                FreshdeskUnifiedTicketView.description.ilike(f"%{query}%"),
                FreshdeskUnifiedTicketView.requester_email.ilike(f"%{query}%"),
                FreshdeskUnifiedTicketView.tags.op('@>')(f'["{query}"]')
            )
        ).limit(limit).all()
        
        results = []
        for ticket in tickets:
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.subject,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "requester_email": ticket.requester_email
            })
            
        return results
    
    @staticmethod
    def calculate_csat(session: Session, merchant_id: int, days: Optional[int] = None) -> Dict[str, Any]:
        """Calculate CSAT score with proper deduplication."""
        # Build base query
        query = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.has_rating == True
        )
        
        # Add time filter if specified
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(FreshdeskUnifiedTicketView.rating_created_at >= cutoff_date)
        
        # Get all rated tickets
        rated_tickets = query.all()
        
        # Deduplicate by customer email (keep most recent rating per customer)
        customer_ratings = {}
        for ticket in rated_tickets:
            email = ticket.requester_email
            if email:
                if email not in customer_ratings or ticket.rating_created_at > customer_ratings[email].rating_created_at:
                    customer_ratings[email] = ticket
        
        # Calculate CSAT
        total_customers = len(customer_ratings)
        if total_customers == 0:
            return {
                "csat_percentage": 0,
                "total_ratings": 0,
                "satisfied_count": 0,
                "unsatisfied_count": 0
            }
        
        # Only rating 103 (Extremely Happy) counts as satisfied
        satisfied_count = sum(1 for ticket in customer_ratings.values() if ticket.rating_score == 103)
        csat_percentage = (satisfied_count / total_customers) * 100
        
        return {
            "csat_percentage": round(csat_percentage, 1),
            "total_ratings": total_customers,
            "satisfied_count": satisfied_count,
            "unsatisfied_count": total_customers - satisfied_count
        }
    
    @staticmethod
    def get_ticket_by_id(session: Session, ticket_id: str, merchant_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed ticket information including conversations."""
        # Get ticket from unified view
        ticket = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.freshdesk_ticket_id == str(ticket_id)
        ).first()
        
        if not ticket:
            return None
        
        # Get conversations
        conversations = session.query(FreshdeskConversation).filter(
            FreshdeskConversation.merchant_id == merchant_id,
            FreshdeskConversation.freshdesk_ticket_id == str(ticket_id)
        ).order_by(FreshdeskConversation.created_at).all()
        
        # Get ratings
        ratings = session.query(FreshdeskRating).filter(
            FreshdeskRating.merchant_id == merchant_id,
            FreshdeskRating.freshdesk_ticket_id == str(ticket_id)
        ).all()
        
        return {
            "ticket_id": ticket.freshdesk_ticket_id,
            "data": {
                "subject": ticket.subject,
                "description": ticket.description,
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "requester": {
                    "name": ticket.requester_name,
                    "email": ticket.requester_email
                }
            },
            "conversations": [
                {
                    "id": conv.freshdesk_conversation_id,
                    "body_text": conv.data.get("body_text", ""),
                    "from_email": conv.data.get("from_email", ""),
                    "created_at": conv.created_at.isoformat() if conv.created_at else None
                }
                for conv in conversations
            ],
            "ratings": [
                {
                    "created_at": rating.created_at.isoformat() if rating.created_at else None,
                    "ratings": rating.ratings,
                    "data": rating.data
                }
                for rating in ratings
            ]
        }
    
    @staticmethod
    def get_tickets_by_email(session: Session, email: str, merchant_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all tickets for a specific customer email."""
        tickets = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.requester_email == email
        ).order_by(
            FreshdeskUnifiedTicketView.created_at.desc()
        ).limit(limit).all()
        
        results = []
        for ticket in tickets:
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.subject,
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None
            })
            
        return results
    
    @staticmethod
    def get_tickets_by_rating(session: Session, rating_type: str, merchant_id: int, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get tickets with specific rating type."""
        # Build base query
        query = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.has_rating == True
        )
        
        # Filter by rating type
        if rating_type == "happy":
            query = query.filter(FreshdeskUnifiedTicketView.rating_score >= 102)
        else:  # unhappy
            query = query.filter(FreshdeskUnifiedTicketView.rating_score < 102)
        
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
    
    @staticmethod
    def get_recent_bad_csat_tickets(session: Session, merchant_id: int, days: int = 7, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent tickets with bad CSAT ratings including full context."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get bad rated tickets
        bad_tickets = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.has_rating == True,
            FreshdeskUnifiedTicketView.rating_score < 102,
            FreshdeskUnifiedTicketView.rating_created_at >= cutoff_date
        ).order_by(
            FreshdeskUnifiedTicketView.rating_created_at.desc()
        ).limit(limit).all()
        
        results = []
        for ticket in bad_tickets:
            # Get conversations for context
            conversations = session.query(FreshdeskConversation).filter(
                FreshdeskConversation.merchant_id == merchant_id,
                FreshdeskConversation.freshdesk_ticket_id == ticket.freshdesk_ticket_id
            ).order_by(FreshdeskConversation.created_at).all()
            
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "data": {
                    "subject": ticket.subject,
                    "requester": {
                        "name": ticket.requester_name,
                        "email": ticket.requester_email
                    }
                },
                "rating_score": ticket.rating_score,
                "rating_feedback": ticket.rating_feedback,
                "bad_rating_date": ticket.rating_created_at.isoformat() if ticket.rating_created_at else None,
                "rating_comment": ticket.rating_feedback,
                "conversations": [
                    {
                        "from_email": conv.data.get("from_email", ""),
                        "body_text": conv.data.get("body_text", ""),
                        "created_at": conv.created_at.isoformat() if conv.created_at else None
                    }
                    for conv in conversations
                ]
            })
            
        return results
    
    @staticmethod
    def get_rating_statistics(session: Session, merchant_id: int, days: Optional[int] = None) -> Dict[str, Any]:
        """Get rating distribution statistics."""
        # Build query
        query = session.query(
            FreshdeskUnifiedTicketView.rating_score,
            func.count(FreshdeskUnifiedTicketView.freshdesk_ticket_id)
        ).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.has_rating == True
        )
        
        # Add time filter
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(FreshdeskUnifiedTicketView.rating_created_at >= cutoff_date)
        
        # Get distribution
        rating_counts = query.group_by(FreshdeskUnifiedTicketView.rating_score).all()
        
        # Convert to dict
        distribution = {score: count for score, count in rating_counts}
        total = sum(distribution.values())
        
        return {
            "total_ratings": total,
            "distribution": distribution,
            "percentages": {
                score: round((count / total) * 100, 1) if total > 0 else 0
                for score, count in distribution.items()
            }
        }
    
    @staticmethod
    def get_csat_detail_log(merchant_id: int, target_date: date, rating_threshold: int = 102) -> Dict[str, Any]:
        """Get detailed CSAT survey data for a specific date.
        
        Args:
            merchant_id: The merchant ID to filter by (NEVER look up by name)
            target_date: The date to analyze for CSAT ratings
            rating_threshold: Ratings below this are considered negative (default 102)
            
        Returns:
            Dict containing:
                - surveys: List of detailed survey data
                - total_count: Total number of surveys
                - below_threshold_count: Count of surveys below threshold
                - avg_rating: Average rating score
        """
        with get_db_session() as session:
            # Convert date to datetime range for the target day
            start_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end_dt = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            # Get all ratings for the target date
            rated_tickets = session.query(FreshdeskUnifiedTicketView).filter(
                FreshdeskUnifiedTicketView.merchant_id == merchant_id,
                FreshdeskUnifiedTicketView.rating_created_at.between(start_dt, end_dt),
                FreshdeskUnifiedTicketView.has_rating == True
            ).all()
            
            surveys = []
            below_threshold_count = 0
            rating_sum = 0
            
            # Map Freshdesk rating scores to labels
            rating_labels = {
                103: "Extremely Happy",
                102: "Very Happy", 
                101: "Happy",
                100: "Neutral",
                -100: "Unhappy",
                -101: "Very Unhappy",
                -102: "Extremely Unhappy",
                -103: "Not Rated"
            }
            
            for ticket in rated_tickets:
                # Calculate response times
                first_response_min = None
                if ticket.first_responded_at and ticket.created_at:
                    first_response_min = round((ticket.first_responded_at - ticket.created_at).total_seconds() / 60, 1)
                
                resolution_min = None
                if ticket.resolved_at and ticket.created_at:
                    resolution_min = round((ticket.resolved_at - ticket.created_at).total_seconds() / 60, 1)
                
                # Get conversation count
                conversation_data = session.query(FreshdeskConversation.data).filter(
                    FreshdeskConversation.freshdesk_ticket_id == ticket.freshdesk_ticket_id
                ).first()
                
                # Count conversations in the JSON array
                conversation_count = len(conversation_data[0]) if conversation_data and conversation_data[0] else 0
                
                # Track below threshold ratings
                if ticket.rating_score < rating_threshold:
                    below_threshold_count += 1
                
                rating_sum += ticket.rating_score
                
                # Build survey entry
                survey_entry = {
                    "ticket_id": int(ticket.freshdesk_ticket_id),
                    "rating": ticket.rating_score,
                    "rating_label": rating_labels.get(ticket.rating_score, "Unknown"),
                    "feedback": ticket.rating_feedback or "",
                    "agent": ticket.responder_email or "unassigned",
                    "customer_email": ticket.requester_email,
                    "tags": ticket.tags or [],
                    "created_at": ticket.rating_created_at.isoformat() if ticket.rating_created_at else None,
                    "first_response_min": first_response_min,
                    "resolution_min": resolution_min,
                    "conversation_count": conversation_count
                }
                
                surveys.append(survey_entry)
            
            # Calculate average rating
            total_count = len(surveys)
            avg_rating = round(rating_sum / total_count, 1) if total_count > 0 else 0.0
            
            # Sort surveys by rating (lowest first) to highlight problem areas
            surveys.sort(key=lambda x: x["rating"])
            
            return {
                "surveys": surveys,
                "total_count": total_count,
                "below_threshold_count": below_threshold_count,
                "avg_rating": avg_rating
            }


# Legacy class name for backwards compatibility
class FreshdeskInsights(FreshdeskAnalytics):
    """Legacy alias for FreshdeskAnalytics - use FreshdeskAnalytics directly."""
    pass