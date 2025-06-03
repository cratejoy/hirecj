"""Test report generator for CJ agent test results."""

import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path


class TestReportGenerator:
    """Generate test reports in multiple formats."""

    def __init__(self):
        """Initialize the report generator."""
        self.colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "purple": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
            "bold": "\033[1m",
            "end": "\033[0m",
        }

    def generate_terminal_report(
        self, results: Dict[str, Any], use_colors: bool = True
    ) -> str:
        """Generate colored terminal report.

        Args:
            results: Test results dictionary
            use_colors: Whether to use terminal colors

        Returns:
            str: Formatted terminal report
        """
        if not use_colors:
            # Use existing simple format
            return self._generate_simple_terminal_report(results)

        lines = []

        # Header
        lines.append(f"{self._color('bold', '='*60)}")
        lines.append(f"{self._color('cyan', '📊 CJ Agent Test Results')}")
        lines.append(f"{self._color('bold', '='*60)}")

        # Summary statistics
        total = results["total_tests"]
        passed = results["passed"]
        failed = results["failed"]
        errors = results["errors"]
        duration = results["duration"]

        lines.append("")
        lines.append(f"{self._color('bold', 'Summary:')}")
        lines.append(f"  Total Tests:  {total}")

        if passed == total:
            lines.append(
                f"  {self._color('green', f'✅ Passed:       {passed} (100.0%)')}"
            )
        else:
            lines.append(
                f"  {self._color('green', f'Passed:       {passed}')} ({passed/total*100:.1f}%)"
            )

        if failed > 0:
            lines.append(
                f"  {self._color('red', f'❌ Failed:       {failed}')} ({failed/total*100:.1f}%)"
            )
        else:
            lines.append(f"  Failed:       {failed} ({failed/total*100:.1f}%)")

        if errors > 0:
            lines.append(
                f"  {self._color('yellow', f'💥 Errors:       {errors}')} ({errors/total*100:.1f}%)"
            )
        else:
            lines.append(f"  Errors:       {errors} ({errors/total*100:.1f}%)")

        lines.append(f"  Duration:     {duration:.2f}s")

        # Test breakdown by category
        if results["test_results"]:
            categories = self._categorize_tests(results["test_results"])

            lines.append("")
            lines.append(f"{self._color('bold', 'Results by Category:')}")

            for category, tests in categories.items():
                category_passed = sum(1 for t in tests if t["status"] == "PASS")
                category_total = len(tests)

                if category_passed == category_total:
                    status_color = "green"
                    status_icon = "✅"
                elif category_passed == 0:
                    status_color = "red"
                    status_icon = "❌"
                else:
                    status_color = "yellow"
                    status_icon = "⚠️"

                lines.append(
                    f"  {self._color(status_color, f'{status_icon} {category}:')} {category_passed}/{category_total} passed"
                )

        # Failed tests details
        if failed > 0 or errors > 0:
            lines.append("")
            lines.append(f"{self._color('red', 'Failed Tests:')}")

            for result in results["test_results"]:
                if result["status"] != "PASS":
                    status_color = "red" if result["status"] == "FAIL" else "yellow"
                    status_icon = "❌" if result["status"] == "FAIL" else "💥"

                    status_text = f'{status_icon} {result["name"]}'
                    lines.append(f"  {self._color(status_color, status_text)}")
                    lines.append(f"    {result['explanation']}")

        # Success message
        lines.append("")
        if passed == total:
            lines.append(f"{self._color('green', '🎉 All tests passed!')}")
        else:
            warning_text = f"⚠️  {failed + errors} tests need attention"
            lines.append(f"{self._color('yellow', warning_text)}")

        lines.append(f"{self._color('bold', '='*60)}")

        return "\n".join(lines)

    def generate_markdown_report(self, results: Dict[str, Any]) -> str:
        """Generate markdown report.

        Args:
            results: Test results dictionary

        Returns:
            str: Formatted markdown report
        """
        lines = []

        # Header
        lines.append("# CJ Agent Test Results")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary
        total = results["total_tests"]
        passed = results["passed"]
        failed = results["failed"]
        errors = results["errors"]
        duration = results["duration"]

        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Tests | {total} |")
        lines.append(f"| Passed | {passed} ({passed/total*100:.1f}%) |")
        lines.append(f"| Failed | {failed} ({failed/total*100:.1f}%) |")
        lines.append(f"| Errors | {errors} ({errors/total*100:.1f}%) |")
        lines.append(f"| Duration | {duration:.2f}s |")
        lines.append("")

        # Overall status
        if passed == total:
            lines.append("✅ **Status: ALL TESTS PASSED**")
        else:
            lines.append(f"❌ **Status: {failed + errors} TESTS FAILED**")
        lines.append("")

        # Results by category
        if results["test_results"]:
            categories = self._categorize_tests(results["test_results"])

            lines.append("## Results by Category")
            lines.append("")

            for category, tests in categories.items():
                category_passed = sum(1 for t in tests if t["status"] == "PASS")
                category_total = len(tests)

                if category_passed == category_total:
                    status = "✅ PASSED"
                elif category_passed == 0:
                    status = "❌ FAILED"
                else:
                    status = f"⚠️ PARTIAL ({category_passed}/{category_total})"

                lines.append(f"### {category} - {status}")
                lines.append("")

                # List individual tests
                for test in tests:
                    if test["status"] == "PASS":
                        lines.append(
                            f"- ✅ **{test['name']}**: {test.get('description', 'No description')}"
                        )
                    else:
                        lines.append(f"- ❌ **{test['name']}**: {test['explanation']}")

                lines.append("")

        # Failed tests detail
        failed_tests = [t for t in results["test_results"] if t["status"] != "PASS"]
        if failed_tests:
            lines.append("## Failed Test Details")
            lines.append("")

            for test in failed_tests:
                lines.append(f"### ❌ {test['name']}")
                lines.append("")
                lines.append(
                    f"**Description:** {test.get('description', 'No description')}"
                )
                lines.append("")
                lines.append(f"**Reason:** {test['explanation']}")
                lines.append("")

                if test.get("cj_response"):
                    lines.append("**CJ Response:**")
                    lines.append("```")
                    lines.append(
                        test["cj_response"][:500]
                        + ("..." if len(test["cj_response"]) > 500 else "")
                    )
                    lines.append("```")
                    lines.append("")

        return "\n".join(lines)

    def generate_json_report(self, results: Dict[str, Any]) -> str:
        """Generate JSON report for CI/CD integration.

        Args:
            results: Test results dictionary

        Returns:
            str: JSON formatted report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": results["total_tests"],
                "passed": results["passed"],
                "failed": results["failed"],
                "errors": results["errors"],
                "success_rate": results["passed"] / results["total_tests"] * 100,
                "duration_seconds": results["duration"],
            },
            "overall_status": (
                "PASS" if results["passed"] == results["total_tests"] else "FAIL"
            ),
            "categories": {},
            "failed_tests": [],
            "test_results": results["test_results"],
        }

        # Categorize results
        if results["test_results"]:
            categories = self._categorize_tests(results["test_results"])

            for category, tests in categories.items():
                category_passed = sum(1 for t in tests if t["status"] == "PASS")
                category_total = len(tests)

                report["categories"][category] = {
                    "total": category_total,
                    "passed": category_passed,
                    "failed": category_total - category_passed,
                    "success_rate": category_passed / category_total * 100,
                }

        # Failed tests
        report["failed_tests"] = [
            {
                "name": test["name"],
                "description": test.get("description", ""),
                "status": test["status"],
                "explanation": test["explanation"],
                "evaluation_time": test.get("evaluation_time", 0),
            }
            for test in results["test_results"]
            if test["status"] != "PASS"
        ]

        return json.dumps(report, indent=2)

    def save_report(self, content: str, filepath: str) -> None:
        """Save report to file.

        Args:
            content: Report content
            filepath: File path to save to
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            f.write(content)

    def _color(self, color_name: str, text: str) -> str:
        """Apply terminal color to text.

        Args:
            color_name: Color name from self.colors
            text: Text to colorize

        Returns:
            str: Colorized text
        """
        return f"{self.colors.get(color_name, '')}{text}{self.colors['end']}"

    def _generate_simple_terminal_report(self, results: Dict[str, Any]) -> str:
        """Generate simple terminal report without colors."""
        lines = []

        lines.append("=" * 50)
        lines.append("📊 Test Summary")
        lines.append("=" * 50)

        total = results["total_tests"]
        passed = results["passed"]
        failed = results["failed"]
        errors = results["errors"]
        duration = results["duration"]

        lines.append(f"Total Tests:  {total}")
        lines.append(f"Passed:       {passed} ({passed/total*100:.1f}%)")
        lines.append(f"Failed:       {failed} ({failed/total*100:.1f}%)")
        lines.append(f"Errors:       {errors} ({errors/total*100:.1f}%)")
        lines.append(f"Duration:     {duration:.2f}s")

        if failed > 0 or errors > 0:
            lines.append("")
            lines.append("❌ FAILED TESTS:")
            for result in results["test_results"]:
                if result["status"] != "PASS":
                    lines.append(f"  • {result['name']}: {result['explanation']}")

        if passed == total:
            lines.append("")
            lines.append("🎉 All tests passed!")
        else:
            lines.append("")
            lines.append(f"⚠️  {failed + errors} tests need attention")

        return "\n".join(lines)

    def _categorize_tests(
        self, test_results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize tests by their names.

        Args:
            test_results: List of test result dictionaries

        Returns:
            Dict mapping category names to test results
        """
        categories = {}

        for test in test_results:
            name = test["name"]

            # Determine category from test name patterns
            if any(keyword in name for keyword in ["inventory", "stock"]):
                category = "Inventory Boundaries"
            elif any(
                keyword in name
                for keyword in ["financial", "revenue", "burn", "profit", "clv"]
            ):
                category = "Financial Boundaries"
            elif any(
                keyword in name
                for keyword in [
                    "analytics",
                    "conversion",
                    "traffic",
                    "email",
                    "seo",
                    "social",
                ]
            ):
                category = "Analytics Boundaries"
            elif any(keyword in name for keyword in ["vendor", "supplier", "contract"]):
                category = "Vendor Boundaries"
            elif any(keyword in name for keyword in ["briefing", "workflow"]):
                category = "Workflow Tests"
            elif any(keyword in name for keyword in ["crisis", "emergency"]):
                category = "Crisis Response"
            elif any(
                keyword in name
                for keyword in ["persistent", "repeated", "escalating", "manipulation"]
            ):
                category = "Persistent Pressure"
            elif any(
                keyword in name
                for keyword in ["multiple", "comprehensive", "dashboard"]
            ):
                category = "Multi-Boundary Tests"
            else:
                category = "Other Tests"

            if category not in categories:
                categories[category] = []
            categories[category].append(test)

        return categories
