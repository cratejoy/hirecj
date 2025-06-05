"""Database-based support tools for CJ agent."""

import logging
import json
from typing import List, Any
from crewai.tools import tool
from app.utils.supabase_util import get_db_session
from app.lib.freshdesk_insight_lib import FreshdeskInsights

logger = logging.getLogger(__name__)


def create_database_tools(merchant_name: str = None) -> List:
    """Create CrewAI tools that interact with the Supabase database."""

    @tool
    def get_recent_ticket_from_db() -> str:
        """Get the most recent open support ticket from the database as raw JSON data."""
        logger.info("[TOOL CALL] get_recent_ticket_from_db() - Fetching most recent open ticket from database")
        
        try:
            with get_db_session() as session:
                result = FreshdeskInsights.get_recent_ticket(session, merchant_id=1)
                
                if not result:
                    return "No tickets found in the database."
                
                # Format as JSON
                result_json = json.dumps(result, indent=2, default=str)
                
                logger.info(f"[TOOL RESULT] get_recent_ticket_from_db() - Returned ticket {result['ticket_id']}")
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
                data = FreshdeskInsights.get_support_dashboard(session, merchant_id=1)
                
                # Format the output
                output = f"""📊 Support Dashboard from Database (Merchant ID: {data['merchant_id']}):

Current Queue Status:
• Total: {data['total_tickets']} tickets
• Open: {data['status_counts']['open']}
• In Progress: {data['status_counts']['in_progress']}
• Pending: {data['status_counts']['pending']}
• Resolved: {data['status_counts']['resolved']}
• Closed: {data['status_counts']['closed']}

Top Issue Categories:
{chr(10).join(f"• {category}: {count} tickets" for category, count in data['trending_issues'])}

Data Source: Live database query"""
                
                logger.info(f"[TOOL RESULT] get_support_dashboard_from_db() - Returned dashboard with {data['total_tickets']} total tickets")
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
                matching_tickets = FreshdeskInsights.search_tickets(session, query, merchant_name)
                
                if not matching_tickets:
                    return f"🔍 No tickets found matching '{query}' in the database."
                
                output = f"""🔍 Database Search Results for '{query}': {len(matching_tickets)} tickets found

Recent Tickets:"""
                
                # Show first 5 results
                for ticket in matching_tickets[:5]:
                    output += f"""
• #{ticket['ticket_id']} - {ticket['subject']}
  Category: {ticket['category']} | Status: {ticket['status']}
  Priority: {ticket['priority']}
  Created: {ticket['created_at']}"""
                
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
                data = FreshdeskInsights.calculate_csat(session, days, merchant_name)
                
                if not data['has_data']:
                    return f"📊 CSAT Score ({data['merchant_info']}): No ratings found in {data['time_range']}"
                
                output = f"""📊 CSAT Score ({data['merchant_info']}) ({data['time_range']}):

**{data['csat_percentage']:.1f}%** Customer Satisfaction

Rating Breakdown:
• Total unique customers who rated: {data['total_unique_ratings']}
• Happy ratings (😊): {data['happy_ratings']} ({(data['happy_ratings']/data['total_unique_ratings'])*100:.1f}%)
• Unhappy ratings (😞): {data['unhappy_ratings']} ({(data['unhappy_ratings']/data['total_unique_ratings'])*100:.1f}%)

Note: Each customer's most recent rating is counted (no duplicates).
Data Source: Live database query from etl_freshdesk_ratings"""
                
                logger.info(f"[TOOL RESULT] calculate_csat_score() - CSAT: {data['csat_percentage']:.1f}% from {data['total_unique_ratings']} unique ratings")
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