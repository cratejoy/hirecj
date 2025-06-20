#!/usr/bin/env python3
"""
Privacy scrubbing utility for production conversations.
Removes PII and sensitive data before using conversations for evals.
"""

import json
import re
import hashlib
from pathlib import Path
from typing import Dict, Any, List
import argparse


# Patterns for common PII
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')


def hash_value(value: str, salt: str = "hirecj") -> str:
    """Create a consistent hash of a value for anonymization."""
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:8]


def scrub_text(text: str) -> str:
    """Remove PII from text content."""
    # Replace emails
    text = EMAIL_PATTERN.sub('[EMAIL_REDACTED]', text)
    
    # Replace phone numbers
    text = PHONE_PATTERN.sub('[PHONE_REDACTED]', text)
    
    # Replace SSNs
    text = SSN_PATTERN.sub('[SSN_REDACTED]', text)
    
    # Replace credit cards
    text = CREDIT_CARD_PATTERN.sub('[CC_REDACTED]', text)
    
    # Replace IPs (but not version numbers like 1.2.3.4)
    def replace_ip(match):
        ip = match.group(0)
        # Check if all octets are < 10 (likely a version number)
        octets = ip.split('.')
        if all(int(o) < 10 for o in octets):
            return ip
        return '[IP_REDACTED]'
    
    text = IP_PATTERN.sub(replace_ip, text)
    
    return text


def anonymize_persona(persona: Dict[str, Any]) -> Dict[str, Any]:
    """Anonymize persona information."""
    if not persona:
        return persona
    
    # Create anonymized copy
    anon_persona = persona.copy()
    
    # Hash the ID to maintain consistency
    if 'id' in anon_persona:
        anon_persona['id'] = f"persona_{hash_value(anon_persona['id'])}"
    
    # Anonymize name and business
    if 'name' in anon_persona:
        anon_persona['name'] = f"User_{hash_value(anon_persona['name'])}"
    
    if 'business' in anon_persona:
        anon_persona['business'] = f"Business_{hash_value(anon_persona['business'])}"
    
    return anon_persona


def scrub_conversation(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """Scrub a single conversation of PII."""
    # Deep copy to avoid modifying original
    scrubbed = json.loads(json.dumps(conversation))
    
    # Anonymize persona
    if 'context' in scrubbed and 'persona' in scrubbed['context']:
        scrubbed['context']['persona'] = anonymize_persona(scrubbed['context']['persona'])
    
    # Scrub messages
    if 'messages' in scrubbed:
        for message in scrubbed['messages']:
            # Scrub user input
            if 'user_input' in message:
                message['user_input'] = scrub_text(message['user_input'])
            
            # Scrub agent processing
            if 'agent_processing' in message:
                ap = message['agent_processing']
                
                if 'thinking' in ap:
                    ap['thinking'] = scrub_text(ap['thinking'])
                
                if 'final_response' in ap:
                    ap['final_response'] = scrub_text(ap['final_response'])
                
                if 'intermediate_responses' in ap:
                    ap['intermediate_responses'] = [
                        scrub_text(resp) for resp in ap['intermediate_responses']
                    ]
                
                # Scrub tool calls
                if 'tool_calls' in ap:
                    for tool_call in ap['tool_calls']:
                        if 'args' in tool_call:
                            # Recursively scrub args
                            tool_call['args'] = scrub_dict_values(tool_call['args'])
                        if 'result' in tool_call:
                            tool_call['result'] = scrub_dict_values(tool_call['result'])
    
    return scrubbed


def scrub_dict_values(data: Any) -> Any:
    """Recursively scrub dictionary values."""
    if isinstance(data, dict):
        return {k: scrub_dict_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [scrub_dict_values(item) for item in data]
    elif isinstance(data, str):
        return scrub_text(data)
    else:
        return data


def process_directory(input_dir: Path, output_dir: Path):
    """Process all conversations in a directory."""
    
    # Create output directory structure
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all JSON files
    json_files = list(input_dir.glob("**/*.json"))
    
    print(f"Found {len(json_files)} conversations to scrub")
    
    for file_path in json_files:
        try:
            print(f"Processing {file_path.name}...")
            
            # Load conversation
            with open(file_path, 'r') as f:
                conversation = json.load(f)
            
            # Scrub PII
            scrubbed = scrub_conversation(conversation)
            
            # Maintain directory structure in output
            relative_path = file_path.relative_to(input_dir)
            output_path = output_dir / relative_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write scrubbed version
            with open(output_path, 'w') as f:
                json.dump(scrubbed, f, indent=2)
            
            print(f"  ✓ Scrubbed to {output_path}")
            
        except Exception as e:
            print(f"  ✗ Error processing {file_path}: {e}")
    
    print(f"\nScrubbing complete. Output written to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description='Scrub PII from conversations')
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=Path('hirecj_evals/conversations/production'),
        help='Directory containing conversations to scrub'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('hirecj_evals/conversations/production_scrubbed'),
        help='Directory to write scrubbed conversations'
    )
    
    args = parser.parse_args()
    
    if not args.input_dir.exists():
        print(f"Error: Input directory {args.input_dir} does not exist")
        return
    
    process_directory(args.input_dir, args.output_dir)


if __name__ == '__main__':
    main()