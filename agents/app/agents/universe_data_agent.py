"""Universe-based data agent that provides immutable data from pre-generated universes."""

from typing import Dict, Any, List
from app.universe.loader import UniverseLoader
from app.universe.views import UniverseViews


class UniverseDataAgent:
    """Provides support data from pre-generated universe files (immutable)."""

    def __init__(self, merchant_name: str, scenario_name: str):
        """Initialize with universe data."""
        self.merchant_name = merchant_name
        self.scenario_name = scenario_name

        # Load the universe
        loader = UniverseLoader()
        self.universe = loader.load_by_merchant_scenario(merchant_name, scenario_name)
        self.views = UniverseViews(self.universe)

        # Cache commonly accessed metrics
        self.base_metrics = self._get_base_metrics()

    def _get_base_metrics(self) -> Dict[str, Any]:
        """Get base metrics from universe data."""
        business_context = self.universe.get("business_context", {})
        current_state = business_context.get("current_state", {})

        # Get top categories from actual ticket distribution
        trending = self.views.get_trending_issues()
        top_categories = [category for category, count in trending[:3]]

        return {
            "mrr": current_state.get("mrr", 0),
            "subscriber_count": current_state.get("subscriber_count", 0),
            "churn_rate": current_state.get("churn_rate", 0),
            "csat_score": current_state.get("csat_score", 0),
            "support_tickets_per_day": current_state.get("support_tickets_per_day", 0),
            "average_response_time_hours": current_state.get(
                "average_response_time_hours", 0
            ),
            "top_categories": top_categories,
            "total_customers": len(self.universe.get("customers", [])),
            "total_tickets": len(self.universe.get("support_tickets", [])),
        }

    def get_support_dashboard(self) -> Dict[str, Any]:
        """Get support dashboard data (compatible with SupportDataAgent interface)."""
        queue_status = self.views.get_queue_status()
        trending = self.views.get_trending_issues()
        satisfaction = self.views.get_customer_satisfaction()
        business_metrics = self.views.get_business_metrics()

        return {
            "queue_status": queue_status,
            "trending_issues": trending,
            "customer_satisfaction": satisfaction,
            "business_metrics": business_metrics,
            "current_day": self.universe["metadata"]["current_day"],
            "universe_id": self.universe["metadata"]["universe_id"],
        }

    def search_tickets(self, query: str) -> Dict[str, Any]:
        """Search tickets (compatible with SupportDataAgent interface)."""
        matching_tickets = self.views.search_tickets(query)

        # Format results to match SupportDataAgent interface
        ticket_excerpts = []
        for ticket in matching_tickets[:10]:  # Limit to 10 results
            excerpt = ticket.get("content", "")[:150] + (
                "..." if len(ticket.get("content", "")) > 150 else ""
            )
            ticket_excerpts.append(
                {
                    "ticket_id": ticket.get("ticket_id", ""),
                    "subject": ticket.get("subject", ""),
                    "excerpt": excerpt,
                    "category": ticket.get("category", ""),
                    "sentiment": ticket.get("sentiment", ""),
                    "priority": ticket.get("priority", ""),
                    "status": ticket.get("status", ""),
                    "created_at": ticket.get("created_at", ""),
                    "customer_id": ticket.get("customer_id", ""),
                }
            )

        # Generate insights from actual ticket content
        categories = set(t.get("category", "") for t in matching_tickets)
        sentiments = [t.get("sentiment", "") for t in matching_tickets]

        # Extract common phrases from actual content
        common_phrases = []
        if matching_tickets:
            # Simple phrase extraction - in full implementation would be more sophisticated
            all_content = " ".join(
                t.get("content", "") + " " + t.get("subject", "")
                for t in matching_tickets
            )
            words = all_content.lower().split()
            phrases = [" ".join(words[i : i + 3]) for i in range(0, len(words) - 2, 3)][
                :5
            ]
            common_phrases = [p for p in phrases if query.lower() in p]

        return {
            "total_results": len(matching_tickets),
            "tickets": ticket_excerpts,
            "insights": {
                "categories": list(categories),
                "sentiment_breakdown": {
                    "positive": sentiments.count("positive"),
                    "negative": sentiments.count("negative"),
                    "neutral": sentiments.count("neutral"),
                    "frustrated": sentiments.count("frustrated"),
                },
                "common_phrases": common_phrases,
            },
        }

    def get_customer_details(self, customer_id: str) -> Dict[str, Any]:
        """Get customer details by ID."""
        customers = self.universe.get("customers", [])
        customer = next(
            (c for c in customers if c.get("customer_id") == customer_id), None
        )

        if not customer:
            return {"error": f"Customer {customer_id} not found"}

        # Get customer's tickets
        customer_tickets = [
            t
            for t in self.universe.get("support_tickets", [])
            if t.get("customer_id") == customer_id
        ]

        return {
            "customer": customer,
            "tickets": customer_tickets,
            "total_tickets": len(customer_tickets),
        }

    def get_category_breakdown(self) -> Dict[str, Any]:
        """Get ticket category breakdown."""
        trending = self.views.get_trending_issues()
        distribution = self.universe.get("ticket_categories_distribution", {})

        return {
            "categories": dict(trending),
            "distribution": distribution,
        }

    def get_timeline_context(self) -> List[Dict[str, Any]]:
        """Get timeline events for context."""
        return self.universe.get("timeline_events", [])

    def get_business_context(self) -> Dict[str, Any]:
        """Get business context and metrics."""
        return self.universe.get("business_context", {})
