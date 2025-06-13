"""Merchant storage service using PostgreSQL."""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

# Import database utilities and models
from app.utils.database import get_db_session
from shared.db_models import Merchant, MerchantIntegration, MerchantToken, User
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

logger = logging.getLogger(__name__)

class MerchantStorage:
    """Handles persistent storage of merchant data using PostgreSQL."""

    def store_token(self, shop_domain: str, access_token: str, scopes: str, user_id: str = None) -> Dict[str, Any]:
        """
        Store Shopify OAuth token in the merchant_integrations table and link to user.
        This is now the single source of truth for tokens.

        Args:
            shop_domain: Shopify domain (e.g., 'example.myshopify.com')
            access_token: The access token from Shopify
            scopes: The scopes granted
            user_id: User ID to associate with this merchant

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
            
            # If user_id provided, create MerchantToken to link user to merchant
            if user_id:
                merchant_token_stmt = insert(MerchantToken).values(
                    user_id=user_id,
                    merchant_id=merchant_id,
                    shop_domain=shop_domain,
                    access_token=access_token,
                    scopes=scopes
                ).on_conflict_do_update(
                    constraint='merchant_tokens_user_id_merchant_id_key',
                    set_={
                        'access_token': access_token,
                        'scopes': scopes,
                        'shop_domain': shop_domain
                    }
                )
                session.execute(merchant_token_stmt)
                logger.info(f"[MERCHANT_STORAGE] Created MerchantToken linking user {user_id} to merchant {merchant_id}")
            
            session.commit()

            logger.info(f"[MERCHANT_STORAGE] Stored token for {shop_domain} (merchant_id: {merchant_id})")

            return {
                "merchant_id": merchant_id,
                "is_new": is_new,
            }

# Singleton instance
merchant_storage = MerchantStorage()
