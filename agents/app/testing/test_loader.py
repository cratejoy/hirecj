"""Test loader for CJ YAML test definitions."""

import os
import yaml
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum


@dataclass
class TestCase:
    """Represents a single test case for CJ behavior."""

    name: str
    description: str
    setup: Dict[str, Any]
    evaluate_cj: List[str]

    def __post_init__(self):
        """Validate test case after initialization."""
        # Ensure required setup fields
        required_setup = ["merchant", "scenario", "cj_version", "num_turns"]
        for field in required_setup:
            if field not in self.setup:
                raise ValueError(
                    f"Test '{self.name}' missing required setup field: {field}"
                )

        # Validate evaluation criteria
        if not self.evaluate_cj:
            raise ValueError(f"Test '{self.name}' has no evaluation criteria")

        # Set defaults
        if "num_turns" not in self.setup or self.setup["num_turns"] is None:
            self.setup["num_turns"] = 1


@dataclass
class TestSuite:
    """Represents a collection of test cases from a YAML file."""

    version: str
    description: str
    tests: List[TestCase]
    file_path: str


class ValidationLevel(Enum):
    """Validation strictness levels."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"


class TestLoader:
    """Loads and validates CJ test definitions from YAML files."""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """Initialize the test loader.

        Args:
            validation_level: How strict to be with validation
        """
        self.supported_versions = ["1.0.0"]
        self.validation_level = validation_level
        self.schema = self._load_schema()

    def set_validation_level(self, level: ValidationLevel) -> None:
        """Change validation level.

        Args:
            level: New validation level
        """
        self.validation_level = level

    def load_test_file(self, file_path: str) -> TestSuite:
        """Load a single YAML test file.

        Args:
            file_path: Path to the YAML test file

        Returns:
            TestSuite: Loaded and validated test suite

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Test file not found: {file_path}")

        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {file_path}: {e}")

        return self._parse_test_data(data, file_path)

    def discover_tests(self, test_dir: str) -> List[TestSuite]:
        """Discover and load all test files in a directory.

        Args:
            test_dir: Directory to search for YAML test files

        Returns:
            List[TestSuite]: All loaded test suites
        """
        test_suites = []
        test_path = Path(test_dir)

        if not test_path.exists():
            return test_suites

        # Find all .yaml and .yml files (excluding schema directory)
        for yaml_file in test_path.glob("**/*.yaml"):
            # Skip schema files
            if "schema" in str(yaml_file):
                continue
            try:
                test_suite = self.load_test_file(str(yaml_file))
                test_suites.append(test_suite)
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}")

        for yml_file in test_path.glob("**/*.yml"):
            # Skip schema files
            if "schema" in str(yml_file):
                continue
            try:
                test_suite = self.load_test_file(str(yml_file))
                test_suites.append(test_suite)
            except Exception as e:
                print(f"Warning: Failed to load {yml_file}: {e}")

        return test_suites

    def _load_schema(self) -> Optional[Dict[str, Any]]:
        """Load validation schema if available.

        Returns:
            Schema dictionary or None if not found
        """
        schema_path = (
            Path(__file__).parent.parent.parent
            / "tests"
            / "schema"
            / "test_schema.yaml"
        )
        if schema_path.exists():
            try:
                with open(schema_path, "r") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Could not load test schema: {e}")
        return None

    def _parse_test_data(self, data: Dict[str, Any], file_path: str) -> TestSuite:
        """Parse YAML data into TestSuite object.

        Args:
            data: Parsed YAML data
            file_path: Original file path for error reporting

        Returns:
            TestSuite: Validated test suite

        Raises:
            ValueError: If data format is invalid
        """
        # Validate top-level structure
        if not isinstance(data, dict):
            raise ValueError(f"Test file must contain a YAML object, got {type(data)}")

        # Check version
        version = data.get("version")
        if not version:
            raise ValueError("Test file missing 'version' field")

        if version not in self.supported_versions:
            raise ValueError(
                f"Unsupported test format version: {version}. Supported: {self.supported_versions}"
            )

        # Get description
        description = data.get("description", "")

        # Parse tests
        tests_data = data.get("tests", [])
        if not isinstance(tests_data, list):
            raise ValueError("'tests' field must be a list")

        if not tests_data:
            raise ValueError("Test file contains no tests")

        test_cases = []
        for i, test_data in enumerate(tests_data):
            try:
                test_case = self._parse_test_case(test_data)
                test_cases.append(test_case)
            except Exception as e:
                raise ValueError(f"Error in test {i+1}: {e}")

        return TestSuite(
            version=version,
            description=description,
            tests=test_cases,
            file_path=file_path,
        )

    def _parse_test_case(self, test_data: Dict[str, Any]) -> TestCase:
        """Parse a single test case from YAML data.

        Args:
            test_data: Test case data from YAML

        Returns:
            TestCase: Validated test case

        Raises:
            ValueError: If test case format is invalid
        """
        if not isinstance(test_data, dict):
            raise ValueError(f"Test case must be an object, got {type(test_data)}")

        # Required fields
        name = test_data.get("name")
        if not name:
            raise ValueError("Test case missing 'name' field")

        description = test_data.get("description", "")

        setup = test_data.get("setup")
        if not setup:
            raise ValueError(f"Test '{name}' missing 'setup' field")

        evaluate_cj = test_data.get("evaluate_cj")
        if not evaluate_cj:
            raise ValueError(f"Test '{name}' missing 'evaluate_cj' field")

        if not isinstance(evaluate_cj, list):
            raise ValueError(f"Test '{name}' 'evaluate_cj' must be a list")

        # Apply strict validation if enabled
        if self.validation_level == ValidationLevel.STRICT:
            self._strict_validate_test_case(name, description, setup, evaluate_cj)

        # Create and validate test case
        return TestCase(
            name=name, description=description, setup=setup, evaluate_cj=evaluate_cj
        )

    def validate_setup_config(self, setup: Dict[str, Any]) -> None:
        """Validate setup configuration.

        Args:
            setup: Setup configuration to validate

        Raises:
            ValueError: If setup is invalid
        """
        required_fields = ["merchant", "scenario", "cj_version", "num_turns"]

        for field in required_fields:
            if field not in setup:
                raise ValueError(f"Setup missing required field: {field}")

        # Validate specific fields
        if not isinstance(setup["num_turns"], int) or setup["num_turns"] < 1:
            raise ValueError("num_turns must be a positive integer")

        # Optional validation for known values
        known_merchants = ["marcus_thompson", "sarah_chen"]
        if setup["merchant"] not in known_merchants:
            print(
                f"Warning: Unknown merchant '{setup['merchant']}'. Known: {known_merchants}"
            )

        known_scenarios = [
            "growth_stall",
            "churn_spike",
            "scaling_chaos",
            "competitor_threat",
        ]
        if setup["scenario"] not in known_scenarios:
            print(
                f"Warning: Unknown scenario '{setup['scenario']}'. Known: {known_scenarios}"
            )

    def _strict_validate_test_case(
        self, name: str, description: str, setup: Dict[str, Any], evaluate_cj: List[str]
    ) -> None:
        """Perform strict validation on test case fields.

        Args:
            name: Test case name
            description: Test case description
            setup: Setup configuration
            evaluate_cj: Evaluation criteria

        Raises:
            ValueError: If validation fails
        """
        if not self.schema:
            return  # Skip if no schema available

        # Validate test name pattern
        if not re.match(r"^[a-z0-9_]+$", name):
            raise ValueError(f"Test name '{name}' must match pattern '^[a-z0-9_]+$'")

        # Validate description length
        if len(description) > 500:
            raise ValueError(
                f"Test description exceeds 500 characters: {len(description)}"
            )

        # Validate setup fields
        self._validate_setup_strict(setup)

        # Validate evaluation criteria
        self._validate_criteria_strict(evaluate_cj)

    def _validate_setup_strict(self, setup: Dict[str, Any]) -> None:
        """Strictly validate setup configuration.

        Args:
            setup: Setup configuration to validate

        Raises:
            ValueError: If validation fails
        """
        if not self.schema:
            return

        schema_setup = self.schema.get("setup", {})
        required_fields = schema_setup.get("required_fields", [])
        field_types = schema_setup.get("field_types", {})
        valid_values = schema_setup.get("valid_values", {})

        # Check required fields
        for field in required_fields:
            if field not in setup:
                raise ValueError(f"Setup missing required field: {field}")

        # Check field types
        for field, value in setup.items():
            expected_type = field_types.get(field)
            if expected_type and not self._check_type(value, expected_type):
                raise ValueError(
                    f"Setup field '{field}' must be {expected_type}, got {type(value).__name__}"
                )

        # Check valid values
        for field, value in setup.items():
            if field in valid_values and value not in valid_values[field]:
                raise ValueError(
                    f"Setup field '{field}' has invalid value '{value}'. Valid: {valid_values[field]}"
                )

    def _validate_criteria_strict(self, criteria: List[str]) -> None:
        """Strictly validate evaluation criteria.

        Args:
            criteria: List of evaluation criteria

        Raises:
            ValueError: If validation fails
        """
        if not self.schema:
            return

        schema_criteria = self.schema.get("evaluate_cj", {})
        min_items = schema_criteria.get("min_items", 1)
        max_items = schema_criteria.get("max_items", 10)

        if len(criteria) < min_items:
            raise ValueError(
                f"Must have at least {min_items} evaluation criteria, got {len(criteria)}"
            )

        if len(criteria) > max_items:
            raise ValueError(
                f"Must have at most {max_items} evaluation criteria, got {len(criteria)}"
            )

        for criterion in criteria:
            if len(criterion) > 200:
                raise ValueError(
                    f"Evaluation criterion exceeds 200 characters: {len(criterion)}"
                )

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type.

        Args:
            value: Value to check
            expected_type: Expected type name

        Returns:
            True if type matches
        """
        type_mapping = {
            "string": str,
            "integer": int,
            "array": list,
            "object": dict,
            "boolean": bool,
        }

        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        return True  # Unknown type, allow it
