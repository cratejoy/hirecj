"""SQLAlchemy models for database views.

This module contains read-only models that map to database views,
providing convenient access to pre-aggregated and joined data.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base


class FreshdeskUnifiedTicketView(Base):
    """Read-only view combining ticket, conversation, and rating data.
    
    This view provides a single source of truth for all ticket-related queries,
    eliminating the need for complex joins and JSONB extractions in application code.
    
    Example usage:
        # Get all open tickets with ratings
        tickets = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.status == 2,
            FreshdeskUnifiedTicketView.has_rating == True
        ).all()
        
        # Find high-priority tickets without responses
        urgent = session.query(FreshdeskUnifiedTicketView).filter(
            FreshdeskUnifiedTicketView.priority == 4,
            FreshdeskUnifiedTicketView.first_responded_at.is_(None)
        ).all()
    """
    
    __tablename__ = "v_freshdesk_unified_tickets"
    __table_args__ = {'info': {'is_view': True}}
    
    # Core identifiers (composite primary key for the view)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), primary_key=True)  # ID of the merchant/store this ticket belongs to
    freshdesk_ticket_id = Column(String(255), primary_key=True)  # Unique string ID from Freshdesk (e.g., "385660")
    ticket_id_numeric = Column(Integer)  # Numeric version of freshdesk_ticket_id extracted via regex
    
    # Basic ticket info
    subject = Column(String)  # Subject line/title of the support ticket
    description = Column(String)  # Initial description text from ticket creation (often null as content comes from conversations)
    type = Column(String)  # Ticket type category (e.g., "How To's", "Question", "Problem", etc.) - can be null
    source = Column(Integer)  # Channel source: 1=Email, 2=Portal, 3=Phone, 4=Chat, 5=Mobihelp, 6=Feedback Widget, 7=Outbound Email, 8=Ecommerce, 9=Bot, 10=Twitter, 11=Facebook, 12=WhatsApp, 13=Custom Channel
    spam = Column(Boolean)  # Whether Freshdesk flagged this ticket as spam
    
    # Status & Priority
    status = Column(Integer)  # Ticket status: 2=Open, 3=Pending, 4=Resolved, 5=Closed, 6=Waiting on Customer, 7=Waiting on Third Party
    priority = Column(Integer)  # Ticket priority: 1=Low, 2=Medium, 3=High, 4=Urgent
    is_escalated = Column(Boolean)  # Whether ticket has been escalated beyond normal support flow
    fr_escalated = Column(Boolean)  # Whether first response SLA was breached (fr = first response)
    nr_escalated = Column(Boolean)  # Whether next response SLA was breached (nr = next response)
    
    # People
    requester_id = Column(Integer)  # Freshdesk contact ID of the customer who created the ticket
    requester_name = Column(String)  # Name of the customer from Freshdesk contact record
    requester_email = Column(String)  # Email address of the customer
    responder_id = Column(Integer)  # Freshdesk agent ID assigned to handle this ticket (can be null if unassigned)
    company_id = Column(Integer)  # Freshdesk company ID if requester is associated with a company (often null)
    group_id = Column(Integer)  # Support group/team ID this ticket is assigned to
    
    # Timestamps
    created_at = Column(DateTime(timezone=True))  # When the ticket was created in Freshdesk
    updated_at = Column(DateTime(timezone=True))  # Last time any field on the ticket was modified in Freshdesk
    due_by = Column(DateTime(timezone=True))  # Overall SLA due date for ticket resolution
    fr_due_by = Column(DateTime(timezone=True))  # First response SLA deadline
    nr_due_by = Column(DateTime(timezone=True))  # Next response SLA deadline (updates as conversation progresses)
    
    # Stats
    first_responded_at = Column(DateTime(timezone=True))  # Timestamp of first agent response to the ticket
    agent_responded_at = Column(DateTime(timezone=True))  # Timestamp of most recent agent response
    requester_responded_at = Column(DateTime(timezone=True))  # Timestamp of most recent customer response
    closed_at = Column(DateTime(timezone=True))  # When ticket was closed (status changed to 5)
    resolved_at = Column(DateTime(timezone=True))  # When ticket was resolved (status changed to 4)
    reopened_at = Column(DateTime(timezone=True))  # When ticket was reopened after being closed/resolved (if applicable)
    pending_since = Column(DateTime(timezone=True))  # When ticket entered pending status (waiting for customer/3rd party)
    status_updated_at = Column(DateTime(timezone=True))  # Last time the status field was changed
    
    # Tags & Custom Fields
    tags = Column(JSONB)  # Array of string tags applied to ticket (e.g., ["#PROCESS_CANCELLATION_PAYWHIRL"])
    custom_fields = Column(JSONB)  # Merchant-specific custom fields as key-value pairs. Common fields in our dataset:
                                   # - cf_store_id: Shopify store ID associated with the ticket
                                   # - cf_store_id953865: Alternative store ID field (likely merchant-specific variant)
                                   # - cf_subscription_id: Subscription/recurring order ID if ticket relates to subscription
                                   # - cf_primary_admin_id: ID of the primary admin user for the merchant
                                   # - cf_ai_state: AI processing state/status for the ticket
                                   # - cf_disposition_code: Resolution/outcome code for categorizing how ticket was resolved
                                   # - cf_escalated_status: Additional escalation tracking beyond standard is_escalated
                                   # - cf_sub_category: Sub-category for more granular ticket classification
                                   # - cf_product_segment_category: Product area category (e.g., "Billing", "Technical", etc.)
                                   # - cf_product_segment_section: More specific product section within category
                                   # - cf_github_issues: GitHub issue numbers linked to this ticket
                                   # - cf_mintgithublink: URL to GitHub issue (legacy field name)
                                   # - cf_sf_mp_breakout: Salesforce marketplace breakout tracking
                                   # - cf_t2checkedforgithub: Boolean flag if T2 support checked for related GitHub issues
    
    # Conversation Summary
    conversation_count = Column(Integer)  # Total number of conversation entries (messages) on this ticket
    last_conversation_at = Column(DateTime(timezone=True))  # Timestamp of the most recent conversation entry
    has_agent_response = Column(Boolean)  # Whether any agent has responded to this ticket (true if any non-incoming conversation exists)
    
    # Rating Info
    has_rating = Column(Boolean)  # Whether customer provided a satisfaction rating for this ticket
    rating_score = Column(Integer)  # Customer satisfaction score: 103=Extremely Happy, 102=Very Happy, 101=Happy, 100=Neutral, -101=Unhappy, -102=Very Unhappy, -103=Extremely Unhappy
    rating_feedback = Column(String)  # Optional text feedback provided with the rating
    rating_created_at = Column(DateTime(timezone=True))  # When the customer submitted their satisfaction rating
    
    # Conversation History
    conversation_history = Column(JSONB)  # Full conversation history as JSONB array from etl_freshdesk_conversations.data
    
    # Relationships
    merchant = relationship("Merchant")
    
    @property
    def conversation(self):
        """Get formatted conversation history as markdown using the embedded conversation_history field.
        
        This property uses the conversation_history JSONB field that's included in the view,
        so no additional database query is needed.
        
        Returns:
            Formatted markdown string or None if no conversations exist
        """
        if not self.conversation_history:
            return None
        
        return self.format_conversation(self.conversation_history)
    
    def format_conversation(self, conversation_data):
        """Format conversation data as markdown.
        
        This is a pure formatting function that doesn't access the database.
        
        Args:
            conversation_data: The conversation data array from FreshdeskConversation
            
        Returns:
            Formatted markdown string or None if no conversation data
        """
        if not conversation_data:
            return None
        
        # Format conversations as markdown
        lines = [f"## Ticket #{self.freshdesk_ticket_id}: {self.subject or 'No subject'}\n"]
        
        for i, msg in enumerate(conversation_data, 1):
            # Determine sender type
            if msg.get('incoming', True):
                sender = f"**Customer** ({msg.get('from_email', 'Unknown')})"
                prefix = ">"
            else:
                sender = f"**Agent** ({msg.get('from_email', 'Unknown')})"
                prefix = ">>"
            
            # Format timestamp
            timestamp = msg.get('created_at', 'Unknown time')
            
            # Get message body (prefer plain text)
            body = msg.get('body_text', msg.get('body', 'No content'))
            
            # Build message block
            lines.append(f"### Message {i} - {timestamp}")
            lines.append(f"{sender}")
            lines.append("")
            
            # Add quoted body
            for line in body.split('\n'):
                lines.append(f"{prefix} {line}")
            lines.append("")
        
        # Add rating if present
        if self.has_rating and self.rating_score is not None:
            lines.append("---")
            lines.append(f"**Customer Rating**: {self._format_rating(self.rating_score)}")
            if self.rating_feedback:
                lines.append(f"**Feedback**: {self.rating_feedback}")
        
        return '\n'.join(lines)
    
    def _format_rating(self, score):
        """Convert Freshdesk rating score to human-readable format."""
        ratings = {
            103: "😊 Extremely Happy",
            102: "😊 Very Happy", 
            101: "🙂 Happy",
            100: "😐 Neutral",
            -101: "😞 Unhappy",
            -102: "😞 Very Unhappy",
            -103: "😞 Extremely Unhappy"
        }
        return ratings.get(score, f"Unknown ({score})")
    
    def __repr__(self):
        return f"<FreshdeskUnifiedTicketView(ticket_id='{self.freshdesk_ticket_id}', subject='{self.subject}')>"