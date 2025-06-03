"""
Cache configuration for LiteLLM
"""

import os
from urllib.parse import urlparse
from typing import Optional

import litellm
from litellm import Cache

from app.config import settings


def setup_litellm_cache() -> Optional[Cache]:
    """
    Setup LiteLLM cache with Redis if available, otherwise use in-memory cache
    """
    # Check if caching is enabled globally
    if not settings.enable_litellm_cache:
        print("⚠️  LiteLLM cache DISABLED by configuration")
        litellm.cache = None
        return None

    redis_url = os.getenv("REDIS_URL")

    if redis_url:
        try:
            # Parse Redis URL
            url = urlparse(redis_url)

            # Determine if we need SSL (Heroku uses rediss://)
            use_ssl = redis_url.startswith("rediss://")

            # Create Redis cache
            cache = Cache(
                type="redis",
                host=url.hostname,
                port=url.port or settings.redis_port,
                password=url.password,
                ssl=use_ssl,
                ttl=settings.cache_ttl,  # Use configured TTL
                namespace="hirecj",  # Namespace for all cache keys
            )

            # Set the cache globally
            litellm.cache = cache

            print(f"✅ LiteLLM Redis cache initialized (host: {url.hostname})")
            return cache

        except Exception as e:
            print(f"⚠️  Failed to initialize Redis cache: {e}")
            print("Falling back to in-memory cache...")

    # Fallback to in-memory cache
    cache = Cache(
        type="local",
        default_in_memory_ttl=settings.cache_ttl_short,  # Use shorter TTL for local dev
    )

    # Set the cache globally
    litellm.cache = cache

    print("✅ LiteLLM in-memory cache initialized")
    return cache


def get_cache_info() -> dict:
    """Get information about the current cache configuration"""
    if not litellm.cache:
        return {"type": "none", "enabled": False}

    cache_type = getattr(litellm.cache, "type", "unknown")

    info = {
        "type": cache_type,
        "enabled": True,
    }

    if cache_type == "redis":
        info.update(
            {
                "host": getattr(litellm.cache.cache, "host", "unknown"),
                "port": getattr(litellm.cache.cache, "port", "unknown"),
                "ttl": getattr(litellm.cache, "ttl", "unknown"),
                "namespace": getattr(litellm.cache, "namespace", "unknown"),
            }
        )
    elif cache_type == "local":
        info.update(
            {
                "ttl": getattr(litellm.cache, "default_ttl", "unknown"),
                "max_size": getattr(
                    litellm.cache.cache, "max_size_in_memory", "unknown"
                ),
            }
        )

    return info
