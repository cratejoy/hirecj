"""Pure data fetching service for Shopify - no analysis or insights."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import logging
from typing import Dict, List, Any, Optional

from app.utils.shopify_util import ShopifyAPI, ShopifyGraphQL
from app.config import settings
from shared.constants import REDIS_TTL_MEDIUM

logger = logging.getLogger(__name__)


class ShopifyDataFetcher:
    """Pure data fetching - no analysis, no insights."""
    
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        
        # Initialize API clients
        self.rest_api = ShopifyAPI(shop_domain=shop_domain, access_token=access_token)
        self.graphql_api = ShopifyGraphQL(shop_domain=shop_domain, access_token=access_token)
        
        # Caching is disabled as Redis is removed.
        # A new caching layer (e.g., in-memory with TTL) could be added here if needed.
        self.cache_enabled = False
            
        self.cache_ttl = REDIS_TTL_MEDIUM  # 15 minutes default
    
    def _get_cached(self, data_type: str) -> Optional[Dict]:
        """Get cached data if available."""
        # Caching disabled
        return None
    
    def _set_cached(self, data_type: str, data: Dict) -> None:
        """Cache data with TTL."""
        # Caching disabled
        pass
    
    def get_counts(self) -> Dict[str, int]:
        """Get basic counts."""
        # Check cache first
        cached = self._get_cached("counts")
        if cached:
            return cached
        
        try:
            data = {
                "customers": self.rest_api.get_customer_count(),
                "total_orders": self.rest_api.get_order_count(status="any"),
                "open_orders": self.rest_api.get_order_count(status="open")
            }
            
            # Cache the result
            self._set_cached("counts", data)
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch counts: {e}")
            raise Exception(f"Failed to fetch counts: {str(e)}")
    
    def get_recent_orders(self, limit: int = 10) -> List[Dict]:
        """Get recent orders."""
        cache_key = f"orders_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            orders, _ = self.rest_api.get_orders(limit=limit)
            self._set_cached(cache_key, orders)
            return orders
        except Exception as e:
            logger.error(f"Failed to fetch orders: {e}")
            raise Exception(f"Failed to fetch orders: {str(e)}")
    
    def get_store_overview(self) -> Dict[str, Any]:
        """Get shop info, recent orders, and top products in one query."""
        cached = self._get_cached("store_overview")
        if cached:
            return cached
        
        try:
            data = self.graphql_api.get_store_pulse()
            self._set_cached("store_overview", data)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch store overview: {e}")
            raise Exception(f"Failed to fetch store overview: {str(e)}")
    
    def get_orders_last_week(self) -> List[Dict]:
        """Get last week's orders for deeper analysis."""
        cached = self._get_cached("orders_last_week")
        if cached:
            return cached
        
        try:
            # Get last week's orders with strict limit
            # Note: Default access is limited to last 60 days of orders
            since = (datetime.now() - timedelta(days=7)).isoformat()
            orders, _ = self.rest_api.get_orders(
                updated_at_min=since,
                limit=50
            )
            
            self._set_cached("orders_last_week", orders)
            return orders
            
        except Exception as e:
            logger.error(f"Failed to fetch orders from last week: {e}")
            raise Exception(f"Failed to fetch orders from last week: {str(e)}")
    
    def clear_cache(self, data_type: Optional[str] = None) -> None:
        """Clear cached data."""
        if not self.cache_enabled:
            return
            
        try:
            if data_type:
                key = self._cache_key(data_type)
                self.redis_client.delete(key)
                logger.info(f"Cleared cache for {data_type}")
            else:
                # Clear all cache for this shop
                pattern = f"shopify_data:{self.shop_domain}:*"
                for key in self.redis_client.scan_iter(match=pattern):
                    self.redis_client.delete(key)
                logger.info(f"Cleared all cache for {self.shop_domain}")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
