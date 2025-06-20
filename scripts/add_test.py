#!/usr/bin/env python3
"""
Interactive script to add test cases with plain English requirements.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

# Paths
CONVERSATIONS_DIR = Path('hirecj_evals/conversations/playground')
ALL_TESTS_FILE = Path('hirecj_evals/datasets/all_tests.jsonl')


def find_recent_conversations(limit: int = 10) -> List[Path]:
    """Find recent conversation files."""
    conversations = []
    
    # Get all JSON files from all date directories
    for date_dir in CONVERSATIONS_DIR.glob('*'):
        if date_dir.is_dir():
            for conv_file in date_dir.glob('*.json'):
                if not conv_file.name.startswith('test_'):  # Skip test files
                    conversations.append(conv_file)
    
    # Sort by modification time, most recent first
    conversations.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    return conversations[:limit]


def display_conversation(conv_data: Dict[str, Any]) -> None:
    """Display a conversation in a readable format."""
    messages = conv_data.get('messages', [])
    
    console.print(f"\n[bold cyan]Conversation ID:[/bold cyan] {conv_data.get('id', 'Unknown')}")
    console.print(f"[bold cyan]Timestamp:[/bold cyan] {conv_data.get('timestamp', 'Unknown')}")
    console.print(f"[bold cyan]Total turns:[/bold cyan] {len(messages)}\n")
    
    for i, msg in enumerate(messages):
        console.print(f"[bold yellow]Turn {msg['turn']}:[/bold yellow]")
        console.print(f"[green]User:[/green] {msg['user_input']}")
        
        response = msg['agent_processing']['final_response']
        # Truncate long responses
        if len(response) > 200:
            response = response[:197] + "..."
        console.print(f"[blue]CJ:[/blue] {response}\n")


def select_conversation() -> Dict[str, Any]:
    """Let user select a conversation."""
    conversations = find_recent_conversations()
    
    if not conversations:
        console.print("[red]No conversations found![/red]")
        sys.exit(1)
    
    # Display table of conversations
    table = Table(title="Recent Conversations")
    table.add_column("", style="cyan", width=3)
    table.add_column("File", style="green")
    table.add_column("Date", style="yellow")
    table.add_column("Time", style="yellow")
    
    for i, conv_path in enumerate(conversations):
        mod_time = datetime.fromtimestamp(conv_path.stat().st_mtime)
        table.add_row(
            str(i + 1),
            conv_path.stem,
            mod_time.strftime('%Y-%m-%d'),
            mod_time.strftime('%H:%M:%S')
        )
    
    console.print(table)
    
    # Get selection
    while True:
        choice = Prompt.ask("\nSelect conversation", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(conversations):
                break
            console.print("[red]Invalid selection![/red]")
        except ValueError:
            console.print("[red]Please enter a number![/red]")
    
    # Load and return conversation
    with open(conversations[idx], 'r') as f:
        return json.load(f), conversations[idx]


def get_requirements() -> List[str]:
    """Get requirements from user."""
    requirements = []
    
    console.print("\n[bold cyan]Enter requirements in plain English[/bold cyan]")
    console.print("[dim]Press Enter with empty line to finish[/dim]\n")
    
    while True:
        req = Prompt.ask(f"Requirement {len(requirements) + 1}", default="")
        if not req:
            if requirements:
                break
            console.print("[yellow]Please enter at least one requirement![/yellow]")
        else:
            requirements.append(req)
            console.print(f"[green]✓ Added:[/green] {req}")
    
    return requirements


def create_test_cases(conv_data: Dict[str, Any], conv_path: Path, requirements: List[str]) -> List[Dict[str, Any]]:
    """Create test cases from conversation with requirements."""
    test_cases = []
    messages = conv_data.get('messages', [])
    
    # Extract base filename
    base_name = conv_path.stem
    
    # Build conversation history
    system_prompt = conv_data['prompts']['cj_prompt'] + '\n\n' + conv_data['prompts']['workflow_prompt']
    conversation_history = [{"role": "system", "content": system_prompt}]
    
    for msg in messages:
        # Add user message
        conversation_history.append({
            "role": "user",
            "content": msg['user_input']
        })
        
        # Create test case for this turn
        test_case = {
            "sample_id": f"{base_name}_turn_{msg['turn']}",
            "input": {
                "messages": conversation_history.copy()
            },
            "actual": {
                "response": msg['agent_processing']['final_response']
            },
            "requirements": requirements  # Same requirements for all turns
        }
        test_cases.append(test_case)
        
        # Add assistant response for next turn
        conversation_history.append({
            "role": "assistant",
            "content": msg['agent_processing']['final_response']
        })
    
    return test_cases


def main():
    """Main entry point."""
    console.print("[bold cyan]Add Test Cases with Requirements[/bold cyan]\n")
    
    # Select conversation
    conv_data, conv_path = select_conversation()
    display_conversation(conv_data)
    
    # Get requirements
    requirements = get_requirements()
    
    # Show summary
    console.print("\n[bold cyan]Summary:[/bold cyan]")
    console.print(f"Conversation: {conv_path.stem}")
    console.print(f"Turns: {len(conv_data.get('messages', []))}")
    console.print("Requirements:")
    for req in requirements:
        console.print(f"  • {req}")
    
    # Confirm
    if not Confirm.ask("\nAdd these test cases?"):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    # Create test cases
    test_cases = create_test_cases(conv_data, conv_path, requirements)
    
    # Ensure directory exists
    ALL_TESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Append to all_tests.jsonl
    with open(ALL_TESTS_FILE, 'a') as f:
        for case in test_cases:
            f.write(json.dumps(case) + '\n')
    
    console.print(f"\n[green]✓ Added {len(test_cases)} test cases to {ALL_TESTS_FILE}[/green]")
    
    # Show what will be tested
    console.print("\n[bold]Test cases added:[/bold]")
    for i, case in enumerate(test_cases):
        console.print(f"  Turn {i+1}: Will check {len(requirements)} requirements")


if __name__ == '__main__':
    main()