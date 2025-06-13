#!/usr/bin/env python3
"""
List all tables in the shared database to verify unification.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.supabase_util import execute_query


def list_all_tables():
    """List all tables in the public schema."""
    query = """
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname = 'public' 
    ORDER BY tablename;
    """
    
    print("📊 Tables in shared database:\n")
    
    tables = execute_query(query)
    for table in tables:
        print(f"  • {table[0]}")
    
    print(f"\n✅ Total tables: {len(tables)}")
    
    # Also check if web_sessions exists
    web_sessions_check = execute_query(
        "SELECT COUNT(*) FROM web_sessions;"
    )
    print(f"\n🔐 Web sessions table exists with {web_sessions_check[0][0]} records")


if __name__ == "__main__":
    print("🔍 Verifying database unification...\n")
    list_all_tables()