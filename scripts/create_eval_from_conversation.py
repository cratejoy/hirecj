#!/usr/bin/env python3
"""
Simple script to convert a conversation to an eval dataset.
Preserves the original filename and creates the eval in the right place.
"""

import json
import argparse
from pathlib import Path


def convert_conversation_to_eval(conv_path: Path, eval_id: str = "no_meta_commentary"):
    """Convert a single conversation to eval format."""
    
    # Load conversation
    with open(conv_path, 'r') as f:
        conv = json.load(f)
    
    # Extract base filename (without .json)
    base_name = conv_path.stem  # e.g., "conv_1750447364223_v0u77ay"
    
    # Create eval cases
    eval_cases = []
    messages = conv.get('messages', [])
    
    # Build conversation history
    system_prompt = conv['prompts']['cj_prompt'] + '\n\n' + conv['prompts']['workflow_prompt']
    conversation_history = [{"role": "system", "content": system_prompt}]
    
    for i, msg in enumerate(messages):
        # Add user message
        conversation_history.append({
            "role": "user",
            "content": msg['user_input']
        })
        
        # Create eval case for this turn
        eval_case = {
            "eval_id": eval_id,
            "sample_id": f"{base_name}_turn_{msg['turn']}",
            "input": {
                "messages": conversation_history.copy()
            },
            "actual": {
                "response": msg['agent_processing']['final_response']
            }
        }
        eval_cases.append(eval_case)
        
        # Add assistant response for next turn
        conversation_history.append({
            "role": "assistant",
            "content": msg['agent_processing']['final_response']
        })
    
    return eval_cases, base_name


def main():
    parser = argparse.ArgumentParser(description='Convert a conversation to eval dataset')
    parser.add_argument('conversation', type=Path, help='Path to conversation JSON file')
    parser.add_argument('--eval-id', default='no_meta_commentary', help='Eval ID to use')
    parser.add_argument('--output-dir', type=Path, default=Path('hirecj_evals/datasets/golden'), 
                        help='Output directory for eval dataset')
    
    args = parser.parse_args()
    
    # Check if conversation exists
    if not args.conversation.exists():
        print(f"Error: Conversation file not found: {args.conversation}")
        return 1
    
    # Convert conversation
    eval_cases, base_name = convert_conversation_to_eval(args.conversation, args.eval_id)
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write JSONL file with same base name
    output_file = args.output_dir / f"{base_name}.jsonl"
    
    with open(output_file, 'w') as f:
        for case in eval_cases:
            f.write(json.dumps(case) + '\n')
    
    print(f"Created eval dataset: {output_file}")
    print(f"Contains {len(eval_cases)} test cases")
    
    # Show what will be tested
    print("\nTest cases:")
    for i, case in enumerate(eval_cases):
        response = case['actual']['response']
        print(f"  Turn {i+1}: {response[:60]}...")
        if len(response) > 60:
            print(f"           ...{response[-40:]}")


if __name__ == '__main__':
    main()