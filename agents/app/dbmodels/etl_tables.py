"""SQLAlchemy models for ETL tables with separate timestamp tracking."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ETLTimestampMixin:
    """Mixin for ETL-specific timestamps.
    
    IMPORTANT: These timestamps track when records were inserted/updated in our ETL database,
    NOT when the actual events occurred in the source systems (Shopify, Freshdesk, etc).
    
    These fields are prefixed with 'etl_' to make it absolutely clear they represent
    ETL operation times, not business event times.
    """

    etl_created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="When this record was inserted into our ETL database"
    )
    etl_updated_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="When this record was last updated in our ETL database"
    )


class ShopifyCustomer(Base, ETLTimestampMixin):
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
    merchant = relationship("Merchant")

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


class FreshdeskTicket(Base, ETLTimestampMixin):
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
    
    """
    Example data content (realistic example from production):
    {
        "freshdesk_id": "385660",                           # Internal reference
        "subject": "subscription question",                 # Ticket title
        "description": null,                                # Description often comes from conversations
        "status": 5,                                        # Status codes: 2=Open, 3=Pending, 4=Resolved, 5=Closed, 10=Waiting on 3rd Party, 12=Waiting on Customer
        "priority": 2,                                      # Priority: 1=Low, 2=Medium, 3=High, 4=Urgent
        "type": null,                                       # Type can be null, "How To's", etc.
        "tags": [                                           # Tags array - often automation rules
            "#PROCESS_CANCELLATION_PAYWHIRL"
        ],
        "created_at": "2025-06-05T13:47:56Z",              # When ticket was created in Freshdesk
        "updated_at": "2025-06-08T14:20:23Z",              # Last update time in Freshdesk
        "due_by": "2025-06-11T23:00:00Z",                 # SLA due date
        "fr_due_by": "2025-06-05T23:00:00Z",              # First response due
        "is_escalated": false,                              # Escalation status
        "requester_id": 43256742939,                       # Freshdesk contact ID
        "requester": {                                      # Contact details
            "id": 43256742939,
            "name": "Anna Brown",
            "email": "apalastro823@gmail.com",
            "phone": null,
            "mobile": null
        },
        "stats": {                                          # Comprehensive ticket statistics
            "closed_at": "2025-06-08T14:20:23Z",           # When ticket was closed
            "reopened_at": null,                            # If/when ticket was reopened
            "resolved_at": "2025-06-08T14:20:23Z",         # When ticket was resolved
            "pending_since": null,                          # When ticket entered pending state
            "status_updated_at": "2025-06-08T14:20:23Z",   # Last status change
            "agent_responded_at": "2025-06-05T13:48:16Z",  # Last agent response
            "first_responded_at": "2025-06-05T13:48:07Z",  # First agent response
            "requester_responded_at": null                  # Last customer response
        },
        "custom_fields": {                                  # Merchant-specific fields - many can be null
            "cf_ai_state": null,
            "cf_store_id": null,
            "cf_sub_category": null,
            "cf_github_issues": null,
            "cf_mintgithublink": null,
            "cf_sf_mp_breakout": null,
            "cf_store_id953865": null,
            "cf_subscription_id": null,
            "cf_disposition_code": null,
            "cf_escalated_status": null,
            "cf_primary_admin_id": null,
            "cf_t2checkedforgithub": false,
            "cf_product_segment_section": null,
            "cf_product_segment_category": null
        },
        "_raw_data": {                                      # Complete API response with additional fields
            "id": 385660,
            "spam": false,
            "source": 1,                                    # Source: 1=Email, 2=Portal, 9=Chat, etc.
            "group_id": 43000623702,                        # Support group ID
            "cc_emails": [],
            "to_emails": ["support@cratejoy.com"],
            "company_id": null,
            "fwd_emails": [],
            "product_id": null,
            "responder_id": null,                           # Agent assigned (can be null)
            "support_email": "cratejoycomsupport@cratejoy.freshdesk.com",
            "email_config_id": 43000134781,
            "reply_cc_emails": [],
            "association_type": null,
            "ticket_cc_emails": [],
            "internal_agent_id": null,
            "internal_group_id": null,
            "ticket_bcc_emails": [],
            "structured_description": null,
            "associated_tickets_count": null,
            "nr_due_by": null,                              # Next response due
            "fr_escalated": false,
            "nr_escalated": false
        }
    }
    """

    # Relationships
    merchant = relationship("Merchant")
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
        Index("idx_etl_freshdesk_tickets_etl_created_at", "etl_created_at"),
    )

    def __repr__(self):
        return f"<FreshdeskTicket(freshdesk_ticket_id='{self.freshdesk_ticket_id}', merchant_id={self.merchant_id})>"


class FreshdeskConversation(Base, ETLTimestampMixin):
    """ETL table for Freshdesk ticket conversations."""

    __tablename__ = "etl_freshdesk_conversations"

    freshdesk_ticket_id = Column(
        String(255), 
        ForeignKey("etl_freshdesk_tickets.freshdesk_ticket_id", ondelete="CASCADE"),
        primary_key=True, 
        nullable=False
    )
    data = Column(JSONB, nullable=False, default={})  # Array of conversation entries
    
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
            "created_at": "2025-06-04T14:22:45Z",          # When message was sent in Freshdesk
            "updated_at": "2025-06-04T14:22:45Z",          # Last update in Freshdesk
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


class FreshdeskRating(Base, ETLTimestampMixin):
    """ETL table for Freshdesk satisfaction ratings (one per ticket max)."""

    __tablename__ = "etl_freshdesk_ratings"

    freshdesk_ticket_id = Column(
        String(255), 
        ForeignKey("etl_freshdesk_tickets.freshdesk_ticket_id", ondelete="CASCADE"),
        primary_key=True, 
        nullable=False
    )
    data = Column(JSONB, nullable=False, default={})  # Rating data
    
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
        "created_at": "2025-06-04T16:20:30Z",             # When rating was submitted in Freshdesk
        "updated_at": "2025-06-04T16:20:30Z"              # Last update in Freshdesk
    }
    
    Note: Freshdesk 7-point rating scale:
    - 103 = Extremely Happy
    - 102 = Very Happy  
    - 101 = Happy
    - 100 = Neutral
    - -101 = Unhappy
    - -102 = Very Unhappy
    - -103 = Extremely Unhappy
    - CSAT % = (Count of 103 ratings only / Total ratings) × 100
    """

    # Relationships
    ticket = relationship("FreshdeskTicket", back_populates="rating")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_freshdesk_ratings_ticket_id", "freshdesk_ticket_id"),
        Index(
            "idx_freshdesk_ratings_rating", 
            data["ratings"]["default_question"].astext,
            postgresql_where=data["ratings"]["default_question"].astext.isnot(None)
        ),
    )

    def __repr__(self):
        return f"<FreshdeskRating(freshdesk_ticket_id='{self.freshdesk_ticket_id}')>"



# For backwards compatibility, create aliases
Customer = ShopifyCustomer
SupportTicket = FreshdeskTicket