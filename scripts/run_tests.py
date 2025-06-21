#!/usr/bin/env python3
"""
Simplified test runner that generates fresh CJ responses and evaluates requirements.
"""

import json
import sys
import asyncio
import httpx
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.app.evals.base import ModelGraded, EvalSample
from agents.app.config import settings
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Paths
ALL_TESTS_FILE = Path('hirecj_evals/datasets/all_tests.jsonl')
AGENTS_URL = "http://localhost:8100"


def load_test_cases() -> List[Dict[str, Any]]:
    """Load test cases from all_tests.jsonl."""
    if not ALL_TESTS_FILE.exists():
        console.print(f"[red]No test file found at {ALL_TESTS_FILE}[/red]")
        console.print("[yellow]Run 'make add-test' to add some test cases first![/yellow]")
        sys.exit(1)
    
    test_cases = []
    with open(ALL_TESTS_FILE, 'r') as f:
        for line in f:
            if line.strip():
                test_cases.append(json.loads(line))
    
    if not test_cases:
        console.print("[red]No test cases found in all_tests.jsonl[/red]")
        console.print("[yellow]Run 'make add-test' to add some test cases![/yellow]")
        sys.exit(1)
    
    return test_cases


async def generate_cj_response(context: dict) -> str:
    """Call CJ agent API to generate a fresh response."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{AGENTS_URL}/api/v1/eval/chat",
                json={
                    "messages": context["messages"],
                    "workflow": context.get("workflow", "ad_hoc_support"),
                    "persona": context.get("persona", "jessica"),
                    "trust_level": context.get("trust_level", 3)
                }
            )
            
            if response.status_code == 200:
                return response.json()["response"]
            else:
                raise Exception(f"API error {response.status_code}: {response.text}")
                
        except Exception as e:
            console.print(f"[red]Error calling CJ API: {e}[/red]")
            raise


def evaluate_requirement(response: str, requirement: str) -> Dict[str, Any]:
    """Evaluate if a response meets a requirement using GPT-4o-mini."""
    # Create evaluator
    evaluator = ModelGraded(
        grader_model="gpt-4o-mini",
        temperature=0.0,
        max_tokens=150,
        grading_prompt=f"""Check if this response meets the following requirement:
{requirement}

Response to evaluate:
{response}

Respond with:
PASS - if requirement is met (explain briefly why)
FAIL - if requirement is not met (quote specific issue)"""
    )
    
    # Create a simple eval sample
    sample = EvalSample(
        eval_id="requirement",
        sample_id="test",
        input={},
        actual={"response": response}
    )
    
    # Run evaluation
    result = evaluator.eval_sample(sample)
    
    return {
        "passed": result.status.value == "pass",
        "reason": result.reason or "",
        "details": result.details
    }


async def main():
    """Main entry point."""
    console.print("[bold cyan]Running Requirements Tests (Live Generation)[/bold cyan]\n")
    
    # Check for API key
    if not settings.openai_api_key:
        console.print("[red]Error: OPENAI_API_KEY not set in environment![/red]")
        sys.exit(1)
    
    # Load test cases
    test_cases = load_test_cases()
    
    # Collect results by requirement
    results_by_requirement = defaultdict(list)
    total_tests = 0
    
    # Count tests
    for tc in test_cases:
        total_tests += len(tc.get("requirements", []))
    
    console.print(f"[cyan]Running {total_tests} tests with fresh CJ responses...[/cyan]\n")
    
    # Run tests with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Generating and evaluating...[/cyan]", total=total_tests)
        
        for test_case in test_cases:
            sample_id = test_case["sample_id"]
            context = test_case["context"]
            
            # Generate fresh CJ response
            progress.update(task, description=f"[cyan]Generating response for {sample_id}...[/cyan]")
            try:
                response = await generate_cj_response(context)
                console.print(f"[dim]Generated: {response[:100]}...[/dim]")
            except Exception as e:
                console.print(f"[red]Failed to generate response for {sample_id}: {e}[/red]")
                # Mark all requirements as failed
                for requirement in test_case.get("requirements", []):
                    results_by_requirement[requirement].append({
                        "sample_id": sample_id,
                        "passed": False,
                        "reason": f"Failed to generate response: {str(e)}"
                    })
                    progress.advance(task)
                continue
            
            # Evaluate each requirement
            for requirement in test_case.get("requirements", []):
                # Update progress
                progress.update(task, description=f"[cyan]{requirement[:50]}...[/cyan]")
                
                try:
                    # Evaluate
                    result = evaluate_requirement(response, requirement)
                    
                    results_by_requirement[requirement].append({
                        "sample_id": sample_id,
                        "passed": result["passed"],
                        "reason": result["reason"]
                    })
                    
                except Exception as e:
                    console.print(f"[red]Error evaluating '{requirement}': {e}[/red]")
                    results_by_requirement[requirement].append({
                        "sample_id": sample_id,
                        "passed": False,
                        "reason": f"Error: {str(e)}"
                    })
                
                progress.advance(task)
    
    # Display results
    console.print("\n" + "="*60)
    console.print("[bold cyan]Results by Requirement[/bold cyan]")
    console.print("="*60 + "\n")
    
    # Create summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Requirement", style="cyan", width=50)
    table.add_column("Passed", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Pass Rate", justify="right", style="bold")
    
    total_passed = 0
    total_failed = 0
    
    for requirement, results in sorted(results_by_requirement.items()):
        passed = sum(1 for r in results if r["passed"])
        failed = len(results) - passed
        total_passed += passed
        total_failed += failed
        
        pass_rate = (passed / len(results) * 100) if results else 0
        
        # Truncate requirement
        display_req = requirement if len(requirement) <= 50 else requirement[:47] + "..."
        
        # Color code
        if pass_rate == 100:
            rate_str = f"[green]{pass_rate:.0f}%[/green]"
        elif pass_rate == 0:
            rate_str = f"[red]{pass_rate:.0f}%[/red]"
        else:
            rate_str = f"[yellow]{pass_rate:.0f}%[/yellow]"
        
        table.add_row(display_req, str(passed), str(failed), rate_str)
    
    console.print(table)
    
    # Overall summary
    console.print("\n" + "="*60)
    total = total_passed + total_failed
    overall_rate = (total_passed / total * 100) if total > 0 else 0
    
    if overall_rate == 100:
        console.print(f"[bold green]✓ All {total} tests passed![/bold green]")
    else:
        color = "green" if overall_rate >= 80 else "yellow" if overall_rate >= 60 else "red"
        console.print(f"[bold {color}]✓ {total_passed}/{total} tests passed ({overall_rate:.1f}%)[/bold {color}]")
    console.print("="*60)
    
    # Show failures
    if total_failed > 0:
        console.print("\n[bold yellow]Failures:[/bold yellow]")
        for requirement, results in sorted(results_by_requirement.items()):
            failures = [r for r in results if not r["passed"]]
            if failures:
                console.print(f"\n[red]{requirement}[/red]")
                for f in failures:
                    console.print(f"  • {f['sample_id']}: {f['reason']}")


if __name__ == '__main__':
    asyncio.run(main())