"""
Database utility wrapper for the agents service.

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

__all__ = [
    "get_connection_string",
    "get_db_connection",
    "execute_query",
    "test_connection",
    "get_engine",
    "get_session_factory",
    "get_db_session",
]
