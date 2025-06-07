#!/usr/bin/env python3
"""Clear all tables, triggers, and functions from the database."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.utils.supabase_util import get_db_connection

def clear_database():
    """Drop all tables, triggers, and functions."""
    print("🗑️  Clearing database...\n")
    
    # Check for --force flag
    if len(sys.argv) < 2 or sys.argv[1] != '--force':
        # Confirm this destructive action
        try:
            response = input("⚠️  This will DELETE ALL DATA. Are you sure? (yes/no): ")
            if response.lower() != 'yes':
                print("Cancelled.")
                return
        except EOFError:
            print("\n❌ Interactive confirmation required. Use --force to skip.")
            print("   python scripts/clear_database.py --force")
            sys.exit(1)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                # Drop all views first
                print("Dropping views...")
                # Get all regular views
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'public'
                """)
                views = [row[0] for row in cur.fetchall()]
                
                for view in views:
                    cur.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
                
                # Get all materialized views
                cur.execute("""
                    SELECT matviewname 
                    FROM pg_matviews 
                    WHERE schemaname = 'public'
                """)
                matviews = [row[0] for row in cur.fetchall()]
                
                for matview in matviews:
                    cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {matview} CASCADE")
                
                total_views = len(views) + len(matviews)
                if total_views:
                    print(f"  Dropped {total_views} views ({len(views)} regular, {len(matviews)} materialized)")
                
                # Drop all tables (CASCADE will drop dependent objects)
                print("Dropping tables...")
                # First, get all tables dynamically
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                """)
                all_tables = [row[0] for row in cur.fetchall()]
                
                if all_tables:
                    # Drop each table individually to ensure CASCADE works properly
                    for table in all_tables:
                        cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                    print(f"  Dropped {len(all_tables)} tables")
                
                # Drop all functions
                print("Dropping functions...")
                # Get all functions dynamically
                cur.execute("""
                    SELECT routine_name, 
                           string_agg(
                               CASE p.data_type 
                                   WHEN 'USER-DEFINED' THEN p.udt_name
                                   ELSE p.data_type 
                               END, ', ' ORDER BY p.ordinal_position
                           ) as params
                    FROM information_schema.routines r
                    LEFT JOIN information_schema.parameters p 
                        ON r.specific_name = p.specific_name
                        AND p.parameter_mode = 'IN'
                    WHERE r.routine_schema = 'public'
                    AND r.routine_type = 'FUNCTION'
                    GROUP BY routine_name
                """)
                functions = cur.fetchall()
                
                for func_name, params in functions:
                    if params:
                        drop_stmt = f"DROP FUNCTION IF EXISTS {func_name}({params}) CASCADE"
                    else:
                        drop_stmt = f"DROP FUNCTION IF EXISTS {func_name}() CASCADE"
                    try:
                        cur.execute(drop_stmt)
                    except Exception:
                        # Try without parameters if it fails
                        cur.execute(f"DROP FUNCTION IF EXISTS {func_name} CASCADE")
                
                if functions:
                    print(f"  Dropped {len(functions)} functions")
                
                # Drop enum types
                print("Dropping enum types...")
                cur.execute("""
                    SELECT typname 
                    FROM pg_type 
                    WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                    AND typtype = 'e'
                """)
                types = [row[0] for row in cur.fetchall()]
                
                for type_name in types:
                    cur.execute(f"DROP TYPE IF EXISTS {type_name} CASCADE")
                
                if types:
                    print(f"  Dropped {len(types)} custom types")
                
                conn.commit()
                print("\n✅ Database cleared successfully!")
                
            except Exception as e:
                conn.rollback()
                print(f"❌ Error clearing database: {e}")
                sys.exit(1)

if __name__ == "__main__":
    clear_database()