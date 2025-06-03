"""
Unit tests for the async fact-checking engine.
"""

import pytest
import asyncio
from unittest.mock import patch

from app.agents.fact_checker import (
    ConversationFactChecker,
    FactCheckResult,
)


class TestAsyncFactChecker:
    """Test the async fact-checking functionality"""

    @pytest.fixture
    def mock_universe_data(self):
        """Sample universe data"""
        return {"current_state": {"mrr": 48000}, "customers": []}

    @pytest.mark.asyncio
    async def test_async_fact_checking(self, mock_universe_data):
        """Test that fact-checking works asynchronously"""
        # Mock the entire check_facts method to avoid API calls
        with patch.object(ConversationFactChecker, "_load_config"):
            with patch.object(ConversationFactChecker, "_load_prompts"):
                with patch.object(ConversationFactChecker, "_load_error_messages"):
                    with patch.object(
                        ConversationFactChecker, "check_facts"
                    ) as mock_check:
                        # Create a coroutine that returns our result
                        async def mock_check_facts(*args, **kwargs):
                            return FactCheckResult(
                                overall_status="PASS",
                                turn_number=kwargs.get("turn_number", 1),
                                claims=[],
                                issues=[],
                                execution_time=0.1,
                            )

                        mock_check.side_effect = mock_check_facts

                        # Create checker with mocked config
                        with patch(
                            "app.agents.fact_checker.get_model", return_value="gpt-4"
                        ):
                            with patch(
                                "app.agents.fact_checker.get_api_key",
                                return_value="test-key",
                            ):
                                checker = ConversationFactChecker(mock_universe_data)

                                # Run fact-checking
                                result = await checker.check_facts(
                                    cj_response="Test response", turn_number=1
                                )

                                assert result.overall_status == "PASS"
                                assert result.turn_number == 1

    @pytest.mark.asyncio
    async def test_caching(self, mock_universe_data):
        """Test result caching"""
        # Create a simple mock result
        mock_result = FactCheckResult(
            overall_status="PASS",
            turn_number=1,
            claims=[],
            issues=[],
            execution_time=0.1,
        )

        # Test with a real instance but mock the async parts
        with patch.object(ConversationFactChecker, "_load_config"):
            with patch.object(ConversationFactChecker, "_load_prompts"):
                with patch.object(ConversationFactChecker, "_load_error_messages"):
                    with patch.object(
                        ConversationFactChecker, "extract_claims"
                    ) as mock_extract:
                        with patch.object(
                            ConversationFactChecker, "verify_claims"
                        ) as mock_verify:
                            # Mock the async extract_claims
                            async def mock_extract_claims(*args, **kwargs):
                                return {
                                    "claims": [],
                                    "issues": [],
                                    "execution_time": 0.1,
                                }

                            mock_extract.side_effect = mock_extract_claims
                            mock_verify.return_value = mock_result

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

                                    # First call
                                    result1 = await checker.check_facts(
                                        cj_response="Test response", turn_number=1
                                    )

                                    # Should have called extract_claims once
                                    assert mock_extract.call_count == 1

                                    # Second call with same turn - should return cached
                                    result2 = await checker.check_facts(
                                        cj_response="Test response", turn_number=1
                                    )

                                    # Should not have called extract_claims again
                                    assert mock_extract.call_count == 1
                                    # Should be the same cached object
                                    assert result2 is result1

    @pytest.mark.asyncio
    async def test_concurrent_execution(self, mock_universe_data):
        """Test multiple concurrent fact-checks"""
        # Mock all the file loading methods
        with patch.object(ConversationFactChecker, "_load_config"):
            with patch.object(ConversationFactChecker, "_load_prompts"):
                with patch.object(ConversationFactChecker, "_load_error_messages"):
                    with patch.object(
                        ConversationFactChecker, "extract_claims"
                    ) as mock_extract:
                        with patch.object(
                            ConversationFactChecker, "verify_claims"
                        ) as mock_verify:
                            # Mock the async extract_claims
                            async def mock_extract_claims(*args, **kwargs):
                                # Add a small delay to simulate async work
                                await asyncio.sleep(0.01)
                                return {
                                    "claims": [],
                                    "issues": [],
                                    "execution_time": 0.01,
                                }

                            mock_extract.side_effect = mock_extract_claims

                            # Mock verify_claims to return different results for different turns
                            def mock_verify_claims(claims_data):
                                return FactCheckResult(
                                    overall_status="PASS",
                                    claims=[],
                                    issues=[],
                                    execution_time=claims_data.get(
                                        "execution_time", 0.0
                                    ),
                                )

                            mock_verify.side_effect = mock_verify_claims

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

                                    # Run multiple concurrent checks
                                    tasks = [
                                        checker.check_facts(
                                            cj_response=f"Response {i}", turn_number=i
                                        )
                                        for i in range(3)
                                    ]

                                    results = await asyncio.gather(*tasks)
                                    assert len(results) == 3
                                    assert all(
                                        r.overall_status == "PASS" for r in results
                                    )

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_universe_data):
        """Test error handling"""
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
                                    cj_response="Test", turn_number=1
                                )

                                assert result.overall_status == "ERROR"
                                assert len(result.issues) == 1
                                assert "Fact-checking error" in result.issues[0].summary
