"""Data consistency evaluator for testing data agent behavior."""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from app.constants import TimeConstants


@dataclass
class ExtractedMetrics:
    """Metrics extracted from CJ's response."""

    total_tickets: Optional[int] = None
    urgent_tickets: Optional[int] = None
    response_time_hours: Optional[float] = None
    response_time_minutes: Optional[int] = None
    csat_score: Optional[float] = None

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for comparison."""
        return {
            "total_tickets": self.total_tickets,
            "urgent_tickets": self.urgent_tickets,
            "response_time_hours": self.response_time_hours,
            "response_time_minutes": self.response_time_minutes,
            "csat_score": self.csat_score,
        }


class DataConsistencyEvaluator:
    """Evaluates data consistency across CJ responses."""

    def __init__(self):
        self.conversation_metrics: List[ExtractedMetrics] = []

    def extract_metrics(self, cj_response: str) -> ExtractedMetrics:
        """Extract metrics from CJ's response using regex patterns."""
        metrics = ExtractedMetrics()

        # Extract total tickets (various formats)
        # Patterns: "187 open tickets", "Total tickets: 187", "187 tickets"
        ticket_patterns = [
            r"(\d+)\s+open\s+tickets",
            r"(\d+)\s+total\s+tickets",
            r"Total\s+tickets[:\s]+(\d+)",
            r"(\d+)\s+tickets\s+in\s+queue",
            r"(\d+)\s+active\s+tickets",
        ]
        for pattern in ticket_patterns:
            match = re.search(pattern, cj_response, re.IGNORECASE)
            if match:
                metrics.total_tickets = int(match.group(1))
                break

        # Extract urgent/escalated tickets
        urgent_patterns = [
            r"(\d+)\s+urgent\s+escalations?",
            r"(\d+)\s+urgent\s+tickets?",
            r"(\d+)\s+escalated\s+tickets?",
            r"Urgent[:\s]+(\d+)",
        ]
        for pattern in urgent_patterns:
            match = re.search(pattern, cj_response, re.IGNORECASE)
            if match:
                metrics.urgent_tickets = int(match.group(1))
                break

        # Extract response time
        # Patterns: "4.1 hour response time", "245 minute response time", "Response time: 4.1 hours"
        response_patterns = [
            r"([\d.]+)\s+hour\s+response\s+time",
            r"Response\s+time[:\s]+([\d.]+)\s+hours?",
            r"Avg\.?\s+response[:\s]+([\d.]+)\s+hours?",
        ]
        for pattern in response_patterns:
            match = re.search(pattern, cj_response, re.IGNORECASE)
            if match:
                metrics.response_time_hours = float(match.group(1))
                break

        # Also check for minutes
        minute_patterns = [
            r"(\d+)\s+minute\s+response\s+time",
            r"Response\s+time[:\s]+(\d+)\s+minutes?",
            r"Avg\.?\s+response[:\s]+(\d+)\s+minutes?",
        ]
        for pattern in minute_patterns:
            match = re.search(pattern, cj_response, re.IGNORECASE)
            if match:
                metrics.response_time_minutes = int(match.group(1))
                break

        # Extract CSAT score
        # Patterns: "CSAT: 3.3/5.0", "CSAT 72%", "Customer satisfaction: 3.3"
        csat_patterns = [
            r"CSAT[:\s]+([\d.]+)(?:/5)?",
            r"Customer\s+satisfaction[:\s]+([\d.]+)",
            r"CSAT\s+score[:\s]+([\d.]+)",
            r"Satisfaction[:\s]+([\d.]+)%",
        ]
        for pattern in csat_patterns:
            match = re.search(pattern, cj_response, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                # Convert percentage to 5-point scale if needed
                if score > 5:
                    metrics.csat_score = score
                else:
                    metrics.csat_score = score
                break

        return metrics

    def add_response(self, cj_response: str) -> ExtractedMetrics:
        """Add a response and extract its metrics."""
        metrics = self.extract_metrics(cj_response)
        self.conversation_metrics.append(metrics)
        return metrics

    def check_consistency(self, tolerance: float = 0.05) -> Tuple[bool, str]:
        """Check if metrics are consistent across responses.

        Args:
            tolerance: Allowed variance (default 5%)

        Returns:
            Tuple of (is_consistent, explanation)
        """
        if len(self.conversation_metrics) < 2:
            return True, "Not enough responses to check consistency"

        issues = []

        # Get first response metrics as baseline
        baseline = self.conversation_metrics[0]

        for i, metrics in enumerate(self.conversation_metrics[1:], 1):
            # Check total tickets consistency
            if baseline.total_tickets and metrics.total_tickets:
                variance = (
                    abs(metrics.total_tickets - baseline.total_tickets)
                    / baseline.total_tickets
                )
                if variance > tolerance:
                    issues.append(
                        f"Total tickets varied by {variance*100:.1f}% "
                        f"(response 1: {baseline.total_tickets}, response {i+1}: {metrics.total_tickets})"
                    )

            # Check CSAT consistency
            if baseline.csat_score and metrics.csat_score:
                variance = (
                    abs(metrics.csat_score - baseline.csat_score) / baseline.csat_score
                )
                if variance > tolerance:
                    issues.append(
                        f"CSAT score varied by {variance*100:.1f}% "
                        f"(response 1: {baseline.csat_score}, response {i+1}: {metrics.csat_score})"
                    )

            # Check response time consistency (convert to same unit)
            baseline_minutes = (
                baseline.response_time_hours * 60
                if baseline.response_time_hours
                else baseline.response_time_minutes
            )
            metrics_minutes = (
                metrics.response_time_hours * 60
                if metrics.response_time_hours
                else metrics.response_time_minutes
            )

            if baseline_minutes and metrics_minutes:
                variance = abs(metrics_minutes - baseline_minutes) / baseline_minutes
                if variance > tolerance:
                    issues.append(
                        f"Response time varied by {variance*100:.1f}% "
                        f"(response 1: {baseline_minutes} min, response {i+1}: {metrics_minutes} min)"
                    )

        if issues:
            return False, "Data inconsistencies found:\n" + "\n".join(issues)

        return True, "All metrics are consistent within tolerance"

    def validate_scenario_bounds(self, scenario: str) -> Tuple[bool, str]:
        """Validate that metrics are within expected bounds for the scenario."""
        if not self.conversation_metrics:
            return True, "No metrics to validate"

        # Define expected bounds per scenario
        scenario_bounds = {
            # Crisis scenarios
            "churn_spike": {
                "total_tickets": (100, 200),
                "csat_score": (3.0, 3.8),  # On 5-point scale
                "csat_percentage": (65, 75),  # If percentage
                "response_time_minutes": (180, 360),  # 3-6 hours
            },
            "growth_stall": {
                "total_tickets": (30, 50),
                "csat_score": (4.0, 4.5),
                "csat_percentage": (80, 90),
                "response_time_minutes": (120, 180),  # 2-3 hours
            },
            "scaling_chaos": {
                "total_tickets": (200, 350),
                "csat_score": (3.5, 4.0),
                "csat_percentage": (70, 80),
                "response_time_minutes": (
                    TimeConstants.MIN_RESPONSE_TIME_MINUTES,
                    TimeConstants.MAX_RESPONSE_TIME_MINUTES,
                ),
            },
            # Normal scenarios
            "summer_lull": {
                "total_tickets": (30, 45),
                "csat_score": (4.2, 4.6),
                "csat_percentage": (84, 92),
                "response_time_minutes": (90, 150),  # 1.5-2.5 hours
            },
            "pre_holiday_prep": {
                "total_tickets": (40, 60),
                "csat_score": (4.3, 4.7),
                "csat_percentage": (86, 94),
                "response_time_minutes": (90, 180),  # 1.5-3 hours
            },
            "steady_operations": {
                "total_tickets": (25, 40),
                "csat_score": (4.3, 4.5),
                "csat_percentage": (86, 90),
                "response_time_minutes": (60, 120),  # 1-2 hours
            },
            "mothers_day_prep": {
                "total_tickets": (50, 70),
                "csat_score": (4.2, 4.6),
                "csat_percentage": (84, 92),
                "response_time_minutes": (120, 180),  # 2-3 hours
            },
            "memorial_day_weekend": {
                "total_tickets": (20, 35),
                "csat_score": (4.3, 4.6),
                "csat_percentage": (86, 92),
                "response_time_minutes": (60, 120),  # 1-2 hours
            },
            "post_black_friday": {
                "total_tickets": (60, 80),
                "csat_score": (4.0, 4.5),
                "csat_percentage": (80, 90),
                "response_time_minutes": (120, 240),  # 2-4 hours
            },
            "january_reset": {
                "total_tickets": (35, 50),
                "csat_score": (4.2, 4.5),
                "csat_percentage": (84, 90),
                "response_time_minutes": (90, 150),  # 1.5-2.5 hours
            },
        }

        if scenario not in scenario_bounds:
            return True, f"No bounds defined for scenario: {scenario}"

        bounds = scenario_bounds[scenario]
        issues = []

        for i, metrics in enumerate(self.conversation_metrics):
            # Check total tickets
            if metrics.total_tickets:
                min_val, max_val = bounds["total_tickets"]
                if not (min_val <= metrics.total_tickets <= max_val):
                    issues.append(
                        f"Response {i+1}: Total tickets ({metrics.total_tickets}) "
                        f"outside expected range {min_val}-{max_val}"
                    )

            # Check CSAT
            if metrics.csat_score:
                # Determine if it's percentage or 5-point scale
                if metrics.csat_score > 10:  # Likely percentage
                    min_val, max_val = bounds["csat_percentage"]
                else:  # 5-point scale
                    min_val, max_val = bounds["csat_score"]

                if not (min_val <= metrics.csat_score <= max_val):
                    issues.append(
                        f"Response {i+1}: CSAT ({metrics.csat_score}) "
                        f"outside expected range {min_val}-{max_val}"
                    )

            # Check response time
            response_minutes = (
                metrics.response_time_hours * 60
                if metrics.response_time_hours
                else metrics.response_time_minutes
            )
            if response_minutes:
                min_val, max_val = bounds["response_time_minutes"]
                if not (min_val <= response_minutes <= max_val):
                    issues.append(
                        f"Response {i+1}: Response time ({response_minutes} min) "
                        f"outside expected range {min_val}-{max_val} min"
                    )

        if issues:
            return False, "Metrics outside scenario bounds:\n" + "\n".join(issues)

        return True, "All metrics within expected scenario bounds"
