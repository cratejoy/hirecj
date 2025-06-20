#!/usr/bin/env python3
"""
Classic number-driven CLI interface for HireCJ evaluation system.
Simple, fast, no typing required - just press numbers.
Now with colors!
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import subprocess
import logging
from typing import List, Dict, Any, Optional, Tuple

# Rich imports for pretty output
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

# Set up console
console = Console()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# History file to remember user preferences
HISTORY_FILE = Path.home() / '.hirecj_evals_history.json'

# Common paths
EVALS_DIR = Path('hirecj_evals')
CONVERSATIONS_DIR = EVALS_DIR / 'conversations'
DATASETS_DIR = EVALS_DIR / 'datasets'
RESULTS_DIR = EVALS_DIR / 'results' / 'runs'


class EvalsHistory:
    """Manages user history and preferences."""
    
    def __init__(self):
        self.history = self._load_history()
    
    def _load_history(self) -> Dict[str, Any]:
        """Load history from file."""
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'last_eval': None,
            'last_dataset': None,
            'recent_runs': []
        }
    
    def save(self):
        """Save history to file."""
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def add_run(self, eval_id: str, dataset: str, result_path: str):
        """Add a run to history."""
        run = {
            'eval_id': eval_id,
            'dataset': dataset,
            'result_path': result_path,
            'timestamp': datetime.now().isoformat()
        }
        self.history['recent_runs'].insert(0, run)
        self.history['recent_runs'] = self.history['recent_runs'][:10]  # Keep last 10
        self.history['last_eval'] = eval_id
        self.history['last_dataset'] = dataset
        self.save()


def clear_screen():
    """Clear the terminal screen."""
    console.clear()


def print_header(title: str):
    """Print a section header with colors."""
    console.print(Panel.fit(
        f"[bold cyan]{title}[/bold cyan]",
        border_style="bright_blue",
        padding=(0, 1)
    ))
    console.print()


def get_number_choice(prompt: str, min_val: int, max_val: int) -> int:
    """Get a number choice from user."""
    while True:
        try:
            choice = console.input(f"\n[bold yellow]{prompt} [{min_val}-{max_val}]:[/bold yellow] ").strip()
            if not choice:
                continue
            num = int(choice)
            if min_val <= num <= max_val:
                return num
            console.print(f"[red]Please enter a number between {min_val} and {max_val}[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Goodbye![/yellow]")
            sys.exit(0)


def list_evaluations() -> List[Dict[str, str]]:
    """List all available evaluations."""
    cmd = ["python", "scripts/run_evals.py", "--list-evals"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    evals = []
    for line in result.stdout.split('\n'):
        if ' - ' in line and not line.startswith('='):
            parts = line.strip().split(' - ', 1)
            if len(parts) == 2:
                eval_id = parts[0].strip()
                desc = parts[1].strip()
                evals.append({'id': eval_id, 'description': desc})
    
    return evals


def find_recent_conversations() -> Optional[Path]:
    """Find conversations from today."""
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = CONVERSATIONS_DIR / 'playground' / today
    
    if today_dir.exists():
        files = list(today_dir.glob("*.json"))
        if files:
            return today_dir
    return None


def find_test_datasets() -> List[Path]:
    """Find test datasets."""
    test_dir = DATASETS_DIR / 'test'
    if test_dir.exists():
        return sorted(test_dir.glob("*.jsonl"))
    return []


def find_generated_datasets() -> List[Path]:
    """Find generated datasets."""
    gen_dir = DATASETS_DIR / 'generated'
    if gen_dir.exists():
        files = list(gen_dir.glob("*.jsonl"))
        # Sort by modification time, newest first
        return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    return []


def run_evaluation(eval_id: str, dataset_path: Path, limit: Optional[int] = None) -> Tuple[bool, str]:
    """Run an evaluation and return success status and result path."""
    cmd = ["python", "scripts/run_evals.py", "--eval", eval_id, "--dataset", str(dataset_path)]
    if limit:
        cmd.extend(["--limit", str(limit)])
    
    # Run with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Running {eval_id}...[/cyan]", total=None)
        result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse output for results
    result_path = None
    
    # Check both stdout and stderr for result path
    all_output = result.stdout + result.stderr
    for line in all_output.split('\n'):
        if 'Results saved to' in line:
            parts = line.split('Results saved to')
            if len(parts) > 1:
                result_path = parts[1].strip()
                break
    
    # Consider success if we got a result path, regardless of return code
    # (run_evals.py exits with 1 if ANY tests fail, but that's expected)
    success = result_path is not None
    
    # Show logs if requested or if there was a real error
    if not success:
        console.print(f"\n[bright_red]✗ Evaluation failed to run[/bright_red]")
        if result.stderr:
            console.print("\n[yellow]Error details:[/yellow]")
            # Show stderr in white/gray instead of red for readability
            for line in result.stderr.split('\n'):
                if line.strip():
                    console.print(f"[bright_white]{line}[/bright_white]")
    
    return success, result_path


def show_results(result_path: str):
    """Display results from a run."""
    try:
        results_file = Path(result_path)
        if not results_file.exists():
            results_file = Path(result_path.replace('/results.json', '')) / 'results.json'
        
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        console.print("\n" + "="*60)
        console.print(f"[bold cyan]Evaluation Results: {data['eval_id']}[/bold cyan]")
        console.print("="*60)
        
        # Create a nice table for results
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", justify="right")
        
        summary = data['summary']
        table.add_row("Total Samples", str(summary['total']))
        table.add_row(
            "Passed", 
            f"[green]{summary['passed']} ({summary['passed']/summary['total']*100:.1f}%)[/green]"
        )
        table.add_row(
            "Failed", 
            f"[bright_red]{summary['failed']} ({summary['failed']/summary['total']*100:.1f}%)[/bright_red]" if summary['failed'] > 0 else f"[green]{summary['failed']} (0.0%)[/green]"
        )
        table.add_row("Accuracy", f"[bold cyan]{summary['accuracy']*100:.1f}%[/bold cyan]")
        table.add_row("Average Score", f"{summary['average_score']:.3f}")
        
        console.print()
        console.print(table)
        
        # Show detailed failures
        failures = [r for r in data['results'] if r['status'].endswith('FAIL')]
        if failures:
            console.print(f"\n[yellow]Failure Details ({len(failures)} total):[/yellow]")
            console.print("-" * 60)
            for i, failure in enumerate(failures):
                console.print(f"\n[bright_red]Failure {i+1}:[/bright_red]")
                console.print(f"  [cyan]Sample ID:[/cyan] {failure['sample_id']}")
                console.print(f"  [cyan]Reason:[/cyan] {failure.get('reason', 'Unknown')}")
                
                # Show the actual response that failed
                if 'details' in failure and 'response_evaluated' in failure['details']:
                    response = failure['details']['response_evaluated']
                    # Truncate if too long
                    if len(response) > 200:
                        response = response[:197] + "..."
                    console.print(f"  [cyan]Response:[/cyan] {response}")
                
                # Show grader feedback
                if 'details' in failure and 'grading_response' in failure['details']:
                    console.print(f"  [cyan]Grader:[/cyan] {failure['details']['grading_response']}")
        
        # Final summary line
        console.print("\n" + "="*60)
        if summary['failed'] == 0:
            console.print(f"[bold green]✓ All {summary['total']} tests passed![/bold green]")
        else:
            pass_rate = summary['passed']/summary['total']*100
            if pass_rate >= 80:
                color = "green"
            elif pass_rate >= 60:
                color = "yellow" 
            else:
                color = "bright_red"
            console.print(f"[bold {color}]✓ {summary['passed']}/{summary['total']} tests passed ({pass_rate:.1f}%)[/bold {color}]")
        console.print("="*60)
    
    except Exception as e:
        console.print(f"[bright_red]Error reading results: {e}[/bright_red]")


def menu_main():
    """Main menu."""
    clear_screen()
    print_header("HireCJ Evaluation System")
    
    console.print("[bold green]1.[/bold green] Run evaluation")
    console.print("[bold yellow]2.[/bold yellow] View recent results")
    console.print("[bold blue]3.[/bold blue] Convert conversations") 
    console.print("[bold cyan]4.[/bold cyan] List all evaluations")
    console.print("[bold magenta]5.[/bold magenta] Quick test")
    console.print("[bold orange3]6.[/bold orange3] Run all evaluations")
    console.print("[dim red]7. Exit[/dim red]")
    
    return get_number_choice("Select", 1, 7)


def menu_select_eval(evals: List[Dict[str, str]]) -> Optional[str]:
    """Select evaluation menu."""
    clear_screen()
    print_header("Select Evaluation")
    
    # Show first 9 evaluations
    for i, eval_info in enumerate(evals[:9]):
        desc = eval_info['description']
        if len(desc) > 50:
            desc = desc[:47] + "..."
        console.print(f"[bold green]{i+1}.[/bold green] [cyan]{eval_info['id']}[/cyan]")
        console.print(f"   [dim]{desc}[/dim]")
        console.print()
    
    if len(evals) > 9:
        console.print("[bold yellow]9.[/bold yellow] More evaluations...")
    console.print("[dim]0. Back[/dim]")
    
    max_choice = min(9, len(evals))
    choice = get_number_choice("Select", 0, max_choice)
    
    if choice == 0:
        return None
    elif choice == 9 and len(evals) > 9:
        # Show all evaluations
        clear_screen()
        print_header("All Evaluations")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="green", width=3)
        table.add_column("Evaluation ID", style="cyan", width=30)
        table.add_column("Description", style="dim white")
        
        for i, eval_info in enumerate(evals):
            table.add_row(str(i+1), eval_info['id'], eval_info['description'])
        
        console.print(table)
        console.print("\n[dim]0. Back[/dim]")
        
        choice = get_number_choice("Select", 0, len(evals))
        if choice == 0:
            return menu_select_eval(evals)  # Go back to first page
        return evals[choice-1]['id']
    else:
        return evals[choice-1]['id']


def menu_select_dataset(eval_id: str) -> Tuple[Optional[Path], Optional[int]]:
    """Select dataset menu."""
    clear_screen()
    print_header("Select Dataset")
    
    options = []
    
    # Quick test option
    test_datasets = find_test_datasets()
    if test_datasets:
        options.append(("Quick test (5 samples)", test_datasets[0], 5))
        options.append(("Full test dataset", test_datasets[0], None))
    
    # Today's conversations
    recent = find_recent_conversations()
    if recent:
        options.append(("Today's conversations", recent, None))
    
    # Recent conversions
    generated = find_generated_datasets()
    if generated:
        options.append(("Recent conversions", None, None))
    
    # Custom file
    options.append(("Enter file path", None, None))
    
    # Display options with colors
    for i, (label, _, _) in enumerate(options):
        if "Quick" in label:
            console.print(f"[bold green]{i+1}.[/bold green] [bright_green]{label}[/bright_green]")
        elif "Today" in label:
            console.print(f"[bold yellow]{i+1}.[/bold yellow] [yellow]{label}[/yellow]")
        elif "Recent" in label:
            console.print(f"[bold blue]{i+1}.[/bold blue] [blue]{label}[/blue]")
        else:
            console.print(f"[bold cyan]{i+1}.[/bold cyan] {label}")
    console.print("[dim]0. Back[/dim]")
    
    choice = get_number_choice("Select", 0, len(options))
    
    if choice == 0:
        return None, None
    
    selected = options[choice-1]
    label, path, limit = selected
    
    if label == "Recent conversions":
        # Show generated datasets submenu
        clear_screen()
        print_header("Recent Conversions")
        
        for i, gen_path in enumerate(generated[:9]):
            mod_time = datetime.fromtimestamp(gen_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            console.print(f"[bold green]{i+1}.[/bold green] [cyan]{gen_path.name}[/cyan]")
            console.print(f"   [dim]Modified: {mod_time}[/dim]")
            console.print()
        console.print("[dim]0. Back[/dim]")
        
        sub_choice = get_number_choice("Select", 0, min(9, len(generated)))
        if sub_choice == 0:
            return menu_select_dataset(eval_id)
        return generated[sub_choice-1], None
    
    elif label == "Today's conversations":
        # Need to convert first
        console.print("\n[yellow]Converting today's conversations...[/yellow]")
        cmd = [
            "python", "scripts/convert_conversations.py",
            "--input-dir", str(recent),
            "--output-dir", str(DATASETS_DIR / 'generated'),
            "--eval-type", "response_quality"  # Use generic type for all conversions
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Converting...[/cyan]", total=None)
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print("[red]✗ Conversion failed[/red]")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return None, None
        
        # Find generated file
        for line in result.stdout.split('\n'):
            if '.jsonl' in line and 'Wrote' in line:
                parts = line.split('to')
                if len(parts) > 1:
                    return Path(parts[1].strip()), None
        
        console.print("[red]✗ Could not find converted file[/red]")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return None, None
    
    elif label == "Enter file path":
        file_path = console.input("\n[cyan]Enter dataset path:[/cyan] ").strip()
        if not file_path:
            return menu_select_dataset(eval_id)
        path = Path(file_path)
        if not path.exists():
            console.print(f"[red]✗ File not found: {path}[/red]")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return menu_select_dataset(eval_id)
        return path, None
    
    else:
        # Return the path with limit info
        return path, limit


def menu_results(history: EvalsHistory, interactive=True):
    """Results menu."""
    clear_screen()
    print_header("Recent Evaluation Runs")
    
    if not history.history['recent_runs']:
        console.print("[yellow]No recent runs found.[/yellow]")
        return
    
    runs = history.history['recent_runs'][:9]
    
    for i, run in enumerate(runs):
        timestamp = datetime.fromisoformat(run['timestamp'])
        time_str = timestamp.strftime("%Y-%m-%d %H:%M")
        dataset_name = Path(run['dataset']).name
        console.print(f"[bold green]{i+1}.[/bold green] [yellow]{time_str}[/yellow] - [cyan]{run['eval_id']}[/cyan]")
        console.print(f"   [dim]Dataset: {dataset_name}[/dim]")
        console.print()
    
    if interactive:
        console.print("[dim]0. Back[/dim]")
        
        choice = get_number_choice("Select to view details", 0, len(runs))
        
        if choice == 0:
            return
        
        run = runs[choice-1]
        if run['result_path']:
            show_results(run['result_path'])
            console.input("\n[dim]Press Enter to continue...[/dim]")
    else:
        # Non-interactive mode - just show the list
        pass


def menu_convert():
    """Conversion menu."""
    clear_screen()
    print_header("Convert Conversations")
    
    console.print("[bold green]1.[/bold green] Today's conversations")
    console.print("[bold yellow]2.[/bold yellow] Specific date")
    console.print("[bold blue]3.[/bold blue] All conversations")
    console.print("[dim]0. Back[/dim]")
    
    choice = get_number_choice("Select", 0, 3)
    
    if choice == 0:
        return
    
    # Determine input directory
    if choice == 1:
        recent = find_recent_conversations()
        if not recent:
            console.print("\n[red]No conversations found for today[/red]")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return
        input_dir = recent
    elif choice == 2:
        date = console.input("\n[cyan]Enter date (YYYY-MM-DD):[/cyan] ").strip()
        if not date:
            return
        input_dir = CONVERSATIONS_DIR / 'playground' / date
        if not input_dir.exists():
            console.print(f"\n[red]No conversations found for {date}[/red]")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return
    else:
        input_dir = CONVERSATIONS_DIR / 'playground'
    
    # Choose eval type
    console.print("\n[bold]Eval type:[/bold]")
    console.print("[bold green]1.[/bold green] tool_selection")
    console.print("[bold yellow]2.[/bold yellow] response_quality")
    console.print("[bold blue]3.[/bold blue] grounding_accuracy")
    console.print("[dim]0. Cancel[/dim]")
    
    eval_choice = get_number_choice("Select", 0, 3)
    
    if eval_choice == 0:
        return
    
    eval_types = ["", "tool_selection", "response_quality", "grounding_accuracy"]
    eval_type = eval_types[eval_choice]
    
    # Run conversion
    output_dir = DATASETS_DIR / 'generated'
    cmd = [
        "python", "scripts/convert_conversations.py",
        "--input-dir", str(input_dir),
        "--output-dir", str(output_dir),
        "--eval-type", eval_type
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Converting conversations...[/cyan]", total=None)
        result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        console.print(f"\n[green]✓ Conversion successful![/green]")
        # Extract key info from output
        for line in result.stdout.split('\n'):
            if 'Wrote' in line:
                console.print(f"[cyan]{line}[/cyan]")
            elif 'Total conversations:' in line:
                console.print(f"[dim]{line}[/dim]")
    else:
        console.print(f"[red]✗ Conversion failed: {result.stderr}[/red]")
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


def quick_test(interactive=True):
    """Run a quick test."""
    if interactive:
        clear_screen()
    print_header("Quick Test")
    
    console.print("[cyan]Running quick test suite...[/cyan]\n")
    
    # Create history object to save results
    history = EvalsHistory()
    
    test_evals = [
        ("no_meta_commentary", "Check for meta-commentary in CJ responses")
    ]
    
    # Find test dataset
    test_datasets = find_test_datasets()
    if not test_datasets:
        console.print("[red]✗ No test datasets found[/red]")
        if interactive:
            console.input("\n[dim]Press Enter to continue...[/dim]")
        return
    
    dataset = test_datasets[0]
    results = []
    test_result_paths = []  # Store result paths in order
    
    # Run tests with progress
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Running tests...[/cyan]", total=len(test_evals))
        
        for eval_id, desc in test_evals:
            progress.update(task, description=f"[cyan]Testing {desc}...[/cyan]")
            
            cmd = ["python", "scripts/run_evals.py", "--eval", eval_id, "--dataset", str(dataset), "--limit", "3"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Check if accuracy line exists
                passed = any('Accuracy:' in line for line in result.stdout.split('\n'))
                results.append((eval_id, "[green]✓ Pass[/green]" if passed else "[yellow]⚠ Ran[/yellow]"))
                
                # Try to extract result path from both stdout and stderr
                all_output = result.stdout + result.stderr
                result_path = None
                for line in all_output.split('\n'):
                    if 'Results saved to' in line:
                        parts = line.split('Results saved to')
                        if len(parts) > 1:
                            result_path = parts[1].strip()
                            history.add_run(eval_id, str(dataset), result_path)
                            break
                test_result_paths.append((eval_id, result_path))
            else:
                results.append((eval_id, "[red]✗ Failed[/red]"))
                test_result_paths.append((eval_id, None))
            
            progress.advance(task)
    
    # Show results in a table
    table = Table(title="Test Results", show_header=True, header_style="bold magenta")
    table.add_column("Evaluation", style="cyan", width=25)
    table.add_column("Status", justify="center", width=10)
    
    for eval_id, status in results:
        table.add_row(eval_id, status)
    
    console.print()
    console.print(table)
    
    all_passed = all("✓" in status for _, status in results)
    if all_passed:
        console.print("\n[bold green]✓ All tests passed![/bold green]")
    else:
        console.print("\n[yellow]⚠ Some tests failed.[/yellow]")
    
    # Show detailed results for each evaluation
    console.print("\n[bold]Detailed Results:[/bold]")
    console.print("=" * 60)
    
    for eval_id, result_path in test_result_paths:
        if result_path:
            console.print(f"\n[cyan]{eval_id}:[/cyan]")
            show_results(result_path)
    
    # Save test summary to history
    console.print(f"\n[dim]Test results saved to history[/dim]")
    
    if interactive:
        console.input("\n[dim]Press Enter to continue...[/dim]")


def list_all_evals():
    """List all evaluations."""
    clear_screen()
    print_header("All Evaluations")
    
    evals = list_evaluations()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Evaluation ID", style="cyan", width=30)
    table.add_column("Description", style="dim white")
    
    for eval_info in evals:
        table.add_row(eval_info['id'], eval_info['description'])
    
    console.print(table)
    console.input("\n[dim]Press Enter to continue...[/dim]")


def run_last():
    """Re-run the last evaluation."""
    history = EvalsHistory()
    
    if not history.history['last_eval'] or not history.history['last_dataset']:
        console.print("\n[red]✗ No previous run found[/red]")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return
    
    eval_id = history.history['last_eval']
    dataset_path = Path(history.history['last_dataset'])
    
    if not dataset_path.exists():
        console.print(f"\n[red]✗ Dataset no longer exists: {dataset_path}[/red]")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return
    
    console.print(f"\n[cyan]Re-running: {eval_id} on {dataset_path.name}[/cyan]")
    success, result_path = run_evaluation(eval_id, dataset_path)
    
    if success and result_path:
        history.add_run(eval_id, str(dataset_path), result_path)
        
        # Automatically show results
        show_results(result_path)
        console.input("\n[dim]Press Enter to continue...[/dim]")


def run_interactive():
    """Run evaluation interactively."""
    history = EvalsHistory()
    
    # Select evaluation
    evals = list_evaluations()
    if not evals:
        console.print("[red]✗ No evaluations found[/red]")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return
    
    eval_id = menu_select_eval(evals)
    if not eval_id:
        return
    
    # Select dataset
    dataset_path, limit = menu_select_dataset(eval_id)
    if not dataset_path:
        return
    
    # Run evaluation
    success, result_path = run_evaluation(eval_id, dataset_path, limit)
    
    if success and result_path:
        history.add_run(eval_id, str(dataset_path), result_path)
        
        # Automatically show results
        show_results(result_path)
        
        console.input("\n[dim]Press Enter to continue...[/dim]")
        
        console.print("\n[bold green]1.[/bold green] Run another evaluation")
        console.print("[bold yellow]2.[/bold yellow] Main menu")
        
        choice = get_number_choice("Select", 1, 2)
        
        if choice == 1:
            run_interactive()
    elif success and not result_path:
        # Evaluation succeeded but couldn't find results path
        console.print("\n[yellow]⚠ Evaluation completed but results location not found[/yellow]")
        console.print("[dim]Check the output above for results[/dim]")
        console.input("\n[dim]Press Enter to continue...[/dim]")
    else:
        # Evaluation failed
        console.print("\n[red]✗ Evaluation failed to complete[/red]")
        console.input("\n[dim]Press Enter to continue...[/dim]")


def run_all_evaluations():
    """Run all available evaluations on a selected dataset."""
    clear_screen()
    print_header("Run All Evaluations")
    
    # Get all evaluations
    all_evals = list_evaluations()
    
    # Filter out base evaluations (those without descriptions or base classes)
    runnable_evals = [
        e for e in all_evals 
        if e['description'] and e['id'] not in ['base_eval', 'model_graded']
    ]
    
    if not runnable_evals:
        console.print("[red]✗ No runnable evaluations found[/red]")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return
    
    # Show evaluations that will be run
    console.print(f"[cyan]Found {len(runnable_evals)} evaluation(s) to run:[/cyan]\n")
    for eval_info in runnable_evals:
        console.print(f"  • [yellow]{eval_info['id']}[/yellow]: {eval_info['description']}")
    console.print()
    
    # Select dataset
    console.print("[bold]Select dataset to evaluate:[/bold]")
    dataset_path, limit = menu_select_dataset(runnable_evals[0]['id'])  # Use first eval for dataset selection
    if not dataset_path:
        return
    
    # Confirm before running
    console.print(f"\n[bold]Ready to run {len(runnable_evals)} evaluation(s) on:[/bold]")
    console.print(f"  [cyan]{dataset_path.name}[/cyan]")
    console.print("\n[yellow]Press Enter to start or Ctrl+C to cancel...[/yellow]")
    console.input()
    
    # Run all evaluations
    history = EvalsHistory()
    results_summary = []
    overall_passed = 0
    overall_failed = 0
    overall_total = 0
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        main_task = progress.add_task(
            f"[cyan]Running {len(runnable_evals)} evaluations...[/cyan]", 
            total=len(runnable_evals)
        )
        
        for i, eval_info in enumerate(runnable_evals):
            eval_id = eval_info['id']
            progress.update(main_task, description=f"[cyan]Running {eval_id}...[/cyan]")
            
            # Run the evaluation
            success, result_path = run_evaluation(eval_id, dataset_path, limit)
            
            if success and result_path:
                # Load and summarize results
                try:
                    with open(result_path, 'r') as f:
                        data = json.load(f)
                    
                    summary = data['summary']
                    results_summary.append({
                        'eval_id': eval_id,
                        'description': eval_info['description'],
                        'total': summary['total'],
                        'passed': summary['passed'],
                        'failed': summary['failed'],
                        'accuracy': summary['accuracy'],
                        'result_path': result_path
                    })
                    
                    overall_passed += summary['passed']
                    overall_failed += summary['failed'] 
                    overall_total += summary['total']
                    
                    # Save to history
                    history.add_run(eval_id, str(dataset_path), result_path)
                    
                except Exception as e:
                    console.print(f"\n[red]✗ Error reading results for {eval_id}: {e}[/red]")
            else:
                console.print(f"\n[red]✗ Failed to run {eval_id}[/red]")
                results_summary.append({
                    'eval_id': eval_id,
                    'description': eval_info['description'],
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'accuracy': 0,
                    'result_path': None
                })
            
            progress.advance(main_task)
    
    # Display comprehensive summary
    console.print("\n" + "="*60)
    console.print("[bold cyan]All Evaluations Complete[/bold cyan]")
    console.print("="*60 + "\n")
    
    # Summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Evaluation", style="cyan", width=25)
    table.add_column("Passed", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Total", justify="right")
    table.add_column("Accuracy", justify="right", style="bold")
    
    for result in results_summary:
        accuracy_str = f"{result['accuracy']*100:.1f}%" if result['total'] > 0 else "N/A"
        table.add_row(
            result['eval_id'],
            str(result['passed']),
            str(result['failed']),
            str(result['total']),
            accuracy_str
        )
    
    # Add overall summary row
    table.add_section()
    overall_accuracy = overall_passed / overall_total if overall_total > 0 else 0
    table.add_row(
        "[bold]OVERALL[/bold]",
        f"[bold green]{overall_passed}[/bold green]",
        f"[bold red]{overall_failed}[/bold red]",
        f"[bold]{overall_total}[/bold]",
        f"[bold cyan]{overall_accuracy*100:.1f}%[/bold cyan]"
    )
    
    console.print(table)
    
    # Final summary
    console.print("\n" + "="*60)
    if overall_failed == 0:
        console.print(f"[bold green]✓ All {overall_total} tests passed across {len(runnable_evals)} evaluations![/bold green]")
    else:
        pass_rate = overall_passed/overall_total*100 if overall_total > 0 else 0
        if pass_rate >= 80:
            color = "green"
        elif pass_rate >= 60:
            color = "yellow"
        else:
            color = "bright_red"
        console.print(f"[bold {color}]✓ {overall_passed}/{overall_total} tests passed ({pass_rate:.1f}%) across {len(runnable_evals)} evaluations[/bold {color}]")
    console.print("="*60)
    
    # Ask to view detailed results
    console.print("\n[bold green]1.[/bold green] View detailed results for each evaluation")
    console.print("[bold yellow]2.[/bold yellow] Main menu")
    
    choice = get_number_choice("Select", 1, 2)
    
    if choice == 1:
        for result in results_summary:
            if result['result_path']:
                console.print(f"\n[bold cyan]Results for {result['eval_id']}:[/bold cyan]")
                show_results(result['result_path'])
                console.input("\n[dim]Press Enter for next evaluation...[/dim]")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='HireCJ Evaluation System')
    parser.add_argument('command', nargs='?', help='Command to run')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Direct commands - use plain output for these
    if args.command == 'list':
        evals = list_evaluations()
        for e in evals:
            print(f"{e['id']:30} - {e['description']}")
        return
    elif args.command == 'history':
        history = EvalsHistory()
        menu_results(history, interactive=False)
        return
    elif args.command == 'again':
        run_last()
        return
    elif args.command == 'test':
        quick_test(interactive=False)
        return
    elif args.command == 'convert':
        menu_convert()
        return
    elif args.command == 'all':
        run_all_evaluations()
        return
    
    # Interactive mode
    while True:
        choice = menu_main()
        
        if choice == 1:
            run_interactive()
        elif choice == 2:
            history = EvalsHistory()
            menu_results(history)
        elif choice == 3:
            menu_convert()
        elif choice == 4:
            list_all_evals()
        elif choice == 5:
            quick_test()
        elif choice == 6:
            run_all_evaluations()
        else:
            console.print("\n[yellow]Goodbye![/yellow]")
            break


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Goodbye![/yellow]")
        sys.exit(0)