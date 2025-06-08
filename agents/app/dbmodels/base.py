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
    """ETL table for core Freshdesk ticket data (excluding conversations and ratings)."""

    __tablename__ = "etl_freshdesk_tickets"

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    freshdesk_ticket_id = Column(String(255), primary_key=True, nullable=False)
    data = Column(JSONB, nullable=False, default={})  # Core ticket data only
    
    # Parsed fields for quick access
    # These timestamps represent when the ticket was actually created/updated in Freshdesk
    # Use these fields instead of created_at/updated_at for business logic and AI agents
    parsed_created_at = Column(DateTime(timezone=True), nullable=True)  # Actual ticket creation time in Freshdesk
    parsed_updated_at = Column(DateTime(timezone=True), nullable=True)  # Actual last update time in Freshdesk
    parsed_email = Column(String(255), nullable=True)  # Customer email extracted from ticket data
    parsed_status = Column(Integer, nullable=True)  # Status code: 2=Open, 3=Pending, 4=Resolved, 5=Closed
    """
    Example data content:
    {
        "freshdesk_id": "385450",                           # Internal reference
        "subject": "New Vendor",                            # Ticket title
        "description": "Hi, I'm interested in...",          # Initial message (text)
        "status": 5,                                        # Status codes: 2=Open, 3=Pending, 4=Resolved, 5=Closed
        "priority": 1,                                      # Priority: 1=Low, 2=Medium, 3=High, 4=Urgent
        "type": "Question",                                 # Ticket type (Question, Problem, etc.)
        "tags": ["vendor", "new"],                          # Tags array
        "created_at": "2025-06-04T14:22:45Z",              # When ticket was created
        "updated_at": "2025-06-04T16:20:30Z",              # Last update time
        "due_by": "2025-06-09T14:22:45Z",                 # SLA due date
        "fr_due_by": "2025-06-05T14:22:45Z",              # First response due
        "is_escalated": false,                              # Escalation status
        "custom_fields": {                                  # Merchant-specific fields
            "cf_shopify_customer_id": "12345678901"        # Shopify customer reference
        },
        "requester_id": 43028420064,                       # Freshdesk contact ID
        "requester": {                                      # Contact details
            "id": 43028420064,
            "email": "customer@example.com",
            "name": "John Doe",
            "phone": "+1234567890"
        },
        "_raw_data": {...}                                  # Complete API response
    }
    """

    # Relationships
    merchant = relationship("Merchant", back_populates="freshdesk_tickets")
    conversations = relationship(
        "FreshdeskConversation", 
        back_populates="ticket",
        cascade="all, delete-orphan",
        uselist=False  # One-to-one relationship
    )
    rating = relationship(
        "FreshdeskRating", 
        back_populates="ticket",
        cascade="all, delete-orphan",
        uselist=False  # One-to-one relationship
    )

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
        Index("idx_etl_freshdesk_tickets_parsed_status", "parsed_status"),
    )

    def __repr__(self):
        return f"<FreshdeskTicket(freshdesk_ticket_id='{self.freshdesk_ticket_id}', merchant_id={self.merchant_id})>"


class FreshdeskConversation(Base, TimestampMixin):
    """ETL table for Freshdesk ticket conversations."""

    __tablename__ = "etl_freshdesk_conversations"

    freshdesk_ticket_id = Column(
        String(255), 
        ForeignKey("etl_freshdesk_tickets.freshdesk_ticket_id", ondelete="CASCADE"),
        primary_key=True, 
        nullable=False
    )
    data = Column(JSONB, nullable=False, default={})  # Array of conversation entries
    
    # Parsed fields for quick access
    # These timestamps represent actual conversation times from Freshdesk
    # Use these fields instead of created_at/updated_at for business logic and AI agents
    parsed_created_at = Column(DateTime(timezone=True), nullable=True)  # First message creation time in conversation
    parsed_updated_at = Column(DateTime(timezone=True), nullable=True)  # Last message creation time in conversation
    """
    Example data content (array of conversation entries):
    [
        {
            "id": 43254879837,                              # Conversation ID
            "user_id": 43028420064,                         # Who sent this message
            "body": "<div>Hi, I need help with...</div>",   # HTML message content
            "body_text": "Hi, I need help with...",         # Plain text version
            "incoming": true,                                # true=customer, false=agent
            "private": false,                                # Internal note flag
            "created_at": "2025-06-04T14:22:45Z",          # When message was sent
            "updated_at": "2025-06-04T14:22:45Z",          # Last update
            "support_email": "support@company.com",          # Email used
            "to_emails": ["customer@example.com"],           # Recipients
            "from_email": "customer@example.com",            # Sender
            "cc_emails": [],                                 # CC recipients
            "bcc_emails": []                                 # BCC recipients
        },
        {
            "id": 43254900123,
            "user_id": 43251782297,                         # Agent's user ID
            "body": "<div>Thank you for reaching out...</div>",
            "body_text": "Thank you for reaching out...",
            "incoming": false,                               # Agent response
            "private": false,
            "created_at": "2025-06-04T14:35:12Z",
            "updated_at": "2025-06-04T14:35:12Z",
            "support_email": "support@company.com",
            "to_emails": ["customer@example.com"],
            "from_email": "agent@company.com",
            "cc_emails": [],
            "bcc_emails": []
        }
    ]
    """

    # Relationships
    ticket = relationship("FreshdeskTicket", back_populates="conversations")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_freshdesk_conversations_ticket_id", "freshdesk_ticket_id"),
    )

    def __repr__(self):
        return f"<FreshdeskConversation(freshdesk_ticket_id='{self.freshdesk_ticket_id}')>"


class FreshdeskRating(Base, TimestampMixin):
    """ETL table for Freshdesk satisfaction ratings (one per ticket max)."""

    __tablename__ = "etl_freshdesk_ratings"

    freshdesk_ticket_id = Column(
        String(255), 
        ForeignKey("etl_freshdesk_tickets.freshdesk_ticket_id", ondelete="CASCADE"),
        primary_key=True, 
        nullable=False
    )
    data = Column(JSONB, nullable=False, default={})  # Rating data
    
    # Parsed fields for quick access
    # This field contains the normalized rating value for easy querying
    # Use this field instead of digging into the JSONB data for AI agents and business logic
    parsed_rating = Column(Integer, nullable=True)  # Raw Freshdesk rating value (103 to -103)
    """
    Example data content:
    {
        "id": 43006810853,                                  # Rating ID
        "ratings": {
            "default_question": 103                         # Rating value: 103=Extremely Happy to -103=Extremely Unhappy
        },
        "user_id": 43028420064,                            # Customer who rated
        "agent_id": 43028290928,                           # Agent who handled ticket
        "feedback": "Great support, very helpful!",         # Optional text feedback
        "group_id": 43000596433,                           # Support group ID
        "survey_id": 43000089898,                          # Survey template ID
        "ticket_id": 385450,                               # Associated ticket ID
        "created_at": "2025-06-04T16:20:30Z",             # When rating was submitted
        "updated_at": "2025-06-04T16:20:30Z"              # Last update
    }
    
    Note: Freshdesk 7-point rating scale:
    - 103 = Extremely Happy
    - 102 = Very Happy  
    - 101 = Happy
    - 100 = Neutral
    - -101 = Unhappy
    - -102 = Very Unhappy
    - -103 = Extremely Unhappy
    - CSAT % = (Count of 103 ratings only / Total ratings) x 100
    """

    # Relationships
    ticket = relationship("FreshdeskTicket", back_populates="rating")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_freshdesk_ratings_ticket_id", "freshdesk_ticket_id"),
        Index(
            "idx_freshdesk_ratings_rating", 
            data["rating"].astext,
            postgresql_where=data["rating"].astext.isnot(None)
        ),
    )

    def __repr__(self):
        return f"<FreshdeskRating(freshdesk_ticket_id='{self.freshdesk_ticket_id}')>"


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


# For backwards compatibility, create aliases
Customer = ShopifyCustomer
SupportTicket = FreshdeskTicket
