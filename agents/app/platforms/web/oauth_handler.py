"""
DEPRECATED: OAuth completion handling for web platform.

This module is part of the old database-driven OAuth handoff flow.
It is being deprecated and removed in Phase 6.4. The new flow uses a direct
server-to-server API call from the Auth service to the SessionInitiator service.
"""

from typing import TYPE_CHECKING
from app.logging_config import get_logger

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)


class OAuthHandler:
    """
    DEPRECATED: This class is no longer used.
    Its logic has been moved to the SessionInitiator service and the auth service.
    """

    def __init__(self, platform: 'WebPlatform'):
        logger.warning(
            "OAuthHandler is deprecated and should not be instantiated. "
            "The OAuth flow is now handled by SessionInitiator."
        )
        self.platform = platform
