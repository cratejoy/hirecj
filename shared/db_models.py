"""Shared database models for tables accessible by multiple services."""
from sqlalchemy import Column, String, JSON, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta

Base = declarative_base()


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
