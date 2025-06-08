"""SQLAlchemy models for the ETL database schema."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    Index,
    Text,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps.
    
    IMPORTANT: These timestamps track when records were inserted/updated in our database,
    NOT when the actual events occurred in the source systems.
    
    These fields should NOT be used by or surfaced to AI agents - they are purely
    for ETL tracking and database maintenance.
    """

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )  # When this record was inserted into our database
    updated_at = Column(
        DateTime(timezone=True), nullable=True
    )  # When this record was last updated in our database (via trigger)


class Merchant(Base, TimestampMixin):
    """Merchant model representing businesses using the support system."""

    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    is_test = Column(Boolean, default=False, nullable=False)

    # Relationships
    integrations = relationship(
        "MerchantIntegration", back_populates="merchant", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Merchant(id={self.id}, name='{self.name}', is_test={self.is_test})>"


class SyncMetadata(Base, TimestampMixin):
    """Track sync operations for incremental updates."""

    __tablename__ = "sync_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(
        Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False
    )
    resource_type = Column(
        String(50), nullable=False
    )  # e.g., 'etl_freshdesk_tickets', 'etl_shopify_customers'
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_successful_id = Column(String(255), nullable=True)
    sync_status = Column(
        String(20), nullable=True
    )  # 'success', 'failed', 'in_progress'
    error_message = Column(Text, nullable=True)

    # Relationships
    merchant = relationship("Merchant")

    # Constraints
    __table_args__ = (
        UniqueConstraint("merchant_id", "resource_type", name="uq_merchant_resource"),
    )

    def __repr__(self):
        return f"<SyncMetadata(merchant_id={self.merchant_id}, resource_type='{self.resource_type}', status='{self.sync_status}')>"


class MerchantIntegration(Base, TimestampMixin):
    """Store merchant integration configurations."""

    __tablename__ = "merchant_integrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(
        Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False
    )
    platform = Column(
        String(50), nullable=False
    )  # Integration platform (freshdesk, shopify)
    api_key = Column(Text, nullable=False)  # Encrypted in application layer
    config = Column(
        JSONB, nullable=False, default={}
    )  # Integration-specific configuration
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="integrations")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("merchant_id", "platform", name="uq_merchant_integration_platform"),
        Index("idx_merchant_integrations_merchant_id", "merchant_id"),
        Index("idx_merchant_integrations_platform", "platform"),
        Index("idx_merchant_integrations_is_active", "is_active"),
    )

    def __repr__(self):
        return f"<MerchantIntegration(merchant_id={self.merchant_id}, platform='{self.platform}', is_active={self.is_active})>"