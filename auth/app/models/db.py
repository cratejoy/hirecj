"""Database models for auth service - subset needed for merchant storage."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Merchant(Base):
    __tablename__ = "merchants"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    is_test = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MerchantIntegration(Base):
    __tablename__ = "merchant_integrations"
    
    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    platform = Column(String(50), nullable=False)  # 'shopify', 'klaviyo', etc
    api_key = Column(Text, nullable=False)  # This stores the access token
    config = Column(JSONB, default={})  # Additional config like shop_domain, scopes
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('merchant_id', 'platform', name='unique_merchant_platform'),
    )