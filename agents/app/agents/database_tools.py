"""Database-based support tools for CJ agent."""

import logging
import json
from typing import List, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from crewai.tools import tool
from sqlalchemy import desc, and_, func
from app.utils.supabase_util import get_db_session
from app.dbmodels.base import FreshdeskTicket, FreshdeskRating, Merchant
from app.config import settings

logger = logging.getLogger(__name__)

# Constants for Freshdesk rating values
RATING_HAPPY = 103
RATING_UNHAPPY = -103


def create_database_tools(merchant_name: str = None) -> List:
    """Create CrewAI tools that interact with the Supabase database."""

    @tool
    def get_recent_ticket_from_db() -> str:
        """Get the most recent open support ticket from the database as raw JSON data."""
        logger.info("[TOOL CALL] get_recent_ticket_from_db() - Fetching most recent open ticket from database")
        
        try:
            with get_db_session() as session:
                # Build query
                query = session.query(FreshdeskTicket)
                
                # For now, hardcode to merchant_id=1 for debugging
                query = query.filter(FreshdeskTicket.merchant_id == 1)
                logger.info("[TOOL DEBUG] Filtering for merchant_id=1")
                
                # Get ALL tickets first to see what we have
                total_count = query.count()
                logger.info(f"[TOOL DEBUG] Total tickets in DB for merchant_id=1: {total_count}")
                
                # Get the most recent 5 tickets to inspect their structure
                recent_tickets = query.order_by(FreshdeskTicket.created_at.desc()).limit(5).all()
                logger.info(f"[TOOL DEBUG] Retrieved {len(recent_tickets)} recent tickets")
                
                # Log the structure of the first ticket to understand the data format
                if recent_tickets:
                    first_ticket = recent_tickets[0]
                    logger.info(f"[TOOL DEBUG] First ticket structure:")
                    logger.info(f"  - freshdesk_ticket_id: {first_ticket.freshdesk_ticket_id}")
                    logger.info(f"  - created_at: {first_ticket.created_at}")
                    logger.info(f"  - data keys: {list(first_ticket.data.keys())}")
                    logger.info(f"  - status value: {first_ticket.data.get('status', 'NO STATUS FIELD')}")
                    logger.info(f"  - full data sample: {str(first_ticket.data)[:200]}...")
                
                # For now, just return the most recent ticket regardless of status
                tickets = recent_tickets[:1] if recent_tickets else []
                
                # Sort by Freshdesk's updated_at timestamp (inside the JSONB data field)
                # This gives us the most recently updated ticket according to Freshdesk
                sorted_tickets = sorted(
                    tickets, 
                    key=lambda t: t.data.get('created_at', ''), 
                    reverse=True
                )
                
                most_recent = sorted_tickets[0]
                
                # Build result including metadata
                result = {
                    "ticket_id": most_recent.freshdesk_ticket_id,
                    "merchant_id": most_recent.merchant_id,
                    "created_at": most_recent.created_at.isoformat() if most_recent.created_at else None,
                    "updated_at": most_recent.updated_at.isoformat() if most_recent.updated_at else None,
                    **most_recent.data  # Include all JSONB data
                }
                
                # Format as JSON
                result_json = json.dumps(result, indent=2, default=str)
                
                logger.info(f"[TOOL RESULT] get_recent_ticket_from_db() - Returned ticket {most_recent.freshdesk_ticket_id} (Freshdesk updated_at: {most_recent.data.get('updated_at', 'N/A')})")
                return f"Most recently updated open ticket from database:\n```json\n{result_json}\n```"
                
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_recent_ticket_from_db() - Error: {str(e)}")
            return f"Error fetching ticket from database: {str(e)}"

    @tool
    def get_support_dashboard_from_db() -> str:
        """Get current support queue status and key metrics from the database."""
        logger.info("[TOOL CALL] get_support_dashboard_from_db() - Fetching support dashboard from database")
        
        try:
            with get_db_session() as session:
                # Build base query
                query = session.query(FreshdeskTicket)
                
                # For now, hardcode to merchant_id=1 for debugging
                query = query.filter(FreshdeskTicket.merchant_id == 1)
                merchant_info = " (Merchant ID: 1)"
                
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
                
                # Count categories
                category_counts = {}
                
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
                    
                    # Get category
                    category = ticket.data.get('category', 'uncategorized')
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                # Sort categories by count
                trending_issues = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
                
                output = f"""📊 Support Dashboard from Database{merchant_info}:

Current Queue Status:
• Total: {total_tickets} tickets
• Open: {status_counts['open']}
• In Progress: {status_counts['in_progress']}
• Pending: {status_counts['pending']}
• Resolved: {status_counts['resolved']}
• Closed: {status_counts['closed']}

Top Issue Categories:
{chr(10).join(f'• {category}: {count} tickets' for category, count in trending_issues[:5])}

Data Source: Live database query"""
                
                logger.info(f"[TOOL RESULT] get_support_dashboard_from_db() - Returned dashboard with {total_tickets} total tickets")
                return output
                
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_support_dashboard_from_db() - Error: {str(e)}")
            return f"Error fetching dashboard from database: {str(e)}"

    @tool
    def search_tickets_in_db(query: str) -> str:
        """Search through support tickets in the database for specific issues, products, or keywords.

        Args:
            query: Search term (e.g., 'shipping delays', 'refund requests', 'product name')
        """
        logger.info(f"[TOOL CALL] search_tickets_in_db(query='{query}') - Searching for tickets in database")
        
        try:
            with get_db_session() as session:
                # Build base query
                db_query = session.query(FreshdeskTicket)
                
                # Filter by merchant if provided
                if merchant_name:
                    merchant = session.query(Merchant).filter_by(name=merchant_name).first()
                    if merchant:
                        db_query = db_query.filter(FreshdeskTicket.merchant_id == merchant.id)
                
                # Get all tickets and filter in Python (since JSONB search is complex)
                all_tickets = db_query.all()
                
                # Search in ticket data
                matching_tickets = []
                search_term = query.lower()
                
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
                        matching_tickets.append(ticket)
                
                if not matching_tickets:
                    return f"🔍 No tickets found matching '{query}' in the database."
                
                # Sort by created_at (most recent first)
                sorted_tickets = sorted(
                    matching_tickets,
                    key=lambda t: t.data.get('created_at', t.created_at.isoformat() if t.created_at else ''),
                    reverse=True
                )
                
                output = f"""🔍 Database Search Results for '{query}': {len(matching_tickets)} tickets found

Recent Tickets:"""
                
                # Show first 5 results
                for ticket in sorted_tickets[:5]:
                    ticket_data = ticket.data
                    output += f"""
• #{ticket.freshdesk_ticket_id} - {ticket_data.get('subject', 'No subject')}
  Category: {ticket_data.get('category', 'uncategorized')} | Status: {ticket_data.get('status', 'unknown')}
  Priority: {ticket_data.get('priority', 'normal')}
  Created: {ticket_data.get('created_at', ticket.created_at.isoformat() if ticket.created_at else 'unknown')}"""
                
                logger.info(f"[TOOL RESULT] search_tickets_in_db(query='{query}') - Found {len(matching_tickets)} matching tickets")
                return output
                
        except Exception as e:
            logger.error(f"[TOOL ERROR] search_tickets_in_db() - Error: {str(e)}")
            return f"Error searching tickets in database: {str(e)}"

    @tool
    def calculate_csat_score(days: int = 30) -> str:
        """Calculate Customer Satisfaction (CSAT) score for a specific time range.
        
        Args:
            days: Number of days to look back (default: 30). Use 0 for all time.
        
        Returns the CSAT score as a percentage of happy ratings (103) vs total ratings.
        Only considers the most recent rating per unique user within the time range.
        """
        # Handle both direct calls and CrewAI calls
        if isinstance(days, dict):
            days = days.get('days', 30)
        
        logger.info(f"[TOOL CALL] calculate_csat_score(days={days}) - Calculating CSAT score")
        
        try:
            with get_db_session() as session:
                # Build base query joining ratings with tickets
                query = session.query(FreshdeskRating).join(
                    FreshdeskTicket,
                    FreshdeskRating.freshdesk_ticket_id == FreshdeskTicket.freshdesk_ticket_id
                )
                
                # Filter by merchant if provided
                if merchant_name:
                    merchant = session.query(Merchant).filter_by(name=merchant_name).first()
                    if merchant:
                        query = query.filter(FreshdeskTicket.merchant_id == merchant.id)
                        merchant_info = f" for {merchant_name}"
                    else:
                        merchant_info = " (merchant not found)"
                else:
                    # For now, hardcode to merchant_id=1 for debugging
                    query = query.filter(FreshdeskTicket.merchant_id == 1)
                    merchant_info = " (Merchant ID: 1)"
                
                # Apply time filter if specified
                if days > 0:
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                    # Filter based on created_at timestamp
                    query = query.filter(FreshdeskRating.created_at >= cutoff_date)
                    time_range = f"last {days} days"
                else:
                    time_range = "all time"
                
                # Get all ratings in the time range
                all_ratings = query.all()
                logger.info(f"[TOOL DEBUG] Found {len(all_ratings)} total ratings in {time_range}")
                
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
                    return f"📊 CSAT Score{merchant_info}: No ratings found in {time_range}"
                
                csat_percentage = (happy_ratings / total_unique_ratings) * 100
                
                output = f"""📊 CSAT Score{merchant_info} ({time_range}):

**{csat_percentage:.1f}%** Customer Satisfaction

Rating Breakdown:
• Total unique customers who rated: {total_unique_ratings}
• Happy ratings (😊): {happy_ratings} ({(happy_ratings/total_unique_ratings)*100:.1f}%)
• Unhappy ratings (😞): {unhappy_ratings} ({(unhappy_ratings/total_unique_ratings)*100:.1f}%)

Note: Each customer's most recent rating is counted (no duplicates).
Data Source: Live database query from etl_freshdesk_ratings"""
                
                logger.info(f"[TOOL RESULT] calculate_csat_score() - CSAT: {csat_percentage:.1f}% from {total_unique_ratings} unique ratings")
                return output
                
        except Exception as e:
            logger.error(f"[TOOL ERROR] calculate_csat_score() - Error: {str(e)}")
            return f"Error calculating CSAT score: {str(e)}"

    # Return the tools created with @tool decorator
    tools = [
        get_recent_ticket_from_db,
        get_support_dashboard_from_db,
        search_tickets_in_db,
        calculate_csat_score,
    ]

    return tools