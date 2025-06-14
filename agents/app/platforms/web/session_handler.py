"""Session management for web platform."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
import asyncio

from fastapi import WebSocket

from app.logging_config import get_logger
from app.models import Message
from app.constants import WorkflowConstants
from shared.user_identity import get_or_create_user

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)


class SessionHandler:
    """Handles session creation and management."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform

    async def create_session(
        self,
        conversation_id: str,
        merchant: str,
        scenario: str,
        workflow: str,
        ws_session: Dict[str, Any],
        user_id: str = None
    ):
        """Create a new conversation session."""
        try:
            # User ID now comes from WebSocket handler (via cookie)
            # Only fall back to shop_domain if no user_id provided
            if not user_id:
                shop_domain = ws_session.get("shop_domain")
                
                if shop_domain:
                    user_id, is_new = get_or_create_user(shop_domain)
                    logger.info(f"[USER_IDENTITY] Backend generated user_id={user_id} "
                               f"for shop_domain={shop_domain} (new={is_new})")
                else:
                    logger.info(f"[USER_IDENTITY] No user_id from cookie and no shop_domain - proceeding anonymously")
            
            logger.info(f"[SESSION_CREATE] Creating session: merchant={merchant}, "
                       f"workflow={workflow}, user_id={user_id or 'None'}")
            
            session = self.platform.session_manager.create_session(
                merchant_name=merchant,
                scenario_name=scenario,
                workflow_name=workflow,
                user_id=user_id,
            )
            # Store the session with the conversation_id as key
            self.platform.session_manager.store_session(conversation_id, session)
            
            return session
            
        except ValueError as e:
            # Handle missing universe or other critical errors
            error_msg = str(e)
            logger.error(f"Failed to start conversation: {error_msg}")
            raise
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error starting conversation: {e}")
            raise

    async def handle_workflow_transition(
        self,
        conversation_id: str,
        session: Any,
        workflow: str,
        target_workflow: str,
        transition_message: str,
        shop_domain: str
    ):
        """Handle workflow transition for authenticated users."""
        logger.info(f"[ALREADY_AUTH] Detected authenticated user {session.user_id} starting {workflow} workflow, transitioning to {target_workflow}")
        
        # IMMEDIATE: Update workflow first for instant feedback
        success = self.platform.session_manager.update_workflow(conversation_id, target_workflow)
        if success:
            logger.info(f"[ALREADY_AUTH] Successfully transitioned {conversation_id} to {target_workflow}")
            
            # ASYNC: Handle CJ's responses without blocking
            async def handle_auth_transition():
                try:
                    # Send transition notification
                    transition_msg = f"Existing session detected: {shop_domain} with workflow transition to {target_workflow}"
                    
                    # Let CJ acknowledge the transition
                    response = await self.platform.message_processor.process_message(
                        session=session,
                        message=transition_msg,
                        sender="system"
                    )
                    
                    # Send CJ's acknowledgment
                    if response:
                        response_data = {
                            "content": response if isinstance(response, str) else response.get("content", response),
                            "factCheckStatus": "available",
                            "timestamp": datetime.now().isoformat(),
                        }
                        # Note: We need access to the websocket here
                        # This will be passed from the message handler
                    
                    # Notify the new workflow about the transition
                    arrival_msg = f"Transitioned from {workflow} workflow"
                    await self.platform.message_processor.process_message(
                        session=session,
                        message=arrival_msg,
                        sender="system"
                    )
                except Exception as e:
                    logger.error(f"[ALREADY_AUTH] Error handling transition messages: {e}")
            
            # Create async task to handle messages without blocking
            asyncio.create_task(handle_auth_transition())
            
            return True
        else:
            logger.error(f"[ALREADY_AUTH] Failed to update workflow for {conversation_id}")
            return False

    def get_shop_domain(self, session: Any) -> str:
        """Extract shop domain from session."""
        shop_domain = WorkflowConstants.DEFAULT_SHOP_DOMAIN
        if hasattr(session, 'oauth_metadata') and session.oauth_metadata:
            shop_domain = session.oauth_metadata.get('shop_domain', shop_domain)
        elif hasattr(session, 'shop_domain'):
            shop_domain = session.shop_domain
        elif session.merchant_name and session.merchant_name != "onboarding_user":
            shop_domain = session.merchant_name
        return shop_domain
