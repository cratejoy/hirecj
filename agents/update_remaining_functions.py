#!/usr/bin/env python3
"""Update the remaining analytics functions to accept session parameter"""

import sys
import os

# Add the agents directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Read the current file
with open('app/lib/freshdesk_analytics_lib.py', 'r') as f:
    content = f.read()

# List of updates to make
updates = [
    # get_open_ticket_distribution
    {
        'old': '        Args:\n            merchant_id: The merchant ID to filter by (NEVER look up by name)',
        'new': '        Args:\n            session: SQLAlchemy session for database queries\n            merchant_id: The merchant ID to filter by (NEVER look up by name)'
    },
    {
        'old': '        """\n        with get_db_session() as session:\n            # Get current time for age calculations',
        'new': '        """\n        # Get current time for age calculations'
    },
    # get_response_time_metrics
    {
        'old': '    def get_response_time_metrics(merchant_id: int, date_range: Dict[str, date]) -> Dict[str, Any]:',
        'new': '    def get_response_time_metrics(session: Session, merchant_id: int, date_range: Dict[str, date]) -> Dict[str, Any]:'
    },
    {
        'old': '        Args:\n            merchant_id: The merchant ID to filter by\n            date_range: Dict with \'start\' and \'end\' date keys',
        'new': '        Args:\n            session: SQLAlchemy session for database queries\n            merchant_id: The merchant ID to filter by\n            date_range: Dict with \'start\' and \'end\' date keys'
    },
    # get_volume_trends
    {
        'old': '    def get_volume_trends(merchant_id: int, days: int = 60) -> Dict[str, Any]:',
        'new': '    def get_volume_trends(session: Session, merchant_id: int, days: int = 60) -> Dict[str, Any]:'
    },
    {
        'old': '        Args:\n            merchant_id: The merchant ID to filter by\n            days: Number of days to analyze (default: 60)',
        'new': '        Args:\n            session: SQLAlchemy session for database queries\n            merchant_id: The merchant ID to filter by\n            days: Number of days to analyze (default: 60)'
    },
    # get_root_cause_analysis
    {
        'old': '    def get_root_cause_analysis(merchant_id: int, date_str: str, spike_threshold: float = 2.0) -> Dict[str, Any]:',
        'new': '    def get_root_cause_analysis(session: Session, merchant_id: int, date_str: str, spike_threshold: float = 2.0) -> Dict[str, Any]:'
    },
    {
        'old': '        Args:\n            merchant_id: The merchant ID to filter by\n            date_str: Date to analyze in YYYY-MM-DD format\n            spike_threshold: Standard deviations to consider a spike (default: 2.0)',
        'new': '        Args:\n            session: SQLAlchemy session for database queries\n            merchant_id: The merchant ID to filter by\n            date_str: Date to analyze in YYYY-MM-DD format\n            spike_threshold: Standard deviations to consider a spike (default: 2.0)'
    }
]

# Apply updates
new_content = content
for update in updates:
    if update['old'] in new_content:
        new_content = new_content.replace(update['old'], update['new'])
        print(f"✓ Updated: {update['old'][:50]}...")
    else:
        print(f"✗ Not found: {update['old'][:50]}...")

# Find and remove 'with get_db_session() as session:' blocks
import re

# Pattern to find these blocks and dedent the content
pattern = r'(\s*)with get_db_session\(\) as session:\n'
matches = list(re.finditer(pattern, new_content))

print(f"\nFound {len(matches)} 'with get_db_session()' blocks to remove")

# Process from end to beginning to maintain positions
for match in reversed(matches):
    indent = match.group(1)
    start = match.start()
    end = match.end()
    
    # Find the end of the with block (next line with same or less indentation)
    lines = new_content[end:].split('\n')
    block_lines = []
    
    for i, line in enumerate(lines):
        if line.strip() == '':  # Empty line
            block_lines.append(line)
        elif line.startswith(indent + '    '):  # Part of the with block
            # Remove one level of indentation
            block_lines.append(line[4:])
        else:  # End of with block
            break
    
    # Replace the with statement and dedent the block
    replacement = '\n'.join(block_lines)
    if block_lines:
        replacement += '\n'
    
    # Only do a few key ones for now
    if 'get_open_ticket_distribution' in new_content[start-200:start] or \
       'get_response_time_metrics' in new_content[start-200:start] or \
       'get_volume_trends' in new_content[start-200:start] or \
       'get_root_cause_analysis' in new_content[start-200:start]:
        new_content = new_content[:start] + replacement + new_content[end + i * (len(lines[0]) + 1):]
        print(f"✓ Removed 'with get_db_session()' block at position {start}")

# Write the updated content
with open('app/lib/freshdesk_analytics_lib.py', 'w') as f:
    f.write(new_content)

print("\nUpdates complete!")