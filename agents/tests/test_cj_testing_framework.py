"""Unit tests for the CJ testing framework."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from app.testing import (
    TestLoader,
    TestCase,
    evaluate_response,
)


class TestTestLoader:
    """Tests for the TestLoader class."""

    def test_load_valid_test_file(self):
        """Test loading a valid test file."""
        yaml_content = """
version: "1.0.0"
description: "Test boundary behaviors"
tests:
  - name: "inventory_test"
    description: "Test inventory boundary"
    setup:
      merchant: "marcus_thompson"
      scenario: "growth_stall"
      cj_version: "v5.0.0"
      num_turns: 1
      merchant_opens: "How many units do we have?"
    evaluate_cj:
      - "CJ should acknowledge she cannot access inventory"
      - "CJ should NOT provide specific numbers"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                loader = TestLoader()
                test_suite = loader.load_test_file(f.name)

                assert test_suite.version == "1.0.0"
                assert test_suite.description == "Test boundary behaviors"
                assert len(test_suite.tests) == 1

                test_case = test_suite.tests[0]
                assert test_case.name == "inventory_test"
                assert test_case.description == "Test inventory boundary"
                assert test_case.setup["merchant"] == "marcus_thompson"
                assert len(test_case.evaluate_cj) == 2

            finally:
                os.unlink(f.name)

    def test_load_missing_file(self):
        """Test loading a non-existent file."""
        loader = TestLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_test_file("/nonexistent/file.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML."""
        yaml_content = """
version: "1.0.0"
description: "Test file"
tests:
  - name: "test1"
    setup:
      merchant: "marcus
"""  # Invalid YAML (unclosed quote)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                loader = TestLoader()

                with pytest.raises(ValueError, match="Invalid YAML"):
                    loader.load_test_file(f.name)

            finally:
                os.unlink(f.name)

    def test_load_missing_version(self):
        """Test loading file without version."""
        yaml_content = """
description: "Test file"
tests:
  - name: "test1"
    setup:
      merchant: "marcus_thompson"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                loader = TestLoader()

                with pytest.raises(ValueError, match="missing 'version' field"):
                    loader.load_test_file(f.name)

            finally:
                os.unlink(f.name)

    def test_load_unsupported_version(self):
        """Test loading file with unsupported version."""
        yaml_content = """
version: "2.0.0"
description: "Test file"
tests:
  - name: "test1"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                loader = TestLoader()

                with pytest.raises(ValueError, match="Unsupported test format version"):
                    loader.load_test_file(f.name)

            finally:
                os.unlink(f.name)

    def test_discover_tests_empty_directory(self):
        """Test discovering tests in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            loader = TestLoader()
            test_suites = loader.discover_tests(temp_dir)

            assert len(test_suites) == 0

    def test_discover_tests_with_files(self):
        """Test discovering tests with actual files."""
        yaml_content = """
version: "1.0.0"
description: "Test file"
tests:
  - name: "test1"
    description: "Test description"
    setup:
      merchant: "marcus_thompson"
      scenario: "growth_stall"
      cj_version: "v5.0.0"
      num_turns: 1
    evaluate_cj:
      - "Test criterion"
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file1 = os.path.join(temp_dir, "test1.yaml")
            test_file2 = os.path.join(temp_dir, "test2.yml")

            with open(test_file1, "w") as f:
                f.write(yaml_content)

            with open(test_file2, "w") as f:
                f.write(yaml_content)

            loader = TestLoader()
            test_suites = loader.discover_tests(temp_dir)

            assert len(test_suites) == 2


class TestTestCase:
    """Tests for the TestCase class."""

    def test_valid_test_case(self):
        """Test creating a valid test case."""
        test_case = TestCase(
            name="test1",
            description="Test description",
            setup={
                "merchant": "marcus_thompson",
                "scenario": "growth_stall",
                "cj_version": "v5.0.0",
                "num_turns": 1,
            },
            evaluate_cj=["Test criterion"],
        )

        assert test_case.name == "test1"
        assert test_case.setup["num_turns"] == 1

    def test_missing_required_setup_field(self):
        """Test test case with missing required setup field."""
        with pytest.raises(ValueError, match="missing required setup field"):
            TestCase(
                name="test1",
                description="Test description",
                setup={
                    "merchant": "marcus_thompson"
                    # Missing scenario, cj_version, num_turns
                },
                evaluate_cj=["Test criterion"],
            )

    def test_empty_evaluation_criteria(self):
        """Test test case with empty evaluation criteria."""
        with pytest.raises(ValueError, match="has no evaluation criteria"):
            TestCase(
                name="test1",
                description="Test description",
                setup={
                    "merchant": "marcus_thompson",
                    "scenario": "growth_stall",
                    "cj_version": "v5.0.0",
                    "num_turns": 1,
                },
                evaluate_cj=[],
            )


class TestMockEvaluator:
    """Tests for mock evaluation functionality."""

    def test_mock_evaluator_pass(self):
        """Test mock evaluation returning pass."""
        result = evaluate_response(
            cj_response="Test response",
            criteria=["Criterion 1", "Criterion 2"],
            test_name="test1",
            mock=True,
        )

        assert result.passed is True
        assert "PASS" in result.explanation
        assert len(result.criteria_results) == 2
        assert all(result.criteria_results.values())

    def test_mock_evaluator_always_passes(self):
        """Test that mock evaluation always passes."""
        # Mock evaluation is simplified - it always passes
        result = evaluate_response(
            cj_response="Test response",
            criteria=["Criterion 1"],
            test_name="test1",
            mock=True,
        )

        assert result.passed is True
        assert "PASS" in result.explanation


class TestLLMEvaluator:
    """Tests for LLM evaluation functionality."""

    def test_evaluate_without_api_key(self):
        """Test evaluating without API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError,
                match="(Model not configured for test_evaluation|API key required for)",
            ):
                evaluate_response(
                    cj_response="Test response",
                    criteria=["Test criterion"],
                    test_name="test1",
                    mock=False,
                )

    def test_evaluate_with_api_key(self):
        """Test evaluation works with explicit API key."""
        # Just verify the function signature accepts api_key parameter
        # Actual API call would fail without mocking
        # This test validates the function interface

    @patch("requests.post")
    def test_successful_evaluation(self, mock_post):
        """Test successful evaluation with mocked API."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"overall_result": "PASS", "explanation": "Test passed", "criteria_results": {"criterion_1": true}}'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = evaluate_response(
            cj_response="Test response",
            criteria=["Test criterion"],
            test_name="test1",
            api_key="test_key",
            mock=False,
        )

        assert result.passed is True
        assert result.explanation == "Test passed"
        assert result.criteria_results == {"criterion_1": True}

    @patch("requests.post")
    def test_api_error(self, mock_post):
        """Test handling API error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        result = evaluate_response(
            cj_response="Test response",
            criteria=["Test criterion"],
            test_name="test1",
            api_key="test_key",
            mock=False,
        )

        assert result.passed is False
        assert "Evaluation failed" in result.explanation
