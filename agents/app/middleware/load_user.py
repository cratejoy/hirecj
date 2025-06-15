"""Middleware to load user context from HTTP session cookie."""

"""Middleware to load user context from HTTP session cookie."""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from shared.auth.session_cookie import get_session

logger = logging.getLogger(__name__)


class LoadUser(BaseHTTPMiddleware):
    """
    Middleware that loads user context from session cookie by calling the
    shared session helper.
    """

    async def dispatch(self, request: Request, call_next):
        """Process the request and load user context if session cookie exists."""
        request.state.user = None
        session_id = request.cookies.get("hirecj_session")

        if session_id:
            logger.debug(f"[MIDDLEWARE] Found session cookie: {session_id[:10]}...")
            try:
                session_data = get_session(session_id)
                if session_data:
                    request.state.user = {
                        "user_id": session_data["user_id"],
                        "session_id": session_data["session_id"],
                        "data": session_data.get("data", {}),
                    }
                    logger.info(f"[MIDDLEWARE] Loaded user {session_data['user_id']} from session")
                else:
                    logger.debug(f"[MIDDLEWARE] Session not found or expired: {session_id[:10]}...")
            except Exception as e:
                logger.error(f"[MIDDLEWARE] Error loading session: {e}", exc_info=True)
        else:
            logger.debug("[MIDDLEWARE] No session cookie found")

        response = await call_next(request)
        return response
