"""Database models with multi-tenancy support."""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Index, 
    UniqueConstraint, Boolean, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


def generate_uuid():
    """Generate a new UUID."""
    return str(uuid.uuid4())


class Account(Base):
    """Account model for multi-tenancy."""
    __tablename__ = "accounts"
    __table_args__ = {"schema": "hirecj"}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    settings = Column(JSONB, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    users = relationship("User", back_populates="account", cascade="all, delete-orphan")
    connections = relationship("Connection", back_populates="account", cascade="all, delete-orphan")
    credentials = relationship("Credential", back_populates="account", cascade="all, delete-orphan")


class User(Base):
    """User model with account association."""
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint('account_id', 'email', name='uq_account_email'),
        {"schema": "hirecj"}
    )
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("hirecj.accounts.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    role = Column(String(50), default="member")  # admin, member, viewer
    settings = Column(JSONB, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    account = relationship("Account", back_populates="users")


class Connection(Base):
    """Service connection with multi-tenant support."""
    __tablename__ = "connections"
    __table_args__ = (
        Index('idx_account_provider', 'account_id', 'provider'),
        {"schema": "hirecj"}
    )
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("hirecj.accounts.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    name = Column(String(255))  # User-friendly name
    data = Column(JSONB, nullable=False, default=dict)  # Schemaless connection data
    credential_id = Column(UUID(as_uuid=False), ForeignKey("hirecj.credentials.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="connections")
    credential = relationship("Credential", back_populates="connections")


class Credential(Base):
    """Credential storage with encryption support."""
    __tablename__ = "credentials"
    __table_args__ = (
        Index('idx_account_provider_cred', 'account_id', 'provider'),
        {"schema": "hirecj"}
    )
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("hirecj.accounts.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    name = Column(String(255))  # User-friendly name
    auth_type = Column(String(50), nullable=False)  # oauth2, api_key, basic
    data = Column(JSONB, nullable=False, default=dict)  # Encrypted credential data
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="credentials")
    connections = relationship("Connection", back_populates="credential")