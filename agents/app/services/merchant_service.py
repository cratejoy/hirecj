"""Service for merchant data access - PostgreSQL only, no Redis."""

from typing import Optional
import logging

from app.config import settings
from app.utils.supabase_util import get_db_session
from app.dbmodels.base import Merchant, MerchantIntegration

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


# Singleton instance
merchant_service = MerchantService()
