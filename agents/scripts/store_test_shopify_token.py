#!/usr/bin/env python3
"""Store test Shopify tokens in PostgreSQL for development."""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# Add project directories to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root.parent))
sys.path.insert(0, str(project_root))

from shared.env_loader import get_env
from sqlalchemy.dialects.postgresql import insert
from app.utils.supabase_util import get_db_session
from app.dbmodels.base import Merchant, MerchantIntegration

def store_test_token(shop_domain: str, access_token: str):
    """Store a test token in PostgreSQL merchant_integrations table."""
    
    db_url = get_env("SUPABASE_CONNECTION_STRING")
    if not db_url:
        print("❌ SUPABASE_CONNECTION_STRING not set in .env file.")
        return

    with get_db_session() as session:
        # Create/update merchant
        merchant_name = shop_domain.replace('.myshopify.com', '')
        
        merchant_stmt = insert(Merchant).values(
            name=merchant_name,
            is_test=True
        ).on_conflict_do_update(
            index_elements=['name'],
            set_={'is_test': True}
        ).returning(Merchant.id)
        
        merchant_id = session.execute(merchant_stmt).scalar_one()
        
        # Store token in merchant_integrations
        config_data = {
            'shop_domain': shop_domain,
            'stored_at': datetime.utcnow().isoformat(),
            'source': 'test_script',
            'scopes': 'read_products,read_orders,read_customers'
        }
        
        integration_stmt = insert(MerchantIntegration).values(
            merchant_id=merchant_id,
            platform='shopify',
            api_key=access_token,
            config=config_data,
            is_active=True
        )
        
        integration_stmt = integration_stmt.on_conflict_do_update(
            index_elements=['merchant_id', 'platform'],
            set_={
                'api_key': integration_stmt.excluded.api_key,
                'config': integration_stmt.excluded.config,
                'is_active': integration_stmt.excluded.is_active
            }
        )
        
        session.execute(integration_stmt)
        session.commit()
        
        print(f"✅ Stored token for {shop_domain} (merchant_id: {merchant_id})")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python agents/scripts/store_test_shopify_token.py <shop_domain> <access_token>")
        print("Example: python agents/scripts/store_test_shopify_token.py cratejoy-dev.myshopify.com shpat_xxxxx")
        sys.exit(1)
    
    shop_domain = sys.argv[1]
    access_token = sys.argv[2]
    
    store_test_token(shop_domain, access_token)
