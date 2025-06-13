"""Shared constants for HireCJ monorepo."""

# Shopify Custom App Installation
SHOPIFY_INSTALL_POLL_INTERVAL_MS = 2000  # 2 seconds
SHOPIFY_INSTALL_TIMEOUT_MS = 600000      # 10 minutes
SHOPIFY_SESSION_EXPIRE_MINUTES = 30      # 30 minutes

# Redis TTLs
REDIS_INSTALL_SESSION_TTL = 1800   # 30 minutes in seconds
REDIS_MERCHANT_SESSION_TTL = 86400 # 24 hours in seconds
REDIS_TTL_SHORT = 300              # 5 minutes in seconds
REDIS_TTL_MEDIUM = 900             # 15 minutes in seconds
REDIS_TTL_LONG = 3600              # 1 hour in seconds