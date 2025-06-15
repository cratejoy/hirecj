"""WebSocket connection and message handling."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
import uuid
import asyncio

from fastapi import WebSocket
from pydantic import ValidationError, TypeAdapter

from shared.logging_config import get_logger
from app.services.fact_extractor import FactExtractor
from app.constants import WebSocketCloseCodes
from shared.protocol.models import (
    IncomingMessage,
    StartConversationMsg,
    UserMsg,
    EndConversationMsg,
    FactCheckMsg,
    PingMsg,
    SystemEventMsg,
    DebugRequestMsg,
    WorkflowTransitionMsg,
    LogoutMsg,
    OAuthCompleteMsg,
    ErrorMsg,
)

from .message_handlers import MessageHandlers
from shared.auth.session_cookie import get_session

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class WebSocketHandler:
    """Handles WebSocket connections and message routing."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform
        self.message_handlers = MessageHandlers(platform)
        # Create TypeAdapter for validating discriminated union
        self.incoming_message_adapter = TypeAdapter(IncomingMessage)

    async def handle_connection(self, websocket: WebSocket):
        """
        Handle new WebSocket connection.

        Args:
            websocket: WebSocket connection object
        """
        # Get user context from cookie BEFORE accepting connection
        session = None                     # <── ADD THIS LINE
        session_id = websocket.cookies.get("hirecj_session")
        user_ctx = None
        conversation_id = None

        # Holders for primitive values to avoid DetachedInstanceError
        session_id_db: str | None = None    # NEW
        session_data_db: dict = {}          # NEW
        
        if session_id:
            logger.info(f"[WEBSOCKET] Found session cookie: {session_id[:10]}...")
            session_data = get_session(session_id)
            if session_data:
                user_ctx = {"user_id": session_data["user_id"]}
                session_id_db = session_data["session_id"]
                session_data_db = session_data.get("data", {})
                logger.info(f"[WEBSOCKET] User {session_data['user_id']} connected via session cookie")
                logger.info(f"[WEBSOCKET] Session data loaded: {session_data_db}")

                # For authenticated users, create conversation ID based on user and session
                session_hash = session_id_db[:8]
                conversation_id = f"user_{user_ctx['user_id']}_{session_hash}"
                logger.info(f"[WEBSOCKET] Created conversation {conversation_id} for authenticated user")
            else:
                logger.debug(f"[WEBSOCKET] Session cookie invalid or expired")
        else:
            logger.info(f"[WEBSOCKET] No session cookie found - anonymous connection")
        
        # For anonymous users, always create a new temporary conversation
        if not conversation_id:
            conversation_id = f"anon_{uuid.uuid4().hex[:8]}"
            logger.info(f"[WEBSOCKET] Created temporary conversation {conversation_id} for anonymous user")

        # Register connection
        self.platform.connections[conversation_id] = websocket

        # Initialize session with user context if available
        ws_session = {
            "user_id": user_ctx["user_id"] if user_ctx else "anonymous",
            "display_name": "Web User",
            "session_start": datetime.now().isoformat(),
            "ip_address": getattr(websocket, "remote_address", None),
            "user_agent": None,  # Would need to be passed from client
            "authenticated": user_ctx is not None,
            "session_id": session_id_db if 'session_id_db' in locals() else None,
            "data": session_data_db if 'session_data_db' in locals() else {},
        }
        
        # Extract oauth_metadata if present in session data
        if 'session_data_db' in locals() and session_data_db:
            if oauth_metadata := session_data_db.get("oauth_metadata"):
                ws_session["oauth_metadata"] = oauth_metadata
                ws_session["shop_domain"] = oauth_metadata.get("shop_domain")
                ws_session["merchant_id"] = oauth_metadata.get("merchant_id")
                logger.info(f"[WEBSOCKET] Loaded OAuth metadata from session: {oauth_metadata}")
        
        self.platform.sessions[conversation_id] = ws_session

        logger.info(
            f"[WEBSOCKET_LIFECYCLE] New WebSocket connection: {conversation_id}"
        )
        websocket_logger.debug(
            f"[WS_DEBUG] WebSocket handler started for conversation: {conversation_id}"
        )

        try:
            # Listen for messages
            async for message in websocket.iter_json():
                await self._handle_websocket_message(
                    websocket, conversation_id, message
                )

        except Exception as e:
            logger.info(f"WebSocket connection {conversation_id} closed: {str(e)}")
        finally:
            await self._handle_disconnect(conversation_id)
            
            # Cleanup on disconnect
            self.platform.connections.pop(conversation_id, None)
            logger.info(f"WebSocket connection {conversation_id} disconnected")

    async def _handle_websocket_message(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """
        Process incoming WebSocket message.

        Args:
            websocket: WebSocket connection
            conversation_id: Conversation identifier
            data: Message data from client
        """
        try:
            # Log all incoming WebSocket messages with clean format
            websocket_logger.info(
                f"[WS_RECEIVE] conversation={conversation_id} type={data.get('type', 'unknown')} "
                f"size={len(str(data))} data={data}"
            )

            # Parse and validate message using Pydantic TypeAdapter
            try:
                message = self.incoming_message_adapter.validate_python(data)
            except ValidationError as e:
                websocket_logger.warning(
                    f"[WS_ERROR] Invalid message format - conversation={conversation_id} errors={e.errors()}"
                )
                await self.platform.send_error(
                    websocket, f"Invalid message format: {e}"
                )
                return

            # Route based on message type using isinstance checks
            if isinstance(message, StartConversationMsg):
                await self.message_handlers.handle_start_conversation(websocket, conversation_id, message, raw_data=data)
            elif isinstance(message, UserMsg):
                await self.message_handlers.handle_message(websocket, conversation_id, message)
            elif isinstance(message, EndConversationMsg):
                await self.message_handlers.handle_end_conversation(websocket, conversation_id, message)
            elif isinstance(message, FactCheckMsg):
                await self.message_handlers.handle_fact_check(websocket, conversation_id, message)
            elif isinstance(message, PingMsg):
                await self.message_handlers.handle_ping(websocket, conversation_id, message)
            elif isinstance(message, DebugRequestMsg):
                await self.message_handlers.handle_debug_request(websocket, conversation_id, message)
            elif isinstance(message, WorkflowTransitionMsg):
                await self.message_handlers.handle_workflow_transition(websocket, conversation_id, message)
            elif isinstance(message, LogoutMsg):
                await self.message_handlers.handle_logout(websocket, conversation_id, message)
            elif isinstance(message, SystemEventMsg):
                await self.message_handlers.handle_system_event(websocket, conversation_id, message)
            elif isinstance(message, OAuthCompleteMsg):
                await self.message_handlers.handle_oauth_complete(websocket, conversation_id, message)
            else:
                logger.warning(f"Unhandled message type: {type(message)}")
                await self.platform.send_error(
                    websocket, f"Unhandled message type: {type(message).__name__}"
                )

        except Exception as e:
            import traceback

            logger.error(
                f"Error handling WebSocket message from {conversation_id}: {str(e)}\n{traceback.format_exc()}"
            )
            # Send more informative error
            error_msg = "Message processing error"
            if "Universe not found" in str(e):
                error_msg = f"Universe not found. Please ensure universe exists for {data.get('merchant_id', 'merchant')} and {data.get('scenario', 'scenario')}"
            elif "No such file or directory" in str(e):
                error_msg = "Configuration file missing. Please check server setup."

            await self.platform.send_error(websocket, error_msg)

    async def _handle_disconnect(self, conversation_id: str):
        """Handle WebSocket disconnect cleanup."""
        # Extract facts on disconnect if session exists
        session = self.platform.session_manager.get_session(conversation_id)
        if session:
            
            # Only extract facts if conversation has messages and user_id
            if session.user_id and session.conversation.messages:
                try:
                    logger.info(f"[FACT_EXTRACTION] Processing conversation {conversation_id} on disconnect")
                    fact_extractor = FactExtractor()
                    new_facts = await fact_extractor.extract_and_add_facts(
                        session.conversation, 
                        session.user_id
                    )
                    
                    if new_facts:
                        logger.info(f"[FACT_EXTRACTION] Extracted {len(new_facts)} facts on disconnect")
                    else:
                        logger.info(f"[FACT_EXTRACTION] No new facts extracted on disconnect")
                except Exception as e:
                    logger.error(f"[FACT_EXTRACTION] Error extracting facts on disconnect: {e}", exc_info=True)
            
            # Save session
            self.platform.conversation_storage.save_session(session)
            logger.info(f"[CONVERSATION] Saved conversation {conversation_id} on disconnect")
