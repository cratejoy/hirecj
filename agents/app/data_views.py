"""Data view definitions for workflows."""

from datetime import datetime, date
from typing import List, Dict, Any
from pydantic import BaseModel


class MetricTrend(BaseModel):
    """A metric with its trend over time."""

    current_value: float
    previous_value: float
    change_percent: float
    trend_direction: str  # "up", "down", "flat"

    @property
    def formatted_change(self) -> str:
        """Format the change for display."""
        symbol = "+" if self.change_percent > 0 else ""
        return f"{symbol}{self.change_percent:.1f}%"


class DailyBriefingView(BaseModel):
    """Data view for daily briefing workflow."""

    date: date
    mrr: MetricTrend
    active_subscribers: MetricTrend
    churn_rate: MetricTrend
    overnight_tickets: int
    ticket_categories: Dict[str, int]  # e.g., {"shipping": 12, "quality": 5}
    csat_score: float
    urgent_issues: List[str]

    def to_flash_report(self) -> str:
        """Format as CJ's daily flash report."""
        return f"""📊 Daily Flash - {self.date.strftime('%B %d')}:
• MRR: ${self.mrr.current_value:,.0f} ({self.mrr.formatted_change})
• Subscribers: {self.active_subscribers.current_value:,.0f} ({self.active_subscribers.formatted_change})
• Churn: {self.churn_rate.current_value:.1%} ({self.churn_rate.formatted_change})
• Overnight tickets: {self.overnight_tickets}
• CSAT: {self.csat_score}/5.0"""


class CrisisMetricsView(BaseModel):
    """Data view for crisis response workflow."""

    timestamp: datetime
    crisis_type: str  # "churn_spike", "quality_issue", "fulfillment_delay"
    severity: str  # "critical", "high", "medium"

    # Key metrics
    hourly_churn_count: int
    mrr_at_risk: float
    affected_customers: int

    # Root cause analysis
    cancellation_reasons: Dict[str, int]
    affected_segments: List[str]
    trending_complaints: List[str]

    # Recommendations
    immediate_actions: List[str]
    estimated_save_rate: float


class WeeklyReviewView(BaseModel):
    """Data view for weekly business review."""

    week_ending: date

    # Performance summary
    revenue_growth: MetricTrend
    customer_acquisition: MetricTrend
    retention_metrics: Dict[str, float]

    # Operational metrics
    avg_ticket_resolution_time: float
    fulfillment_accuracy: float
    inventory_turns: float

    # Competitive intelligence
    competitor_moves: List[str]
    market_trends: List[str]

    # Opportunities
    upsell_opportunities: int
    at_risk_segments: List[Dict[str, Any]]


class CustomerSegmentView(BaseModel):
    """Detailed view of a customer segment."""

    segment_name: str
    size: int
    avg_ltv: float
    avg_order_value: float
    churn_risk: str  # "low", "medium", "high"
    engagement_score: float
    common_issues: List[str]
    recommended_actions: List[str]
