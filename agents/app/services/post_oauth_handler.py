"""Handler for post-OAuth workflow transitions."""

from typing import Dict, Any, Optional

from app.logging_config import get_logger
from shared.models.api import OAuthHandoffRequest
from shared.user_identity import get_or_create_user
from app.services.session_manager import SessionManager
from app.services.message_processor import MessageProcessor

logger = get_logger(__name__)


class PostOAuthHandler:
    """
    Handles the workflow transition after OAuth completion.
    
    This service prepares the appropriate workflow state when a user
    completes OAuth authentication, ensuring they see the right content
    immediately upon return to the application.
    """

    def __init__(self):
        self.session_manager = SessionManager()
        self.message_processor = MessageProcessor()
        # Temporary storage for OAuth completion states
        # In production, this would be Redis or similar
        self._oauth_completion_states: Dict[str, Dict[str, Any]] = {}
        logger.info("[POST_OAUTH] Handler initialized")

    async def handle_oauth_completion(self, request: OAuthHandoffRequest) -> bool:
        """
        Handle OAuth completion by preparing the appropriate workflow state.

        Args:
            request: OAuth completion data from auth service

        Returns:
            True if handled successfully, False otherwise
        """
        logger.info(
            f"[POST_OAUTH] Handling OAuth completion for conversation: {request.conversation_id}"
        )

        try:
            # 1. Ensure we have user identity (should already exist from auth service)
            user_id, is_new_user = get_or_create_user(
                request.shop_domain, request.email
            )
            logger.info(
                f"[POST_OAUTH] User identity confirmed: user_id={user_id}, new_user={is_new_user}"
            )

            # 2. Create a session with the post-auth workflow
            merchant_name = request.shop_domain.replace(".myshopify.com", "")
            session = self.session_manager.create_session(
                merchant_name=merchant_name,
                scenario_name="post_auth",
                workflow_name="shopify_post_auth",  # The key workflow transition
                user_id=user_id,
            )

            # 3. Add OAuth metadata to the session
            session.oauth_metadata = {
                "provider": "shopify",
                "is_new_merchant": request.is_new,
                "shop_domain": request.shop_domain,
                "authenticated": True,
            }
            logger.info(
                f"[POST_OAUTH] Created session {session.id} with shopify_post_auth workflow"
            )

            # 4. Store the state temporarily until WebSocket connects
            # Note: We no longer generate the message here - it happens async after WebSocket connects
            self._oauth_completion_states[request.conversation_id] = {
                "session": session,
                "pending_analysis": True,  # Flag to trigger async analysis
                "user_id": user_id,
                "shop_domain": request.shop_domain,
            }

            logger.info(
                f"[POST_OAUTH] Successfully prepared post-auth state for conversation {request.conversation_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"[POST_OAUTH] Failed to handle OAuth completion: {e}", exc_info=True
            )
            return False

    def get_post_auth_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and remove the post-auth state for a conversation.
        
        This is a one-time retrieval - the state is removed after access
        to prevent stale data issues.
        
        Args:
            conversation_id: The conversation ID to look up
            
        Returns:
            The stored state if found, None otherwise
        """
        state = self._oauth_completion_states.pop(conversation_id, None)
        
        if state:
            logger.info(
                f"[POST_OAUTH] Retrieved post-auth state for conversation {conversation_id}"
            )
        else:
            logger.debug(
                f"[POST_OAUTH] No post-auth state found for conversation {conversation_id}"
            )

        return state


# Singleton instance for the application
post_oauth_handler = PostOAuthHandler()