"""Session cookie management for HTTP-based authentication."""

import secrets
import logging
from datetime import datetime, timedelta
from sqlalchemy import delete, select

from shared.database import get_db_session
from shared.db_models import WebSession

logger = logging.getLogger(__name__)

# Session configuration
SESSION_TTL_HOURS = 24
SESSION_ID_PREFIX = "sess_"


def issue_session(user_id: str) -> str:
    """
    Create a new web session in the database.
    
    Args:
        user_id: The authenticated user's ID
        
    Returns:
        The generated session ID to be stored in cookie
    """
    # Generate secure session ID
    session_id = f"{SESSION_ID_PREFIX}{secrets.token_hex(16)}"
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    
    logger.info(f"[SESSION] Issuing new session for user {user_id}")
    
    with get_db_session() as db:
        # Clean up any existing sessions for this user
        # This ensures one active session per user
        existing_count = db.execute(
            delete(WebSession).where(WebSession.user_id == user_id)
        ).rowcount
        
        if existing_count > 0:
            logger.info(f"[SESSION] Cleaned up {existing_count} existing sessions for user {user_id}")
        
        # Create new session
        session = WebSession(
            session_id=session_id,
            user_id=user_id,
            expires_at=expires_at,
            data={}
        )
        db.add(session)
        
        logger.info(f"[SESSION] Successfully issued session {session_id} for user {user_id}, expires at {expires_at}")
    
    return session_id


def get_session(session_id: str) -> dict | None:
    """
    Retrieve session data from database.
    
    Args:
        session_id: The session ID from cookie
        
    Returns:
        Session data dict with user_id, or None if invalid/expired
    """
    if not session_id:
        return None

    with get_db_session() as db:
        session = db.scalar(
            select(WebSession)
            .where(WebSession.session_id == session_id)
            .where(WebSession.expires_at > datetime.utcnow())
        )
        
        if session:
            # Update last accessed time
            session.last_accessed_at = datetime.utcnow()
            
            logger.debug(f"[SESSION] Retrieved valid session for user {session.user_id}")
            return {
                "user_id": session.user_id,
                "session_id": session.session_id,
                "data": session.data or {}
            }
        else:
            logger.debug(f"[SESSION] No valid session found for ID {session_id}")
            return None


def revoke_session(session_id: str) -> bool:
    """
    Revoke a session by deleting it from database.
    
    Args:
        session_id: The session ID to revoke
        
    Returns:
        True if session was found and revoked, False otherwise
    """
    with get_db_session() as db:
        result = db.execute(
            delete(WebSession).where(WebSession.session_id == session_id)
        )
        
        if result.rowcount > 0:
            logger.info(f"[SESSION] Revoked session {session_id}")
            return True
        else:
            logger.debug(f"[SESSION] No session found to revoke: {session_id}")
            return False
