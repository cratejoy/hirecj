"""
Database utility wrapper for the auth service.

This module now delegates all functionality to the centralized `shared.database`
module to ensure a single source of truth for database connections.
"""

# Re-export all functions from the shared database utility
from shared.database import (
    get_connection_string,
    get_db_connection,
    execute_query,
    test_connection,
    get_engine,
    get_session_factory,
    get_db_session,
)

# For compatibility, re-export engine and SessionLocal from the shared source
engine = get_engine()
SessionLocal = get_session_factory()


__all__ = [
    "get_connection_string",
    "get_db_connection",
    "execute_query",
    "test_connection",
    "get_engine",
    "engine",
    "get_session_factory",
    "SessionLocal",
    "get_db_session",
]
