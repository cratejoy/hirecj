#!/usr/bin/env python3
"""Fill database with migrations, seed data, and recent records."""

import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

def run_command(cmd, description, ignore_errors=False):
    """Run a command and handle errors."""
    print(f"\n📌 {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        if ignore_errors:
            print(f"⚠️  {description} had warnings but continuing...")
            if result.stderr:
                print(f"   Details: {result.stderr.strip()}")
        else:
            print(f"❌ Failed: {description}")
            print(f"Error: {result.stderr}")
            sys.exit(1)
    else:
        print(f"✅ {description} completed")
        if result.stdout:
            print(result.stdout)

def fill_database():
    """Run migrations, seed data, and sync recent records."""
    print("🚀 Filling database with fresh data\n")
    
    # Calculate date 180 days ago for comprehensive sync
    one_hundred_eighty_days_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%dT00:00:00Z')
    print(f"Will sync tickets from: {one_hundred_eighty_days_ago} (180 days)")
    print(f"Will sync customers from: {one_hundred_eighty_days_ago} (180 days)")
    
    base_dir = Path(__file__).parent.parent
    scripts_dir = base_dir / "scripts"
    
    # Step 1: Run migrations
    print("\n" + "="*60)
    print("STEP 1: Running migrations")
    print("="*60)
    
    migrations_dir = base_dir / "app" / "migrations"
    # Get all SQL migration files in order
    migrations = sorted([
        f.name for f in migrations_dir.glob("*.sql") 
        if f.name[0:3].isdigit()
    ])
    
    for migration in migrations:
        migration_path = migrations_dir / migration
        if migration_path.exists():
            run_command(
                f"cd {base_dir} && source venv/bin/activate && python scripts/run_migration.py {migration_path}",
                f"Migration: {migration}",
                ignore_errors=True  # Ignore if migration already exists
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
    print("STEP 4: Syncing Freshdesk tickets with conversations (180 days)")
    print("="*60)
    print("⚠️  Note: This will fetch ALL tickets from the last 180 days including stats data")
    print("⚠️  This may take several minutes depending on the number of tickets")
    
    run_command(
        f"cd {base_dir} && source venv/bin/activate && python scripts/sync_freshdesk.py --days 180",
        "Full sync of Freshdesk tickets (180 days with stats)"
    )
    
    # Step 5: Skip satisfaction ratings for quick test
    print("\n" + "="*60)
    print("STEP 5: Skipping satisfaction ratings sync for quick test")
    print("="*60)
    print("⚠️  Note: Ratings sync is included in the ticket sync above")
    
    # Step 6: Show summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    # Get counts using Python to avoid shell issues
    summary_cmd = f"""cd {base_dir} && source venv/bin/activate && python -c "
from app.utils.supabase_util import get_db_session
from app.dbmodels.base import Merchant
from app.dbmodels.etl_tables import ShopifyCustomer, FreshdeskTicket, FreshdeskConversation, FreshdeskRating
from sqlalchemy import text
with get_db_session() as session:
    print(f'Merchants: {{session.query(Merchant).count()}}')
    print(f'Shopify Customers: {{session.query(ShopifyCustomer).count()}}')
    print(f'Freshdesk Tickets: {{session.query(FreshdeskTicket).count()}}')
    print(f'  - Conversations: {{session.query(FreshdeskConversation).count()}}')
    print(f'  - Ratings: {{session.query(FreshdeskRating).count()}}')
    
    # Check conversation coverage using the separate table
    result = session.execute(text('''
        SELECT 
            COUNT(DISTINCT c.freshdesk_ticket_id) as with_conversations,
            (SELECT COUNT(*) FROM etl_freshdesk_tickets) as total
        FROM etl_freshdesk_conversations c
    '''))
    row = result.fetchone()
    if row[1] > 0:
        coverage = (row[0] / row[1]) * 100
        print(f'  - Tickets with conversations: {{row[0]}}/{{row[1]}} ({{coverage:.1f}}%)')
"
"""
    
    subprocess.run(summary_cmd, shell=True)
    
    print("\n✨ Database filled successfully!")

if __name__ == "__main__":
    fill_database()