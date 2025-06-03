"""
Unit tests for the fact-checking engine.
"""

import pytest
from unittest.mock import patch
from app.agents.fact_checker import (
    ConversationFactChecker,
    FactCheckResult,
    FactClaim,
    FactIssue,
    VerificationStatus,
    Severity,
)


class TestFactChecker:
    """Test the core fact-checking functionality"""

    @pytest.fixture
    def mock_universe_data(self):
        """Sample universe data for testing"""
        return {
            "current_state": {
                "mrr": 48000,
                "subscriber_count": 1200,
                "churn_rate": 8.5,
                "csat_score": 4.2,
                "support_tickets_per_day": 25,
            },
            "customers": [
                {
                    "customer_id": "CUST001",
                    "name": "John Smith",
                    "email": "john.smith@example.com",
                    "subscription_tier": "Premium Box",
                    "satisfaction_score": 5,
                },
                {
                    "customer_id": "CUST002",
                    "name": "Jane Doe",
                    "email": "jane.doe@example.com",
                    "subscription_tier": "Classic Box",
                    "satisfaction_score": 3,
                },
            ],
            "timeline_events": [
                {
                    "day": 1,
                    "date": "2024-01-01",
                    "event": "New Year promotion launched",
                    "impact": "positive",
                }
            ],
        }

    def test_fact_claim_creation(self):
        """Test creating fact claims"""
        claim = FactClaim(
            claim="We have 1200 subscribers",
            verification=VerificationStatus.VERIFIED,
            actual_data="1200",
            source="universe",
        )

        assert claim.claim == "We have 1200 subscribers"
        assert claim.verification == VerificationStatus.VERIFIED
        assert claim.to_dict()["verification"] == "VERIFIED"

    def test_fact_issue_creation(self):
        """Test creating fact issues"""
        issue = FactIssue(
            severity=Severity.MAJOR,
            summary="Incorrect subscriber count",
            claim="We have 1500 subscribers",
            expected="1200",
            actual="1500",
        )

        assert issue.severity == Severity.MAJOR
        assert issue.to_dict()["severity"] == "major"

    def test_fact_check_result_properties(self):
        """Test fact check result properties"""
        result = FactCheckResult(overall_status="WARNING")

        # Add some issues
        result.issues.append(
            FactIssue(severity=Severity.MINOR, summary="Minor discrepancy")
        )
        result.issues.append(
            FactIssue(severity=Severity.CRITICAL, summary="Critical error")
        )

        assert result.has_issues is True
        assert len(result.critical_issues) == 1
        assert result.critical_issues[0].severity == Severity.CRITICAL

    def test_extract_json_from_response(self):
        """Test JSON extraction"""
        # Create a simple fact checker with mocked dependencies
        with patch.object(ConversationFactChecker, "_load_config"):
            with patch.object(ConversationFactChecker, "_load_prompts"):
                with patch.object(ConversationFactChecker, "_load_error_messages"):
                    with patch(
                        "app.agents.fact_checker.get_model", return_value="gpt-4"
                    ):
                        with patch(
                            "app.agents.fact_checker.get_api_key",
                            return_value="test-key",
                        ):
                            checker = ConversationFactChecker({})

                            # In JSON mode, we only get clean JSON from the API
                            clean_json = '{"claims": [], "issues": []}'
                            result = checker._extract_json(clean_json)
                            assert result == {"claims": [], "issues": []}

    def test_format_tool_outputs(self):
        """Test formatting of tool outputs"""
        with patch.object(ConversationFactChecker, "_load_config"):
            with patch.object(ConversationFactChecker, "_load_prompts"):
                with patch.object(ConversationFactChecker, "_load_error_messages"):
                    with patch(
                        "app.agents.fact_checker.get_model", return_value="gpt-4"
                    ):
                        with patch(
                            "app.agents.fact_checker.get_api_key",
                            return_value="test-key",
                        ):
                            checker = ConversationFactChecker({})

                            tool_outputs = [
                                {
                                    "tool": "get_support_dashboard",
                                    "output": {
                                        "queue_size": 25,
                                        "avg_response_time": 2.5,
                                    },
                                },
                                {
                                    "tool": "get_customer_profile",
                                    "output": {
                                        "customer_id": "CUST001",
                                        "name": "John Smith",
                                    },
                                },
                            ]

                            formatted = checker._format_tool_outputs(tool_outputs)
                            assert "get_support_dashboard" in formatted
                            assert "queue_size" in formatted
                            assert "get_customer_profile" in formatted
                            assert "John Smith" in formatted

    def test_verify_claims_pass(self):
        """Test verifying claims with no issues"""
        with patch.object(ConversationFactChecker, "_load_config"):
            with patch.object(ConversationFactChecker, "_load_prompts"):
                with patch.object(ConversationFactChecker, "_load_error_messages"):
                    with patch(
                        "app.agents.fact_checker.get_model", return_value="gpt-4"
                    ):
                        with patch(
                            "app.agents.fact_checker.get_api_key",
                            return_value="test-key",
                        ):
                            checker = ConversationFactChecker({})

                            claims_data = {
                                "claims": [
                                    {
                                        "claim": "We have 1200 subscribers",
                                        "verification": "VERIFIED",
                                        "actual_data": "1200",
                                        "source": "universe",
                                    }
                                ],
                                "issues": [],
                            }

                            result = checker.verify_claims(claims_data)
                            assert result.overall_status == "PASS"
                            assert len(result.claims) == 1
                            assert len(result.issues) == 0

    def test_verify_claims_with_issues(self):
        """Test verifying claims with issues"""
        with patch.object(ConversationFactChecker, "_load_config"):
            with patch.object(ConversationFactChecker, "_load_prompts"):
                with patch.object(ConversationFactChecker, "_load_error_messages"):
                    with patch(
                        "app.agents.fact_checker.get_model", return_value="gpt-4"
                    ):
                        with patch(
                            "app.agents.fact_checker.get_api_key",
                            return_value="test-key",
                        ):
                            checker = ConversationFactChecker({})

                            claims_data = {
                                "claims": [
                                    {
                                        "claim": "We have 1500 subscribers",
                                        "verification": "INCORRECT",
                                        "actual_data": "1200",
                                        "source": "universe",
                                    }
                                ],
                                "issues": [
                                    {
                                        "severity": "major",
                                        "summary": "Incorrect subscriber count",
                                        "claim": "We have 1500 subscribers",
                                        "expected": "1200",
                                        "actual": "1500",
                                    }
                                ],
                            }

                            result = checker.verify_claims(claims_data)
                            assert result.overall_status == "WARNING"
                            assert len(result.issues) == 1
                            assert result.issues[0].severity == Severity.MAJOR

    @pytest.mark.asyncio
    async def test_check_facts_integration(self, mock_universe_data):
        """Test full fact-checking flow"""
        # Mock all dependencies
        with patch.object(ConversationFactChecker, "_load_config"):
            with patch.object(ConversationFactChecker, "_load_prompts"):
                with patch.object(ConversationFactChecker, "_load_error_messages"):
                    with patch.object(
                        ConversationFactChecker, "extract_claims"
                    ) as mock_extract:
                        with patch.object(
                            ConversationFactChecker, "verify_claims"
                        ) as mock_verify:
                            # Mock extract_claims to return claims data
                            async def mock_extract_claims(*args, **kwargs):
                                return {
                                    "claims": [
                                        {
                                            "claim": "We have 1200 active subscribers",
                                            "type": "metric",
                                            "expected_value": "1200",
                                        }
                                    ],
                                    "execution_time": 0.1,
                                }

                            mock_extract.side_effect = mock_extract_claims

                            # Mock verify_claims to return a result
                            mock_verify.return_value = FactCheckResult(
                                overall_status="PASS",
                                claims=[
                                    FactClaim(
                                        claim="We have 1200 active subscribers",
                                        verification=VerificationStatus.VERIFIED,
                                        actual_data="1200",
                                        source="universe",
                                    )
                                ],
                                issues=[],
                                execution_time=0.1,
                            )

                            with patch(
                                "app.agents.fact_checker.get_model",
                                return_value="gpt-4",
                            ):
                                with patch(
                                    "app.agents.fact_checker.get_api_key",
                                    return_value="test-key",
                                ):
                                    checker = ConversationFactChecker(
                                        mock_universe_data
                                    )

                                    cj_response = "We have 1200 active subscribers."
                                    tool_outputs = []

                                    result = await checker.check_facts(
                                        cj_response, tool_outputs, turn_number=1
                                    )

                                    assert result.overall_status == "PASS"
                                    assert len(result.claims) == 1
                                    assert (
                                        result.claims[0].verification
                                        == VerificationStatus.VERIFIED
                                    )
                                    assert result.turn_number == 1
                                    assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_check_facts_with_error(self, mock_universe_data):
        """Test fact-checking with error handling"""
        with patch.object(ConversationFactChecker, "_load_config"):
            with patch.object(ConversationFactChecker, "_load_prompts"):
                with patch.object(ConversationFactChecker, "_load_error_messages"):
                    with patch.object(
                        ConversationFactChecker, "extract_claims"
                    ) as mock_extract:
                        # Mock extract_claims to raise an exception
                        async def mock_extract_error(*args, **kwargs):
                            raise Exception("API Error")

                        mock_extract.side_effect = mock_extract_error

                        with patch(
                            "app.agents.fact_checker.get_model", return_value="gpt-4"
                        ):
                            with patch(
                                "app.agents.fact_checker.get_api_key",
                                return_value="test-key",
                            ):
                                checker = ConversationFactChecker(mock_universe_data)

                                result = await checker.check_facts(
                                    "Some response", [], turn_number=1
                                )

                                assert result.overall_status == "ERROR"
                                assert len(result.issues) == 1
                                assert "Fact-checking error" in result.issues[0].summary
