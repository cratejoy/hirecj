"""Freshdesk insights library for querying and analyzing Freshdesk data from the database."""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from app.dbmodels.base import FreshdeskTicket, FreshdeskRating, Merchant, FreshdeskConversation

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
        
        # Build query
        query = session.query(FreshdeskTicket).filter(FreshdeskTicket.merchant_id == merchant_id)
        
        # Get the most recent tickets by parsed_created_at
        most_recent = query.order_by(FreshdeskTicket.parsed_created_at.desc()).first()
        
        if not most_recent:
            return None
        
        # Build result including metadata
        result = {
            "ticket_id": most_recent.freshdesk_ticket_id,
            "merchant_id": most_recent.merchant_id,
            "created_at": most_recent.parsed_created_at.isoformat() if most_recent.parsed_created_at else None,
            "updated_at": most_recent.parsed_updated_at.isoformat() if most_recent.parsed_updated_at else None,
            "data": most_recent.data
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
        
        # Build base query
        query = session.query(FreshdeskTicket)
        query = query.filter(FreshdeskTicket.merchant_id == merchant_id).order_by(FreshdeskTicket.parsed_created_at.desc()).limit(500)
        
        # Get all tickets
        all_tickets = query.all()
        total_tickets = len(all_tickets)
        
        # Count by status
        status_counts = {
            'open': 0,
            'in_progress': 0,
            'resolved': 0,
            'closed': 0,
            'pending': 0
        }
        
        for ticket in all_tickets:
            # Get status (can be string or int)
            status = ticket.data.get('status', '')
            if isinstance(status, str):
                status = status.lower()
            elif isinstance(status, int):
                # Map Freshdesk status codes to string values
                # 2=Open, 3=Pending, 4=Resolved, 5=Closed
                status_map = {2: 'open', 3: 'pending', 4: 'resolved', 5: 'closed'}
                status = status_map.get(status, 'open')
            
            if status in status_counts:
                status_counts[status] += 1
            elif status in ['completed', 'done']:
                status_counts['resolved'] += 1
        
        return {
            "merchant_id": merchant_id,
            "total_tickets": total_tickets,
            "status_counts": status_counts,
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
        
        # Build base query
        db_query = session.query(FreshdeskTicket)
        
        # Filter by merchant if provided
        if merchant_name:
            merchant = session.query(Merchant).filter_by(name=merchant_name).first()
            if merchant:
                db_query = db_query.filter(FreshdeskTicket.merchant_id == merchant.id)
        else:
            # Default to merchant_id=1 for now
            db_query = db_query.filter(FreshdeskTicket.merchant_id == 1)
        
        # Get all tickets and filter in Python (since JSONB search is complex)
        all_tickets = db_query.all()
        
        # Search in ticket data
        matching_tickets = []
        search_term = search_query.lower()
        
        for ticket in all_tickets:
            ticket_data = ticket.data
            # Search in common fields
            searchable_text = ' '.join([
                str(ticket_data.get('subject', '')),
                str(ticket_data.get('description', '')),
                str(ticket_data.get('category', '')),
                str(ticket_data.get('priority', '')),
                str(ticket_data.get('tags', [])),
                str(ticket.freshdesk_ticket_id)
            ]).lower()
            
            if search_term in searchable_text:
                matching_tickets.append({
                    "ticket_id": ticket.freshdesk_ticket_id,
                    "subject": ticket_data.get('subject', 'No subject'),
                    "category": ticket_data.get('category', 'uncategorized'),
                    "status": ticket_data.get('status', 'unknown'),
                    "priority": ticket_data.get('priority', 'normal'),
                    "created_at": ticket.parsed_created_at.isoformat() if ticket.parsed_created_at else None,
                    "data": ticket_data
                })
        
        # Sort by parsed_created_at (most recent first)
        sorted_tickets = sorted(
            matching_tickets,
            key=lambda t: t['created_at'] if t['created_at'] else '',
            reverse=True
        )
        
        logger.info(f"[INSIGHTS] Found {len(matching_tickets)} matching tickets")
        return sorted_tickets
    
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
        
        # Build base query joining ratings with tickets
        query = session.query(FreshdeskRating).join(
            FreshdeskTicket,
            FreshdeskRating.freshdesk_ticket_id == FreshdeskTicket.freshdesk_ticket_id
        )
        
        # Filter by merchant
        merchant_info = None
        if merchant_name:
            merchant = session.query(Merchant).filter_by(name=merchant_name).first()
            if merchant:
                query = query.filter(FreshdeskTicket.merchant_id == merchant.id)
                merchant_info = merchant_name
            else:
                merchant_info = "merchant not found"
        else:
            # Default to merchant_id=1
            query = query.filter(FreshdeskTicket.merchant_id == 1)
            merchant_info = "Merchant ID: 1"
        
        # Note: We can't efficiently filter ratings by date without a parsed_created_at field
        # For now, we'll get all ratings and filter in Python
        if start_date and end_date:
            # Ensure timezone awareness
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            # Add time to end_date to make it inclusive of the whole day
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=end_date.tzinfo)
            time_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif days is not None and days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            time_range = f"last {days} days"
        else:
            time_range = "all time"
            start_date = None
            end_date = None
            cutoff_date = None
        
        # Get all ratings (we'll filter by date in Python)
        all_ratings_query = query.all()
        
        # Filter by date in Python if needed
        all_ratings = []
        for rating in all_ratings_query:
            created_at_str = rating.data.get('created_at')
            if not created_at_str:
                continue
                
            # Parse the timestamp
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue
                
            # Apply date filter if specified
            if start_date and end_date:
                if start_date <= created_at <= end_date:
                    all_ratings.append(rating)
            elif 'cutoff_date' in locals() and cutoff_date:
                if created_at >= cutoff_date:
                    all_ratings.append(rating)
            else:
                all_ratings.append(rating)
        
        logger.info(f"[INSIGHTS] Found {len(all_ratings)} total ratings in {time_range}")
        
        # Group by user to get most recent rating per user
        user_ratings = {}
        for rating in all_ratings:
            # Extract user_id from the JSONB data
            user_id = rating.data.get('user_id')
            if not user_id:
                continue
                
            # Get the rating value and timestamp
            rating_value = rating.data.get('ratings', {}).get('default_question')
            # Get created_at from the rating's JSONB data
            created_at_str = rating.data.get('created_at')
            if not created_at_str:
                continue
            
            # Parse the timestamp string to datetime for comparison
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue
            
            # Keep only the most recent rating per user
            if user_id not in user_ratings or created_at > user_ratings[user_id]['created_at']:
                user_ratings[user_id] = {
                    'rating': rating_value,
                    'created_at': created_at,
                    'ticket_id': rating.freshdesk_ticket_id
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
        
        # Get the ticket
        ticket = session.query(FreshdeskTicket).filter(
            and_(
                FreshdeskTicket.freshdesk_ticket_id == ticket_id_str,
                FreshdeskTicket.merchant_id == merchant_id
            )
        ).first()
        
        if not ticket:
            return None
        
        # Get conversations for this ticket
        conversations = session.query(FreshdeskConversation).filter(
            FreshdeskConversation.freshdesk_ticket_id == ticket_id_str
        ).order_by(FreshdeskConversation.parsed_created_at.asc()).all()
        
        # Get ratings for this ticket
        ratings = session.query(FreshdeskRating).filter(
            FreshdeskRating.freshdesk_ticket_id == ticket_id_str
        ).all()
        
        # Build result
        result = {
            "ticket_id": ticket.freshdesk_ticket_id,
            "merchant_id": ticket.merchant_id,
            "created_at": ticket.parsed_created_at.isoformat() if ticket.parsed_created_at else None,
            "updated_at": ticket.parsed_updated_at.isoformat() if ticket.parsed_updated_at else None,
            "data": ticket.data,
            "conversations": conversations[0].data if conversations else [],
            "ratings": [ratings[0].data] if ratings else []
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
        
        # Query tickets where requester email matches
        tickets = session.query(FreshdeskTicket).filter(
            and_(
                FreshdeskTicket.merchant_id == merchant_id,
                func.lower(FreshdeskTicket.parsed_email) == email.lower()
            )
        ).order_by(FreshdeskTicket.parsed_created_at.desc()).all()
        
        results = []
        for ticket in tickets:
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.data.get('subject', 'No subject'),
                "status": ticket.data.get('status'),
                "priority": ticket.data.get('priority'),
                "created_at": ticket.parsed_created_at.isoformat() if ticket.parsed_created_at else None,
                "requester": ticket.data.get('requester', {}),
                "data": ticket.data
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
        
        # Handle special cases for groupings
        if rating_value == "positive":
            logger.info("[INSIGHTS] Fetching tickets with positive ratings (>100)")
            rating_filter = FreshdeskRating.parsed_rating > Rating.NEUTRAL
            rating_name = "positive"
        elif rating_value == "negative":
            logger.info("[INSIGHTS] Fetching tickets with negative ratings (<100)")
            rating_filter = FreshdeskRating.parsed_rating < Rating.NEUTRAL
            rating_name = "negative"
        elif rating_value == "satisfied":
            logger.info("[INSIGHTS] Fetching tickets with satisfied CSAT ratings (103)")
            rating_filter = FreshdeskRating.parsed_rating == Rating.EXTREMELY_HAPPY
            rating_name = "satisfied"
        elif rating_value == "unsatisfied":
            logger.info("[INSIGHTS] Fetching tickets with unsatisfied CSAT ratings (<102)")
            rating_filter = FreshdeskRating.parsed_rating < Rating.VERY_HAPPY
            rating_name = "unsatisfied"
        else:
            rating_name = Rating.get_name(rating_value)
            logger.info(f"[INSIGHTS] Fetching tickets with rating {rating_value} ({rating_name})")
            rating_filter = FreshdeskRating.parsed_rating == rating_value
        
        # Build efficient query using joins and database filtering
        query = session.query(
            FreshdeskTicket,
            FreshdeskRating,
            func.cast(FreshdeskRating.data['created_at'].astext, DateTime).label('rating_created_at')
        ).join(
            FreshdeskRating,
            FreshdeskTicket.freshdesk_ticket_id == FreshdeskRating.freshdesk_ticket_id
        ).filter(
            and_(
                FreshdeskTicket.merchant_id == merchant_id,
                rating_filter
            )
        )
        
        # Apply date filters at database level
        if start_date and end_date:
            # Ensure timezone awareness
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            query = query.filter(
                func.cast(FreshdeskRating.data['created_at'].astext, DateTime).between(
                    start_date, end_date
                )
            )
        elif days is not None and days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(
                func.cast(FreshdeskRating.data['created_at'].astext, DateTime) >= cutoff_date
            )
        
        # Order by rating creation time descending
        query = query.order_by(
            func.cast(FreshdeskRating.data['created_at'].astext, DateTime).desc()
        )
        
        # Apply limit if specified
        if limit:
            query = query.limit(limit)
        
        # Execute query
        results = []
        for ticket, rating, rating_created_at in query.all():
            results.append({
                "ticket_id": ticket.freshdesk_ticket_id,
                "subject": ticket.data.get('subject', 'No subject'),
                "status": ticket.data.get('status'),
                "priority": ticket.data.get('priority'),
                "created_at": ticket.parsed_created_at.isoformat() if ticket.parsed_created_at else None,
                "rating_created_at": rating.data.get('created_at'),
                "rating_value": rating.parsed_rating,
                "rating_name": Rating.get_name(rating.parsed_rating),
                "requester": ticket.data.get('requester', {}),
                "feedback": rating.data.get('feedback'),
                "data": ticket.data
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
        
        # Get recent unhappy ratings
        bad_ratings = session.query(FreshdeskRating).join(
            FreshdeskTicket,
            FreshdeskRating.freshdesk_ticket_id == FreshdeskTicket.freshdesk_ticket_id
        ).filter(
            and_(
                FreshdeskTicket.merchant_id == merchant_id,
                FreshdeskRating.parsed_rating < Rating.VERY_HAPPY  # All unsatisfied ratings (<102)
            )
        ).all()
        
        # Sort by created_at from JSONB data and limit in Python
        ratings_with_dates = []
        for rating in bad_ratings:
            created_at_str = rating.data.get('created_at')
            if not created_at_str:
                continue
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                ratings_with_dates.append((rating, created_at))
            except (ValueError, AttributeError):
                continue
        
        # Sort by created_at descending and take the limit
        ratings_with_dates.sort(key=lambda x: x[1], reverse=True)
        bad_ratings = [r[0] for r in ratings_with_dates[:limit]]
        
        results = []
        for rating in bad_ratings:
            # Get full ticket details with conversations
            ticket_details = FreshdeskInsights.get_ticket_by_id(
                session, 
                rating.freshdesk_ticket_id, 
                merchant_id
            )
            
            if ticket_details:
                # Add rating info to the top level for easy access
                ticket_details['bad_rating_date'] = rating.data.get('created_at')
                ticket_details['rating_comment'] = rating.data.get('comments', {}).get('default_question')
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
        
        # Build base query
        query = session.query(
            FreshdeskRating.parsed_rating,
            func.count(FreshdeskRating.freshdesk_ticket_id).label('count')
        ).join(
            FreshdeskTicket,
            FreshdeskRating.freshdesk_ticket_id == FreshdeskTicket.freshdesk_ticket_id
        ).filter(
            FreshdeskTicket.merchant_id == merchant_id
        )
        
        # Apply date filters
        if start_date and end_date:
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            query = query.filter(
                func.cast(FreshdeskRating.data['created_at'].astext, DateTime).between(
                    start_date, end_date
                )
            )
        elif days is not None and days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(
                func.cast(FreshdeskRating.data['created_at'].astext, DateTime) >= cutoff_date
            )
        
        # Group by rating value
        query = query.group_by(FreshdeskRating.parsed_rating)
        
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