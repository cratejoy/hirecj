#!/usr/bin/env python
"""Check what tables exist in the database"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.supabase_util import execute_query

def check_tables():
    print("=== Checking database tables ===")
    results = execute_query("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    if results:
        print(f"Found {len(results)} tables:")
        for row in results:
            print(f"  - {row[0]}")
    
    print("\n=== Checking for any table with 'ticket' in name ===")
    results = execute_query("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_name ILIKE '%ticket%'
    """)
    
    if results:
        print(f"Found {len(results)} ticket-related tables:")
        for row in results:
            print(f"  - {row[0]}")
    
    print("\n=== Checking for any table with 'freshdesk' in name ===")
    results = execute_query("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_name ILIKE '%freshdesk%'
    """)
    
    if results:
        print(f"Found {len(results)} freshdesk-related tables:")
        for row in results:
            print(f"  - {row[0]}")

if __name__ == "__main__":
    check_tables()