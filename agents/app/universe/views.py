"""Data views for querying universe data."""

import os
import yaml
from typing import Dict, Any, List
from app.config import settings
from app.constants import FileFormats, SatisfactionScores


class UniverseViews:
    """Provides simple views on universe data."""

    def __init__(self, universe: Dict[str, Any]):
        """Initialize with universe data."""
        self.universe = universe
        self.current_day = universe["metadata"]["current_day"]

    def get_todays_tickets(self) -> List[Dict[str, Any]]:
        """Get tickets created on current day."""

        # For now, return all tickets (in full implementation would filter by day)
        return self.universe.get("support_tickets", [])

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current ticket queue status."""

        tickets = self.get_todays_tickets()

        return {
            "total": len(tickets),
            "open": len([t for t in tickets if t["status"] == "open"]),
            "resolved": len([t for t in tickets if t["status"] == "resolved"]),
            "in_progress": len([t for t in tickets if t["status"] == "in_progress"]),
        }

    def search_tickets(self, query: str) -> List[Dict[str, Any]]:
        """Simple text search across ticket content."""

        tickets = self.universe.get("support_tickets", [])
        query_lower = query.lower()

        matching_tickets = []
        for ticket in tickets:
            if (
                query_lower in ticket.get("content", "").lower()
                or query_lower in ticket.get("subject", "").lower()
            ):
                matching_tickets.append(ticket)

        return matching_tickets

    def find_tickets_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Find tickets by category."""

        tickets = self.universe.get("support_tickets", [])
        return [t for t in tickets if t.get("category") == category]

    def find_tickets_by_sentiment(self, sentiment: str) -> List[Dict[str, Any]]:
        """Find tickets by sentiment."""

        tickets = self.universe.get("support_tickets", [])
        return [t for t in tickets if t.get("sentiment") == sentiment]

    def get_trending_issues(self, days: int = None) -> List[tuple]:
        """Get trending issues by category count."""

        if days is None:
            days = settings.trending_window_days

        tickets = self.universe.get("support_tickets", [])

        # Count by category
        category_counts = {}
        for ticket in tickets:
            category = ticket.get("category", "unknown")
            category_counts[category] = category_counts.get(category, 0) + 1

        # Sort by count descending
        return sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    def get_customer_satisfaction(self) -> Dict[str, Any]:
        """Get customer satisfaction metrics."""

        customers = self.universe.get("customers", [])
        if not customers:
            return {"average_score": 0, "total_customers": 0}

        scores = [c.get("satisfaction_score", 0) for c in customers]
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "average_score": round(avg_score, 2),
            "total_customers": len(customers),
            "score_distribution": {
                "5": len([s for s in scores if s == SatisfactionScores.VERY_SATISFIED]),
                "4": len([s for s in scores if s == SatisfactionScores.SATISFIED]),
                "3": len([s for s in scores if s == SatisfactionScores.NEUTRAL]),
                "2": len([s for s in scores if s == SatisfactionScores.UNSATISFIED]),
                "1": len(
                    [s for s in scores if s == SatisfactionScores.VERY_UNSATISFIED]
                ),
            },
        }

    def get_business_metrics(self) -> Dict[str, Any]:
        """Get current business metrics."""

        return self.universe.get("business_context", {}).get("current_state", {})

    def get_product_mentions(self) -> Dict[str, int]:
        """Count product mentions in tickets."""

        tickets = self.universe.get("support_tickets", [])
        product_mentions = {}

        # Simple product detection (would be more sophisticated in full implementation)
        products = ["Sweet Heat", "Memphis Magic", "Jade Glow", "Rose Clay"]

        for ticket in tickets:
            content = ticket.get("content", "") + " " + ticket.get("subject", "")
            for product in products:
                if product.lower() in content.lower():
                    product_mentions[product] = product_mentions.get(product, 0) + 1

        return product_mentions


def list_available_universes() -> List[Dict[str, Any]]:
    """List all available universes without requiring parameters."""
    universes_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "universes"
    )
    universes = []

    if not os.path.exists(universes_dir):
        return universes

    for filename in os.listdir(universes_dir):
        if filename.endswith(".yaml"):
            universe_path = os.path.join(universes_dir, filename)
            try:
                with open(universe_path, "r") as f:
                    universe_data = yaml.safe_load(f)

                # Extract metadata
                metadata = universe_data.get("metadata", {})
                business_context = universe_data.get("business_context", {})
                current_state = business_context.get("current_state", {})

                # Parse merchant and scenario from universe_id
                universe_id = metadata.get("universe_id", "")
                parts = universe_id.split("_")
                if len(parts) >= FileFormats.UNIVERSE_ID_MIN_PARTS:
                    merchant_id = "_".join(parts[:-2])  # Everything except last 2 parts
                    scenario_id = parts[-2]  # Second to last part
                else:
                    # Fallback parsing
                    merchant_id = metadata.get("merchant_id", "unknown")
                    scenario_id = metadata.get("scenario_id", "unknown")

                universes.append(
                    {
                        "universe_id": universe_id,
                        "merchant_id": merchant_id,
                        "scenario_id": scenario_id,
                        "generated_at": metadata.get("generated_at", ""),
                        "timeline_days": metadata.get("timeline_days", 90),
                        "current_day": metadata.get("current_day", 1),
                        "total_customers": len(universe_data.get("customers", [])),
                        "total_tickets": len(universe_data.get("support_tickets", [])),
                        "mrr": current_state.get("mrr", 0),
                        "csat_score": current_state.get("csat_score", 0),
                    }
                )
            except Exception:
                # Skip universes that can't be loaded
                continue

    return universes
