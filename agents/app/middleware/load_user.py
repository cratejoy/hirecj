"""Middleware to load user context from HTTP session cookie."""

import logging
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from sqlalchemy import select

from app.utils.supabase_util import get_db_session
from shared.db_models import WebSession

logger = logging.getLogger(__name__)


class LoadUser(BaseHTTPMiddleware):
    """
    Middleware that loads user context from session cookie.
    
    This middleware:
    1. Reads the hirecj_session cookie from incoming requests
    2. Looks up the session in PostgreSQL
    3. Attaches user context to request.state
    4. Updates the session's last accessed timestamp
    
    The user context is then available to:
    - Regular HTTP endpoints via request.state.user
    - WebSocket handlers via websocket.scope["state"].user
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and load user context if session cookie exists."""
        # Initialize user context as None
        request.state.user = None
        
        # Get session cookie
        session_id = request.cookies.get("hirecj_session")
        
        if session_id:
            logger.debug(f"[MIDDLEWARE] Found session cookie: {session_id[:10]}...")
            
            try:
                # Use SQLAlchemy session from supabase_util
                with get_db_session() as db:
                    # Query for valid (non-expired) session
                    session = db.scalar(
                        select(WebSession)
                        .where(WebSession.session_id == session_id)
                        .where(WebSession.expires_at > datetime.utcnow())
                    )
                    
                    if session:
                        # Update last accessed time
                        session.last_accessed_at = datetime.utcnow()
                        db.commit()
                        
                        # Set user context on request state
                        request.state.user = {
                            "user_id": session.user_id,
                            "session_id": session.session_id,
                            "data": session.data or {}
                        }
                        
                        logger.info(f"[MIDDLEWARE] Loaded user {session.user_id} from session")
                    else:
                        logger.debug(f"[MIDDLEWARE] Session not found or expired: {session_id[:10]}...")
                        
            except Exception as e:
                logger.error(f"[MIDDLEWARE] Error loading session: {e}", exc_info=True)
        else:
            logger.debug("[MIDDLEWARE] No session cookie found")
        
        # Continue with request processing
        response = await call_next(request)
        return response