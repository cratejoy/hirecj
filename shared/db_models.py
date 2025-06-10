"""Shared database models for tables accessible by multiple services."""
from sqlalchemy import Column, String, JSON, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta

Base = declarative_base()

class OAuthCompletionState(Base):
    """
    Stores temporary state for OAuth completion to be picked up by another service.
    This is a short-lived record to pass information from the auth callback
    to the agent WebSocket handler.
    """
    __tablename__ = 'oauth_completion_state'

    conversation_id = Column(String, primary_key=True)
    data = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Expire after 10 minutes to prevent orphaned records
    expires_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow() + timedelta(minutes=10))

    def __repr__(self):
        return f"<OAuthCompletionState(conversation_id='{self.conversation_id}', processed={self.processed})>"


class OAuthCSRFState(Base):
    """Stores temporary state for Shopify OAuth CSRF protection."""
    __tablename__ = 'oauth_csrf_state'

    state = Column(String, primary_key=True)
    shop = Column(String, nullable=False)
    conversation_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow() + timedelta(minutes=10))

    def __repr__(self):
        return f"<OAuthCSRFState(state='{self.state}', shop='{self.shop}')>"
