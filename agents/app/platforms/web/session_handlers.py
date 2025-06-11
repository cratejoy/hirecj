"""Session-related message handlers."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime

from fastapi import WebSocket

from app.logging_config import get_logger
from app.models import Message
from app.constants import WebSocketCloseCodes

from .oauth_handler import OAuthHandler
from .session_handler import SessionHandler

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class SessionHandlers:
    """Handles session-related WebSocket messages."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform
        self.oauth_handler = OAuthHandler(platform)
        self.session_handler = SessionHandler(platform)

    async def handle_start_conversation(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle start_conversation message."""
        # Initialize conversation with CrewAI
        start_data = data.get("data", {})
        if not isinstance(start_data, dict):
            await self.platform.send_error(
                websocket, "Invalid start_conversation data format"
            )
            return

        workflow = start_data.get("workflow", "ad_hoc_support")
        
        # Get workflow requirements
        workflow_data = self.platform.workflow_loader.get_workflow(workflow)
        requirements = workflow_data.get('requirements', {})
        
        # Use requirements to determine defaults and validation
        if not requirements.get('merchant', True):
            # Workflow doesn't require merchant
            merchant = start_data.get("merchant_id", "onboarding_user")
        else:
            # Workflow requires merchant
            merchant = start_data.get("merchant_id")
            if not merchant:
                await self.platform.send_error(websocket, "Merchant ID required for this workflow")
                return
        
        if not requirements.get('scenario', True):
            # Workflow doesn't require scenario
            scenario = start_data.get("scenario", "default")
        else:
            # Workflow requires scenario
            scenario = start_data.get("scenario")
            if not scenario:
                await self.platform.send_error(websocket, "Scenario required for this workflow")
                return

        # Check for existing session first
        logger.info(
            f"[SESSION_CHECK] Looking for existing session: {conversation_id}"
        )
        existing_session = self.platform.session_manager.get_session(conversation_id)
        if existing_session:
            logger.info(
                f"[RECONNECT] Resuming existing session for {conversation_id}"
            )
            logger.info(
                f"[RECONNECT] Session has {len(existing_session.conversation.messages)} messages"
            )
            session = existing_session
        else:
            logger.info(
                f"[NEW_SESSION] Creating new session for {conversation_id}"
            )
            # Create conversation session
            try:
                ws_session = self.platform.sessions.get(conversation_id, {})
                session = await self.session_handler.create_session(
                    conversation_id, merchant, scenario, workflow, ws_session
                )
            except ValueError as e:
                # Handle missing universe or other critical errors
                error_msg = str(e)
                logger.error(f"Failed to start conversation: {error_msg}")
                await self.platform.send_error(
                    websocket, f"Cannot start conversation: {error_msg}"
                )
                # Close the WebSocket with error code
                await websocket.close(
                    code=WebSocketCloseCodes.INTERNAL_ERROR,
                    reason="Universe not found",
                )
                return
            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error starting conversation: {e}")
                await self.platform.send_error(
                    websocket,
                    "Failed to start conversation due to internal error",
                )
                await websocket.close(
                    code=WebSocketCloseCodes.INTERNAL_ERROR,
                    reason="Internal error",
                )
                return
        
        # Check for OAuth completion status
        oauth_data = await self.oauth_handler.check_oauth_completion(conversation_id)
        if oauth_data:
            await self.oauth_handler.process_oauth_completion(websocket, session, oauth_data)
            return

        # Create conversation data
        conversation_data = {
            "conversationId": conversation_id,
            "merchantId": merchant,
            "scenario": scenario,
            "workflow": workflow,
            "sessionId": session.id,
            "workflow_requirements": requirements,
            "user_id": session.user_id,
        }

        if existing_session:
            # Include message history for resumed conversations
            conversation_data["resumed"] = True
            conversation_data["messageCount"] = len(
                session.conversation.messages
            )
            conversation_data["messages"] = [
                {
                    "sender": msg.sender,
                    "content": msg.content,
                    "timestamp": (
                        msg.timestamp.isoformat()
                        if hasattr(msg.timestamp, "isoformat")
                        else str(msg.timestamp)
                    ),
                }
                for msg in session.conversation.messages[
                    -10:
                ]  # Last 10 messages
            ]

        await websocket.send_json(
            {
                "type": "conversation_started",
                "data": conversation_data,
            }
        )
        
        # Import workflow handlers for the rest
        from .workflow_handlers import WorkflowHandlers
        workflow_handlers = WorkflowHandlers(self.platform)
        
        # Check if starting onboarding workflow but already authenticated
        await workflow_handlers._check_already_authenticated(
            websocket, conversation_id, session, workflow, requirements, conversation_data
        )

        # Register progress callback
        await workflow_handlers._setup_progress_callback(websocket)

        # Handle initial workflow action
        await workflow_handlers._handle_initial_workflow_action(websocket, session, workflow)

    async def handle_session_update(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle session_update message."""
        update_data = data.get("data", {})
        
        # Validate frontend is NOT sending user_id (it shouldn't)
        if "user_id" in update_data:
            logger.warning(f"[SESSION_UPDATE] Frontend sent user_id - this is incorrect! "
                         f"User IDs must be generated by backend only.")
        
        # Store raw data in WebSocket session for later use
        session = self.platform.sessions.get(conversation_id, {})
        session.update(update_data)
        self.platform.sessions[conversation_id] = session
        
        logger.info(f"[SESSION_UPDATE] Stored merchant data for {conversation_id}")
        logger.info(f"[SESSION_UPDATE] Data: merchant_id={update_data.get('merchant_id')}, "
                   f"shop_domain={update_data.get('shop_domain')}")

    async def handle_logout(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle logout message."""
        logger.info(f"[LOGOUT] Processing logout request for conversation {conversation_id}")
        
        # End any active session
        session = self.platform.session_manager.get_session(conversation_id)
        if session:
            # Save conversation before logout
            self.platform.conversation_storage.save_session(session)
            # Remove session
            self.platform.session_manager.end_session(conversation_id)
            logger.info(f"[LOGOUT] Ended session for conversation {conversation_id}")
        
        # Clear WebSocket session data
        if conversation_id in self.platform.sessions:
            del self.platform.sessions[conversation_id]
            logger.info(f"[LOGOUT] Cleared WebSocket session data")
        
        # Send logout confirmation
        await websocket.send_json({
            "type": "logout_complete",
            "data": {
                "message": "Successfully logged out"
            }
        })
        
        # Close WebSocket connection
        await websocket.close()
        logger.info(f"[LOGOUT] Logout complete, connection closed")
