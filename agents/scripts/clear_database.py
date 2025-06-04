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
                cur.execute("""
                    DROP VIEW IF EXISTS ticket_analytics CASCADE;
                    DROP MATERIALIZED VIEW IF EXISTS daily_ticket_metrics CASCADE;
                """)
                
                # Drop all tables (CASCADE will drop dependent objects)
                print("Dropping tables...")
                cur.execute("""
                    DROP TABLE IF EXISTS daily_ticket_summaries CASCADE;
                    DROP TABLE IF EXISTS etl_freshdesk_ratings CASCADE;
                    DROP TABLE IF EXISTS etl_freshdesk_conversations CASCADE;
                    DROP TABLE IF EXISTS etl_freshdesk_tickets CASCADE;
                    DROP TABLE IF EXISTS etl_shopify_customers CASCADE;
                    DROP TABLE IF EXISTS merchant_integrations CASCADE;
                    DROP TABLE IF EXISTS sync_metadata CASCADE;
                    DROP TABLE IF EXISTS support_tickets CASCADE;
                    DROP TABLE IF EXISTS customers CASCADE;
                    DROP TABLE IF EXISTS merchants CASCADE;
                """)
                
                # Drop all functions
                print("Dropping functions...")
                cur.execute("""
                    DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
                    DROP FUNCTION IF EXISTS refresh_daily_metrics() CASCADE;
                """)
                
                # Drop enum types
                print("Dropping enum types...")
                cur.execute("""
                    DROP TYPE IF EXISTS source_type CASCADE;
                """)
                
                conn.commit()
                print("\n✅ Database cleared successfully!")
                
            except Exception as e:
                conn.rollback()
                print(f"❌ Error clearing database: {e}")
                sys.exit(1)

if __name__ == "__main__":
    clear_database()