#!/usr/bin/env python3
"""Fill database with migrations, seed data, and recent records."""

import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n📌 {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    
    print(f"✅ {description} completed")
    if result.stdout:
        print(result.stdout)

def fill_database():
    """Run migrations, seed data, and sync recent records."""
    print("🚀 Filling database with fresh data\n")
    
    # Calculate date 90 days ago for tickets, 4 days for customers
    ninety_days_ago = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%dT00:00:00Z')
    four_days_ago = (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%dT00:00:00Z')
    print(f"Will sync tickets from: {ninety_days_ago} (90 days)")
    print(f"Will sync customers from: {four_days_ago} (4 days)")
    
    base_dir = Path(__file__).parent.parent
    scripts_dir = base_dir / "scripts"
    
    # Step 1: Run migrations
    print("\n" + "="*60)
    print("STEP 1: Running migrations")
    print("="*60)
    
    migrations_dir = scripts_dir / "migrations"
    migrations = [
        "001_create_all_tables.sql"  # This already creates tables with the new schema
    ]
    
    for migration in migrations:
        migration_path = migrations_dir / migration
        if migration_path.exists():
            run_command(
                f"cd {base_dir} && source venv/bin/activate && python scripts/run_migration.py {migration_path}",
                f"Migration: {migration}"
            )
    
    # Step 2: Seed test merchant
    print("\n" + "="*60)
    print("STEP 2: Seeding test merchant")
    print("="*60)
    
    run_command(
        f"cd {base_dir} && source venv/bin/activate && python scripts/seed_test_data.py",
        "Seed test merchant"
    )
    
    # # Step 3: Sync Shopify customers
    # print("\n" + "="*60)
    # print("STEP 3: Syncing Shopify customers")
    # print("="*60)
    
    # run_command(
    #     f"cd {base_dir} && source venv/bin/activate && python scripts/sync_shopify.py --customers --since {four_days_ago}",
    #     "Sync Shopify customers"
    # )
    
    # Step 4: Sync Freshdesk tickets with conversations
    print("\n" + "="*60)
    print("STEP 4: Syncing Freshdesk tickets with conversations")
    print("="*60)
    print("📌 Using smart sync strategy:")
    print("   - Fetching all tickets from last 90 days")
    print("   - Fetching conversations only for tickets from last 30 days")
    print("⚠️  Note: This fetches conversations individually and may take time")
    
    run_command(
        f"cd {base_dir} && source venv/bin/activate && python scripts/sync_freshdesk.py --days 90 --conversation-days 30",
        "Smart sync of Freshdesk tickets"
    )
    
    # Step 5: Show summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    # Get counts using Python to avoid shell issues
    summary_cmd = f"""cd {base_dir} && source venv/bin/activate && python -c "
from app.utils.supabase_util import get_db_session
from app.models.base import Merchant, ShopifyCustomer, FreshdeskTicket
from sqlalchemy import text
with get_db_session() as session:
    print(f'Merchants: {{session.query(Merchant).count()}}')
    print(f'Shopify Customers: {{session.query(ShopifyCustomer).count()}}')
    print(f'Freshdesk Tickets: {{session.query(FreshdeskTicket).count()}}')
    
    # Check conversation coverage
    result = session.execute(text('''
        SELECT 
            COUNT(*) as with_conversations,
            (SELECT COUNT(*) FROM etl_freshdesk_tickets) as total
        FROM etl_freshdesk_tickets 
        WHERE data ? 'conversations'
    '''))
    row = result.fetchone()
    if row[1] > 0:
        coverage = (row[0] / row[1]) * 100
        print(f'  - With conversations: {{row[0]}}/{{row[1]}} ({{coverage:.1f}}%)')
"
"""
    
    subprocess.run(summary_cmd, shell=True)
    
    print("\n✨ Database filled successfully!")

if __name__ == "__main__":
    fill_database()