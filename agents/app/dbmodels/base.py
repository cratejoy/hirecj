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
    """Mixin for created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=True
    )  # onupdate is set via trigger


class Merchant(Base, TimestampMixin):
    """Merchant model representing businesses using the support system."""

    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    is_test = Column(Boolean, default=False, nullable=False)

    # Relationships
    shopify_customers = relationship(
        "ShopifyCustomer", back_populates="merchant", cascade="all, delete-orphan"
    )
    freshdesk_tickets = relationship(
        "FreshdeskTicket", back_populates="merchant", cascade="all, delete-orphan"
    )
    integrations = relationship(
        "MerchantIntegration", back_populates="merchant", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Merchant(id={self.id}, name='{self.name}', is_test={self.is_test})>"


class ShopifyCustomer(Base, TimestampMixin):
    """ETL table for Shopify customer records with flexible JSONB storage."""

    __tablename__ = "etl_shopify_customers"

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    shopify_customer_id = Column(String(255), primary_key=True, nullable=False)
    data = Column(JSONB, nullable=False, default={})  # Flexible data storage

    # Relationships
    merchant = relationship("Merchant", back_populates="shopify_customers")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "shopify_customer_id",
            name="etl_shopify_customers_merchant_id_shopify_customer_id_key",
        ),
        Index("idx_etl_shopify_customers_merchant_id", "merchant_id"),
        Index("idx_etl_shopify_customers_shopify_customer_id", "shopify_customer_id"),
        Index("idx_etl_shopify_customers_data_gin", "data", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<ShopifyCustomer(shopify_customer_id='{self.shopify_customer_id}', merchant_id={self.merchant_id})>"


class FreshdeskTicket(Base, TimestampMixin):
    """ETL table for Freshdesk ticket records with flexible JSONB storage."""

    __tablename__ = "etl_freshdesk_tickets"

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    freshdesk_ticket_id = Column(String(255), primary_key=True, nullable=False)
    data = Column(JSONB, nullable=False, default={})  # Flexible ticket data storage

    # Relationships
    merchant = relationship("Merchant", back_populates="freshdesk_tickets")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "freshdesk_ticket_id",
            name="etl_freshdesk_tickets_merchant_id_freshdesk_ticket_id_key",
        ),
        Index("idx_etl_freshdesk_tickets_merchant_id", "merchant_id"),
        Index("idx_etl_freshdesk_tickets_freshdesk_ticket_id", "freshdesk_ticket_id"),
        Index("idx_etl_freshdesk_tickets_data_gin", "data", postgresql_using="gin"),
        Index("idx_etl_freshdesk_tickets_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<FreshdeskTicket(freshdesk_ticket_id='{self.freshdesk_ticket_id}', merchant_id={self.merchant_id})>"


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
    type = Column(
        String(50), nullable=False
    )  # Integration type (freshdesk, shopify) - now a string
    api_key = Column(Text, nullable=False)  # Encrypted in application layer
    config = Column(
        JSONB, nullable=False, default={}
    )  # Integration-specific configuration
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="integrations")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("merchant_id", "type", name="uq_merchant_integration_type"),
        Index("idx_merchant_integrations_merchant_id", "merchant_id"),
        Index("idx_merchant_integrations_type", "type"),
        Index("idx_merchant_integrations_is_active", "is_active"),
    )

    def __repr__(self):
        return f"<MerchantIntegration(merchant_id={self.merchant_id}, type='{self.type}', is_active={self.is_active})>"


class DailyTicketSummary(Base, TimestampMixin):
    """Daily aggregated ticket summaries for each merchant."""

    __tablename__ = "daily_ticket_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(
        DateTime(timezone=True), nullable=False
    )  # The date this summary covers
    merchant_id = Column(
        Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False
    )
    message = Column(Text, nullable=False)  # The generated summary message

    # Relationships
    merchant = relationship("Merchant", backref="daily_summaries")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("merchant_id", "date", name="uq_merchant_daily_summary"),
        Index("idx_daily_ticket_summaries_merchant_id", "merchant_id"),
        Index("idx_daily_ticket_summaries_date", "date"),
        Index("idx_daily_ticket_summaries_merchant_date", "merchant_id", "date"),
    )

    def __repr__(self):
        return (
            f"<DailyTicketSummary(merchant_id={self.merchant_id}, date='{self.date}')>"
        )


# For backwards compatibility, create aliases
Customer = ShopifyCustomer
SupportTicket = FreshdeskTicket
