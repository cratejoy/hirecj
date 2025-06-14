"""Service for merchant data access - PostgreSQL only, no Redis."""

from typing import Optional
import logging

from typing import Optional
from sqlalchemy import select

from app.config import settings
from app.utils.supabase_util import get_db_session
from shared.db_models import Merchant, MerchantIntegration, MerchantToken

logger = logging.getLogger(__name__)


class MerchantService:
    """Service for merchant data access - single source of truth."""

    def get_shopify_token(self, shop_domain: str) -> Optional[str]:
        """Get Shopify access token from PostgreSQL only."""

        merchant_name = shop_domain.replace('.myshopify.com', '')
        with get_db_session() as session:
            query = session.query(MerchantIntegration.api_key).join(Merchant).filter(
                Merchant.name == merchant_name,
                MerchantIntegration.platform == 'shopify',
                MerchantIntegration.is_active == True
            )
            result = query.scalar()
            if result is None:
                raise RuntimeError(f"No active Shopify token for {shop_domain}")
            return result

    def get_active_shopify_domain_for_user(self, user_id: str) -> Optional[str]:
        """Return shop_domain if this user already has an active Shopify integration."""
        with get_db_session() as db:
            return db.scalar(
                select(MerchantToken.shop_domain)
                .join(
                    MerchantIntegration,
                    MerchantIntegration.merchant_id == MerchantToken.merchant_id
                )
                .where(MerchantToken.user_id == user_id)
                .where(MerchantIntegration.platform == "shopify")
                .where(MerchantIntegration.is_active.is_(True))
                .limit(1)
            )


# Singleton instance
merchant_service = MerchantService()
