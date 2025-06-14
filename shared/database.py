"""
Shared PostgreSQL connection utilities with SQLAlchemy support.

This is the single source of truth for all database connections.
"""

import os
import psycopg2
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

# This import will load environment variables from the root .env file.
from shared.env_loader import get_env


def get_connection_string() -> str:
    """Return the database connection string from environment variables."""
    conn_string = get_env("SUPABASE_CONNECTION_STRING")
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


def execute_query(query: str, params=None):
    """Execute a raw SQL query and return results using psycopg2."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            # For queries that don't return rows (e.g., INSERT, UPDATE)
            conn.commit()
            return None


# --- SQLAlchemy Setup ---

# Global engine and session factory to avoid re-creation
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the global SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_connection_string(),
            poolclass=NullPool,  # Recommended for serverless environments
            echo=False,
        )
    return _engine


def get_session_factory():
    """Get or create the global session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _SessionLocal


@contextmanager
def get_db_session() -> Session:
    """Provide a transactional scope around a series of operations."""
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


def test_connection() -> bool:
    """Test the database connection."""
    try:
        result = execute_query("SELECT 1")
        return result[0][0] == 1
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
