"""Freshdesk insights library for querying and analyzing Freshdesk data from the database."""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func, String, or_, case
from app.dbmodels.base import Merchant
from app.dbmodels.etl_tables import FreshdeskTicket, FreshdeskRating, FreshdeskConversation, FreshdeskUnifiedTicketView

logger = logging.getLogger(__name__)

# Rating constants - raw Freshdesk values stored directly in parsed_rating field
# CSAT calculation: only 103 (Extremely Happy) counts as satisfied
# Everything under 102 is considered "unhappy" for CSAT purposes
class Rating:
    EXTREMELY_HAPPY = 103    # The only rating that counts for CSAT
    VERY_HAPPY = 102         # Not counted for CSAT
    HAPPY = 101              # Not counted for CSAT
    NEUTRAL = 100            # Not counted for CSAT
    UNHAPPY = -101           # Not counted for CSAT
    VERY_UNHAPPY = -102      # Not counted for CSAT
    EXTREMELY_UNHAPPY = -103 # Not counted for CSAT
    
    @classmethod
    def get_all_values(cls) -> List[int]:
        """Get all possible rating values."""
        return [
            cls.EXTREMELY_HAPPY,
            cls.VERY_HAPPY,
            cls.HAPPY,
            cls.NEUTRAL,
            cls.UNHAPPY,
            cls.VERY_UNHAPPY,
            cls.EXTREMELY_UNHAPPY
        ]
    
    @classmethod
    def get_name(cls, value: int) -> str:
        """Get human-readable name for a rating value."""
        names = {
            cls.EXTREMELY_HAPPY: "extremely_happy",
            cls.VERY_HAPPY: "very_happy",
            cls.HAPPY: "happy",
            cls.NEUTRAL: "neutral",
            cls.UNHAPPY: "unhappy",
            cls.VERY_UNHAPPY: "very_unhappy",
            cls.EXTREMELY_UNHAPPY: "extremely_unhappy"
        }
        return names.get(value, f"unknown_{value}")
    
    @classmethod
    def is_csat_satisfied(cls, value: int) -> bool:
        """Check if a rating counts as satisfied for CSAT calculation."""
        return value == cls.EXTREMELY_HAPPY
    
    @classmethod
    def is_csat_unsatisfied(cls, value: int) -> bool:
        """Check if a rating counts as unsatisfied for CSAT calculation."""
        return value < cls.VERY_HAPPY



class FreshdeskInsights:
    """Provides database query methods for Freshdesk data analysis."""
    
    @staticmethod
    def get_recent_ticket(session: Session, merchant_id: int = 1) -> Optional[Dict[str, Any]]:
        """
        Get the most recent open support ticket from the database.
        
        Args:
            session: SQLAlchemy database session
            merchant_id: Merchant ID to filter by (default: 1)
            
        Returns:
            Dictionary containing ticket data or None if no tickets found
        """
        logger.info(f"[INSIGHTS] Fetching most recent ticket for merchant_id={merchant_id}")
        
        # Use unified view for simpler query
        most_recent = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id
        ).order_by(FreshdeskUnifiedTicketView.created_at.desc()).first()
        
        if not most_recent:
            return None
        
        # Build result using view fields
        result = {
            "ticket_id": most_recent.freshdesk_ticket_id,
            "merchant_id": most_recent.merchant_id,
            "created_at": most_recent.created_at.isoformat() if most_recent.created_at else None,
            "updated_at": most_recent.updated_at.isoformat() if most_recent.updated_at else None,
            "subject": most_recent.subject,
            "status": most_recent.status,
            "priority": most_recent.priority,
            "requester_email": most_recent.requester_email
        }
        
        return result
    
    @staticmethod
    def get_support_dashboard(session: Session, merchant_id: int = 1) -> Dict[str, Any]:
        """
        Get support queue status and key metrics from the database.
        
        Args:
            session: SQLAlchemy database session
            merchant_id: Merchant ID to filter by (default: 1)
            
        Returns:
            Dictionary containing dashboard data
        """
        logger.info(f"[INSIGHTS] Fetching support dashboard for merchant_id={merchant_id}")
        
        # Use unified view to get ticket counts by status
        from sqlalchemy import case
        
        # Map Freshdesk status codes: 2=Open, 3=Pending, 4=Resolved, 5=Closed
        status_counts = session.query(
            func.sum(case((FreshdeskUnifiedTicketView.status == 2, 1), else_=0)).label('open'),
            func.sum(case((FreshdeskUnifiedTicketView.status == 3, 1), else_=0)).label('pending'),
            func.sum(case((FreshdeskUnifiedTicketView.status == 4, 1), else_=0)).label('resolved'),
            func.sum(case((FreshdeskUnifiedTicketView.status == 5, 1), else_=0)).label('closed'),
            func.count(FreshdeskUnifiedTicketView.freshdesk_ticket_id).label('total')
        ).filter(
            FreshdeskUnifiedTicketView.merchant_id == merchant_id
        ).first()
        
        return {
            "merchant_id": merchant_id,
            "total_tickets": status_counts.total or 0,
            "status_counts": {
                'open': status_counts.open or 0,
                'pending': status_counts.pending or 0,
                'resolved': status_counts.resolved or 0,
                'closed': status_counts.closed or 0,
                'in_progress': 0  # Freshdesk doesn't have this status
            },
        }
    
    @staticmethod
    def search_tickets(session: Session, search_query: str, merchant_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search through support tickets for specific issues, products, or keywords.
        
        Args:
            session: SQLAlchemy database session
            search_query: Search term to look for
            merchant_name: Optional merchant name to filter by
            
        Returns:
            List of matching tickets
        """
        logger.info(f"[INSIGHTS] Searching tickets for query='{search_query}', merchant={merchant_name}")
        
        # Build base query using unified view
        query = session.query(FreshdeskUnifiedTicketView)
        
        # Filter by merchant if provided
        merchant_id = 1  # Default
        if merchant_name:
            merchant = session.query(Merchant).filter_by(name=merchant_name).first()
            if merchant:
                merchant_id = merchant.id
        
        query = query.filter(FreshdeskUnifiedTicketView.merchant_id == merchant_id)
        
        # Use database search capabilities on indexed fields
        search_term = f"%{search_query}%"
        from sqlalchemy import or_
        
        query = query.filter(
            or_(
                FreshdeskUnifiedTicketView.subject.ilike(search_term),
                FreshdeskUnifiedTicketView.description_text.ilike(search_term),
                FreshdeskUnifiedTicketView.freshdesk_ticket_id.ilike(search_term),
                FreshdeskUnifiedTicketView.requester_email.ilike(search_term),
                func.cast(FreshdeskUnifiedTicketView.tags, String).ilike(search_term)
            )
        )
        
        # Order by created_at descending
        tickets = query.order_by(FreshdeskUnifiedTicketView.created_at.desc()).all()
        
        # Build results using view fields
        matching_tickets = []
        for ticket in tickets:
            matching_tickets.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.subject or 'No subject',
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "requester_email": ticket.requester_email,
                "tags": ticket.tags or []
            })
        
        logger.info(f"[INSIGHTS] Found {len(matching_tickets)} matching tickets")
        return matching_tickets
    
    @staticmethod
    def calculate_csat(session: Session, 
                      days: Optional[int] = None, 
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      merchant_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate Customer Satisfaction (CSAT) score for a specific time range.
        
        Args:
            session: SQLAlchemy database session
            days: Number of days to look back (only used if start_date and end_date are not provided)
            start_date: Start date for the time range (inclusive)
            end_date: End date for the time range (inclusive)
            merchant_name: Optional merchant name to filter by
            
        Returns:
            Dictionary containing CSAT data
        """
        # Validate parameters
        if (start_date or end_date) and days is not None:
            raise ValueError("Cannot specify both days and date range. Use either days OR start_date/end_date.")
        
        # Log parameters
        if start_date and end_date:
            logger.info(f"[INSIGHTS] Calculating CSAT from {start_date} to {end_date}, merchant={merchant_name}")
        elif days is not None:
            logger.info(f"[INSIGHTS] Calculating CSAT for days={days}, merchant={merchant_name}")
        else:
            logger.info(f"[INSIGHTS] Calculating CSAT for all time, merchant={merchant_name}")
        
        # Build base query using unified view
        query = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.has_rating == True
        )
        
        # Filter by merchant
        merchant_info = None
        merchant_id = 1  # Default
        if merchant_name:
            merchant = session.query(Merchant).filter_by(name=merchant_name).first()
            if merchant:
                merchant_id = merchant.id
                merchant_info = merchant_name
            else:
                merchant_info = "merchant not found"
        else:
            merchant_info = "Merchant ID: 1"
        
        query = query.filter(FreshdeskUnifiedTicketView.merchant_id == merchant_id)
        
        # Apply date filters using the view's rating_created_at
        if start_date and end_date:
            # Ensure timezone awareness
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            # Add time to end_date to make it inclusive of the whole day
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(
                FreshdeskUnifiedTicketView.rating_created_at.between(start_date, end_date)
            )
            time_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif days is not None and days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(
                FreshdeskUnifiedTicketView.rating_created_at >= cutoff_date
            )
            time_range = f"last {days} days"
        else:
            time_range = "all time"
        
        # Get all rated tickets
        rated_tickets = query.all()
        logger.info(f"[INSIGHTS] Found {len(rated_tickets)} total ratings in {time_range}")
        
        # Group by requester_email to get most recent rating per user
        user_ratings = {}
        for ticket in rated_tickets:
            email = ticket.requester_email
            if not email:
                continue
                
            # Keep only the most recent rating per user
            if email not in user_ratings or ticket.rating_created_at > user_ratings[email]['created_at']:
                user_ratings[email] = {
                    'rating': ticket.rating_score,
                    'created_at': ticket.rating_created_at,
                    'ticket_id': ticket.freshdesk_ticket_id
                }
        
        # Calculate CSAT from unique user ratings
        total_unique_ratings = len(user_ratings)
        # CSAT only counts 103 (Extremely Happy) as satisfied
        satisfied_ratings = sum(1 for r in user_ratings.values() if r['rating'] == Rating.EXTREMELY_HAPPY)
        # Everything under 102 is considered unsatisfied
        unsatisfied_ratings = sum(1 for r in user_ratings.values() if r['rating'] and r['rating'] < Rating.VERY_HAPPY)
        
        if total_unique_ratings == 0:
            csat_percentage = 0.0
        else:
            csat_percentage = (satisfied_ratings / total_unique_ratings) * 100
        
        return {
            "csat_percentage": csat_percentage,
            "total_unique_ratings": total_unique_ratings,
            "satisfied_ratings": satisfied_ratings,
            "unsatisfied_ratings": unsatisfied_ratings,
            "time_range": time_range,
            "merchant_info": merchant_info,
            "has_data": total_unique_ratings > 0
        }
    
    @staticmethod
    def get_ticket_by_id(session: Session, ticket_id: Union[int, str], merchant_id: int = 1) -> Optional[Dict[str, Any]]:
        """
        Get a specific ticket by ID with conversations and ratings.
        
        Args:
            session: SQLAlchemy database session
            ticket_id: Freshdesk ticket ID (can be int or string)
            merchant_id: Merchant ID to filter by (default: 1)
            
        Returns:
            Dictionary containing ticket data with conversations and ratings
        """
        logger.info(f"[INSIGHTS] Fetching ticket {ticket_id} for merchant_id={merchant_id}")
        
        # Convert ticket_id to string since it's stored as string in database
        ticket_id_str = str(ticket_id)
        
        # Get ticket from unified view
        ticket = session.query(FreshdeskUnifiedTicketView).filter(
            and_(
                FreshdeskUnifiedTicketView.freshdesk_ticket_id == ticket_id_str,
                FreshdeskUnifiedTicketView.merchant_id == merchant_id
            )
        ).first()
        
        if not ticket:
            return None
        
        # Get conversations for this ticket (still need raw table for full conversation data)
        conversation = session.query(FreshdeskConversation).filter(
            FreshdeskConversation.freshdesk_ticket_id == ticket_id_str
        ).first()
        
        # Build result using view fields
        result = {
            "ticket_id": ticket.freshdesk_ticket_id,
            "merchant_id": ticket.merchant_id,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "subject": ticket.subject,
            "description": ticket.description_text,
            "status": ticket.status,
            "priority": ticket.priority,
            "requester_name": ticket.requester_name,
            "requester_email": ticket.requester_email,
            "has_rating": ticket.has_rating,
            "rating_score": ticket.rating_score,
            "rating_feedback": ticket.rating_feedback,
            "conversations": conversation.data if conversation else [],
            "conversation_count": ticket.conversation_count or 0
        }
        
        return result
    
    @staticmethod
    def get_tickets_by_email(session: Session, email: str, merchant_id: int = 1) -> List[Dict[str, Any]]:
        """
        Get all tickets for a specific customer email.
        
        Args:
            session: SQLAlchemy database session
            email: Customer email address
            merchant_id: Merchant ID to filter by (default: 1)
            
        Returns:
            List of tickets for the customer
        """
        logger.info(f"[INSIGHTS] Fetching tickets for email {email}, merchant_id={merchant_id}")
        
        # Query tickets using unified view
        tickets = session.query(FreshdeskUnifiedTicketView).filter(
            and_(
                FreshdeskUnifiedTicketView.merchant_id == merchant_id,
                func.lower(FreshdeskUnifiedTicketView.requester_email) == email.lower()
            )
        ).order_by(FreshdeskUnifiedTicketView.created_at.desc()).all()
        
        results = []
        for ticket in tickets:
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.subject or 'No subject',
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "requester_name": ticket.requester_name,
                "requester_email": ticket.requester_email,
                "has_rating": ticket.has_rating,
                "rating_score": ticket.rating_score if ticket.has_rating else None
            })
        
        logger.info(f"[INSIGHTS] Found {len(results)} tickets for email {email}")
        return results
    
    @staticmethod
    def get_tickets_by_rating(session: Session, 
                             rating_value: Optional[int] = None,
                             rating_type: Optional[str] = None,
                             days: Optional[int] = None,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             merchant_id: int = 1,
                             limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all tickets with a particular rating in a time range.
        
        Args:
            session: SQLAlchemy database session
            rating_value: Numeric rating value (e.g., 3, -3) - takes precedence over rating_type
            rating_type: String rating type (e.g., "happy", "unhappy") - for backwards compatibility
            days: Number of days to look back
            start_date: Start date for the time range
            end_date: End date for the time range
            merchant_id: Merchant ID to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of tickets with the specified rating
        """
        # Validate parameters
        if (start_date or end_date) and days is not None:
            raise ValueError("Cannot specify both days and date range.")
        
        # Determine rating value
        if rating_value is None:
            if rating_type is None:
                raise ValueError("Must specify either rating_value or rating_type")
            # Map string types to values for backwards compatibility
            rating_map = {
                "extremely_happy": Rating.EXTREMELY_HAPPY,
                "very_happy": Rating.VERY_HAPPY,
                "happy": Rating.HAPPY,  # For backward compatibility, map to HAPPY not EXTREMELY_HAPPY
                "neutral": Rating.NEUTRAL,
                "unhappy": Rating.UNHAPPY,  # For backward compatibility, map to UNHAPPY not EXTREMELY_UNHAPPY
                "very_unhappy": Rating.VERY_UNHAPPY,
                "extremely_unhappy": Rating.EXTREMELY_UNHAPPY,
                # Also support groupings
                "positive": "positive",  # Special case - will handle below
                "negative": "negative",  # Special case - will handle below
                "satisfied": "satisfied",  # CSAT satisfied (103 only)
                "unsatisfied": "unsatisfied"  # CSAT unsatisfied (<102)
            }
            
            if rating_type not in rating_map:
                raise ValueError(f"Unknown rating_type: {rating_type}")
            
            rating_value = rating_map[rating_type]
        
        # Build query using unified view
        query = session.query(FreshdeskUnifiedTicketView).filter(
            and_(
                FreshdeskUnifiedTicketView.merchant_id == merchant_id,
                FreshdeskUnifiedTicketView.has_rating == True
            )
        )
        
        # Handle special cases for groupings
        if rating_value == "positive":
            logger.info("[INSIGHTS] Fetching tickets with positive ratings (>100)")
            query = query.filter(FreshdeskUnifiedTicketView.rating_score > Rating.NEUTRAL)
            rating_name = "positive"
        elif rating_value == "negative":
            logger.info("[INSIGHTS] Fetching tickets with negative ratings (<100)")
            query = query.filter(FreshdeskUnifiedTicketView.rating_score < Rating.NEUTRAL)
            rating_name = "negative"
        elif rating_value == "satisfied":
            logger.info("[INSIGHTS] Fetching tickets with satisfied CSAT ratings (103)")
            query = query.filter(FreshdeskUnifiedTicketView.rating_score == Rating.EXTREMELY_HAPPY)
            rating_name = "satisfied"
        elif rating_value == "unsatisfied":
            logger.info("[INSIGHTS] Fetching tickets with unsatisfied CSAT ratings (<102)")
            query = query.filter(FreshdeskUnifiedTicketView.rating_score < Rating.VERY_HAPPY)
            rating_name = "unsatisfied"
        else:
            rating_name = Rating.get_name(rating_value)
            logger.info(f"[INSIGHTS] Fetching tickets with rating {rating_value} ({rating_name})")
            query = query.filter(FreshdeskUnifiedTicketView.rating_score == rating_value)
        
        # Apply date filters using view's rating_created_at
        if start_date and end_date:
            # Ensure timezone awareness
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            query = query.filter(
                FreshdeskUnifiedTicketView.rating_created_at.between(start_date, end_date)
            )
        elif days is not None and days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(
                FreshdeskUnifiedTicketView.rating_created_at >= cutoff_date
            )
        
        # Order by rating creation time descending
        query = query.order_by(FreshdeskUnifiedTicketView.rating_created_at.desc())
        
        # Apply limit if specified
        if limit:
            query = query.limit(limit)
        
        # Execute query and build results
        results = []
        for ticket in query.all():
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.subject or 'No subject',
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "rating_created_at": ticket.rating_created_at.isoformat() if ticket.rating_created_at else None,
                "rating_value": ticket.rating_score,
                "rating_name": Rating.get_name(ticket.rating_score),
                "requester_name": ticket.requester_name,
                "requester_email": ticket.requester_email,
                "feedback": ticket.rating_feedback
            })
        
        logger.info(f"[INSIGHTS] Found {len(results)} tickets with rating {rating_value} ({rating_name})")
        return results
    
    @staticmethod
    def get_recent_bad_csat_tickets(session: Session, 
                                   limit: int = 10,
                                   merchant_id: int = 1) -> List[Dict[str, Any]]:
        """
        Get the N most recent tickets with bad CSAT ratings, including conversations and ratings.
        
        Args:
            session: SQLAlchemy database session
            limit: Maximum number of tickets to return (default: 10)
            merchant_id: Merchant ID to filter by
            
        Returns:
            List of tickets with bad ratings, including full context
        """
        logger.info(f"[INSIGHTS] Fetching {limit} most recent bad CSAT tickets")
        
        # Use unified view to get recent bad CSAT tickets efficiently
        bad_tickets = session.query(FreshdeskUnifiedTicketView).filter(
            and_(
                FreshdeskUnifiedTicketView.merchant_id == merchant_id,
                FreshdeskUnifiedTicketView.has_rating == True,
                FreshdeskUnifiedTicketView.rating_score < Rating.VERY_HAPPY  # All unsatisfied ratings (<102)
            )
        ).order_by(
            FreshdeskUnifiedTicketView.rating_created_at.desc()
        ).limit(limit).all()
        
        results = []
        for ticket in bad_tickets:
            # Get full ticket details with conversations
            ticket_details = FreshdeskInsights.get_ticket_by_id(
                session, 
                ticket.freshdesk_ticket_id, 
                merchant_id
            )
            
            if ticket_details:
                # Add rating info to the top level for easy access
                ticket_details['bad_rating_date'] = ticket.rating_created_at.isoformat() if ticket.rating_created_at else None
                ticket_details['rating_comment'] = ticket.rating_feedback
                results.append(ticket_details)
        
        logger.info(f"[INSIGHTS] Found {len(results)} bad CSAT tickets with full context")
        return results
    
    @staticmethod
    def get_rating_statistics(session: Session,
                             days: Optional[int] = None,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             merchant_id: int = 1) -> Dict[str, Any]:
        """
        Get rating statistics for all rating types in a time range.
        
        Args:
            session: SQLAlchemy database session
            days: Number of days to look back
            start_date: Start date for the time range
            end_date: End date for the time range
            merchant_id: Merchant ID to filter by
            
        Returns:
            Dictionary with rating statistics including counts and percentages
        """
        # Validate parameters
        if (start_date or end_date) and days is not None:
            raise ValueError("Cannot specify both days and date range.")
        
        logger.info("[INSIGHTS] Calculating rating statistics")
        
        # Build base query using unified view
        query = session.query(
            FreshdeskUnifiedTicketView.rating_score,
            func.count(FreshdeskUnifiedTicketView.freshdesk_ticket_id).label('count')
        ).filter(
            and_(
                FreshdeskUnifiedTicketView.merchant_id == merchant_id,
                FreshdeskUnifiedTicketView.has_rating == True
            )
        )
        
        # Apply date filters
        if start_date and end_date:
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            query = query.filter(
                FreshdeskUnifiedTicketView.rating_created_at.between(start_date, end_date)
            )
        elif days is not None and days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(
                FreshdeskUnifiedTicketView.rating_created_at >= cutoff_date
            )
        
        # Group by rating score
        query = query.group_by(FreshdeskUnifiedTicketView.rating_score)
        
        # Execute query and build results
        stats = {
            "total_ratings": 0,
            "by_rating": {},
            "csat_percentage": 0.0,
            "period": {
                "days": days,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
        
        satisfied_count = 0
        for rating_value, count in query.all():
            if rating_value is not None:
                rating_name = Rating.get_name(rating_value)
                stats["by_rating"][rating_name] = {
                    "value": rating_value,
                    "count": count,
                    "percentage": 0.0  # Will calculate after
                }
                stats["total_ratings"] += count
                
                # Only count 103 (Extremely Happy) for CSAT
                if rating_value == Rating.EXTREMELY_HAPPY:
                    satisfied_count = count
        
        # Calculate percentages
        if stats["total_ratings"] > 0:
            for rating_name, rating_data in stats["by_rating"].items():
                rating_data["percentage"] = round(
                    (rating_data["count"] / stats["total_ratings"]) * 100, 2
                )
            
            # CSAT percentage is only 103 ratings / total ratings
            stats["csat_percentage"] = round((satisfied_count / stats["total_ratings"]) * 100, 2)
        
        logger.info(f"[INSIGHTS] Rating statistics: {stats['total_ratings']} total, "
                   f"CSAT: {stats['csat_percentage']}%")
        
        return stats