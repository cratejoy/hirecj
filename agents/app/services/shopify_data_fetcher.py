"""Pure data fetching service for Shopify - no analysis or insights."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import redis
import json
import logging

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
        
        # Redis for caching expensive operations
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.cache_enabled = True
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
            self.redis_client = None
            self.cache_enabled = False
            
        self.cache_ttl = REDIS_TTL_MEDIUM  # 15 minutes default
    
    def _cache_key(self, data_type: str) -> str:
        """Generate cache key for data type."""
        return f"shopify_data:{self.shop_domain}:{data_type}"
    
    def _get_cached(self, data_type: str) -> Optional[Dict]:
        """Get cached data if available."""
        if not self.cache_enabled:
            return None
            
        try:
            key = self._cache_key(data_type)
            data = self.redis_client.get(key)
            if data:
                logger.debug(f"Cache hit for {data_type}")
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    def _set_cached(self, data_type: str, data: Dict) -> None:
        """Cache data with TTL."""
        if not self.cache_enabled:
            return
            
        try:
            key = self._cache_key(data_type)
            self.redis_client.setex(key, self.cache_ttl, json.dumps(data))
            logger.debug(f"Cached {data_type} for {self.cache_ttl}s")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def get_counts(self) -> Dict[str, int]:
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
    
    async def get_recent_orders(self, limit: int = 10) -> List[Dict]:
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
    
    async def get_store_overview(self) -> Dict[str, Any]:
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
    
    async def get_week_orders(self) -> List[Dict]:
        """Get last week's orders for deeper analysis."""
        cached = self._get_cached("week_orders")
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
            
            self._set_cached("week_orders", orders)
            return orders
            
        except Exception as e:
            logger.error(f"Failed to fetch week orders: {e}")
            raise Exception(f"Failed to fetch week orders: {str(e)}")
    
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