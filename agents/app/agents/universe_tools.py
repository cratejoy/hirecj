"""Universe-based support tools for CJ agent."""

import logging
from typing import List, Any
from pydantic import BaseModel, Field
from crewai.tools.base_tool import tool
from app.config import settings

logger = logging.getLogger(__name__)


class SearchInput(BaseModel):
    """Input for search_support_tickets tool."""

    query: str = Field(
        description="Search term (e.g., 'shipping delays', 'refund requests', 'product name')"
    )


class CustomerInput(BaseModel):
    """Input for get_customer_profile tool."""

    customer_id: str = Field(description="Customer ID (e.g., 'cust_001', 'cust_123')")


def create_universe_tools(data_agent: Any) -> List:
    """Create CrewAI tools that interact with the Universe Data Agent."""

    @tool
    def get_support_dashboard() -> str:
        """Get current support queue status and key metrics from universe data."""
        logger.info("[TOOL CALL] get_support_dashboard() - Fetching support dashboard data")
        data = data_agent.get_support_dashboard()

        queue = data["queue_status"]
        business = data["business_metrics"]
        satisfaction = data["customer_satisfaction"]
        trending = data["trending_issues"][
            : settings.trending_issues_display_count
        ]  # Top trending issues

        output = f"""📊 Support Dashboard (Universe: {data['universe_id']}):

Current Queue Status:
• Total: {queue['total']} | Open: {queue['open']} | In Progress: {queue['in_progress']} | Resolved: {queue['resolved']}

Business Metrics:
• MRR: ${business.get('mrr', 0):,} | Subscribers: {business.get('subscriber_count', 0):,}
• Churn Rate: {business.get('churn_rate', 0)}% | CSAT: {business.get('csat_score', 0)}/5
• Avg Response Time: {business.get('average_response_time_hours', 0)} hours

Customer Satisfaction:
• Average Score: {satisfaction['average_score']}/5 ({satisfaction['total_customers']} customers)

Top Issue Categories:
{chr(10).join(f'• {category}: {count} tickets' for category, count in trending)}

Universe Context: Day {data['current_day']}/90 of scenario timeline"""

        logger.info(f"[TOOL RESULT] get_support_dashboard() - Returned dashboard with {queue['total']} total tickets")
        return output

    @tool
    def search_support_tickets(query: str) -> str:
        """Search through support tickets for specific issues, products, or keywords.

        Args:
            query: Search term (e.g., 'shipping delays', 'refund requests', 'product name')
        """
        logger.info(f"[TOOL CALL] search_support_tickets(query='{query}') - Searching for tickets")
        results = data_agent.search_tickets(query)

        if results["total_results"] == 0:
            return f"🔍 No tickets found matching '{query}'. This may indicate the issue is not common or doesn't exist in our current data."

        output = f"""🔍 Search Results for '{query}': {results['total_results']} tickets found

Recent Tickets:
"""

        for ticket in results["tickets"][
            : settings.search_results_display_count
        ]:  # Show search results
            output += f"""
• #{ticket['ticket_id']} - {ticket['subject']}
  Category: {ticket['category']} | Status: {ticket['status']} | Sentiment: {ticket['sentiment']}
  Preview: {ticket['excerpt']}
"""

        insights = results["insights"]
        if insights["categories"]:
            output += f"\nCategories: {', '.join(insights['categories'])}"

        sentiment_breakdown = insights["sentiment_breakdown"]
        total_sentiment = sum(sentiment_breakdown.values())
        if total_sentiment > 0:
            output += "\nSentiment: "
            output += f"Positive: {sentiment_breakdown['positive']} | "
            output += f"Negative: {sentiment_breakdown['negative']} | "
            output += f"Neutral: {sentiment_breakdown['neutral']} | "
            output += f"Frustrated: {sentiment_breakdown['frustrated']}"

        logger.info(f"[TOOL RESULT] search_support_tickets(query='{query}') - Found {results['total_results']} matching tickets")
        return output

    @tool
    def get_customer_profile(customer_id: str) -> str:
        """Get detailed customer information and support history.

        Args:
            customer_id: Customer ID (e.g., 'cust_001', 'cust_123')
        """
        logger.info(f"[TOOL CALL] get_customer_profile(customer_id='{customer_id}') - Fetching customer details")
        data = data_agent.get_customer_details(customer_id)

        if "error" in data:
            logger.warning(f"[TOOL ERROR] get_customer_profile(customer_id='{customer_id}') - {data['error']}")
            return f"❌ {data['error']}"

        customer = data["customer"]
        tickets = data["tickets"]

        output = f"""👤 Customer Profile: {customer['name']} ({customer_id})

Contact: {customer['email']}
Subscription: {customer['subscription_tier']} (since {customer['subscription_start_date']})
Status: {customer['status']} | Satisfaction: {customer['satisfaction_score']}/5

Account Summary:
• Lifetime Value: ${customer['lifetime_value']:,}
• Total Orders: {customer['orders_count']}
• Last Order: {customer['last_order_date']}
• Support Tickets: {customer['support_tickets_count']}

Recent Support History ({len(tickets)} tickets):"""

        for ticket in tickets[-3:]:  # Last 3 tickets
            output += f"""
• #{ticket['ticket_id']} - {ticket['subject']} ({ticket['status']})
  {ticket['category']} | Created: {ticket['created_at'][:10]}"""

        logger.info(f"[TOOL RESULT] get_customer_profile(customer_id='{customer_id}') - Returned profile for {customer['name']} with {len(tickets)} tickets")
        return output

    @tool
    def get_trending_issues() -> str:
        """Get current trending support issues and category breakdown."""
        logger.info("[TOOL CALL] get_trending_issues() - Fetching trending issues")
        dashboard = data_agent.get_support_dashboard()
        trending = dashboard["trending_issues"]

        output = "📈 Trending Support Issues:\n\n"

        for i, (category, count) in enumerate(trending, 1):
            percentage = (count / sum(c for _, c in trending)) * 100 if trending else 0
            output += f"{i}. {category.title()}: {count} tickets ({percentage:.1f}%)\n"

        # Get category distribution details
        category_data = data_agent.get_category_breakdown()
        distribution = category_data.get("distribution", {})

        if distribution:
            output += "\nCategory Details:\n"
            for category, details in distribution.items():
                if isinstance(details, dict):
                    avg_per_day = details.get("average_per_day", 0)
                    common_issues = details.get("common_issues", [])
                    output += f"• {category.title()}: ~{avg_per_day}/day"
                    if common_issues:
                        output += f" (Common: {', '.join(common_issues[:2])})"
                    output += "\n"

        logger.info(f"[TOOL RESULT] get_trending_issues() - Returned {len(trending)} trending categories")
        return output

    @tool
    def get_business_timeline() -> str:
        """Get recent business events and timeline context that might affect support."""
        logger.info("[TOOL CALL] get_business_timeline() - Fetching business timeline")
        timeline = data_agent.get_timeline_context()

        if not timeline:
            logger.info("[TOOL RESULT] get_business_timeline() - No timeline events available")
            return "📅 No recent timeline events available."

        output = "📅 Recent Business Timeline:\n\n"

        # Show recent events (last 10 days and upcoming 5 days)
        current_day = data_agent.universe["metadata"]["current_day"]
        relevant_events = [
            event
            for event in timeline
            if current_day - 10 <= event["day"] <= current_day + 5
        ]

        for event in relevant_events:
            impact_emoji = {
                "positive": "📈",
                "negative": "📉",
                "minor_negative": "📉",
                "none": "📊",
            }.get(event["impact"], "📊")

            day_label = f"Day {event['day']}"
            if event["day"] == current_day:
                day_label += " (TODAY)"
            elif event["day"] < current_day:
                day_label += f" ({current_day - event['day']} days ago)"
            else:
                day_label += f" (in {event['day'] - current_day} days)"

            output += f"{impact_emoji} {day_label}: {event['event']}\n"
            if event.get("details"):
                output += f"   Details: {event['details']}\n"

        logger.info(f"[TOOL RESULT] get_business_timeline() - Returned {len(relevant_events)} relevant events")
        return output

    @tool
    def get_recent_ticket() -> str:
        """Get the most recent open support ticket as raw JSON data."""
        logger.info("[TOOL CALL] get_recent_ticket() - Fetching most recent open ticket")
        
        # Get all tickets from universe data
        tickets = data_agent.universe.get("support_tickets", [])
        
        # Filter for open tickets only
        open_tickets = [t for t in tickets if t.get("status", "").lower() in ["open", "in_progress", "pending"]]
        
        if not open_tickets:
            logger.info("[TOOL RESULT] get_recent_ticket() - No open tickets found")
            return "No open tickets found in the system."
        
        # Sort by created_at to get most recent (assuming ISO format dates sort correctly)
        sorted_tickets = sorted(open_tickets, key=lambda t: t.get("created_at", ""), reverse=True)
        most_recent = sorted_tickets[0]
        
        # Return as formatted JSON
        import json
        result = json.dumps(most_recent, indent=2)
        
        logger.info(f"[TOOL RESULT] get_recent_ticket() - Returned ticket {most_recent.get('ticket_id', 'unknown')}")
        return f"Most recent open ticket:\n```json\n{result}\n```"

    # Return the tools created with @tool decorator
    tools = [
        get_support_dashboard,
        search_support_tickets,
        get_customer_profile,
        get_trending_issues,
        get_business_timeline,
        get_recent_ticket,
    ]

    return tools
