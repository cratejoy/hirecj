"""Shared database models for tables accessible by multiple services."""
from sqlalchemy import Column, String, JSON, DateTime, Boolean, Integer, Text, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
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


class WebSession(Base):
    """Web session for HTTP cookie-based authentication."""
    __tablename__ = 'web_sessions'
    
    session_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    data = Column(JSON, default=dict)
    
    def is_valid(self) -> bool:
        """Check if session is still valid (not expired)."""
        return datetime.utcnow() < self.expires_at
    
    def __repr__(self):
        return f"<WebSession(session_id='{self.session_id}', user_id='{self.user_id}', expires_at='{self.expires_at}')>"



class Merchant(Base):
    """Merchant accounts in the system."""
    __tablename__ = "merchants"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    is_test = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Merchant(id={self.id}, name='{self.name}')>"


class MerchantIntegration(Base):
    """Platform integrations for merchants (Shopify, Freshdesk, etc)."""
    __tablename__ = "merchant_integrations"
    
    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    platform = Column(String(50), nullable=False)  # 'shopify', 'freshdesk', etc
    api_key = Column(Text, nullable=False)  # Access token or API key
    config = Column(JSONB, default={})  # Platform-specific config
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('merchant_id', 'platform', name='unique_merchant_platform'),
    )
    
    def __repr__(self):
        return f"<MerchantIntegration(merchant_id={self.merchant_id}, platform='{self.platform}')>"


class User(Base):
    """User accounts linked to Shopify shops."""
    __tablename__ = 'users'
    
    id = Column(String(50), primary_key=True)
    shop_domain = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<User(id='{self.id}', shop_domain='{self.shop_domain}')>"


class MerchantToken(Base):
    """Links users to merchants with their OAuth tokens."""
    __tablename__ = 'merchant_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), ForeignKey('users.id'), nullable=False)
    merchant_id = Column(Integer, ForeignKey('merchants.id'), nullable=False)
    shop_domain = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=False)
    scopes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'merchant_id', name='unique_user_merchant'),
    )
    
    def __repr__(self):
        return f"<MerchantToken(user_id='{self.user_id}', merchant_id={self.merchant_id}, shop_domain='{self.shop_domain}')>"
