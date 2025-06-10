"""Database utilities for auth service."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Create engine
engine = create_engine(settings.supabase_connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session():
    """Get a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()