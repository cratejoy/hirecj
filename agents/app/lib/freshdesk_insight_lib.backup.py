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


# TODO
# - Get ticket by ID (join conversations and ratings)
# - Get ticket by email
# - Get all the tickets with a particular rating given a particular days, start, or end
# - given a filterset of tickets, 


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
        
        # Get the most recent tickets by created_at in the JSON data
        most_recent = query.order_by(FreshdeskTicket.data['created_at'].desc()).first()
        
        if not most_recent:
            return None
        
        # Build result including metadata
        result = {
            "ticket_id": most_recent.freshdesk_ticket_id,
            "merchant_id": most_recent.merchant_id,
            "created_at": most_recent.created_at.isoformat() if most_recent.created_at else None,
            "updated_at": most_recent.updated_at.isoformat() if most_recent.updated_at else None,
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
        query = query.filter(FreshdeskTicket.merchant_id == merchant_id).order_by(FreshdeskTicket.data['created_at'].desc()).limit(500)
        
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
                    "created_at": ticket_data.get('created_at'),
                    "data": ticket_data
                })
        
        # Sort by created_at (most recent first)
        sorted_tickets = sorted(
            matching_tickets,
            key=lambda t: t['created_at'],
            reverse=True
        )
        
        logger.info(f"[INSIGHTS] Found {len(matching_tickets)} matching tickets")
        return sorted_tickets
    
    @staticmethod
    def calculate_csat(session: Session, days: int = 30, merchant_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate Customer Satisfaction (CSAT) score for a specific time range.
        
        Args:
            session: SQLAlchemy database session
            days: Number of days to look back (0 for all time)
            merchant_name: Optional merchant name to filter by
            
        Returns:
            Dictionary containing CSAT data
        """
        logger.info(f"[INSIGHTS] Calculating CSAT for days={days}, merchant={merchant_name}")
        
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
        
        # Apply time filter if specified (filter by Freshdesk's created_at in JSONB data)
        if days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            # Filter using JSONB operator to query the created_at field inside the data column
            query = query.filter(
                FreshdeskRating.data['created_at'].astext >= cutoff_date.isoformat()
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
            created_at = rating.data.get('created_at', rating.created_at.isoformat() if rating.created_at else None)
            
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