#!/usr/bin/env python3
"""Test runner for CJ agent behavior tests."""

import argparse
import concurrent.futures
import os
import sys
import threading
import time
from typing import List, Dict, Any

# Add project root to path for local imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

# Local imports (after path setup)
from app.testing import (  # noqa: E402
    TestLoader,
    evaluate_response,
    TestReportGenerator,
    ValidationLevel,
)
from app.config import settings  # noqa: E402


class CJTestRunner:
    """Main test runner for CJ agent tests."""

    def __init__(
        self,
        use_mock_evaluator: bool = False,
        max_workers: int = 3,
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        exact_match: bool = False,
    ):
        """Initialize the test runner.

        Args:
            use_mock_evaluator: Whether to use mock evaluator instead of GPT-4
            max_workers: Maximum number of parallel workers
            validation_level: Test validation level
            exact_match: Whether to use exact name matching for test filtering
        """
        self.test_loader = TestLoader(validation_level=validation_level)
        self.report_generator = TestReportGenerator()
        self.max_workers = max_workers
        self._progress_lock = threading.Lock()
        self._completed_tests = 0
        self._exact_match = exact_match

        self.use_mock = use_mock_evaluator
        if use_mock_evaluator:
            print("⚠️  Using mock evaluator (all tests will pass)")
        else:
            # Verify API key is available
            try:
                from app.model_config import (
                    ModelPurpose,
                    get_model,
                    get_api_key,
                    get_provider,
                )

                model = get_model(ModelPurpose.TEST_EVALUATION)
                api_key = get_api_key(model)
                if not api_key:
                    provider = get_provider(model)
                    raise ValueError(
                        f"API key required for {provider}. Set appropriate environment variable."
                    )
                print(f"✅ Using LLM evaluator: {model}")
            except ValueError as e:
                print(f"❌ Failed to initialize LLM evaluator: {e}")
                print(
                    "💡 Set required API key environment variable or use --mock-evaluator"
                )
                sys.exit(1)

    def run_tests(
        self,
        test_dirs: List[str],
        verbose: bool = False,
        output_format: str = "terminal",
        output_file: str = None,
        parallel: bool = True,
        tag_filter: str = None,
        test_name_filter: str = None,
        no_interactive: bool = False,
    ) -> Dict[str, Any]:
        """Run all tests in the specified directories.

        Args:
            test_dirs: List of directories to search for tests
            verbose: Whether to show detailed output

        Returns:
            Dict containing test results and statistics
        """
        print("🚀 CJ Agent Test Runner")
        print("=" * 50)

        # No longer need test server - using direct function calls
        print("✅ Running tests with direct conversation generation")

        # Discover tests
        all_test_suites = []
        for test_path in test_dirs:
            if os.path.isfile(test_path) and test_path.endswith((".yaml", ".yml")):
                # Single test file
                try:
                    test_suite = self.test_loader.load_test_file(test_path)
                    all_test_suites.append(test_suite)
                except Exception as e:
                    print(f"❌ Failed to load test file {test_path}: {e}")
                    return {"error": f"Failed to load test file: {e}"}
            else:
                # Directory
                test_suites = self.test_loader.discover_tests(test_path)
                all_test_suites.extend(test_suites)

        if not all_test_suites:
            print("❌ No test files found in:", test_dirs)
            return {"error": "No tests found"}

        # Apply tag filtering if specified
        if tag_filter:
            filtered_suites = []
            for suite in all_test_suites:
                filtered_tests = [
                    test
                    for test in suite.tests
                    if tag_filter in getattr(test, "tags", [])
                ]
                if filtered_tests:
                    suite.tests = filtered_tests
                    filtered_suites.append(suite)
            all_test_suites = filtered_suites
            if not all_test_suites:
                print(f"❌ No tests found with tag: {tag_filter}")
                return {"error": "No matching tests found"}

        # Apply test name filtering if specified (supports partial matching)
        if test_name_filter:
            filtered_suites = []
            matching_tests = []
            exact_match = getattr(self, "_exact_match", False)

            for suite in all_test_suites:
                if exact_match:
                    filtered_tests = [
                        test
                        for test in suite.tests
                        if test_name_filter.lower() == test.name.lower()
                    ]
                else:
                    filtered_tests = [
                        test
                        for test in suite.tests
                        if test_name_filter.lower() in test.name.lower()
                    ]
                if filtered_tests:
                    suite.tests = filtered_tests
                    filtered_suites.append(suite)
                    matching_tests.extend([(test, suite) for test in filtered_tests])

            all_test_suites = filtered_suites
            if not all_test_suites:
                print(f"❌ No tests found matching: {test_name_filter}")
                return {"error": "No matching tests found"}

            # Show which tests matched and ask for confirmation if multiple
            if len(matching_tests) > 1:
                print(
                    f"🔍 Found {len(matching_tests)} tests matching '{test_name_filter}':"
                )
                for test, suite in matching_tests:
                    print(f"   • {test.name} (in {os.path.basename(suite.file_path)})")
                print()

                if not no_interactive:
                    # Check if we should run all or ask for specific selection
                    response = (
                        input("Run all matching tests? (y/n/select): ").strip().lower()
                    )
                    if response == "n":
                        return {"error": "Cancelled by user"}
                    elif response == "select" or response == "s":
                        print("\nSelect test by number:")
                        for i, (test, suite) in enumerate(matching_tests, 1):
                            print(f"  {i}. {test.name}")

                        try:
                            selection = int(input("\nEnter test number: ")) - 1
                            if 0 <= selection < len(matching_tests):
                                selected_test, selected_suite = matching_tests[
                                    selection
                                ]
                                # Update suites to only contain the selected test
                                selected_suite.tests = [selected_test]
                                all_test_suites = [selected_suite]
                            else:
                                print("❌ Invalid selection")
                                return {"error": "Invalid test selection"}
                        except ValueError:
                            print("❌ Invalid input")
                            return {"error": "Invalid test selection"}
                else:
                    print("🤖 Running all matching tests (non-interactive mode)")

        total_tests = sum(len(suite.tests) for suite in all_test_suites)
        print(f"📋 Found {len(all_test_suites)} test suites with {total_tests} tests")
        if tag_filter:
            print(f"🏷️  Filtered by tag: {tag_filter}")
        if test_name_filter:
            print(f"🔍 Filtered by test name containing: {test_name_filter}")
        print()

        # Run tests
        results = {
            "total_tests": total_tests,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "test_results": [],
            "start_time": time.time(),
            "test_suites": [],
        }

        self._completed_tests = 0
        self._total_tests_for_progress = total_tests

        if parallel and total_tests > 1:
            results = self._run_tests_parallel(all_test_suites, results, verbose)
        else:
            results = self._run_tests_sequential(all_test_suites, results, verbose)

        results["end_time"] = time.time()
        results["duration"] = results["end_time"] - results["start_time"]

        # Generate and display reports
        if output_format == "terminal":
            report = self.report_generator.generate_terminal_report(results)
            print(report)
        elif output_format == "markdown":
            report = self.report_generator.generate_markdown_report(results)
            if output_file:
                with open(output_file, "w") as f:
                    f.write(report)
                print(f"📄 Markdown report saved to: {output_file}")
            else:
                print(report)
        elif output_format == "json":
            report = self.report_generator.generate_json_report(results)
            if output_file:
                with open(output_file, "w") as f:
                    f.write(report)
                print(f"📄 JSON report saved to: {output_file}")
            else:
                print(report)

        return results

    def _run_tests_sequential(self, all_test_suites, results, verbose):
        """Run tests sequentially (original behavior)."""
        for suite in all_test_suites:
            suite_results = []
            print(f"\n📁 Running test suite: {os.path.basename(suite.file_path)}")
            if suite.description:
                print(f"   {suite.description}")
            print()

            for test_case in suite.tests:
                test_result = self._run_single_test(test_case, verbose)
                results["test_results"].append(test_result)
                suite_results.append(test_result)

                self._update_results_and_display(
                    results, test_result, test_case, verbose
                )
                self._update_progress()

            results["test_suites"].append(
                {
                    "name": os.path.basename(suite.file_path),
                    "description": suite.description,
                    "results": suite_results,
                }
            )

        return results

    def _run_tests_parallel(self, all_test_suites, results, verbose):
        """Run tests in parallel using ThreadPoolExecutor."""
        print(f"⚡ Running tests in parallel (max {self.max_workers} workers)")

        # Collect all test cases with suite info
        all_test_cases = []
        for suite in all_test_suites:
            for test_case in suite.tests:
                all_test_cases.append((test_case, suite))

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # Submit all test cases
            future_to_test = {
                executor.submit(self._run_single_test, test_case, verbose): (
                    test_case,
                    suite,
                )
                for test_case, suite in all_test_cases
            }

            # Process completed tests
            suite_results = {}
            for future in concurrent.futures.as_completed(future_to_test):
                test_case, suite = future_to_test[future]
                try:
                    test_result = future.result()
                    results["test_results"].append(test_result)

                    # Group by suite
                    suite_key = os.path.basename(suite.file_path)
                    if suite_key not in suite_results:
                        suite_results[suite_key] = {
                            "name": suite_key,
                            "description": suite.description,
                            "results": [],
                        }
                    suite_results[suite_key]["results"].append(test_result)

                    self._update_results_and_display(
                        results, test_result, test_case, verbose
                    )
                    self._update_progress()

                except Exception as exc:
                    error_result = {
                        "name": test_case.name,
                        "description": test_case.description,
                        "status": "ERROR",
                        "explanation": f"Test execution exception: {exc}",
                        "cj_response": "",
                        "evaluation_time": 0,
                    }
                    results["test_results"].append(error_result)
                    results["errors"] += 1
                    print(f"   💥 {test_case.name} - ERROR: {exc}")
                    self._update_progress()

        # Add suite results to main results
        results["test_suites"] = list(suite_results.values())
        return results

    def _update_results_and_display(self, results, test_result, test_case, verbose):
        """Update results counters and display test outcome."""
        if test_result["status"] == "PASS":
            results["passed"] += 1
            print(f"   ✅ {test_case.name}")
        elif test_result["status"] == "FAIL":
            results["failed"] += 1
            print(f"   ❌ {test_case.name}")
            if not verbose:
                print(f"      {test_result['explanation']}")
        else:  # ERROR
            results["errors"] += 1
            print(f"   💥 {test_case.name} - ERROR")
            print(f"      {test_result['explanation']}")

        if verbose:
            # Show the clean conversation only
            merchant_name = test_case.setup.get("merchant", "Merchant")
            merchant_opens = test_case.setup.get("merchant_opens", "")
            cj_response = test_result.get("cj_response", "N/A")

            print()
            print("      💬 Conversation:")
            print(f"      👤 {merchant_name}: {merchant_opens}")
            print(f"      🤖 CJ: {cj_response}")

            if test_result["status"] != "PASS":
                print()
                print(
                    f"      📝 Evaluation: {test_result.get('explanation', 'No explanation')}"
                )

    def _update_progress(self):
        """Update and display progress indicator."""
        with self._progress_lock:
            self._completed_tests += 1
            if hasattr(self, "_total_tests_for_progress"):
                progress = self._completed_tests / self._total_tests_for_progress * 100
                print(
                    f"\n      📊 Progress: {self._completed_tests}/{self._total_tests_for_progress} ({progress:.1f}%)\n"
                )

    def _run_single_test(self, test_case, verbose: bool = False) -> Dict[str, Any]:
        """Run a single test case.

        Args:
            test_case: The test case to run
            verbose: Whether to show detailed output

        Returns:
            Dict containing test result
        """
        result = {
            "name": test_case.name,
            "description": test_case.description,
            "status": "ERROR",
            "explanation": "",
            "cj_response": "",
            "evaluation_time": 0,
        }

        try:
            # Generate conversation via API
            start_time = time.time()
            cj_response = self._call_cj_api(test_case.setup)
            api_time = time.time() - start_time

            if verbose:
                print(f"      🤖 API call took {api_time:.2f}s")

            result["cj_response"] = cj_response

            # Evaluate response
            eval_start = time.time()
            evaluation = evaluate_response(
                cj_response=cj_response,
                criteria=test_case.evaluate_cj,
                test_name=test_case.name,
                mock=self.use_mock,
            )
            eval_time = time.time() - eval_start
            result["evaluation_time"] = eval_time

            if verbose:
                print(f"      🧠 Evaluation took {eval_time:.2f}s")

            result["status"] = "PASS" if evaluation.passed else "FAIL"
            result["explanation"] = evaluation.explanation
            result["criteria_results"] = evaluation.criteria_results

        except Exception as e:
            result["explanation"] = f"Test execution failed: {str(e)}"

        return result

    def _call_cj_api(self, setup: Dict[str, Any]) -> str:
        """Generate conversation directly without HTTP server.

        Args:
            setup: Test setup configuration

        Returns:
            str: CJ's response

        Raises:
            Exception: If conversation generation fails
        """
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from scripts.tools.generate_conversation import generate_conversation_with_crew

        try:
            # Suppress CrewAI verbose output by redirecting stdout/stderr
            captured_output = io.StringIO()

            with redirect_stdout(captured_output), redirect_stderr(captured_output):
                # Generate conversation directly
                conversation = generate_conversation_with_crew(
                    merchant_name=setup.get("merchant", "marcus_thompson"),
                    scenario_name=setup.get("scenario", "growth_stall"),
                    cj_version=setup.get("cj_version", settings.default_cj_version),
                    merchant_opens=setup.get("merchant_opens", ""),
                    workflow_name=setup.get("workflow"),
                    num_turns=setup.get("num_turns", 1),
                )

            # Extract CJ's responses
            cj_messages = [
                msg.content for msg in conversation.messages if msg.sender == "cj"
            ]

            return "\n\n".join(cj_messages)

        except Exception as e:
            raise Exception(f"Conversation generation failed: {str(e)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run CJ agent behavior tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_cj_tests.py                               # Run all tests in parallel
  python run_cj_tests.py --verbose                     # Show clean conversation output
  python run_cj_tests.py --mock-evaluator              # Use mock evaluator for testing
  python run_cj_tests.py tests/cj_boundaries/          # Run specific directory
  python run_cj_tests.py --sequential                  # Force sequential execution
  python run_cj_tests.py --output-format markdown     # Generate markdown report
  python run_cj_tests.py --output-file report.md      # Save report to file
  python run_cj_tests.py --tag-filter boundaries       # Run only tests with 'boundaries' tag
  python run_cj_tests.py --strict-validation           # Enable strict test validation

  # Test name filtering:
  python run_cj_tests.py --test-name daily_briefing    # Run all tests containing "daily_briefing"
  python run_cj_tests.py --test-name daily_briefing_normal --exact-match  # Run only "daily_briefing_normal"
  python run_cj_tests.py --test-name daily_briefing --no-interactive     # Run all matches without asking
        """,
    )

    parser.add_argument(
        "test_dirs",
        nargs="*",
        default=["tests/cj_boundaries", "tests/cj_workflows", "tests/cj_edge_cases"],
        help="Directories to search for test files",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed test output"
    )

    parser.add_argument(
        "--mock-evaluator",
        action="store_true",
        help="Use mock evaluator instead of GPT-4 (for testing)",
    )

    parser.add_argument(
        "--output-format",
        choices=["terminal", "markdown", "json"],
        default="terminal",
        help="Output format for test results",
    )

    parser.add_argument(
        "--output-file",
        help="File to save report (for markdown/json formats)",
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Run tests in parallel (default: True)",
    )

    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Force sequential test execution",
    )

    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Maximum number of parallel workers (default: 3)",
    )

    parser.add_argument(
        "--tag-filter",
        help="Only run tests with this tag",
    )

    parser.add_argument(
        "--test-name",
        help="Only run tests whose names contain this string (case-insensitive)",
    )

    parser.add_argument(
        "--exact-match",
        action="store_true",
        help="Match test names exactly instead of using partial matching",
    )

    parser.add_argument(
        "--strict-validation",
        action="store_true",
        help="Enable strict validation of test files",
    )

    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Non-interactive mode (run all matching tests without asking)",
    )

    args = parser.parse_args()

    # Handle sequential override
    parallel = args.parallel and not args.sequential

    # Set validation level
    validation_level = (
        ValidationLevel.STRICT if args.strict_validation else ValidationLevel.STANDARD
    )

    # Create test runner
    runner = CJTestRunner(
        use_mock_evaluator=args.mock_evaluator,
        max_workers=args.max_workers,
        validation_level=validation_level,
        exact_match=args.exact_match,
    )

    # Run tests
    results = runner.run_tests(
        args.test_dirs,
        verbose=args.verbose,
        output_format=args.output_format,
        output_file=args.output_file,
        parallel=parallel,
        tag_filter=args.tag_filter,
        test_name_filter=args.test_name,
        no_interactive=args.no_interactive,
    )

    # Exit with appropriate code
    if "error" in results:
        sys.exit(1)
    elif results["failed"] > 0 or results["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
