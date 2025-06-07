"""Merchant storage service using Redis."""

import json
from datetime import datetime
from typing import Optional, Dict, Any
import redis
from app.config import settings
from shared.constants import REDIS_MERCHANT_SESSION_TTL
import logging

logger = logging.getLogger(__name__)


class MerchantStorage:
    """Handles persistent storage of merchant data using Redis."""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("[MERCHANT_STORAGE] Connected to Redis successfully")
        except Exception as e:
            logger.error(f"[MERCHANT_STORAGE] Failed to connect to Redis: {e}")
            # Fail fast - Redis is required, no fallbacks
            raise RuntimeError(f"Redis is required for merchant storage. Failed to connect: {e}")
    
    def create_merchant(self, merchant_data: Dict[str, Any]) -> None:
        """Create a new merchant record."""
        shop_domain = merchant_data["shop_domain"]
        key = f"merchant:{shop_domain}"
        
        # Convert datetime to ISO format for JSON serialization
        if "created_at" in merchant_data and hasattr(merchant_data["created_at"], "isoformat"):
            merchant_data["created_at"] = merchant_data["created_at"].isoformat()
        
        try:
            self.redis_client.set(
                key,
                json.dumps(merchant_data),
                ex=REDIS_MERCHANT_SESSION_TTL  # 24 hours
            )
            # Also maintain a set of all merchants
            self.redis_client.sadd("merchants", shop_domain)
            logger.info(f"[MERCHANT_STORAGE] Created merchant: {shop_domain}")
        except Exception as e:
            logger.error(f"[MERCHANT_STORAGE] Failed to create merchant in Redis: {e}")
            raise RuntimeError(f"Failed to store merchant data: {e}")
    
    def get_merchant(self, shop_domain: str) -> Optional[Dict[str, Any]]:
        """Get merchant data by shop domain."""
        key = f"merchant:{shop_domain}"
        
        try:
            data = self.redis_client.get(key)
            if data:
                merchant = json.loads(data)
                # Keep datetime as ISO string for consistency
                logger.debug(f"[MERCHANT_STORAGE] Retrieved merchant: {shop_domain}")
                return merchant
            return None
        except Exception as e:
            logger.error(f"[MERCHANT_STORAGE] Failed to get merchant from Redis: {e}")
            raise RuntimeError(f"Failed to retrieve merchant data: {e}")
    
    def update_token(self, shop_domain: str, access_token: str) -> None:
        """Update merchant's access token."""
        merchant = self.get_merchant(shop_domain)
        if merchant:
            merchant["access_token"] = access_token
            merchant["last_seen"] = datetime.utcnow().isoformat()
            
            key = f"merchant:{shop_domain}"
            
            try:
                self.redis_client.set(
                    key,
                    json.dumps(merchant),
                    ex=REDIS_MERCHANT_SESSION_TTL
                )
                logger.info(f"[MERCHANT_STORAGE] Updated token for merchant: {shop_domain}")
            except Exception as e:
                logger.error(f"[MERCHANT_STORAGE] Failed to update token in Redis: {e}")
                raise RuntimeError(f"Failed to update merchant token: {e}")


# Singleton instance
merchant_storage = MerchantStorage()