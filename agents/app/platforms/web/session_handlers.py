"""Session-related message handlers."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime

from fastapi import WebSocket

from app.logging_config import get_logger
from app.models import Message
from app.constants import WebSocketCloseCodes
from app.services.post_oauth_handler import post_oauth_handler

from .session_handler import SessionHandler

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class SessionHandlers:
    """Handles session-related WebSocket messages."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform
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

        # Determine workflow and merchant based on authentication state
        ws_session = self.platform.sessions.get(conversation_id, {})
        is_authenticated = ws_session.get("authenticated", False)
        user_id = ws_session.get("user_id") if is_authenticated else None
        
        # Initialize defaults
        workflow = "shopify_onboarding"
        merchant = None
        scenario = None
        
        if is_authenticated and user_id:
            # For authenticated users, check their merchant associations
            from app.utils.supabase_util import get_db_session
            from shared.db_models import MerchantToken
            from sqlalchemy import select
            
            try:
                with get_db_session() as db:
                    # Find the user's most recent merchant
                    merchant_token = db.scalar(
                        select(MerchantToken)
                        .where(MerchantToken.user_id == user_id)
                        .order_by(MerchantToken.created_at.desc())
                        .limit(1)
                    )
                    
                    if merchant_token:
                        merchant = merchant_token.shop_domain.replace(".myshopify.com", "")
                        # Check if this is a recent OAuth (within last 60 seconds)
                        from datetime import datetime, timedelta
                        if merchant_token.created_at > datetime.utcnow() - timedelta(seconds=60):
                            workflow = "shopify_post_auth"
                            scenario = "post_auth"
                            logger.info(f"[WORKFLOW] Recent OAuth detected for {merchant} - using post_auth workflow")
                        else:
                            workflow = "ad_hoc_support"
                            scenario = "normal_day"
                            logger.info(f"[WORKFLOW] Authenticated user with merchant {merchant}")
                    else:
                        logger.info(f"[WORKFLOW] Authenticated user without merchant - using onboarding")
            except Exception as e:
                logger.error(f"[WORKFLOW] Error determining merchant: {e}")
        else:
            logger.info(f"[WORKFLOW] Anonymous user - using onboarding workflow")
        
        # Check if this conversation has post-OAuth state waiting
        post_auth_state = post_oauth_handler.get_post_auth_state(conversation_id)
        if post_auth_state:
            # Use the prepared post-auth workflow state
            session = post_auth_state["session"]
            initial_message = post_auth_state.get("initial_message")

            # Store the session for future use
            self.platform.session_manager.store_session(conversation_id, session)
            
            # Preserve the workflow from the post-auth session
            workflow = session.conversation.workflow
            logger.info(f"[POST_OAUTH] Using post-auth state for {conversation_id}, preserving workflow: {workflow}")
        else:
            initial_message = None
        
        # Get workflow requirements
        workflow_data = self.platform.workflow_loader.get_workflow(workflow)
        requirements = workflow_data.get('requirements', {})
        
        # Use server-determined values with appropriate defaults
        if not requirements.get('merchant', True):
            # Workflow doesn't require merchant
            if not merchant:
                merchant = "onboarding_user"
        else:
            # Workflow requires merchant
            if not merchant:
                await self.platform.send_error(websocket, "Merchant ID required for this workflow")
                return
        
        if not requirements.get('scenario', True):
            # Workflow doesn't require scenario
            if not scenario:
                scenario = "default"
        else:
            # Workflow requires scenario
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
            # Preserve the workflow from the existing session
            workflow = session.conversation.workflow
            logger.info(f"[RECONNECT] Preserving existing session workflow: {workflow}")
        else:
            logger.info(
                f"[NEW_SESSION] Creating new session for {conversation_id}"
            )
            # Create conversation session
            try:
                ws_session = self.platform.sessions.get(conversation_id, {})
                # Get user_id from WebSocket session (set by WebSocket handler from cookie)
                user_id = ws_session.get("user_id") if ws_session.get("user_id") != "anonymous" else None
                
                session = await self.session_handler.create_session(
                    conversation_id, merchant, scenario, workflow, ws_session, user_id
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

        # If this is a pending post-OAuth analysis, send placeholder and trigger async processing
        if post_auth_state and post_auth_state.get("pending_analysis"):
            await websocket.send_json({
                "type": "cj_message",
                "data": {
                    "content": "🔄 Connection successful! Analyzing your store...",
                    "factCheckStatus": "available",
                    "timestamp": datetime.now().isoformat(),
                }
            })
            
            # Trigger async analysis
            import asyncio
            asyncio.create_task(self._process_post_oauth_analysis(
                websocket, session, conversation_id
            ))
            return
        
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
    
    async def _process_post_oauth_analysis(
        self, websocket: WebSocket, session: 'Session', conversation_id: str
    ):
        """Process post-OAuth analysis asynchronously."""
        try:
            logger.info(f"[POST_OAUTH] Starting async analysis for {conversation_id}")
            
            # Import here to avoid circular imports
            from app.services.message_processor import MessageProcessor
            
            processor = MessageProcessor()
            
            # Generate the analysis (this takes 17-20 seconds)
            response = await processor.process_message(
                session=session,
                message="SYSTEM_EVENT: shopify_oauth_complete",
                sender="system"
            )
            
            logger.info(f"[POST_OAUTH] Analysis complete for {conversation_id}")
            
            # Send the analysis result
            if isinstance(response, dict) and response.get("type") == "message_with_ui":
                await websocket.send_json({
                    "type": "cj_message",
                    "data": {
                        "content": response["content"],
                        "factCheckStatus": "available",
                        "timestamp": datetime.now().isoformat(),
                        "ui_elements": response.get("ui_elements", [])
                    }
                })
            else:
                await websocket.send_json({
                    "type": "cj_message",
                    "data": {
                        "content": response,
                        "factCheckStatus": "available",
                        "timestamp": datetime.now().isoformat(),
                    }
                })
        except Exception as e:
            logger.error(f"[POST_OAUTH] Failed to process analysis: {e}", exc_info=True)
            # Send a fallback message if analysis fails
            await websocket.send_json({
                "type": "cj_message",
                "data": {
                    "content": "Welcome! Your store is connected. How can I help you today?",
                    "factCheckStatus": "available",
                    "timestamp": datetime.now().isoformat(),
                }
            })
