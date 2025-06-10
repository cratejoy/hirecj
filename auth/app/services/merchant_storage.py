"""Merchant storage service using PostgreSQL."""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

# This is a bit of a hack to import from the agents service.
# Ideally, dbmodels would be in a shared library.
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'agents'))

from app.utils.supabase_util import get_db_session
from app.dbmodels.base import Merchant, MerchantIntegration
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

class MerchantStorage:
    """Handles persistent storage of merchant data using PostgreSQL."""

    def store_token(self, shop_domain: str, access_token: str, scopes: str) -> Dict[str, Any]:
        """
        Store Shopify OAuth token in the merchant_integrations table.
        This is now the single source of truth for tokens.

        Args:
            shop_domain: Shopify domain (e.g., 'example.myshopify.com')
            access_token: The access token from Shopify
            scopes: The scopes granted

        Returns:
            A dict containing merchant_id and a boolean is_new
        """
        merchant_name = shop_domain.replace('.myshopify.com', '')
        
        with get_db_session() as session:
            # Check if merchant exists to determine if they are new
            existing_merchant = session.query(Merchant).filter_by(name=merchant_name).first()
            is_new = existing_merchant is None

            # Upsert merchant
            merchant_stmt = insert(Merchant).values(
                name=merchant_name,
                is_test=False  # OAuth installs are not test merchants
            ).on_conflict_do_update(
                index_elements=['name'],
                set_={'is_test': False}
            ).returning(Merchant.id)
            
            merchant_id = session.execute(merchant_stmt).scalar_one()

            # Upsert integration
            config_data = {
                'shop_domain': shop_domain,
                'scopes': scopes,
                'installed_at': datetime.now(timezone.utc).isoformat()
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

            logger.info(f"[MERCHANT_STORAGE] Stored token for {shop_domain} (merchant_id: {merchant_id})")

            return {
                "merchant_id": merchant_id,
                "is_new": is_new,
            }

# Singleton instance
merchant_storage = MerchantStorage()
