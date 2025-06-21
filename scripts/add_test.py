#!/usr/bin/env python3
"""
Interactive script to add test cases with plain English requirements.
Only saves conversation context, not CJ's responses.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

# Paths
CONVERSATIONS_BASE = Path('hirecj_evals/conversations')
ALL_TESTS_FILE = Path('hirecj_evals/datasets/all_tests.jsonl')


def find_recent_conversations(limit: int = 10) -> List[Tuple[Path, Dict[str, Any]]]:
    """Find recent conversation files."""
    conversations = []
    
    # Search through all source directories
    for source_dir in CONVERSATIONS_BASE.glob('*'):
        if not source_dir.is_dir():
            continue
            
        # Search through date directories
        for date_dir in source_dir.glob('*'):
            if not date_dir.is_dir():
                continue
                
            # Find JSON files
            for conv_file in date_dir.glob('*.json'):
                try:
                    with open(conv_file, 'r') as f:
                        data = json.load(f)
                    
                    # Extract basic info
                    conv_info = {
                        'file': conv_file,
                        'timestamp': data.get('timestamp', ''),
                        'message_count': len(data.get('messages', [])),
                        'workflow': data.get('context', {}).get('workflow', {}).get('name', 'unknown')
                    }
                    conversations.append((conv_file, conv_info))
                except Exception as e:
                    console.print(f"[red]Error reading {conv_file}: {e}[/red]")
    
    # Sort by timestamp descending and return top N
    conversations.sort(key=lambda x: x[1]['timestamp'], reverse=True)
    return conversations[:limit]


def extract_conversation_context(conv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract context (user messages only) from conversation data."""
    context_messages = []
    
    for msg in conv_data.get('messages', []):
        # Add user message
        context_messages.append({
            "role": "user",
            "content": msg['user_input']
        })
        
        # Add assistant message (but not the agent_processing details)
        if msg.get('agent_processing', {}).get('final_response'):
            context_messages.append({
                "role": "assistant", 
                "content": msg['agent_processing']['final_response']
            })
    
    return context_messages


def select_conversation() -> Tuple[Dict[str, Any], Path]:
    """Let user select a conversation to convert."""
    conversations = find_recent_conversations()
    
    if not conversations:
        console.print("[red]No conversations found![/red]")
        sys.exit(1)
    
    # Display table
    table = Table(title="Recent Conversations")
    table.add_column("#", style="cyan", width=5)
    table.add_column("File", style="green")
    table.add_column("Date", style="yellow")
    table.add_column("Time", style="yellow")
    
    for i, (path, info) in enumerate(conversations, 1):
        timestamp = info['timestamp']
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date = dt.strftime('%Y-%m-%d')
                time = dt.strftime('%H:%M:%S')
            except:
                date = time = "Unknown"
        else:
            date = time = "Unknown"
            
        table.add_row(
            str(i),
            path.stem,
            date,
            time
        )
    
    console.print(table)
    
    # Get selection
    choice = Prompt.ask("\nSelect conversation", default="1")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(conversations):
            path, _ = conversations[idx]
            with open(path, 'r') as f:
                return json.load(f), path
    except:
        pass
    
    console.print("[red]Invalid selection![/red]")
    sys.exit(1)


def main():
    """Main entry point."""
    console.print("[bold cyan]Add Test Cases with Requirements[/bold cyan]\n")
    
    # Select conversation
    conv_data, conv_path = select_conversation()
    console.print(f"\n[green]Selected:[/green] {conv_path.name}")
    
    # Extract context
    context_messages = extract_conversation_context(conv_data)
    
    # Show messages
    console.print("\n[bold]Conversation Context:[/bold]")
    for i, msg in enumerate(context_messages):
        role_color = "blue" if msg["role"] == "user" else "green"
        console.print(f"[{role_color}]{msg['role']}:[/{role_color}] {msg['content'][:100]}...")
    
    # Get workflow info
    workflow = conv_data.get('context', {}).get('workflow', {}).get('name', 'ad_hoc_support')
    persona = conv_data.get('context', {}).get('persona', {}).get('name', 'jessica')
    
    # Collect requirements for each turn
    test_cases = []
    
    # Process each user message
    user_turns = [(i, msg) for i, msg in enumerate(context_messages) if msg["role"] == "user"]
    
    for turn_num, (msg_idx, user_msg) in enumerate(user_turns, 1):
        console.print(f"\n[bold yellow]Turn {turn_num}:[/bold yellow]")
        console.print(f"User: {user_msg['content']}")
        
        # Get messages up to this point (context for this turn)
        turn_context = context_messages[:msg_idx + 1]
        
        # Ask for requirements
        console.print("\n[cyan]Enter requirements for CJ's response (one per line, empty line to finish):[/cyan]")
        requirements = []
        while True:
            req = Prompt.ask("Requirement", default="")
            if not req:
                break
            requirements.append(req)
        
        if requirements:
            test_case = {
                "sample_id": f"{conv_path.stem}_turn_{turn_num}",
                "context": {
                    "messages": turn_context,
                    "workflow": workflow,
                    "persona": persona
                },
                "requirements": requirements
            }
            test_cases.append(test_case)
    
    # Save test cases
    if test_cases:
        console.print(f"\n[green]Adding {len(test_cases)} test cases to {ALL_TESTS_FILE}[/green]")
        
        # Ensure directory exists
        ALL_TESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Append to file
        with open(ALL_TESTS_FILE, 'a') as f:
            for tc in test_cases:
                f.write(json.dumps(tc) + '\n')
        
        console.print("[bold green]✓ Test cases added successfully![/bold green]")
        console.print("\nRun 'make test-reqs' to evaluate these requirements")
    else:
        console.print("[yellow]No test cases created[/yellow]")


if __name__ == '__main__':
    main()