#!/usr/bin/env python3
"""
Convert captured conversations from JSON to JSONL eval format.
This script processes conversations captured by the playground and converts them
to OpenAI-compatible JSONL format for use in evaluations.
"""

import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def load_conversation(file_path: Path) -> Dict[str, Any]:
    """Load a conversation JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def convert_to_eval_format(conversation: Dict[str, Any], eval_type: str = "tool_selection") -> List[Dict[str, Any]]:
    """
    Convert a conversation to eval format.
    
    Returns a list of eval cases (one per message turn).
    """
    eval_cases = []
    
    # Extract context
    context = conversation.get('context', {})
    prompts = conversation.get('prompts', {})
    messages = conversation.get('messages', [])
    
    # Build conversation history for each turn
    conversation_history = []
    
    for i, message in enumerate(messages):
        # Add system message if first turn
        if i == 0:
            conversation_history.append({
                "role": "system",
                "content": prompts.get('cj_prompt', '') + '\n\n' + prompts.get('workflow_prompt', '')
            })
        
        # Add user message
        conversation_history.append({
            "role": "user",
            "content": message['user_input']
        })
        
        # Create eval case for this turn
        eval_case = {
            "eval_id": eval_type,
            "sample_id": f"{conversation['id']}_turn_{message['turn']}",
            
            # Input context
            "input": {
                "messages": conversation_history.copy(),
                "context": {
                    "workflow": context['workflow']['name'],
                    "available_tools": context['workflow'].get('available_tools', []),
                    "persona": context['persona']['name'],
                    "trust_level": context['trustLevel']
                }
            },
            
            # Actual output from conversation
            "actual": {
                "thinking": message['agent_processing']['thinking'],
                "tool_calls": [tc['tool'] for tc in message['agent_processing']['tool_calls']],
                "response": message['agent_processing']['final_response']
            },
            
            # Metadata for analysis
            "metadata": {
                "source_conversation": conversation['id'],
                "turn": message['turn'],
                "timestamp": conversation['timestamp'],
                "latency_ms": message['metrics']['latency_ms'],
                "tokens": message['metrics']['tokens']
            }
        }
        
        # Add ideal expectations (would be manually added or generated)
        if eval_type == "tool_selection":
            # For tool selection evals, we'd manually specify expected tools
            # This is a placeholder - in practice, this would be added manually
            eval_case["ideal"] = {
                "tool_selection": {
                    "should_use_tool": len(message['agent_processing']['tool_calls']) > 0,
                    "acceptable_tools": [],  # Would be filled in manually
                    "unacceptable_tools": []  # Would be filled in manually
                }
            }
        
        eval_cases.append(eval_case)
        
        # Add assistant message to history for next turn
        conversation_history.append({
            "role": "assistant",
            "content": message['agent_processing']['final_response']
        })
    
    return eval_cases


def process_conversations(input_dir: Path, output_dir: Path, eval_type: str, date_filter: str = None):
    """Process all conversations in a directory."""
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all conversation files
    pattern = "**/*.json" if not date_filter else f"**/{date_filter}/*.json"
    conversation_files = list(input_dir.glob(pattern))
    
    print(f"Found {len(conversation_files)} conversations to process")
    
    all_eval_cases = []
    
    for file_path in conversation_files:
        try:
            print(f"Processing {file_path.name}...")
            conversation = load_conversation(file_path)
            eval_cases = convert_to_eval_format(conversation, eval_type)
            all_eval_cases.extend(eval_cases)
            print(f"  Generated {len(eval_cases)} eval cases")
        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
    
    # Write output JSONL file
    output_file = output_dir / f"{eval_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    
    with open(output_file, 'w') as f:
        for case in all_eval_cases:
            f.write(json.dumps(case) + '\n')
    
    print(f"\nWrote {len(all_eval_cases)} eval cases to {output_file}")
    
    # Generate summary statistics
    print("\nSummary Statistics:")
    print(f"  Total conversations: {len(conversation_files)}")
    print(f"  Total eval cases: {len(all_eval_cases)}")
    print(f"  Average turns per conversation: {len(all_eval_cases) / len(conversation_files):.1f}")
    
    # Tool usage statistics
    tool_usage = {}
    for case in all_eval_cases:
        for tool in case['actual']['tool_calls']:
            tool_usage[tool] = tool_usage.get(tool, 0) + 1
    
    if tool_usage:
        print("\nTool Usage:")
        for tool, count in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool}: {count}")


def main():
    parser = argparse.ArgumentParser(description='Convert conversations to eval format')
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=Path('hirecj_evals/conversations/playground'),
        help='Directory containing conversation JSON files'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('hirecj_evals/datasets/generated'),
        help='Directory to write JSONL eval files'
    )
    parser.add_argument(
        '--eval-type',
        choices=['tool_selection', 'response_quality', 'grounding_accuracy'],
        default='tool_selection',
        help='Type of eval to generate'
    )
    parser.add_argument(
        '--date',
        help='Filter conversations by date (YYYY-MM-DD format)'
    )
    
    args = parser.parse_args()
    
    process_conversations(
        args.input_dir,
        args.output_dir,
        args.eval_type,
        args.date
    )


if __name__ == '__main__':
    main()