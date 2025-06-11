"""Service to pre-prepare sessions for specific workflows."""

from typing import Dict, Any, Optional

from app.logging_config import get_logger
from shared.models.api import OAuthHandoffRequest
from shared.user_identity import get_or_create_user
from app.services.session_manager import SessionManager
from app.services.message_processor import MessageProcessor

logger = get_logger(__name__)


class SessionInitiator:
    """
    Handles pre-warming sessions for specific events, like OAuth completion.
    This service creates a session and generates the first message *before*
    the user connects via WebSocket, ensuring a fast and seamless experience.
    """

    def __init__(self):
        self.session_manager = SessionManager()
        self.message_processor = MessageProcessor()
        # In a multi-worker setup, this cache would need to be external (e.g., Redis)
        self._session_cache: Dict[str, Dict[str, Any]] = {}
        logger.info("SessionInitiator initialized.")

    async def prepare_oauth_session(self, request: OAuthHandoffRequest) -> bool:
        """
        Create and pre-warm a session for the shopify_post_auth workflow.

        Args:
            request: The OAuth handoff request from the Auth service.

        Returns:
            True if session was prepared successfully, False otherwise.
        """
        logger.info(
            f"[SESSION_INITIATOR] Preparing session for conv_id: {request.conversation_id}"
        )

        try:
            # 1. Get or create user identity
            user_id, is_new_user = get_or_create_user(
                request.shop_domain, request.email
            )
            logger.info(
                f"[SESSION_INITIATOR] User identity: user_id={user_id}, new_user={is_new_user}"
            )

            # 2. Create a new session with the post-auth workflow
            merchant_name = request.shop_domain.replace(".myshopify.com", "")
            session = self.session_manager.create_session(
                merchant_name=merchant_name,
                scenario_name="post_auth",  # Generic scenario, as workflow drives logic
                workflow_name="shopify_post_auth",
                user_id=user_id,
            )

            # 3. Inject OAuth metadata into the session for the agent to use
            session.oauth_metadata = {
                "provider": "shopify",
                "is_new_merchant": request.is_new,
                "shop_domain": request.shop_domain,
                "authenticated": True,
            }
            logger.info(
                f"[SESSION_INITIATOR] Injected OAuth metadata into session {session.id}"
            )

            # 4. Generate the initial message from the workflow's initial action
            initial_message = await self.message_processor.process_message(
                session=session,
                message="SYSTEM_EVENT: shopify_oauth_complete",
                sender="system",
            )

            if not initial_message:
                logger.error(
                    "[SESSION_INITIATOR] Failed to generate initial message for post-auth workflow."
                )
                return False

            # 5. Cache the prepared session and initial message
            self._session_cache[request.conversation_id] = {
                "session": session,
                "initial_message": initial_message,
            }

            logger.info(
                f"[SESSION_INITIATOR] Session for conv_id {request.conversation_id} is pre-warmed and cached."
            )
            return True

        except Exception as e:
            logger.error(
                f"[SESSION_INITIATOR] Failed to prepare session: {e}", exc_info=True
            )
            return False

    def get_prepared_session(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and remove a pre-warmed session from the cache.
        This is a one-time use retrieval.
        """
        prepared_data = self._session_cache.pop(conversation_id, None)
        if prepared_data:
            logger.info(
                f"[SESSION_INITIATOR] Retrieved pre-warmed session for {conversation_id}"
            )
        else:
            logger.warning(
                f"[SESSION_INITIATOR] No pre-warmed session found for {conversation_id}"
            )

        return prepared_data


# Singleton instance for the application
session_initiator = SessionInitiator()
