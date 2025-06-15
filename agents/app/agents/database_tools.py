"""Database-based support tools for CJ agent."""

import logging
import json
from typing import List, Any, Optional
from datetime import datetime, date, timedelta
from crewai.tools import tool
from app.utils.supabase_util import get_db_session
from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics, FreshdeskInsights

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
    def calculate_csat_score(days: Optional[int] = None, 
                            start_date: Optional[str] = None, 
                            end_date: Optional[str] = None) -> str:
        """Calculate Customer Satisfaction (CSAT) score for a specific time range.
        
        Args:
            days: Number of days to look back (only used if start_date and end_date are not provided)
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)
        
        Returns the CSAT score as a percentage of happy ratings (103) vs total ratings.
        Only considers the most recent rating per unique user within the time range.
        """
        # Handle both direct calls and CrewAI calls
        if isinstance(days, dict):
            # Extract from dictionary if CrewAI passes args as dict
            args_dict = days  # Save the original dict
            days = args_dict.get('days')
            start_date = args_dict.get('start_date')
            end_date = args_dict.get('end_date')
        
        # Parse date strings if provided
        parsed_start = None
        parsed_end = None
        if start_date:
            parsed_start = datetime.fromisoformat(start_date)
        if end_date:
            parsed_end = datetime.fromisoformat(end_date)
        
        logger.info(f"[TOOL CALL] calculate_csat_score(days={days}, start_date={start_date}, end_date={end_date}) - Calculating CSAT score")
        
        try:
            with get_db_session() as session:
                data = FreshdeskInsights.calculate_csat(session, days, parsed_start, parsed_end, merchant_name)
                
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

    @tool
    def get_ticket_details(ticket_id: int) -> str:
        """Get complete details for a specific support ticket including all conversations and ratings.
        
        Args:
            ticket_id: The Freshdesk ticket ID to retrieve
            
        Returns detailed ticket information with full conversation history and any ratings.
        """
        logger.info(f"[TOOL CALL] get_ticket_details(ticket_id={ticket_id}) - Fetching ticket details")
        
        try:
            with get_db_session() as session:
                result = FreshdeskInsights.get_ticket_by_id(session, ticket_id, merchant_id=1)
                
                if not result:
                    return f"Ticket #{ticket_id} not found in the database."
                
                # Format the output
                output = f"""📋 Ticket #{result['ticket_id']} Details:

**Subject:** {result['data'].get('subject', 'No subject')}
**Status:** {result['data'].get('status')}
**Priority:** {result['data'].get('priority')}
**Created:** {result['data'].get('created_at')}
**Requester:** {result['data'].get('requester', {}).get('name')} ({result['data'].get('requester', {}).get('email')})

**Conversation History ({len(result['conversations'])} messages):**"""
                
                for i, conv in enumerate(result['conversations'], 1):
                    output += f"""
{i}. From: {conv.get('from_email', 'Unknown')}
   Date: {conv.get('created_at', 'Unknown')}
   Message: {conv.get('body_text', '')[:500]}{'...' if len(conv.get('body_text', '')) > 500 else ''}
"""
                
                if result['ratings']:
                    output += f"\n**Customer Rating:**\n"
                    for rating in result['ratings']:
                        rating_val = rating['ratings'].get('default_question')
                        rating_text = "😊 Happy" if rating_val == 103 else "😞 Unhappy" if rating_val == -103 else "Unknown"
                        output += f"- {rating_text} (rated on {rating['created_at']})\n"
                        if rating['data'].get('comments', {}).get('default_question'):
                            output += f"  Comment: {rating['data']['comments']['default_question']}\n"
                
                output += "\nData Source: Live database query"
                
                logger.info(f"[TOOL RESULT] get_ticket_details() - Returned ticket with {len(result['conversations'])} conversations")
                return output
                
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_ticket_details() - Error: {str(e)}")
            return f"Error fetching ticket details: {str(e)}"
    
    @tool
    def get_customer_history(email: str) -> str:
        """Get all support tickets for a specific customer email address.
        
        Args:
            email: The customer's email address
            
        Returns all tickets associated with this customer, sorted by most recent first.
        """
        logger.info(f"[TOOL CALL] get_customer_history(email='{email}') - Fetching customer ticket history")
        
        try:
            with get_db_session() as session:
                tickets = FreshdeskInsights.get_tickets_by_email(session, email, merchant_id=1)
                
                if not tickets:
                    return f"No tickets found for customer email: {email}"
                
                output = f"""📧 Customer History for {email}:
Found {len(tickets)} tickets

Ticket Summary:"""
                
                for ticket in tickets:
                    status_emoji = "✅" if ticket['status'] in [4, 'resolved', 'closed'] else "🔄"
                    output += f"""
{status_emoji} #{ticket['ticket_id']} - {ticket['subject']}
   Status: {ticket['status']} | Priority: {ticket['priority']}
   Created: {ticket['created_at']}"""
                
                output += "\n\nData Source: Live database query"
                
                logger.info(f"[TOOL RESULT] get_customer_history() - Found {len(tickets)} tickets for {email}")
                return output
                
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_customer_history() - Error: {str(e)}")
            return f"Error fetching customer history: {str(e)}"
    
    @tool
    def get_tickets_with_rating(rating_type: str = "unhappy", days: Optional[int] = None) -> str:
        """Get all tickets with a specific customer rating (happy or unhappy).
        
        Args:
            rating_type: Either "happy" or "unhappy" 
            days: Number of days to look back (optional)
            
        Returns tickets that received the specified rating.
        """
        # Handle CrewAI dict args
        if isinstance(rating_type, dict):
            args_dict = rating_type
            rating_type = args_dict.get('rating_type', 'unhappy')
            days = args_dict.get('days')
        
        logger.info(f"[TOOL CALL] get_tickets_with_rating(rating_type='{rating_type}', days={days})")
        
        try:
            with get_db_session() as session:
                tickets = FreshdeskInsights.get_tickets_by_rating(
                    session, 
                    rating_type=rating_type,
                    days=days,
                    merchant_id=1
                )
                
                if not tickets:
                    time_str = f"in the last {days} days" if days else "all time"
                    return f"No {rating_type} rated tickets found {time_str}"
                
                emoji = "😊" if rating_type == "happy" else "😞"
                time_str = f"Last {days} days" if days else "All time"
                
                output = f"""{emoji} {rating_type.capitalize()} Rated Tickets ({time_str}):
Found {len(tickets)} tickets

Recent {rating_type.capitalize()} Tickets:"""
                
                for ticket in tickets[:10]:  # Show first 10
                    output += f"""
• #{ticket['ticket_id']} - {ticket['subject']}
  Customer: {ticket['requester'].get('name')} ({ticket['requester'].get('email')})
  Ticket Created: {ticket['created_at']}
  Rating Given: {ticket['rating_created_at']}
  Current Status: {ticket['status']}"""
                
                if len(tickets) > 10:
                    output += f"\n\n... and {len(tickets) - 10} more {rating_type} tickets"
                
                output += "\n\nData Source: Live database query"
                
                logger.info(f"[TOOL RESULT] Found {len(tickets)} {rating_type} tickets")
                return output
                
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_tickets_with_rating() - Error: {str(e)}")
            return f"Error fetching rated tickets: {str(e)}"
    
    @tool  
    def analyze_bad_csat_tickets(limit: int = 5) -> str:
        """Get the most recent tickets with bad customer satisfaction ratings, including full conversation context.
        
        Args:
            limit: Maximum number of bad CSAT tickets to analyze (default: 5)
            
        Returns detailed information about recent unhappy customers including the full conversation.
        """
        # Handle CrewAI dict args
        if isinstance(limit, dict):
            limit = limit.get('limit', 5)
            
        logger.info(f"[TOOL CALL] analyze_bad_csat_tickets(limit={limit})")
        
        try:
            with get_db_session() as session:
                bad_tickets = FreshdeskInsights.get_recent_bad_csat_tickets(
                    session,
                    limit=limit,
                    merchant_id=1
                )
                
                if not bad_tickets:
                    return "Great news! No bad CSAT ratings found."
                
                output = f"""😞 Recent Bad CSAT Analysis:
Found {len(bad_tickets)} unhappy customers

Detailed Breakdown:
"""
                
                for i, ticket in enumerate(bad_tickets, 1):
                    output += f"""
{'='*60}
{i}. Ticket #{ticket.get('ticket_id', 'Unknown')} - {ticket.get('data', {}).get('subject', 'No subject')}
   Customer: {ticket.get('data', {}).get('requester', {}).get('name', 'Unknown')} ({ticket.get('data', {}).get('requester', {}).get('email', 'Unknown')})
   Bad Rating Date: {ticket.get('bad_rating_date', 'Unknown')}
   
   Customer's Rating Comment: {ticket.get('rating_comment') or 'No comment provided'}
   
   Conversation Summary ({len(ticket.get('conversations', []))} messages):"""
                    
                    # Show last 2 messages for context
                    conversations = ticket.get('conversations', [])
                    recent_convs = conversations[-2:] if len(conversations) > 1 else conversations
                    for conv in recent_convs:
                        output += f"""
   - From: {conv.get('from_email', 'Unknown')} at {conv.get('created_at', 'Unknown')}
     "{conv.get('body_text', '')[:200]}{'...' if len(conv.get('body_text', '')) > 200 else ''}"
"""
                
                output += f"""
{'='*60}

Key Insights: These are your most recent unhappy customers. Consider reaching out to understand their concerns better.

Data Source: Live database query with full conversation context"""
                
                logger.info(f"[TOOL RESULT] Analyzed {len(bad_tickets)} bad CSAT tickets")
                return output
                
        except Exception as e:
            logger.error(f"[TOOL ERROR] analyze_bad_csat_tickets() - Error: {str(e)}")
            return f"Error analyzing bad CSAT tickets: {str(e)}"

    @tool
    def get_daily_snapshot(date_str: Optional[str] = None) -> str:
        """Get comprehensive daily health metrics for support operations.
        
        Args:
            date_str: Date in YYYY-MM-DD format (defaults to yesterday if not provided)
            
        Returns daily metrics including ticket volumes, response times, CSAT, and SLA performance.
        """
        # Handle CrewAI dict args
        if isinstance(date_str, dict):
            date_str = date_str.get('date_str')
        
        logger.info(f"[TOOL CALL] get_daily_snapshot(date_str='{date_str}')")
        
        try:
            # Parse date or use yesterday as default
            if date_str:
                from datetime import date as date_type
                target_date = date_type.fromisoformat(date_str)
            else:
                from datetime import date as date_type, timedelta
                target_date = date_type.today() - timedelta(days=1)
            
            # Get merchant_id - hardcoded to 1 for now
            merchant_id = 1
            
            # Get the daily snapshot with session
            with get_db_session() as session:
                snapshot = FreshdeskAnalytics.get_daily_snapshot(session, merchant_id, target_date)
            
            # Format time helper
            def format_minutes(minutes):
                if minutes < 60:
                    return f"{int(minutes)} min"
                hours = int(minutes // 60)
                mins = int(minutes % 60)
                return f"{hours}h {mins}m"
            
            # Format the output
            output = f"""📊 Daily Support Snapshot for {snapshot['date']}:

📥 **Volume Metrics:**
• New Tickets: {snapshot['new_tickets']}
• Closed Tickets: {snapshot['closed_tickets']}
• Open at EOD: {snapshot['open_eod']}

⏱️ **Response Times:**
• Median First Agent Response: {format_minutes(snapshot['median_first_response_min'])}
• Median Resolution: {format_minutes(snapshot['median_resolution_min'])}
• Quick Closes (<10min): {snapshot['quick_close_count']}

😊 **Customer Satisfaction:**
• New Ratings: {snapshot['new_csat_count']}
• CSAT Score: {snapshot['csat_percentage']}% (perfect scores)
• Bad Ratings (<Very Happy): {snapshot['bad_csat_count']}

🚨 **SLA Performance:**
• Breaches: {snapshot['sla_breaches']}

Data Source: Live database analytics"""
            
            logger.info(f"[TOOL RESULT] get_daily_snapshot() - Retrieved metrics for {target_date}")
            return output
            
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_daily_snapshot() - Error: {str(e)}")
            return f"Error fetching daily snapshot: {str(e)}"

    @tool
    def get_csat_detail_log(date_str: Optional[str] = None, rating_threshold: int = 102, include_conversations: bool = False) -> str:
        """Get detailed CSAT survey data including all ratings, feedback, and response times for a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format (defaults to yesterday if not provided)
            rating_threshold: Ratings below this are considered negative (default 102 = Very Happy)
            include_conversations: If True, includes full conversation history for negative ratings
            
        Returns detailed breakdown of each CSAT survey including customer feedback and ticket metrics.
        """
        # Handle CrewAI dict args
        if isinstance(date_str, dict):
            args_dict = date_str
            date_str = args_dict.get('date_str')
            rating_threshold = args_dict.get('rating_threshold', 102)
            include_conversations = args_dict.get('include_conversations', False)
        
        logger.info(f"[TOOL CALL] get_csat_detail_log(date_str='{date_str}', rating_threshold={rating_threshold}, include_conversations={include_conversations})")
        
        try:
            # Parse date or use yesterday as default
            if date_str:
                from datetime import date as date_type
                target_date = date_type.fromisoformat(date_str)
            else:
                from datetime import date as date_type, timedelta
                target_date = date_type.today() - timedelta(days=1)
            
            # Get merchant_id - hardcoded to 1 for now
            merchant_id = 1
            
            # Get the CSAT detail log with session
            with get_db_session() as session:
                csat_data = FreshdeskAnalytics.get_csat_detail_log(
                    session, 
                    merchant_id, 
                    target_date, 
                    rating_threshold,
                    include_conversations
                )
            
            # Format time helper
            def format_minutes(minutes):
                if minutes is None:
                    return "N/A"
                if minutes < 60:
                    return f"{int(minutes)} min"
                hours = int(minutes // 60)
                mins = int(minutes % 60)
                return f"{hours}h {mins}m"
            
            # Format the output
            below_threshold_pct = (csat_data['below_threshold_count']/csat_data['total_count']*100) if csat_data['total_count'] > 0 else 0
            output = f"""📊 Detailed CSAT Log for {target_date}:
            
**Summary:**
• Total Surveys: {csat_data['total_count']}
• Average Rating: {csat_data['avg_rating']} 
• Below Threshold (<{rating_threshold}): {csat_data['below_threshold_count']} ({below_threshold_pct:.1f}%)

**Individual Survey Details:**
"""
            
            if not csat_data['surveys']:
                output += "\nNo CSAT surveys received on this date."
            else:
                # Group by rating for better readability
                unhappy_surveys = [s for s in csat_data['surveys'] if s['rating'] < rating_threshold]
                happy_surveys = [s for s in csat_data['surveys'] if s['rating'] >= rating_threshold]
                
                if unhappy_surveys:
                    output += "\n❌ **Negative Ratings:**\n"
                    for survey in unhappy_surveys:
                        output += f"""
Ticket #{survey['ticket_id']} - {survey['rating_label']} ({survey['rating']})
• Customer: {survey['customer_email']}
• Agent: {survey['agent']}
• Response Time: {format_minutes(survey['first_response_min'])}
• Resolution Time: {format_minutes(survey['resolution_min'])}
• Conversations: {survey['conversation_count']}
• Tags: {', '.join(survey['tags']) if survey['tags'] else 'None'}
• Feedback: "{survey['feedback'] or 'No feedback provided'}"
"""
                        # Include conversation if requested
                        if include_conversations and 'conversation' in survey and survey['conversation']:
                            output += f"\n📧 **Full Conversation:**\n{survey['conversation']}\n"
                            output += "-" * 80 + "\n"
                
                if happy_surveys:
                    output += "\n✅ **Positive Ratings:**\n"
                    # Show first 5 happy ratings for brevity
                    for survey in happy_surveys[:5]:
                        output += f"""
Ticket #{survey['ticket_id']} - {survey['rating_label']} ({survey['rating']})
• Customer: {survey['customer_email']}
• Response: {format_minutes(survey['first_response_min'])} | Resolution: {format_minutes(survey['resolution_min'])}
"""
                    if len(happy_surveys) > 5:
                        output += f"\n... and {len(happy_surveys) - 5} more positive ratings"
            
            output += "\n\nData Source: Live database analytics"
            
            logger.info(f"[TOOL RESULT] get_csat_detail_log() - Retrieved {csat_data['total_count']} surveys for {target_date}")
            return output
            
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_csat_detail_log() - Error: {str(e)}")
            return f"Error fetching CSAT detail log: {str(e)}"

    @tool
    def get_open_ticket_distribution() -> str:
        """Get distribution of open tickets by age to monitor backlog health and identify aging tickets.
        
        Returns ticket counts grouped by age (0-4h, 4-24h, 1-2d, 3-7d, >7d) and details of oldest tickets.
        Helps identify tickets at risk of SLA breach and backlog bottlenecks.
        """
        logger.info("[TOOL CALL] get_open_ticket_distribution()")
        
        try:
            # Get merchant_id - hardcoded to 1 for now
            merchant_id = 1
            
            # Get the distribution data with session
            with get_db_session() as session:
                distribution = FreshdeskAnalytics.get_open_ticket_distribution(session, merchant_id)
            
            # Format the output
            output = f"""📊 Open Ticket Distribution Analysis:

**Backlog Overview:**
• Total Open Tickets: {distribution['total_open']}

**Age Distribution:**
"""
            
            # Display buckets in order
            bucket_order = ["0-4h", "4-24h", "1-2d", "3-7d", ">7d"]
            for bucket in bucket_order:
                data = distribution['age_buckets'][bucket]
                # Create a simple bar chart
                bar_length = int(data['percentage'] / 5) if data['percentage'] > 0 else 0
                bar = "█" * bar_length if bar_length > 0 else ""
                output += f"• {bucket:>6}: {data['count']:3d} tickets ({data['percentage']:5.1f}%) {bar}\n"
            
            # Highlight concerning patterns
            old_tickets = distribution['age_buckets']['>7d']['count']
            if old_tickets > 0:
                output += f"\n⚠️ **Alert**: {old_tickets} ticket(s) older than 7 days!\n"
            
            # Show oldest tickets
            if distribution['oldest_tickets']:
                output += "\n**10 Oldest Open Tickets:**\n"
                for i, ticket in enumerate(distribution['oldest_tickets'], 1):
                    # Priority indicator
                    priority_emoji = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴"}.get(ticket['priority'], "⚪")
                    
                    output += f"""
{i}. {priority_emoji} Ticket #{ticket['ticket_id']} - {ticket['age_display']} old
   Subject: {ticket['subject']}
   Status: {ticket['status']}
   Customer: {ticket['customer_email']}
   Tags: {', '.join(ticket['tags']) if ticket['tags'] else 'None'}
   Last Updated: {ticket['last_updated']}
"""
            else:
                output += "\n✅ No open tickets - backlog is clear!"
            
            # Add insights
            if distribution['total_open'] > 0:
                fresh_pct = distribution['age_buckets']['0-4h']['percentage']
                aging_pct = distribution['age_buckets']['3-7d']['percentage'] + distribution['age_buckets']['>7d']['percentage']
                
                output += "\n**Insights:**\n"
                if fresh_pct > 50:
                    output += f"• {fresh_pct:.1f}% of tickets are fresh (<4h) - good responsiveness\n"
                if aging_pct > 20:
                    output += f"• {aging_pct:.1f}% of tickets are aging (>3d) - consider prioritizing these\n"
                
                # Check for "Waiting" statuses in oldest tickets
                waiting_count = sum(1 for t in distribution['oldest_tickets'] 
                                  if 'Waiting' in t['status'])
                if waiting_count > 0:
                    output += f"• {waiting_count} oldest tickets are waiting on customer/third party\n"
            
            output += "\nData Source: Live database analytics"
            
            logger.info(f"[TOOL RESULT] get_open_ticket_distribution() - Found {distribution['total_open']} open tickets")
            return output
            
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_open_ticket_distribution() - Error: {str(e)}")
            return f"Error analyzing open ticket distribution: {str(e)}"

    @tool
    def get_response_time_metrics(days: int = 7) -> str:
        """Analyze team response and resolution time performance with statistical insights.
        
        Args:
            days: Number of days to analyze (default: 7)
            
        Returns detailed metrics including percentiles, outliers, and CSAT correlation with speed.
        """
        # Handle CrewAI dict args
        if isinstance(days, dict):
            days = days.get('days', 7)
        
        logger.info(f"[TOOL CALL] get_response_time_metrics(days={days})")
        
        try:
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            date_range = {'start_date': start_date, 'end_date': end_date}
            
            # Get metrics with session
            with get_db_session() as session:
                metrics = FreshdeskAnalytics.get_response_time_metrics(
                    session,
                    merchant_id=1,
                    date_range=date_range
                )
            
            # Format time helper
            def format_time(minutes):
                if minutes < 60:
                    return f"{int(minutes)}m"
                hours = int(minutes // 60)
                mins = int(minutes % 60)
                return f"{hours}h {mins}m"
            
            # Format the output
            output = f"""📊 Response Time Performance Analysis ({days} days):

⏱️ **First Response Times:**"""
            
            if metrics['first_response']:
                fr = metrics['first_response']
                output += f"""
• Median: {format_time(fr['median_min'])}
• Average: {format_time(fr['mean_min'])}
• 25th percentile: {format_time(fr['p25_min'])} (25% respond faster)
• 75th percentile: {format_time(fr['p75_min'])} (75% respond faster)
• 95th percentile: {format_time(fr['p95_min'])} (95% respond faster)
"""
                if fr['outliers']:
                    output += f"\n⚠️ Outliers (>2σ from mean): {len(fr['outliers'])} tickets\n"
                    for outlier in fr['outliers'][:3]:
                        output += f"   - Ticket #{outlier['ticket_id']}: {format_time(outlier['response_min'])}\n"
            else:
                output += "\n   No response time data available\n"
            
            output += "\n⏰ **Resolution Times:**"
            if metrics['resolution']:
                res = metrics['resolution']
                output += f"""
• Median: {format_time(res['median_min'])}
• Average: {format_time(res['mean_min'])}
• 25th percentile: {format_time(res['p25_min'])}
• 75th percentile: {format_time(res['p75_min'])}
• 95th percentile: {format_time(res['p95_min'])}
"""
                if res['outliers']:
                    output += f"\n⚠️ Outliers (>2σ from mean): {len(res['outliers'])} tickets\n"
                    for outlier in res['outliers'][:3]:
                        output += f"   - Ticket #{outlier['ticket_id']}: {format_time(outlier['resolution_min'])}\n"
            else:
                output += "\n   No resolution time data available\n"
            
            # Quick resolution breakdown
            output += f"\n🚀 **Quick Resolution Performance:**\n"
            output += f"Total Resolved: {metrics['total_resolved']} tickets\n\n"
            
            if metrics['quick_resolutions']:
                for bucket, data in metrics['quick_resolutions'].items():
                    bar_length = int(data['percentage'] / 5) if data['percentage'] > 0 else 0
                    bar = "█" * bar_length if bar_length > 0 else ""
                    csat_str = f" (CSAT: {data['avg_csat']}/5)" if data['avg_csat'] > 0 else ""
                    output += f"• {bucket:>6}: {data['count']:3d} ({data['percentage']:5.1f}%) {bar}{csat_str}\n"
            
            # CSAT correlation
            output += "\n😊 **CSAT vs Response Speed:**\n"
            if any(cat['count'] > 0 for cat in metrics['csat_by_speed'].values()):
                for category, data in metrics['csat_by_speed'].items():
                    if data['count'] > 0:
                        # Convert rating to emoji
                        if data['avg_rating'] >= 102:
                            emoji = "😊"
                        elif data['avg_rating'] >= 100:
                            emoji = "😐"
                        else:
                            emoji = "😞"
                        output += f"• {category}: {data['count']} tickets, avg rating: {emoji} {data['avg_rating']}\n"
            else:
                output += "No rated tickets to analyze\n"
            
            # Insights
            output += "\n💡 **Key Insights:**\n"
            
            # Response time insights
            if metrics['first_response'] and metrics['first_response']['median_min'] < 60:
                output += f"✅ Excellent median first response time: {format_time(metrics['first_response']['median_min'])}\n"
            elif metrics['first_response'] and metrics['first_response']['median_min'] > 240:
                output += f"⚠️ Slow median first response time: {format_time(metrics['first_response']['median_min'])}\n"
            
            # Quick resolution insights
            if metrics['quick_resolutions'] and metrics['quick_resolutions']['<30min']['percentage'] > 50:
                output += f"✅ {metrics['quick_resolutions']['<30min']['percentage']:.1f}% of tickets resolved within 30 minutes\n"
            
            # CSAT correlation insights
            if metrics['csat_by_speed']:
                ultra_fast = metrics['csat_by_speed'].get('ultra_fast_<5min', {})
                slow = metrics['csat_by_speed'].get('slow_>180min', {})
                if ultra_fast.get('avg_rating', 0) > slow.get('avg_rating', 0):
                    output += "✅ Faster resolutions correlate with higher satisfaction\n"
            
            output += "\nData Source: Live database analytics"
            
            logger.info(f"[TOOL RESULT] get_response_time_metrics() - Analyzed {len(metrics.get('first_response', {}).get('outliers', []))} response outliers")
            return output
            
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_response_time_metrics() - Error: {str(e)}")
            return f"Error analyzing response time metrics: {str(e)}"

    @tool
    def get_volume_trends(days: int = 60) -> str:
        """Analyze ticket volume trends to detect spikes, patterns, and unusual activity.
        
        Args:
            days: Number of days to analyze (default: 60)
            
        Returns daily volume data with spike detection, 7-day rolling average, and trend analysis.
        Helps identify when support load is abnormal and whether volume is trending up or down.
        """
        # Handle CrewAI dict args
        if isinstance(days, dict):
            days = days.get('days', 60)
        
        logger.info(f"[TOOL CALL] get_volume_trends(days={days})")
        
        try:
            # Get merchant_id - hardcoded to 1 for now
            merchant_id = 1
            
            # Get volume trends with session
            with get_db_session() as session:
                trends = FreshdeskAnalytics.get_volume_trends(session, merchant_id, days)
            
            # Format the output
            output = f"""📊 Ticket Volume Trend Analysis ({days} days):

**Summary Statistics:**
• Average Daily Volume: {trends['summary']['avg_daily_volume']} tickets
• Standard Deviation: ±{trends['summary']['std_dev']} tickets
• Spike Threshold: {trends['summary']['spike_threshold']} tickets (>2σ)
• Total Tickets: {trends['summary']['total_tickets']} over {trends['summary']['days_analyzed']} days

**Trend Analysis:**
• Overall Trend: {trends['summary']['trend'].upper()}"""
            
            if trends['summary']['trend_percentage'] != 0:
                trend_emoji = "📈" if trends['summary']['trend_percentage'] > 0 else "📉"
                output += f" {trend_emoji} {abs(trends['summary']['trend_percentage']):.1f}%"
            
            # Add highest/lowest days
            if trends['summary']['highest_day']:
                output += f"\n• Highest Volume: {trends['summary']['highest_day']['volume']} tickets on {trends['summary']['highest_day']['date']}"
            if trends['summary']['lowest_day']:
                output += f"\n• Lowest Volume: {trends['summary']['lowest_day']['volume']} tickets on {trends['summary']['lowest_day']['date']}"
            if trends['summary']['zero_ticket_days'] > 0:
                output += f"\n• Days with NO tickets: {trends['summary']['zero_ticket_days']}"
            
            # Spike detection
            if trends['summary']['spike_days']:
                output += f"\n\n🚨 **Spike Days Detected ({len(trends['summary']['spike_days'])} total):**\n"
                for spike in trends['summary']['spike_days'][:5]:  # Show top 5 spikes
                    output += f"• {spike['date']}: {spike['volume']} tickets ({spike['deviation']:.1f}σ above average)\n"
                if len(trends['summary']['spike_days']) > 5:
                    output += f"... and {len(trends['summary']['spike_days']) - 5} more spike days\n"
            else:
                output += "\n\n✅ No significant spikes detected"
            
            # Recent trend (last 7 days)
            if len(trends['daily_volumes']) >= 7:
                recent_volumes = trends['daily_volumes'][-7:]
                output += "\n\n📅 **Last 7 Days:**\n"
                for day in recent_volumes:
                    spike_indicator = " 🚨 SPIKE" if day['is_spike'] else ""
                    bar_length = int(day['new_tickets'] / 5) if day['new_tickets'] > 0 else 0
                    bar = "█" * min(bar_length, 20)  # Cap at 20 chars
                    output += f"• {day['date']}: {day['new_tickets']:3d} tickets {bar}{spike_indicator}\n"
            
            # Rolling average insight
            if trends['rolling_7d_avg']:
                current_avg = trends['rolling_7d_avg'][-1]['avg']
                week_ago_avg = trends['rolling_7d_avg'][-8]['avg'] if len(trends['rolling_7d_avg']) >= 8 else current_avg
                
                output += f"\n**7-Day Rolling Average:**\n"
                output += f"• Current: {current_avg:.1f} tickets/day\n"
                if current_avg != week_ago_avg:
                    change = ((current_avg - week_ago_avg) / week_ago_avg * 100) if week_ago_avg > 0 else 0
                    change_emoji = "📈" if change > 0 else "📉"
                    output += f"• Week-over-week change: {change_emoji} {abs(change):.1f}%\n"
            
            # Insights
            output += "\n💡 **Key Insights:**\n"
            
            # Spike frequency
            spike_count = len(trends['summary']['spike_days'])
            spike_rate = (spike_count / trends['summary']['days_analyzed'] * 100) if trends['summary']['days_analyzed'] > 0 else 0
            if spike_rate > 10:
                output += f"⚠️ High spike frequency: {spike_rate:.1f}% of days exceed normal volume\n"
            elif spike_count > 0:
                output += f"📊 Spike frequency: {spike_count} spikes in {days} days ({spike_rate:.1f}%)\n"
            
            # Trend insight
            if trends['summary']['trend'] == "increasing":
                output += f"📈 Volume is trending UP by {trends['summary']['trend_percentage']:.1f}%\n"
            elif trends['summary']['trend'] == "decreasing":
                output += f"📉 Volume is trending DOWN by {abs(trends['summary']['trend_percentage']):.1f}%\n"
            else:
                output += "➡️ Volume is relatively stable\n"
            
            # Variability insight
            if trends['summary']['std_dev'] > trends['summary']['avg_daily_volume'] * 0.5:
                output += "⚠️ High variability in daily volumes - consider staffing flexibility\n"
            
            output += "\nData Source: Live database analytics"
            
            logger.info(f"[TOOL RESULT] get_volume_trends() - Analyzed {trends['summary']['days_analyzed']} days, found {spike_count} spikes")
            return output
            
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_volume_trends() - Error: {str(e)}")
            return f"Error analyzing volume trends: {str(e)}"

    @tool
    def get_sla_exceptions(first_response_min: Optional[int] = None, resolution_min: Optional[int] = None, include_pending: bool = True) -> str:
        """Monitor SLA compliance and identify tickets breaching service level agreements.
        
        Args:
            first_response_min: First response SLA in minutes (default: 60 min / 1 hour)
            resolution_min: Resolution SLA in minutes (default: 1440 min / 24 hours)
            include_pending: Include open/pending tickets in resolution checks (default: True)
            
        Returns comprehensive SLA breach analysis with patterns and insights.
        """
        # Handle CrewAI dict args
        if isinstance(first_response_min, dict):
            args_dict = first_response_min
            first_response_min = args_dict.get('first_response_min')
            resolution_min = args_dict.get('resolution_min')
            include_pending = args_dict.get('include_pending', True)
        
        # Build SLA config
        sla_config = {
            "include_pending": include_pending
        }
        if first_response_min is not None:
            sla_config["first_response_min"] = first_response_min
        if resolution_min is not None:
            sla_config["resolution_min"] = resolution_min
        
        logger.info(f"[TOOL CALL] get_sla_exceptions(config={sla_config})")
        
        try:
            # Get merchant_id
            merchant_id = 1
            
            # Get SLA exceptions with session
            with get_db_session() as session:
                analysis = FreshdeskAnalytics.get_sla_exceptions(
                    session,
                    merchant_id,
                    sla_config if sla_config != {"include_pending": include_pending} else None
                )
            
            # Format output
            output = f"""🚨 SLA Exception Report:

**Current SLA Thresholds:**
• First Response: {analysis['sla_config']['first_response_min']} minutes ({analysis['sla_config']['first_response_min'] / 60:.1f} hours)
• Resolution: {analysis['sla_config']['resolution_min']} minutes ({analysis['sla_config']['resolution_min'] / 60:.1f} hours)
• Including Pending Tickets: {'Yes' if analysis['sla_config']['include_pending'] else 'No'}

**Summary:**
• Total SLA Breaches: {analysis['summary']['total_breaches']}
• Response Breaches: {analysis['summary']['response_breaches']} (avg overage: {analysis['summary']['avg_response_breach_min']} min)
• Resolution Breaches: {analysis['summary']['resolution_breaches']} (avg overage: {analysis['summary']['avg_resolution_breach_min']} min)
• Tickets with No Response: {analysis['summary']['no_response_count']}
"""
            
            # First Response Breaches
            if analysis['breaches']['first_response']:
                output += "\n❌ **First Response SLA Breaches (worst first):**\n"
                for i, breach in enumerate(analysis['breaches']['first_response'][:5], 1):
                    if breach.get('no_response'):
                        output += f"""
{i}. #{breach['ticket_id']} - NO RESPONSE YET
   Subject: {breach['subject']}
   Created: {breach['created_at']}
   Overdue by: {breach['breach_by_min']} min ({breach['breach_by_min'] / 60:.1f} hours)
   Priority: {breach['priority']} | Status: {breach['status']}
"""
                    else:
                        output += f"""
{i}. #{breach['ticket_id']} - {breach['response_time_min']} min response time
   Subject: {breach['subject']}
   Overdue by: {breach['breach_by_min']} min
   Priority: {breach['priority']} | Escalated: {'Yes' if breach.get('fr_escalated') else 'No'}
"""
                
                if len(analysis['breaches']['first_response']) > 5:
                    output += f"\n... and {len(analysis['breaches']['first_response']) - 5} more response breaches\n"
            
            # Resolution Breaches
            if analysis['breaches']['resolution']:
                output += "\n⏰ **Resolution SLA Breaches (worst first):**\n"
                for i, breach in enumerate(analysis['breaches']['resolution'][:5], 1):
                    status_str = "STILL OPEN" if breach.get('still_open') else "Resolved"
                    output += f"""
{i}. #{breach['ticket_id']} - {breach['resolution_time_min']} min ({breach['resolution_time_min'] / 1440:.1f} days)
   Subject: {breach['subject']}
   Overdue by: {breach['breach_by_min']} min ({breach['breach_by_min'] / 1440:.1f} days)
   Status: {status_str} | Priority: {breach['priority']}
   Escalated: {'Yes' if breach.get('is_escalated') else 'No'}
"""
                
                if len(analysis['breaches']['resolution']) > 5:
                    output += f"\n... and {len(analysis['breaches']['resolution']) - 5} more resolution breaches\n"
            
            # Patterns
            output += "\n📊 **Breach Patterns:**\n"
            
            # Priority patterns
            if analysis['patterns']['by_priority']:
                output += "\nBy Priority Level:\n"
                priority_names = {1: "Low", 2: "Medium", 3: "High", 4: "Urgent"}
                
                for breach_type in ['response', 'resolution']:
                    if analysis['patterns']['by_priority'][breach_type]:
                        output += f"\n{breach_type.title()} Breaches:\n"
                        for priority, data in sorted(analysis['patterns']['by_priority'][breach_type].items()):
                            priority_name = priority_names.get(priority, f"Priority {priority}")
                            output += f"• {priority_name}: {data['count']} breaches (avg {data['avg_breach_min']} min over SLA)\n"
            
            # Tag patterns
            if analysis['patterns']['top_breach_tags']:
                output += "\nMost Common Tags in Breaches:\n"
                for tag_data in analysis['patterns']['top_breach_tags']:
                    output += f"• {tag_data['tag']}: {tag_data['count']} breaches\n"
            
            # Insights
            insights = []
            if analysis['summary']['no_response_count'] > 0:
                insights.append(f"⚠️ {analysis['summary']['no_response_count']} tickets have received no response at all")
            
            if analysis['patterns']['by_priority'].get('response', {}).get(4, {}).get('count', 0) > 0:
                urgent_count = analysis['patterns']['by_priority']['response'][4]['count']
                insights.append(f"🔴 {urgent_count} urgent priority tickets breached response SLA")
            
            open_resolution_breaches = sum(1 for b in analysis['breaches']['resolution'] if b.get('still_open'))
            if open_resolution_breaches > 0:
                insights.append(f"⏳ {open_resolution_breaches} tickets are still open and breaching resolution SLA")
            
            if insights:
                output += "\n💡 **Key Insights:**\n"
                for insight in insights:
                    output += f"{insight}\n"
            
            output += "\nData Source: Live database analysis"
            
            logger.info(f"[TOOL RESULT] get_sla_exceptions() - Found {analysis['summary']['total_breaches']} total breaches")
            return output
            
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_sla_exceptions() - Error: {str(e)}")
            return f"Error analyzing SLA exceptions: {str(e)}"
    
    @tool
    def get_root_cause_analysis(date_str: str, spike_threshold: float = 2.0) -> str:
        """Analyze root causes when ticket volume spikes on a specific date.
        
        Args:
            date_str: Date to analyze in YYYY-MM-DD format
            spike_threshold: Standard deviations above mean to consider a spike (default: 2.0)
            
        Returns analysis of what drove the spike including tag breakdowns, ticket types,
        example tickets, and insights about potential causes (holidays, system issues, etc).
        """
        # Handle CrewAI dict args
        if isinstance(date_str, dict):
            args_dict = date_str
            date_str = args_dict.get('date_str')
            spike_threshold = args_dict.get('spike_threshold', 2.0)
        
        logger.info(f"[TOOL CALL] get_root_cause_analysis(date_str='{date_str}', spike_threshold={spike_threshold})")
        
        try:
            # Get merchant_id - hardcoded to 1 for now
            merchant_id = 1
            
            # Get root cause analysis with session
            with get_db_session() as session:
                analysis = FreshdeskAnalytics.get_root_cause_analysis(session, merchant_id, date_str, spike_threshold)
            
            # Format the output
            output = f"""🔍 Root Cause Analysis for {analysis['date']}:

**Volume Overview:**
• Total Tickets: {analysis['total_tickets']}
• Historical Average: {analysis['historical_avg']} (±{analysis['historical_std']})
• Normal Range: {analysis['normal_range'][0]} - {analysis['normal_range'][1]} tickets
• Deviation: {analysis['deviation']:.1f}σ from mean
• Spike Detected: {'🚨 YES' if analysis['spike_detected'] else '✅ NO'}"""
            
            if analysis['spike_detected']:
                output += "\n\n📊 **Tag Analysis (Top Issues):**"
                
                if analysis['tag_analysis']:
                    for i, tag_data in enumerate(analysis['tag_analysis'][:5], 1):
                        increase_str = f"+{tag_data['percentage_increase']:.0f}%" if tag_data['percentage_increase'] < 999 else "NEW"
                        output += f"\n\n{i}. **{tag_data['tag']}** - {tag_data['today_count']} tickets ({increase_str})"
                        output += f"\n   Normal: {tag_data['avg_count']} | Increase: +{tag_data['delta']} tickets"
                        
                        if tag_data['example_tickets']:
                            output += "\n   Example tickets:"
                            for ex in tag_data['example_tickets'][:2]:
                                output += f"\n   • #{ex['ticket_id']}: {ex['subject'][:50]}..."
                else:
                    output += "\n   No tagged tickets found - all tickets are untagged"
                
                # Type analysis
                if analysis['type_analysis']:
                    output += "\n\n📋 **Ticket Type Breakdown:**"
                    for type_data in analysis['type_analysis'][:3]:
                        output += f"\n• {type_data['type']}: {type_data['today_count']} tickets (normally {type_data['avg_count']})"
                
                # Untagged warning
                if analysis['untagged_count'] > 0:
                    untagged_pct = (analysis['untagged_count'] / analysis['total_tickets'] * 100)
                    output += f"\n\n⚠️ **Untagged Tickets:** {analysis['untagged_count']} ({untagged_pct:.0f}% of total)"
                
                # Insights
                output += "\n\n💡 **Insights:**"
                for insight in analysis['insights']:
                    output += f"\n• {insight}"
                
                # Recommendations
                output += "\n\n📌 **Recommended Actions:**"
                
                # Tag-specific recommendations
                if analysis['tag_analysis']:
                    top_tags = analysis['tag_analysis'][:2]
                    for tag_data in top_tags:
                        tag = tag_data['tag'].lower()
                        if 'ship' in tag or 'delivery' in tag:
                            output += "\n• Check with shipping partners for delays or system issues"
                        elif 'payment' in tag or 'billing' in tag:
                            output += "\n• Verify payment processor status and transaction logs"
                        elif 'cancel' in tag:
                            output += "\n• Review cancellation reasons - possible product or service issue"
                        elif 'subscription' in tag:
                            output += "\n• Check subscription renewal systems and billing cycles"
                
                # General recommendations
                if analysis['deviation'] > 3:
                    output += "\n• Consider all-hands support response for severe spike"
                elif analysis['deviation'] > 2:
                    output += "\n• Alert support team about increased volume"
                    
                output += "\n• Review example tickets to understand customer pain points"
                output += "\n• Update knowledge base for trending issues"
                
            else:
                output += "\n\n✅ Volume is within normal range - no significant issues detected"
                
                # Still show top tags for context
                if analysis['tag_analysis']:
                    output += "\n\n📊 **Most Common Issues Today:**"
                    for tag_data in analysis['tag_analysis'][:3]:
                        output += f"\n• {tag_data['tag']}: {tag_data['today_count']} tickets"
            
            output += "\n\nData Source: Live database analytics with 30-day historical comparison"
            
            logger.info(f"[TOOL RESULT] get_root_cause_analysis() - Analyzed {analysis['total_tickets']} tickets, spike={'YES' if analysis['spike_detected'] else 'NO'}")
            return output
            
        except Exception as e:
            logger.error(f"[TOOL ERROR] get_root_cause_analysis() - Error: {str(e)}")
            return f"Error analyzing root causes: {str(e)}"

    # Return the tools created with @tool decorator
    tools = [
        get_recent_ticket_from_db,
        get_support_dashboard_from_db,
        search_tickets_in_db,
        calculate_csat_score,
        get_ticket_details,
        get_customer_history,
        get_tickets_with_rating,
        analyze_bad_csat_tickets,
        get_daily_snapshot,
        get_csat_detail_log,
        get_open_ticket_distribution,
        get_response_time_metrics,
        get_volume_trends,
        get_root_cause_analysis,
    ]

    return tools