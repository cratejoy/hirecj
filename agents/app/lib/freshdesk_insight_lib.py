"""Freshdesk insights library for querying and analyzing Freshdesk data from the database."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from app.dbmodels.base import FreshdeskTicket, FreshdeskRating, Merchant

logger = logging.getLogger(__name__)

# Constants for Freshdesk rating values
RATING_HAPPY = 103
RATING_UNHAPPY = -103



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
        
        # Apply time filter if specified
        if start_date and end_date:
            # Ensure timezone awareness
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            # Add time to end_date to make it inclusive of the whole day
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=end_date.tzinfo)
            
            query = query.filter(
                and_(
                    FreshdeskRating.parsed_created_at >= start_date,
                    FreshdeskRating.parsed_created_at <= end_date
                )
            )
            time_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif days is not None and days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(
                FreshdeskRating.parsed_created_at >= cutoff_date
            )
            time_range = f"last {days} days"
        else:
            time_range = "all time"
        
        # Get all ratings in the time range
        all_ratings = query.all()
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
            created_at = rating.parsed_created_at
            
            # Keep only the most recent rating per user
            if user_id not in user_ratings or created_at > user_ratings[user_id]['created_at']:
                user_ratings[user_id] = {
                    'rating': rating_value,
                    'created_at': created_at,
                    'ticket_id': rating.freshdesk_ticket_id
                }
        
        # Calculate CSAT from unique user ratings
        total_unique_ratings = len(user_ratings)
        happy_ratings = sum(1 for r in user_ratings.values() if r['rating'] == RATING_HAPPY)
        unhappy_ratings = sum(1 for r in user_ratings.values() if r['rating'] == RATING_UNHAPPY)
        
        if total_unique_ratings == 0:
            csat_percentage = 0.0
        else:
            csat_percentage = (happy_ratings / total_unique_ratings) * 100
        
        return {
            "csat_percentage": csat_percentage,
            "total_unique_ratings": total_unique_ratings,
            "happy_ratings": happy_ratings,
            "unhappy_ratings": unhappy_ratings,
            "time_range": time_range,
            "merchant_info": merchant_info,
            "has_data": total_unique_ratings > 0
        }
    
    @staticmethod
    def get_ticket_by_id(session: Session, ticket_id: int, merchant_id: int = 1) -> Optional[Dict[str, Any]]:
        """
        Get a specific ticket by ID with conversations and ratings.
        
        Args:
            session: SQLAlchemy database session
            ticket_id: Freshdesk ticket ID
            merchant_id: Merchant ID to filter by (default: 1)
            
        Returns:
            Dictionary containing ticket data with conversations and ratings
        """
        logger.info(f"[INSIGHTS] Fetching ticket {ticket_id} for merchant_id={merchant_id}")
        
        # Get the ticket
        ticket = session.query(FreshdeskTicket).filter(
            and_(
                FreshdeskTicket.freshdesk_ticket_id == ticket_id,
                FreshdeskTicket.merchant_id == merchant_id
            )
        ).first()
        
        if not ticket:
            return None
        
        # Get conversations for this ticket
        from app.dbmodels.base import FreshdeskConversation
        conversations = session.query(FreshdeskConversation).filter(
            FreshdeskConversation.freshdesk_ticket_id == ticket_id
        ).order_by(FreshdeskConversation.parsed_created_at.asc()).all()
        
        # Get ratings for this ticket
        ratings = session.query(FreshdeskRating).filter(
            FreshdeskRating.freshdesk_ticket_id == ticket_id
        ).all()
        
        # Build result
        result = {
            "ticket_id": ticket.freshdesk_ticket_id,
            "merchant_id": ticket.merchant_id,
            "created_at": ticket.parsed_created_at.isoformat() if ticket.parsed_created_at else None,
            "updated_at": ticket.parsed_updated_at.isoformat() if ticket.parsed_updated_at else None,
            "data": ticket.data,
            "conversations": [
                {
                    "conversation_id": conv.freshdesk_conversation_id,
                    "created_at": conv.parsed_created_at.isoformat() if conv.parsed_created_at else None,
                    "from_email": conv.data.get('from_email'),
                    "body_text": conv.data.get('body_text'),
                    "data": conv.data
                } for conv in conversations
            ],
            "ratings": [
                {
                    "rating_id": rating.freshdesk_rating_id,
                    "created_at": rating.parsed_created_at.isoformat() if rating.parsed_created_at else None,
                    "ratings": rating.data.get('ratings', {}),
                    "data": rating.data
                } for rating in ratings
            ]
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
                             rating_type: str = "unhappy",
                             days: Optional[int] = None,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             merchant_id: int = 1) -> List[Dict[str, Any]]:
        """
        Get all tickets with a particular rating in a time range.
        
        Args:
            session: SQLAlchemy database session
            rating_type: "happy" or "unhappy"
            days: Number of days to look back
            start_date: Start date for the time range
            end_date: End date for the time range
            merchant_id: Merchant ID to filter by
            
        Returns:
            List of tickets with the specified rating
        """
        # Validate parameters
        if (start_date or end_date) and days is not None:
            raise ValueError("Cannot specify both days and date range.")
        
        logger.info(f"[INSIGHTS] Fetching {rating_type} rated tickets")
        
        # Determine rating value
        rating_value = RATING_HAPPY if rating_type == "happy" else RATING_UNHAPPY
        
        # Build base query
        query = session.query(FreshdeskRating).join(
            FreshdeskTicket,
            FreshdeskRating.freshdesk_ticket_id == FreshdeskTicket.freshdesk_ticket_id
        ).filter(
            and_(
                FreshdeskTicket.merchant_id == merchant_id,
                FreshdeskRating.parsed_rating == rating_value
            )
        )
        
        # Apply time filter
        if start_date and end_date:
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=end_date.tzinfo)
            
            query = query.filter(
                and_(
                    FreshdeskRating.parsed_created_at >= start_date,
                    FreshdeskRating.parsed_created_at <= end_date
                )
            )
        elif days is not None and days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(
                FreshdeskRating.parsed_created_at >= cutoff_date
            )
        
        # Order by rating creation date
        ratings = query.order_by(FreshdeskRating.parsed_created_at.desc()).all()
        
        # Get unique tickets
        seen_tickets = set()
        results = []
        
        for rating in ratings:
            ticket_id = rating.freshdesk_ticket_id
            if ticket_id not in seen_tickets:
                seen_tickets.add(ticket_id)
                # Get the ticket
                ticket = session.query(FreshdeskTicket).filter(
                    FreshdeskTicket.freshdesk_ticket_id == ticket_id
                ).first()
                
                if ticket:
                    results.append({
                        "ticket_id": ticket_id,
                        "subject": ticket.data.get('subject', 'No subject'),
                        "status": ticket.data.get('status'),
                        "created_at": ticket.parsed_created_at.isoformat() if ticket.parsed_created_at else None,
                        "rating_created_at": rating.parsed_created_at.isoformat() if rating.parsed_created_at else None,
                        "rating": rating_type,
                        "requester": ticket.data.get('requester', {}),
                        "data": ticket.data
                    })
        
        logger.info(f"[INSIGHTS] Found {len(results)} {rating_type} rated tickets")
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
                FreshdeskRating.parsed_rating == RATING_UNHAPPY
            )
        ).order_by(
            FreshdeskRating.parsed_created_at.desc()
        ).limit(limit).all()
        
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
                ticket_details['bad_rating_date'] = rating.parsed_created_at.isoformat() if rating.parsed_created_at else None
                ticket_details['rating_comment'] = rating.data.get('comments', {}).get('default_question')
                results.append(ticket_details)
        
        logger.info(f"[INSIGHTS] Found {len(results)} bad CSAT tickets with full context")
        return results