#!/usr/bin/env python
"""Check structure of etl_freshdesk_tickets table"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.supabase_util import execute_query

def check_structure():
    print("=== Checking etl_freshdesk_tickets table structure ===")
    results = execute_query("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'etl_freshdesk_tickets'
        ORDER BY ordinal_position
    """)
    
    if results:
        print(f"Found {len(results)} columns:")
        for col_name, data_type, nullable in results:
            print(f"  - {col_name}: {data_type} {'(nullable)' if nullable == 'YES' else '(not null)'}")
    
    print("\n=== Sample ticket data (first row) ===")
    results = execute_query("""
        SELECT * FROM etl_freshdesk_tickets LIMIT 1
    """)
    
    if results:
        # Get column names
        col_results = execute_query("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'etl_freshdesk_tickets'
            ORDER BY ordinal_position
        """)
        
        columns = [row[0] for row in col_results]
        
        print("\nFirst ticket:")
        for i, value in enumerate(results[0]):
            print(f"  {columns[i]}: {str(value)[:200]}...")

if __name__ == "__main__":
    check_structure()