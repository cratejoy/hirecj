#!/usr/bin/env python3
"""Seed test data into the database using SQLAlchemy."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
from sqlalchemy.dialects.postgresql import insert
from app.utils.supabase_util import get_db_session
from app.dbmodels.base import Merchant, MerchantIntegration

def seed_test_merchant(merchant_name: str):
    """Create a test merchant record using SQLAlchemy."""
    with get_db_session() as session:
        # Use PostgreSQL's INSERT ... ON CONFLICT
        stmt = insert(Merchant).values(
            name=merchant_name,
            is_test=True
        )
        
        # On conflict, update is_test and let the trigger handle updated_at
        stmt = stmt.on_conflict_do_update(
            index_elements=['name'],
            set_=dict(is_test=stmt.excluded.is_test)
        )
        
        # Execute and get the result
        result = session.execute(stmt.returning(Merchant))
        merchant = result.scalar_one()
        
        # Refresh to get all fields
        session.refresh(merchant)
        
        print(f"✅ Merchant created/updated:")
        print(f"   ID: {merchant.id}")
        print(f"   Name: {merchant.name}")
        print(f"   Test: {merchant.is_test}")
        print(f"   Created: {merchant.created_at}")
        print(f"   Updated: {merchant.updated_at}")
        
        # Check if this was an insert or update
        if merchant.updated_at and merchant.created_at != merchant.updated_at:
            print("   (Record was updated)")
        else:
            print("   (New record created)")
        
        return merchant.id

def seed_merchant_integrations(merchant_id: int):
    """Create merchant integration records with API keys."""
    with get_db_session() as session:
        # Get API keys from environment
        freshdesk_key = os.getenv('FRESHDESK_API_KEY')
        shopify_key = os.getenv('SHOPIFY_API_KEY')
        
        integrations_created = []
        
        # Seed Freshdesk integration
        if freshdesk_key:
            stmt = insert(MerchantIntegration).values(
                merchant_id=merchant_id,
                platform='freshdesk',
                api_key=freshdesk_key,
                config={
                    'domain': os.getenv('FRESHDESK_DOMAIN', 'cratejoy.freshdesk.com')
                },
                is_active=True
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['merchant_id', 'platform'],
                set_={
                    'api_key': stmt.excluded.api_key,
                    'config': stmt.excluded.config,
                    'is_active': stmt.excluded.is_active
                }
            )
            
            session.execute(stmt)
            integrations_created.append('Freshdesk')
        
        # Seed Shopify integration
        if shopify_key:
            stmt = insert(MerchantIntegration).values(
                merchant_id=merchant_id,
                platform='shopify',
                api_key=shopify_key,
                config={
                    'shop_name': os.getenv('SHOPIFY_SHOP_NAME', 'amir-elaguizy'),
                    'api_version': '2024-01'
                },
                is_active=True
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['merchant_id', 'platform'],
                set_={
                    'api_key': stmt.excluded.api_key,
                    'config': stmt.excluded.config,
                    'is_active': stmt.excluded.is_active
                }
            )
            
            session.execute(stmt)
            integrations_created.append('Shopify')
        
        session.commit()
        
        if integrations_created:
            print(f"\n✅ Integrations created/updated:")
            for integration in integrations_created:
                print(f"   - {integration}")
        else:
            print(f"\n⚠️  No API keys found in environment - skipping integrations")
        
        return integrations_created

def main():
    """Main function to seed test data."""
    print("🌱 Seeding test data with SQLAlchemy...\n")
    
    try:
        # Create test merchant
        merchant_id = seed_test_merchant("amir_elaguizy")
        
        # Create merchant integrations
        seed_merchant_integrations(merchant_id)
        
        print(f"\n✨ Test data seeded successfully!")
        
        print(f"\n📚 Next steps:")
        print(f"1. Run initial data sync:")
        print(f"   python scripts/sync_freshdesk.py --tickets --since 2024-01-01T00:00:00Z")
        print(f"   python scripts/sync_shopify.py --customers --since 2024-01-01T00:00:00Z")
        print(f"\n2. Run incremental syncs:")
        print(f"   python scripts/sync_freshdesk.py --tickets")
        print(f"   python scripts/sync_shopify.py --customers")
        print(f"\n3. Check data in database:")
        print(f"   - Merchants: SELECT * FROM merchants;")
        print(f"   - Customers: SELECT COUNT(*) FROM etl_shopify_customers;")
        print(f"   - Tickets: SELECT COUNT(*) FROM etl_freshdesk_tickets;")
        print(f"   - Sync status: SELECT * FROM sync_metadata;")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()