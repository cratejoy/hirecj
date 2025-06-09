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
        
        try:
            with get_db_session() as session:
                query = session.query(MerchantIntegration.api_key).join(Merchant).filter(
                    Merchant.name == merchant_name,
                    MerchantIntegration.platform == 'shopify',
                    MerchantIntegration.is_active == True
                )
                result = query.scalar()
                
                if result:
                    logger.info(f"Got token from PostgreSQL for {shop_domain}")
                    return result
                else:
                    logger.warning(f"No active Shopify token found for {shop_domain}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get token from PostgreSQL: {e}")
            return None


# Singleton instance
merchant_service = MerchantService()
