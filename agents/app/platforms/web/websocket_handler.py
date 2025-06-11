"""WebSocket connection and message handling."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
import uuid
import asyncio

from fastapi import WebSocket

from app.logging_config import get_logger
from app.services.fact_extractor import FactExtractor
from app.constants import WebSocketCloseCodes

from .message_handlers import MessageHandlers

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class WebSocketHandler:
    """Handles WebSocket connections and message routing."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform
        self.message_handlers = MessageHandlers(platform)

    async def handle_connection(self, websocket: WebSocket, conversation_id: str = None):
        """
        Handle new WebSocket connection.

        Args:
            websocket: WebSocket connection object
            conversation_id: Optional existing conversation ID
        """
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"web_session_{uuid.uuid4().hex[:8]}"

        # Register connection
        self.platform.connections[conversation_id] = websocket

        # Initialize session
        self.platform.sessions[conversation_id] = {
            "user_id": "anonymous",
            "display_name": "Web User",
            "session_start": datetime.now().isoformat(),
            "ip_address": getattr(websocket, "remote_address", None),
            "user_agent": None,  # Would need to be passed from client
        }

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

            # Basic validation
            if not isinstance(data, dict):
                websocket_logger.warning(
                    f"[WS_ERROR] Invalid message format - conversation={conversation_id} type={type(data)}"
                )
                await self.platform.send_error(
                    websocket, "Invalid message format: expected JSON object"
                )
                return

            message_type = data.get("type", "message")

            # Validate message types
            valid_types = [
                "message",
                "start_conversation",
                "end_conversation",
                "fact_check",
                "ping",
                "session_update",
                "system_event",
                "debug_request",
                "workflow_transition",
                "logout",
            ]
            if message_type not in valid_types:
                logger.warning(
                    f"Invalid message type from {conversation_id}: {message_type}"
                )
                await self.platform.send_error(
                    websocket, f"Invalid message type: {message_type}"
                )
                return

            # Route to appropriate handler
            handler_method = getattr(self.message_handlers, f"handle_{message_type}", None)
            if handler_method:
                await handler_method(websocket, conversation_id, data)
            else:
                logger.warning(f"No handler for message type: {message_type}")
                await self.platform.send_error(
                    websocket, f"Unsupported message type: {message_type}"
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
