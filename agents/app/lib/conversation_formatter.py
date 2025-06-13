"""Utility functions for formatting conversation data.

This module provides session-aware functions for retrieving and formatting
conversation history, avoiding the anti-pattern of accessing sessions in model files.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.dbmodels.view_models import FreshdeskUnifiedTicketView
from app.dbmodels.etl_tables import FreshdeskConversation
from app.config import logger


def get_formatted_conversation(session: Session, ticket: FreshdeskUnifiedTicketView) -> Optional[str]:
    """Get formatted conversation history for a ticket.
    
    This function now uses the embedded conversation_history field when available,
    falling back to a separate query only if needed.
    
    Args:
        session: SQLAlchemy session for database queries
        ticket: The unified ticket view object
        
    Returns:
        Formatted markdown string of the conversation or None if no conversations
    """
    # First check if conversation_history is already loaded in the view
    if ticket.conversation_history is not None:
        # Use the embedded data - no query needed!
        return ticket.format_conversation(ticket.conversation_history)
    
    # Fallback: Query conversations for this ticket (for older code or if view not updated)
    conv_record = session.query(FreshdeskConversation).filter(
        FreshdeskConversation.freshdesk_ticket_id == ticket.freshdesk_ticket_id
    ).first()
    
    if not conv_record or not conv_record.data:
        return None
    
    # Use the model's formatting method
    return ticket.format_conversation(conv_record.data)


def get_conversation_for_ticket_id(session: Session, merchant_id: int, ticket_id: str) -> Optional[str]:
    """Get formatted conversation by ticket ID.
    
    Convenience function that loads both ticket and conversation data.
    
    Args:
        session: SQLAlchemy session
        merchant_id: Merchant ID
        ticket_id: Freshdesk ticket ID
        
    Returns:
        Formatted conversation markdown or None if not found
    """
    # Get the ticket
    ticket = session.query(FreshdeskUnifiedTicketView).filter(
        FreshdeskUnifiedTicketView.merchant_id == merchant_id,
        FreshdeskUnifiedTicketView.freshdesk_ticket_id == ticket_id
    ).first()
    
    if not ticket:
        return None
    
    return get_formatted_conversation(session, ticket)


def get_conversations_for_bad_ratings(session: Session, merchant_id: int, limit: int = 5) -> dict:
    """Get conversations for recent tickets with bad ratings.
    
    This is useful for the CSAT detail log tool to review what went wrong.
    
    Args:
        session: SQLAlchemy session
        merchant_id: Merchant ID
        limit: Maximum number of tickets to return
        
    Returns:
        Dict mapping ticket IDs to formatted conversations
    """
    # Get recent tickets with bad ratings
    bad_tickets = session.query(FreshdeskUnifiedTicketView).filter(
        FreshdeskUnifiedTicketView.merchant_id == merchant_id,
        FreshdeskUnifiedTicketView.has_rating == True,
        FreshdeskUnifiedTicketView.rating_score < 102  # Below "Very Happy"
    ).order_by(
        FreshdeskUnifiedTicketView.rating_created_at.desc()
    ).limit(limit).all()
    
    results = {}
    for ticket in bad_tickets:
        results[ticket.freshdesk_ticket_id] = get_formatted_conversation(session, ticket)
    
    return results