"""Database utilities and helpers."""

import os
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy import select

from .models import Account, User
from .session import get_db_session


class TenantContext:
    """Thread-local storage for current tenant context."""
    _current_account_id: Optional[str] = None
    
    @classmethod
    def set_account(cls, account_id: str):
        """Set current account context."""
        cls._current_account_id = account_id
    
    @classmethod
    def get_account(cls) -> Optional[str]:
        """Get current account context."""
        return cls._current_account_id
    
    @classmethod
    def clear(cls):
        """Clear account context."""
        cls._current_account_id = None


def get_current_account_id() -> str:
    """Get current account ID from context."""
    account_id = TenantContext.get_account()
    if not account_id:
        raise ValueError("No account context set")
    return account_id


async def create_account(name: str, slug: str) -> Account:
    """Create a new account."""
    with get_db_session() as db:
        account = Account(
            name=name,
            slug=slug,
            settings={}
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account


async def create_user(account_id: str, email: str, name: str, role: str = "member") -> User:
    """Create a new user for an account."""
    with get_db_session() as db:
        user = User(
            account_id=account_id,
            email=email,
            name=name,
            role=role,
            settings={}
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def apply_account_filter(query, model_class, account_id: Optional[str] = None):
    """Apply account filter to a query."""
    if account_id is None:
        account_id = get_current_account_id()
    
    if hasattr(model_class, 'account_id'):
        return query.filter(model_class.account_id == account_id)
    return query


@asynccontextmanager
async def with_account_context(account_id: str):
    """Context manager for setting account context."""
    previous = TenantContext.get_account()
    TenantContext.set_account(account_id)
    try:
        yield
    finally:
        if previous:
            TenantContext.set_account(previous)
        else:
            TenantContext.clear()


# Database initialization helpers
def init_database():
    """Initialize database with extensions and schema."""
    from .session import engine
    
    with engine.connect() as conn:
        # Enable extensions
        conn.execute("CREATE EXTENSION IF NOT EXISTS 'uuid-ossp'")
        conn.execute("CREATE EXTENSION IF NOT EXISTS 'pgcrypto'")
        
        # Create schema
        conn.execute("CREATE SCHEMA IF NOT EXISTS hirecj")
        conn.commit()


def create_tables():
    """Create all tables from models."""
    from .models import Base
    from .session import engine
    
    Base.metadata.create_all(bind=engine)