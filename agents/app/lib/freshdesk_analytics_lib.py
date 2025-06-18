"""Freshdesk Analytics Library

This library provides comprehensive analytics functions for support team metrics,
designed to power the support_daily workflow with actionable insights.
"""

from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import func, and_, or_, case, distinct
from sqlalchemy.orm import Session

from app.dbmodels.view_models import FreshdeskUnifiedTicketView
from app.utils.supabase_util import get_db_session
from app.config import logger


class FreshdeskAnalytics:
    """Analytics engine for Freshdesk support metrics."""
    
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
                - avg_csat: Average CSAT score (1-5 scale conversion)
                - bad_csat_count: Count of ratings ≤3 (on 1-5 scale)
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
        def calculate_median(values: List[float]) -> Optional[float]:
            if not values:
                return None
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
                "median_first_response_min": round(median_first_response_min, 1) if median_first_response_min is not None else None,
                "median_resolution_min": round(median_resolution_min, 1) if median_resolution_min is not None else None,
                "quick_close_count": quick_close_count,
                "new_csat_count": new_csat_count,
                "csat_percentage": round(csat_percentage, 1),
                "bad_csat_count": bad_csat_count,
                "sla_breaches": sla_breaches
            }


    @staticmethod
    def get_recent_ticket(session: Session, merchant_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent open ticket with conversation history."""
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
            },
            "conversation_count": ticket.conversation_count,
            "has_agent_response": ticket.has_agent_response,
            "conversation": ticket.conversation
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
        # Search in subject, description, customer name, email, and tags
        tickets = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            or_(
                FreshdeskUnifiedTicketView.subject.ilike(f"%{query}%"),
                FreshdeskUnifiedTicketView.description.ilike(f"%{query}%"),
                FreshdeskUnifiedTicketView.requester_email.ilike(f"%{query}%"),
                FreshdeskUnifiedTicketView.requester_name.ilike(f"%{query}%"),
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
                "requester_email": ticket.requester_email,
                "customer_name": ticket.requester_name
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
        """Get detailed ticket information from the unified view."""
        # Get ticket from unified view
        ticket = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.freshdesk_ticket_id == str(ticket_id)
        ).first()
        
        if not ticket:
            return None
        
        return {
            "ticket_id": ticket.freshdesk_ticket_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "requester_name": ticket.requester_name,
            "requester_email": ticket.requester_email,
            "conversation": ticket.conversation,  # Formatted conversation from view
            "conversation_count": ticket.conversation_count,
            "has_agent_response": ticket.has_agent_response,
            "has_rating": ticket.has_rating,
            "rating_score": ticket.rating_score,
            "rating_feedback": ticket.rating_feedback,
            "rating_created_at": ticket.rating_created_at.isoformat() if ticket.rating_created_at else None
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
        
        # Get bad rated tickets from unified view
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
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.subject,
                "requester_name": ticket.requester_name,
                "requester_email": ticket.requester_email,
                "rating_score": ticket.rating_score,
                "rating_feedback": ticket.rating_feedback,
                "bad_rating_date": ticket.rating_created_at.isoformat() if ticket.rating_created_at else None,
                "conversation": ticket.conversation
            })
            
        return results
    
    @staticmethod
    def get_recent_tickets_with_conversations(session: Session, merchant_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most recent tickets with full conversation history for systemic issue analysis.
        
        Args:
            session: Database session
            merchant_id: Merchant ID
            limit: Number of tickets to return (default 50)
            
        Returns:
            List of tickets with all fields including conversation
        """
        tickets = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id
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
                "type": ticket.type,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "requester_name": ticket.requester_name,
                "requester_email": ticket.requester_email,
                "tags": ticket.tags or [],
                "conversation": ticket.conversation,
                "has_rating": ticket.has_rating,
                "rating_score": ticket.rating_score,
                "rating_feedback": ticket.rating_feedback,
                "first_responded_at": ticket.first_responded_at.isoformat() if ticket.first_responded_at else None,
                "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                "is_escalated": ticket.is_escalated,
                "conversation_count": ticket.conversation_count
            })
            
        return results
    
    @staticmethod
    def get_recent_tickets_for_review(
        session: Session, 
        merchant_id: int, 
        limit: int = 20,
        cursor: Optional[str] = None,
        status_filter: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Get recent support tickets with cursor-based pagination for manual review.
        
        Args:
            session: Database session
            merchant_id: Merchant ID
            limit: Number of tickets per page (default 20, max 100)
            cursor: Pagination cursor (ticket_id from previous page)
            status_filter: Optional list of status codes to filter by
            
        Returns:
            Dict containing:
            - tickets: List of ticket data with conversations
            - has_more: Boolean indicating if more results exist
            - next_cursor: Ticket ID to use for next page (if has_more)
            - date_range: Dict with oldest and newest ticket dates
        """
        # Enforce limit
        limit = min(limit, 100)
        
        # Build base query
        query = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id
        )
        
        # Apply status filter if provided
        if status_filter:
            query = query.filter(FreshdeskUnifiedTicketView.status.in_(status_filter))
        
        # Apply cursor filter if provided
        if cursor:
            # Get the cursor ticket to find its created_at
            cursor_ticket = session.query(
                FreshdeskUnifiedTicketView.created_at,
                FreshdeskUnifiedTicketView.freshdesk_ticket_id
            ).filter(
                FreshdeskUnifiedTicketView.freshdesk_ticket_id == cursor,
                FreshdeskUnifiedTicketView.merchant_id == merchant_id
            ).first()
            
            if cursor_ticket:
                # Use tuple comparison for stable pagination
                query = query.filter(
                    or_(
                        FreshdeskUnifiedTicketView.created_at < cursor_ticket.created_at,
                        and_(
                            FreshdeskUnifiedTicketView.created_at == cursor_ticket.created_at,
                            FreshdeskUnifiedTicketView.freshdesk_ticket_id < cursor_ticket.freshdesk_ticket_id
                        )
                    )
                )
        
        # Order by created_at DESC, ticket_id DESC for stable ordering
        query = query.order_by(
            FreshdeskUnifiedTicketView.created_at.desc(),
            FreshdeskUnifiedTicketView.freshdesk_ticket_id.desc()
        )
        
        # Fetch limit + 1 to check if more exist
        tickets = query.limit(limit + 1).all()
        
        # Check if we have more results
        has_more = len(tickets) > limit
        if has_more:
            tickets = tickets[:limit]  # Remove the extra ticket
        
        # Format results
        results = []
        for ticket in tickets:
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.subject,
                "status": ticket.status,
                "priority": ticket.priority,
                "type": ticket.type,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "requester_name": ticket.requester_name,
                "requester_email": ticket.requester_email,
                "tags": ticket.tags or [],
                "conversation": ticket.conversation,
                "has_rating": ticket.has_rating,
                "rating_score": ticket.rating_score,
                "rating_feedback": ticket.rating_feedback,
                "first_responded_at": ticket.first_responded_at.isoformat() if ticket.first_responded_at else None,
                "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                "is_escalated": ticket.is_escalated,
                "conversation_count": ticket.conversation_count
            })
        
        # Determine date range
        date_range = None
        if results:
            date_range = {
                "oldest": results[-1]["created_at"],
                "newest": results[0]["created_at"]
            }
        
        # Build response
        response = {
            "tickets": results,
            "has_more": has_more,
            "date_range": date_range
        }
        
        # Add next cursor if there are more results
        if has_more and results:
            response["next_cursor"] = results[-1]["ticket_id"]
        
        return response
    
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
    def get_csat_detail_log(session: Session, merchant_id: int, target_date: date, rating_threshold: int = 102, include_conversations: bool = False) -> Dict[str, Any]:
        """Get detailed CSAT survey data for a specific date.
        
        Args:
            session: SQLAlchemy session for database queries
            merchant_id: The merchant ID to filter by (NEVER look up by name)
            target_date: The date to analyze for CSAT ratings
            rating_threshold: Ratings below this are considered negative (default 102)
            include_conversations: If True, includes formatted conversation history for negative ratings
            
        Returns:
            Dict containing:
                - surveys: List of detailed survey data
                - total_count: Total number of surveys
                - below_threshold_count: Count of surveys below threshold
                - avg_rating: Average rating score
        """
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
            
            # Get conversation count (already in the view)
            conversation_count = ticket.conversation_count
            
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
                "agent": f"Agent {ticket.responder_id}" if ticket.responder_id else "unassigned",
                "customer_email": ticket.requester_email,
                "tags": ticket.tags or [],
                "created_at": ticket.rating_created_at.isoformat() if ticket.rating_created_at else None,
                "first_response_min": first_response_min,
                "resolution_min": resolution_min,
                "conversation_count": conversation_count
            }
            
            # Add conversation if requested and rating is below threshold
            if include_conversations and ticket.rating_score < rating_threshold:
                # Use the embedded conversation property - no additional query needed!
                survey_entry["conversation"] = ticket.conversation
            
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
    
    @staticmethod
    def get_sla_exceptions(session: Session, merchant_id: int, sla_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get tickets breaching response/resolution SLAs with pattern detection.
        
        Args:
            session: SQLAlchemy session for database queries
            merchant_id: The merchant ID to filter by
            sla_config: SLA configuration with thresholds (optional, uses defaults if not provided)
                - first_response_min: First response SLA in minutes (default: 60)
                - resolution_min: Resolution SLA in minutes (default: 1440/24hrs)
                - business_hours_only: Whether to calculate only business hours (default: False)
                - include_pending: Whether to include pending tickets in resolution breaches (default: True)
                
        Returns:
            Dict containing:
                - sla_config: Applied SLA configuration
                - breaches: First response and resolution SLA breaches
                - summary: Statistical summary of breaches
                - patterns: Common patterns in breaches
        """
        # Default SLA configuration
        default_config = {
            "first_response_min": 60,      # 1 hour
            "resolution_min": 1440,         # 24 hours
            "business_hours_only": False,   # Not implemented yet
            "include_pending": True         # Include pending tickets in resolution checks
        }
        
        # Merge with provided config
        if sla_config:
            config = {**default_config, **sla_config}
        else:
            config = default_config
        
        # Get all tickets for merchant
        all_tickets = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id
        ).all()
        
        # Track breaches
        response_breaches = []
        resolution_breaches = []
        
        # Analyze each ticket
        for ticket in all_tickets:
            # Check first response SLA
            if ticket.created_at and ticket.first_responded_at:
                response_time_min = (ticket.first_responded_at - ticket.created_at).total_seconds() / 60
                if response_time_min > config["first_response_min"]:
                    breach_by_min = response_time_min - config["first_response_min"]
                    response_breaches.append({
                        "ticket_id": ticket.freshdesk_ticket_id,
                        "subject": ticket.subject,
                        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                        "first_responded_at": ticket.first_responded_at.isoformat() if ticket.first_responded_at else None,
                        "response_time_min": round(response_time_min, 1),
                        "breach_by_min": round(breach_by_min, 1),
                        "status": ticket.status,
                        "priority": ticket.priority,
                        "tags": ticket.tags or [],
                        "fr_escalated": ticket.fr_escalated  # Check if marked as escalated
                    })
            elif ticket.created_at and not ticket.first_responded_at and ticket.status in [2, 3, 6]:  # Open, Pending, Waiting
                # No response yet - check if overdue
                time_since_created = (datetime.utcnow().replace(tzinfo=timezone.utc) - ticket.created_at).total_seconds() / 60
                if time_since_created > config["first_response_min"]:
                    response_breaches.append({
                        "ticket_id": ticket.freshdesk_ticket_id,
                        "subject": ticket.subject,
                        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                        "first_responded_at": None,
                        "response_time_min": None,
                        "breach_by_min": round(time_since_created - config["first_response_min"], 1),
                        "status": ticket.status,
                        "priority": ticket.priority,
                        "tags": ticket.tags or [],
                        "fr_escalated": ticket.fr_escalated,
                        "no_response": True
                    })
            
            # Check resolution SLA
            check_resolution = False
            if ticket.status in [4, 5]:  # Resolved or Closed
                check_resolution = True
            elif config["include_pending"] and ticket.status in [2, 3, 6]:  # Open, Pending, Waiting
                check_resolution = True
            
            if check_resolution and ticket.created_at:
                if ticket.resolved_at:
                    resolution_time_min = (ticket.resolved_at - ticket.created_at).total_seconds() / 60
                else:
                    # Still open - calculate time since creation
                    resolution_time_min = (datetime.utcnow().replace(tzinfo=timezone.utc) - ticket.created_at).total_seconds() / 60
                
                if resolution_time_min > config["resolution_min"]:
                    breach_by_min = resolution_time_min - config["resolution_min"]
                    resolution_breaches.append({
                        "ticket_id": ticket.freshdesk_ticket_id,
                        "subject": ticket.subject,
                        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                        "resolution_time_min": round(resolution_time_min, 1),
                        "breach_by_min": round(breach_by_min, 1),
                        "status": ticket.status,
                        "priority": ticket.priority,
                        "assigned_agent": ticket.responder_id,
                        "tags": ticket.tags or [],
                        "is_escalated": ticket.is_escalated,
                        "still_open": ticket.status not in [4, 5]
                    })
        
        # Analyze patterns in breaches
        patterns = {
            "response": {},
            "resolution": {}
        }
        
        # Pattern: By priority
        for breach in response_breaches:
            priority = breach.get("priority", "unknown")
            if priority not in patterns["response"]:
                patterns["response"][priority] = {"count": 0, "avg_breach_min": 0}
            patterns["response"][priority]["count"] += 1
            patterns["response"][priority]["avg_breach_min"] += breach["breach_by_min"]
        
        for breach in resolution_breaches:
            priority = breach.get("priority", "unknown")
            if priority not in patterns["resolution"]:
                patterns["resolution"][priority] = {"count": 0, "avg_breach_min": 0}
            patterns["resolution"][priority]["count"] += 1
            patterns["resolution"][priority]["avg_breach_min"] += breach["breach_by_min"]
        
        # Calculate averages
        for pattern_type in patterns:
            for priority in patterns[pattern_type]:
                count = patterns[pattern_type][priority]["count"]
                if count > 0:
                    patterns[pattern_type][priority]["avg_breach_min"] = round(
                        patterns[pattern_type][priority]["avg_breach_min"] / count, 1
                    )
        
        # Tag analysis for top breach reasons
        tag_counts = {}
        for breach in response_breaches + resolution_breaches:
            for tag in breach.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "sla_config": config,
            "breaches": {
                "first_response": sorted(response_breaches, key=lambda x: x["breach_by_min"], reverse=True),
                "resolution": sorted(resolution_breaches, key=lambda x: x["breach_by_min"], reverse=True)
            },
            "summary": {
                "total_breaches": len(response_breaches) + len(resolution_breaches),
                "response_breaches": len(response_breaches),
                "resolution_breaches": len(resolution_breaches),
                "avg_response_breach_min": round(sum(b["breach_by_min"] for b in response_breaches) / len(response_breaches), 1) if response_breaches else 0,
                "avg_resolution_breach_min": round(sum(b["breach_by_min"] for b in resolution_breaches) / len(resolution_breaches), 1) if resolution_breaches else 0,
                "no_response_count": sum(1 for b in response_breaches if b.get("no_response", False))
            },
            "patterns": {
                "by_priority": patterns,
                "top_breach_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
                "insights": []
            }
        }
    
    @staticmethod
    def get_open_ticket_distribution(session: Session, merchant_id: int) -> Dict[str, Any]:
        """Get distribution of open tickets by age and identify oldest tickets.
        
        Args:
            session: SQLAlchemy session for database queries
            merchant_id: The merchant ID to filter by (NEVER look up by name)
            
        Returns:
            Dict containing:
                - age_buckets: Distribution of tickets by age ranges
                - total_open: Total number of open tickets
                - oldest_tickets: Details of the 10 oldest open tickets
        """
        # Get current time for age calculations
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Query all open tickets (statuses: Open, Pending, Waiting on Customer, Waiting on Third Party)
        open_tickets = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id,
            FreshdeskUnifiedTicketView.status.in_([2, 3, 6, 7])  # Open statuses
        ).all()
        
        # Initialize age buckets
        age_buckets = {
            "0-4h": {"count": 0, "tickets": []},
            "4-24h": {"count": 0, "tickets": []},
            "1-2d": {"count": 0, "tickets": []},
            "3-7d": {"count": 0, "tickets": []},
            ">7d": {"count": 0, "tickets": []},
        }
        
        # Categorize tickets by age
        for ticket in open_tickets:
                if ticket.created_at:
                    # Ensure created_at has timezone info
                    created_at = ticket.created_at
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    
                    age = now - created_at
                    age_hours = age.total_seconds() / 3600
                    
                    # Determine bucket
                    if age_hours <= 4:
                        bucket = "0-4h"
                    elif age_hours <= 24:
                        bucket = "4-24h"
                    elif age_hours <= 48:
                        bucket = "1-2d"
                    elif age_hours <= 168:  # 7 days
                        bucket = "3-7d"
                    else:
                        bucket = ">7d"
                    
                    age_buckets[bucket]["count"] += 1
                    age_buckets[bucket]["tickets"].append({
                        "ticket": ticket,
                        "age_hours": age_hours
                    })
        
        total_open = len(open_tickets)
        
        # Calculate percentages and remove ticket objects from response
        for bucket in age_buckets:
                count = age_buckets[bucket]["count"]
                age_buckets[bucket] = {
                    "count": count,
                    "percentage": round((count / total_open * 100) if total_open > 0 else 0, 1)
                }
        
        # Get the 10 oldest tickets with details
        oldest_tickets = []
        all_tickets_with_age = []
        
        for ticket in open_tickets:
                if ticket.created_at:
                    created_at = ticket.created_at
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    
                    age = now - created_at
                    age_hours = age.total_seconds() / 3600
                    
                    all_tickets_with_age.append({
                        "ticket": ticket,
                        "age_hours": age_hours
                    })
        
        # Sort by age and get oldest 10
        all_tickets_with_age.sort(key=lambda x: x["age_hours"], reverse=True)
        
        for item in all_tickets_with_age[:10]:
                ticket = item["ticket"]
                age_hours = item["age_hours"]
                
                # Format age display
                if age_hours < 1:
                    age_display = f"{int(age_hours * 60)}m"
                elif age_hours < 24:
                    age_display = f"{int(age_hours)}h {int((age_hours % 1) * 60)}m"
                elif age_hours < 168:  # Less than 7 days
                    days = int(age_hours / 24)
                    hours = int(age_hours % 24)
                    if hours > 0:
                        age_display = f"{days}d {hours}h"
                    else:
                        age_display = f"{days}d"
                else:
                    days = int(age_hours / 24)
                    age_display = f"{days}d"
                
                # Map status codes to names
                status_names = {
                    2: "Open",
                    3: "Pending",
                    6: "Waiting on Customer",
                    7: "Waiting on Third Party"
                }
                
                oldest_tickets.append({
                    "ticket_id": int(ticket.freshdesk_ticket_id),
                    "subject": ticket.subject or "No subject",
                    "age_hours": round(age_hours, 1),
                    "age_display": age_display,
                    "status": status_names.get(ticket.status, f"Status {ticket.status}"),
                    "priority": ticket.priority,
                    "tags": ticket.tags or [],
                    "customer_email": ticket.requester_email,
                    "last_updated": ticket.updated_at.isoformat() if ticket.updated_at else None
                })
        
        return {
            "age_buckets": age_buckets,
            "total_open": total_open,
            "oldest_tickets": oldest_tickets
        }
    
    @staticmethod
    def get_response_time_metrics(session: Session, merchant_id: int, date_range: Dict[str, date]) -> Dict[str, Any]:
        """Get detailed response and resolution time metrics with statistical analysis.
        
        Args:
        session: SQLAlchemy session for database queries
        merchant_id: The merchant ID to filter by (NEVER look up by name)
        date_range: Dict with 'start_date' and 'end_date' keys
        
        Returns:
        Dict containing:
                - first_response: Statistical breakdown of first response times
                - resolution: Statistical breakdown of resolution times
                - quick_resolutions: Tickets resolved in various time buckets
                - total_resolved: Total number of resolved tickets
                - csat_by_speed: CSAT correlation with response/resolution speed
        """
        import numpy as np
        
        # Convert dates to datetime for filtering
        start_dt = datetime.combine(date_range['start_date'], datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(date_range['end_date'], datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Get all tickets created in the date range
        tickets = session.query(FreshdeskUnifiedTicketView).filter(
        FreshdeskUnifiedTicketView.merchant_id == merchant_id,
        FreshdeskUnifiedTicketView.created_at.between(start_dt, end_dt)
        ).all()
        
        # Collect response and resolution times
        first_response_times = []
        resolution_times = []
        tickets_with_times = []
        
        for ticket in tickets:
                ticket_data = {
                    'ticket_id': int(ticket.freshdesk_ticket_id),
                    'has_rating': ticket.has_rating,
                    'rating_score': ticket.rating_score if ticket.has_rating else None
                }
                
                # First response time
                if ticket.first_responded_at and ticket.created_at:
                    response_min = (ticket.first_responded_at - ticket.created_at).total_seconds() / 60
                    if response_min >= 0:  # Sanity check
                        first_response_times.append(response_min)
                        ticket_data['first_response_min'] = response_min
                
                # Resolution time
                if ticket.resolved_at and ticket.created_at:
                    resolution_min = (ticket.resolved_at - ticket.created_at).total_seconds() / 60
                    if resolution_min >= 0:  # Sanity check
                        resolution_times.append(resolution_min)
                        ticket_data['resolution_min'] = resolution_min
                
                if 'first_response_min' in ticket_data or 'resolution_min' in ticket_data:
                    tickets_with_times.append(ticket_data)
        
        # Calculate statistics for first response
        first_response_stats = {}
        if first_response_times:
                fr_array = np.array(first_response_times)
                first_response_stats = {
                    'median_min': float(np.median(fr_array)),
                    'mean_min': float(np.mean(fr_array)),
                    'p25_min': float(np.percentile(fr_array, 25)),
                    'p75_min': float(np.percentile(fr_array, 75)),
                    'p95_min': float(np.percentile(fr_array, 95)),
                    'outliers': []
                }
                
                # Find outliers (>2 standard deviations from mean)
                mean = np.mean(fr_array)
                std = np.std(fr_array)
                outlier_threshold = mean + (2 * std)
                
                for i, time_val in enumerate(first_response_times):
                    if time_val > outlier_threshold:
                        # Find the corresponding ticket
                        for ticket_data in tickets_with_times:
                            if ticket_data.get('first_response_min') == time_val:
                                first_response_stats['outliers'].append({
                                    'ticket_id': ticket_data['ticket_id'],
                                    'response_min': round(time_val, 1)
                                })
                                break
        
        # Calculate statistics for resolution
        resolution_stats = {}
        if resolution_times:
                res_array = np.array(resolution_times)
                resolution_stats = {
                    'median_min': float(np.median(res_array)),
                    'mean_min': float(np.mean(res_array)),
                    'p25_min': float(np.percentile(res_array, 25)),
                    'p75_min': float(np.percentile(res_array, 75)),
                    'p95_min': float(np.percentile(res_array, 95)),
                    'outliers': []
                }
                
                # Find outliers
                mean = np.mean(res_array)
                std = np.std(res_array)
                outlier_threshold = mean + (2 * std)
                
                for i, time_val in enumerate(resolution_times):
                    if time_val > outlier_threshold:
                        # Find the corresponding ticket
                        for ticket_data in tickets_with_times:
                            if ticket_data.get('resolution_min') == time_val:
                                resolution_stats['outliers'].append({
                                    'ticket_id': ticket_data['ticket_id'],
                                    'resolution_min': round(time_val, 1)
                                })
                                break
        
        # Quick resolution analysis
        quick_resolutions = {
                '<5min': {'count': 0, 'with_rating': 0, 'total_rating': 0},
                '<10min': {'count': 0, 'with_rating': 0, 'total_rating': 0},
                '<30min': {'count': 0, 'with_rating': 0, 'total_rating': 0},
                '<60min': {'count': 0, 'with_rating': 0, 'total_rating': 0}
        }
        
        total_resolved = len(resolution_times)
        
        for ticket_data in tickets_with_times:
                if 'resolution_min' in ticket_data:
                    res_time = ticket_data['resolution_min']
                    
                    # Count in appropriate buckets
                    if res_time < 5:
                        quick_resolutions['<5min']['count'] += 1
                        if ticket_data['has_rating'] and ticket_data['rating_score']:
                            quick_resolutions['<5min']['with_rating'] += 1
                            quick_resolutions['<5min']['total_rating'] += ticket_data['rating_score']
                    if res_time < 10:
                        quick_resolutions['<10min']['count'] += 1
                        if ticket_data['has_rating'] and ticket_data['rating_score']:
                            quick_resolutions['<10min']['with_rating'] += 1
                            quick_resolutions['<10min']['total_rating'] += ticket_data['rating_score']
                    if res_time < 30:
                        quick_resolutions['<30min']['count'] += 1
                        if ticket_data['has_rating'] and ticket_data['rating_score']:
                            quick_resolutions['<30min']['with_rating'] += 1
                            quick_resolutions['<30min']['total_rating'] += ticket_data['rating_score']
                    if res_time < 60:
                        quick_resolutions['<60min']['count'] += 1
                        if ticket_data['has_rating'] and ticket_data['rating_score']:
                            quick_resolutions['<60min']['with_rating'] += 1
                            quick_resolutions['<60min']['total_rating'] += ticket_data['rating_score']
        
        # Calculate percentages and average CSAT
        for bucket in quick_resolutions:
                data = quick_resolutions[bucket]
                data['percentage'] = round((data['count'] / total_resolved * 100) if total_resolved > 0 else 0, 1)
                # Convert Freshdesk rating to 1-5 scale approximation
                if data['with_rating'] > 0:
                    avg_freshdesk_rating = data['total_rating'] / data['with_rating']
                    # Map -103 to 103 scale to 1-5 scale
                    data['avg_csat'] = round(((avg_freshdesk_rating + 103) / 206) * 4 + 1, 1)
                else:
                    data['avg_csat'] = 0.0
                # Clean up temporary fields
                del data['with_rating']
                del data['total_rating']
        
        # CSAT by speed categories
        csat_by_speed = {
                'ultra_fast_<5min': {'count': 0, 'total_rating': 0},
                'fast_5-30min': {'count': 0, 'total_rating': 0},
                'normal_30-180min': {'count': 0, 'total_rating': 0},
                'slow_>180min': {'count': 0, 'total_rating': 0}
        }
        
        for ticket_data in tickets_with_times:
                if 'resolution_min' in ticket_data and ticket_data['has_rating'] and ticket_data['rating_score']:
                    res_time = ticket_data['resolution_min']
                    rating = ticket_data['rating_score']
                    
                    if res_time < 5:
                        csat_by_speed['ultra_fast_<5min']['count'] += 1
                        csat_by_speed['ultra_fast_<5min']['total_rating'] += rating
                    elif res_time < 30:
                        csat_by_speed['fast_5-30min']['count'] += 1
                        csat_by_speed['fast_5-30min']['total_rating'] += rating
                    elif res_time < 180:
                        csat_by_speed['normal_30-180min']['count'] += 1
                        csat_by_speed['normal_30-180min']['total_rating'] += rating
                    else:
                        csat_by_speed['slow_>180min']['count'] += 1
                        csat_by_speed['slow_>180min']['total_rating'] += rating
        
        # Calculate average ratings for each speed category
        for category in csat_by_speed:
                data = csat_by_speed[category]
                if data['count'] > 0:
                    data['avg_rating'] = round(data['total_rating'] / data['count'], 1)
                else:
                    data['avg_rating'] = 0.0
                del data['total_rating']
        
        return {
                'first_response': first_response_stats,
                'resolution': resolution_stats,
                'quick_resolutions': quick_resolutions,
                'total_resolved': total_resolved,
                'csat_by_speed': csat_by_speed
        }
    
    @staticmethod
    def get_volume_trends(session: Session, merchant_id: int, days: int = 60) -> Dict[str, Any]:
        """Get daily ticket volume trends with spike detection and analysis.
        
        Args:
        session: SQLAlchemy session for database queries
        merchant_id: The merchant ID to filter by (NEVER look up by name)
        days: Number of days to analyze (default 60)
        
        Returns:
        Dict containing:
                - daily_volumes: List of daily ticket counts with spike indicators
                - summary: Overall statistics including spikes and trends
                - rolling_7d_avg: 7-day rolling average for smoothing
        """
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get daily ticket counts
        daily_counts = {}
        tickets = session.query(FreshdeskUnifiedTicketView).filter(
        FreshdeskUnifiedTicketView.merchant_id == merchant_id,
        FreshdeskUnifiedTicketView.created_at >= datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        FreshdeskUnifiedTicketView.created_at <= datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        ).all()
        
        # Count tickets by day
        for ticket in tickets:
                if ticket.created_at:
                    ticket_date = ticket.created_at.date()
                    daily_counts[ticket_date] = daily_counts.get(ticket_date, 0) + 1
        
        # Fill in missing days with 0
        current = start_date
        while current <= end_date:
                if current not in daily_counts:
                    daily_counts[current] = 0
                current += timedelta(days=1)
        
        # Sort by date
        sorted_dates = sorted(daily_counts.keys())
        daily_volumes = []
        
        # Calculate statistics for spike detection
        volumes = [daily_counts[d] for d in sorted_dates]
        if volumes:
                mean_volume = sum(volumes) / len(volumes)
                # Calculate standard deviation
                variance = sum((x - mean_volume) ** 2 for x in volumes) / len(volumes)
                std_dev = variance ** 0.5
                spike_threshold = mean_volume + (2 * std_dev)  # 2σ threshold
        else:
                mean_volume = 0
                std_dev = 0
                spike_threshold = 0
        
        # Build daily volume list with spike detection
        for date_val in sorted_dates:
                count = daily_counts[date_val]
                is_spike = count > spike_threshold if spike_threshold > 0 else False
                deviation = (count - mean_volume) / std_dev if std_dev > 0 else 0
                
                daily_volumes.append({
                    "date": date_val.isoformat(),
                    "new_tickets": count,
                    "is_spike": is_spike,
                    "deviation": round(deviation, 1)
                })
        
        # Calculate 7-day rolling average
        rolling_7d_avg = []
        for i, date_val in enumerate(sorted_dates):
                # Get last 7 days including current
                start_idx = max(0, i - 6)
                window_values = volumes[start_idx:i+1]
                avg = sum(window_values) / len(window_values) if window_values else 0
                
                rolling_7d_avg.append({
                    "date": date_val.isoformat(),
                    "avg": round(avg, 1)
                })
        
        # Identify spike days
        spike_days = [
                {
                    "date": vol["date"],
                    "volume": vol["new_tickets"],
                    "deviation": vol["deviation"]
                }
                for vol in daily_volumes if vol["is_spike"]
        ]
        
        # Calculate trend (comparing first week to last week)
        if len(volumes) >= 14:
                first_week_avg = sum(volumes[:7]) / 7
                last_week_avg = sum(volumes[-7:]) / 7
                if first_week_avg > 0:
                    trend_percentage = ((last_week_avg - first_week_avg) / first_week_avg) * 100
                    if trend_percentage > 10:
                        trend = "increasing"
                    elif trend_percentage < -10:
                        trend = "decreasing"
                    else:
                        trend = "stable"
                else:
                    trend = "stable"
                    trend_percentage = 0
        else:
                trend = "insufficient_data"
                trend_percentage = 0
        
        # Find highest volume day
        max_day = None
        if daily_volumes:
                max_vol = max(daily_volumes, key=lambda x: x["new_tickets"])
                max_day = {
                    "date": max_vol["date"],
                    "volume": max_vol["new_tickets"]
                }
        
        # Find lowest volume day (excluding zeros)
        min_day = None
        non_zero_volumes = [v for v in daily_volumes if v["new_tickets"] > 0]
        if non_zero_volumes:
                min_vol = min(non_zero_volumes, key=lambda x: x["new_tickets"])
                min_day = {
                    "date": min_vol["date"],
                    "volume": min_vol["new_tickets"]
                }
        
        return {
                "daily_volumes": daily_volumes,
                "summary": {
                    "avg_daily_volume": round(mean_volume, 1),
                    "std_dev": round(std_dev, 1),
                    "spike_threshold": round(spike_threshold, 1),
                    "spike_days": spike_days,
                    "trend": trend,
                    "trend_percentage": round(trend_percentage, 1),
                    "total_tickets": sum(volumes),
                    "days_analyzed": len(volumes),
                    "highest_day": max_day,
                    "lowest_day": min_day,
                    "zero_ticket_days": len([v for v in volumes if v == 0])
                },
                "rolling_7d_avg": rolling_7d_avg
        }
    
    @staticmethod
    def get_root_cause_analysis(session: Session, merchant_id: int, date_str: str, spike_threshold: float = 2.0) -> Dict[str, Any]:
        """Analyze root causes when a spike is detected on a specific date.
        
        Args:
        session: SQLAlchemy session for database queries
        merchant_id: The merchant ID to filter by (NEVER look up by name)
        date_str: Date to analyze in YYYY-MM-DD format
        spike_threshold: Standard deviations above mean to consider a spike (default 2.0)
        
        Returns:
        Dict containing:
                - spike_detected: Whether the date had a spike
                - tag_analysis: Breakdown by tags with deltas from average
                - type_analysis: Breakdown by ticket type
                - example_tickets: Sample tickets from spike categories
                - insights: Suggested root causes
        """
        # Parse the target date
        target_date = datetime.fromisoformat(date_str).date()
        
        # Get tickets for the target date
        start_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        target_tickets = session.query(FreshdeskUnifiedTicketView).filter(
        FreshdeskUnifiedTicketView.merchant_id == merchant_id,
        FreshdeskUnifiedTicketView.created_at.between(start_dt, end_dt)
        ).all()
        
        target_count = len(target_tickets)
        
        # Get historical data for comparison (30 days before target)
        hist_start = target_date - timedelta(days=30)
        hist_end = target_date - timedelta(days=1)
        
        hist_tickets = session.query(FreshdeskUnifiedTicketView).filter(
                FreshdeskUnifiedTicketView.merchant_id == merchant_id,
                FreshdeskUnifiedTicketView.created_at >= datetime.combine(hist_start, datetime.min.time()).replace(tzinfo=timezone.utc),
                FreshdeskUnifiedTicketView.created_at < datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        ).all()
        
        # Calculate daily average and std dev from historical data
        daily_counts = {}
        for ticket in hist_tickets:
                if ticket.created_at:
                    day = ticket.created_at.date()
                    daily_counts[day] = daily_counts.get(day, 0) + 1
        
        # Fill missing days with 0
        current = hist_start
        while current < target_date:
                if current not in daily_counts:
                    daily_counts[current] = 0
                current += timedelta(days=1)
        
        volumes = list(daily_counts.values())
        if volumes:
                mean_volume = sum(volumes) / len(volumes)
                variance = sum((x - mean_volume) ** 2 for x in volumes) / len(volumes)
                std_dev = variance ** 0.5
                spike_level = mean_volume + (spike_threshold * std_dev)
        else:
                mean_volume = 0
                std_dev = 0
                spike_level = 0
        
        # Check if target date is a spike
        spike_detected = target_count > spike_level if spike_level > 0 else False
        deviation = (target_count - mean_volume) / std_dev if std_dev > 0 else 0
        
        # Analyze tags
        tag_counts_target = {}
        tag_counts_hist = {}
        
        # Count tags for target date
        for ticket in target_tickets:
                if ticket.tags:
                    for tag in ticket.tags:
                        tag_counts_target[tag] = tag_counts_target.get(tag, 0) + 1
        
        # Count tags historically (daily average)
        for ticket in hist_tickets:
                if ticket.tags:
                    for tag in ticket.tags:
                        tag_counts_hist[tag] = tag_counts_hist.get(tag, 0) + 1
        
        # Calculate daily averages for historical tags
        days_in_history = len(daily_counts)
        if days_in_history > 0:
                for tag in tag_counts_hist:
                    tag_counts_hist[tag] = tag_counts_hist[tag] / days_in_history
        
        # Analyze tag differences
        tag_analysis = []
        all_tags = set(tag_counts_target.keys()) | set(tag_counts_hist.keys())
        
        for tag in all_tags:
                target_val = tag_counts_target.get(tag, 0)
                hist_avg = tag_counts_hist.get(tag, 0)
                delta = target_val - hist_avg
                
                if target_val > 0:  # Only include tags that appeared on target date
                    percentage_increase = ((target_val - hist_avg) / hist_avg * 100) if hist_avg > 0 else float('inf')
                    
                    # Get example tickets for this tag
                    examples = []
                    for ticket in target_tickets:
                        if ticket.tags and tag in ticket.tags and len(examples) < 3:
                            examples.append({
                                "ticket_id": int(ticket.freshdesk_ticket_id),
                                "subject": ticket.subject or "No subject",
                                "created_at": ticket.created_at.isoformat() if ticket.created_at else None
                            })
                    
                    tag_analysis.append({
                        "tag": tag,
                        "today_count": target_val,
                        "avg_count": round(hist_avg, 1),
                        "delta": round(delta, 1),
                        "percentage_increase": round(percentage_increase, 1) if percentage_increase != float('inf') else 999.9,
                        "example_tickets": examples
                    })
        
        # Sort by delta (biggest increases first)
        tag_analysis.sort(key=lambda x: x["delta"], reverse=True)
        
        # Analyze ticket types
        type_counts_target = {}
        type_counts_hist = {}
        
        for ticket in target_tickets:
                ticket_type = ticket.type or "unspecified"
                type_counts_target[ticket_type] = type_counts_target.get(ticket_type, 0) + 1
        
        for ticket in hist_tickets:
                ticket_type = ticket.type or "unspecified"
                type_counts_hist[ticket_type] = type_counts_hist.get(ticket_type, 0) + 1
        
        # Calculate daily averages for types
        if days_in_history > 0:
                for ticket_type in type_counts_hist:
                    type_counts_hist[ticket_type] = type_counts_hist[ticket_type] / days_in_history
        
        # Type analysis
        type_analysis = []
        all_types = set(type_counts_target.keys()) | set(type_counts_hist.keys())
        
        for ticket_type in all_types:
                target_val = type_counts_target.get(ticket_type, 0)
                hist_avg = type_counts_hist.get(ticket_type, 0)
                
                if target_val > 0:
                    type_analysis.append({
                        "type": ticket_type,
                        "today_count": target_val,
                        "avg_count": round(hist_avg, 1),
                        "delta": round(target_val - hist_avg, 1)
                    })
        
        type_analysis.sort(key=lambda x: x["delta"], reverse=True)
        
        # Count untagged tickets
        untagged_count = sum(1 for t in target_tickets if not t.tags or len(t.tags) == 0)
        
        # Generate insights
        insights = []
        
        if spike_detected:
                # Find the most significant tag increases
                significant_tags = [t for t in tag_analysis if t["delta"] > 5 and t["percentage_increase"] > 100]
                
                if significant_tags:
                    top_tag = significant_tags[0]
                    insights.append(f"Major spike driven by '{top_tag['tag']}' issues (+{top_tag['percentage_increase']:.0f}%)")
                    
                    # Look for patterns in tag names
                    shipping_tags = [t for t in significant_tags if any(word in t["tag"].lower() for word in ["ship", "delivery", "transit", "package"])]
                    if shipping_tags:
                        insights.append("Multiple shipping-related tags suggest delivery system issues")
                    
                    payment_tags = [t for t in significant_tags if any(word in t["tag"].lower() for word in ["payment", "billing", "charge", "refund"])]
                    if payment_tags:
                        insights.append("Payment/billing issues detected - possible payment processor problems")
                
                # Check if it's a specific day pattern
                day_name = target_date.strftime("%A")
                if day_name == "Monday":
                    insights.append("Monday spike - likely weekend accumulation")
                elif day_name in ["Saturday", "Sunday"]:
                    insights.append("Weekend spike - possible promotional or system issues")
                
                # Check for holiday patterns (basic US holidays)
                if target_date.month == 5 and 25 <= target_date.day <= 31:
                    insights.append("Memorial Day period - expect shipping delays and order issues")
                elif target_date.month == 7 and 1 <= target_date.day <= 7:
                    insights.append("July 4th period - holiday shopping and shipping delays")
                elif target_date.month == 11 and 20 <= target_date.day <= 30:
                    insights.append("Black Friday/Cyber Monday period - peak shopping volume")
        else:
                insights.append("No significant spike detected on this date")
        
        return {
                "spike_detected": spike_detected,
                "date": target_date.isoformat(),
                "total_tickets": target_count,
                "normal_range": [round(mean_volume - 2*std_dev, 1), round(mean_volume + 2*std_dev, 1)],
                "deviation": round(deviation, 1),
                "tag_analysis": tag_analysis[:10],  # Top 10 tags
                "type_analysis": type_analysis,
                "untagged_count": untagged_count,
                "insights": insights,
                "historical_avg": round(mean_volume, 1),
                "historical_std": round(std_dev, 1)
        }


