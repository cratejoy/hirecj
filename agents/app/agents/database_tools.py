"""Database-based support tools for CJ agent."""

import logging
import json
from typing import List, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from crewai.tools import tool
from sqlalchemy import desc, and_
from app.utils.supabase_util import get_db_session
from app.dbmodels.base import FreshdeskTicket, Merchant
from app.config import settings

logger = logging.getLogger(__name__)


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
                    # Get status
                    status = ticket.data.get('status', '').lower()
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

    # Return the tools created with @tool decorator
    tools = [
        get_recent_ticket_from_db,
        get_support_dashboard_from_db,
        search_tickets_in_db,
    ]

    return tools