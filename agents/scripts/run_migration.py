#!/usr/bin/env python3
"""Run database migrations for the HireCJ data pipeline."""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.supabase_util import get_db_connection

def run_migration(migration_file: str):
    """Execute a SQL migration file."""
    print(f"Running migration: {migration_file}")
    
    # Read the migration file
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    # Execute the migration
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
    
    print("✅ Migration completed successfully")

def show_example_queries():
    """Show example queries without inserting data."""
    print("\n📊 Example queries (no data inserted):")
    print("""
    -- Insert a production merchant
    INSERT INTO merchants (name, is_test) VALUES ('acme_corp', FALSE);
    
    -- Insert a test merchant  
    INSERT INTO merchants (name, is_test) VALUES ('test_merchant_1', TRUE);
    
    -- Find all test merchants
    SELECT * FROM merchants WHERE is_test = TRUE;
    
    -- Insert customer with ETL'd data
    INSERT INTO customers (merchant_id, shopify_id, data)
    VALUES (1, 'cust_123', '{
        "name": "John Smith",
        "email": "john@example.com",
        "subscription_tier": "premium",
        "tags": ["vip", "early_adopter"]
    }');
    
    -- Find VIP customers
    SELECT shopify_id, data->>'name' as name
    FROM customers
    WHERE data->'tags' ? 'vip';
    
    -- Find high priority tickets
    SELECT external_id, data->>'subject' as subject
    FROM support_tickets
    WHERE data->>'priority' = 'high';
    
    -- Count tickets by category
    SELECT 
        data->>'category' as category,
        COUNT(*) as count
    FROM support_tickets
    GROUP BY category
    ORDER BY count DESC;
    """)

def show_schema_info():
    """Display information about the created schema."""
    print("\n📋 Schema Information:")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get table information
            cur.execute("""
                SELECT 
                    table_name,
                    obj_description(pgc.oid, 'pg_class') as comment
                FROM information_schema.tables
                JOIN pg_catalog.pg_class pgc ON pgc.relname = table_name
                WHERE table_schema = 'public'
                AND table_name IN ('merchants', 'customers', 'support_tickets', 'sync_metadata')
                ORDER BY table_name
            """)
            
            tables = cur.fetchall()
            for table_name, comment in tables:
                print(f"\n{table_name}: {comment}")
                
                # Get column information
                cur.execute("""
                    SELECT 
                        column_name, 
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND table_schema = 'public'
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = cur.fetchall()
                for col_name, data_type, nullable, default in columns:
                    nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                    default_str = f" DEFAULT {default}" if default else ""
                    print(f"  - {col_name}: {data_type} {nullable_str}{default_str}")

if __name__ == "__main__":
    # Check if a specific migration file was provided
    if len(sys.argv) > 1:
        migration_file = Path(sys.argv[1])
    else:
        migration_file = Path(__file__).parent / "001_create_all_tables.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    try:
        # Run the migration
        run_migration(migration_file)
        
        # Show schema information
        show_schema_info()
        
        # Show example queries only for base tables migration
        if "001_create_all_tables" in str(migration_file):
            show_example_queries()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)