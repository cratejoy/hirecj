"""PostgreSQL connection utilities with SQLAlchemy support."""

import os
import psycopg2
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

# Use centralized config - no direct load_dotenv!
from app.config import settings


def get_connection_string():
    """Return connection string."""
    # Get from settings which uses centralized env loader
    conn_string = settings.supabase_connection_string
    
    if not conn_string:
        raise ValueError("SUPABASE_CONNECTION_STRING must be set in .env")
    
    return conn_string


@contextmanager
def get_db_connection():
    """Get a raw psycopg2 database connection context manager."""
    conn = psycopg2.connect(get_connection_string())
    try:
        yield conn
    finally:
        conn.close()


def execute_query(query, params=None):
    """Execute a query and return results using psycopg2."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            conn.commit()
            return None


def test_connection():
    """Test database connection."""
    try:
        result = execute_query("SELECT 1")
        return result[0][0] == 1
    except Exception as e:
        print(f"Connection failed: {e}")
        return False


# SQLAlchemy setup
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        # Use NullPool to avoid connection pooling issues with serverless
        _engine = create_engine(
            get_connection_string(),
            poolclass=NullPool,
            echo=False  # Set to True for SQL logging
        )
    return _engine


def get_session_factory():
    """Get or create session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _SessionLocal


@contextmanager
def get_db_session() -> Session:
    """Get a SQLAlchemy session context manager."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()