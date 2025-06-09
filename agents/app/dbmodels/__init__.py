"""Database models for the ETL system."""

# Import from base models (non-ETL tables)
from .base import (
    Base,
    TimestampMixin,
    Merchant,
    SyncMetadata,
    MerchantIntegration,
)

# Import from ETL tables
from .etl_tables import (
    ETLTimestampMixin,
    ShopifyCustomer,
    FreshdeskTicket,
    FreshdeskConversation,
    FreshdeskRating,
    # Aliases for backwards compatibility
    Customer,
    SupportTicket,
)

__all__ = [
    # Base models
    'Base',
    'TimestampMixin',
    'Merchant',
    'SyncMetadata',
    'MerchantIntegration',
    # ETL models
    'ETLTimestampMixin',
    'ShopifyCustomer',
    'FreshdeskTicket',
    'FreshdeskConversation',
    'FreshdeskRating',
    # Aliases
    'Customer',
    'SupportTicket',
]