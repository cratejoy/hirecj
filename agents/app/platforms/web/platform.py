"""
Web Platform Implementation

Handles WebSocket connections for the web chat interface.
This is the primary platform for Demo 1.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import WebSocket

from ..base import (
    Platform,
    PlatformType,
    OutgoingMessage,
    Participant,
    Conversation,
)
from app.logging_config import get_logger
from app.services.session_manager import SessionManager
from app.services.message_processor import MessageProcessor
from app.services.conversation_storage import ConversationStorage
from app.workflows.loader import WorkflowLoader

from .websocket_handler import WebSocketHandler
from .session_handler import SessionHandler

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class WebPlatform(Platform):
    """Web chat platform using WebSocket connections"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize web platform.

        Args:
            config: Configuration dictionary (currently minimal for Demo 1)
        """
        super().__init__(PlatformType.WEB, config)

        # Track active WebSocket connections
        self.connections: Dict[str, Any] = {}  # conversation_id -> websocket
        self.sessions: Dict[str, Dict[str, Any]] = {}  # session management

        # Default configuration
        self.max_message_length = config.get(
            "max_message_length", 200
        )
        self.session_timeout = config.get(
            "session_timeout", 300
        )

        # Initialize managers
        self.session_manager = SessionManager()
        self.message_processor = MessageProcessor()
        self.conversation_storage = ConversationStorage()
        self.workflow_loader = WorkflowLoader()
        
        # Initialize handlers
        self.websocket_handler = WebSocketHandler(self)
        self.session_handler = SessionHandler(self)

    async def connect(self) -> None:
        """Initialize web platform (no external connections needed)"""
        logger.info("Web platform ready for WebSocket connections")
        self._set_connected(True)

    async def disconnect(self) -> None:
        """Cleanup web platform resources"""
        # Close all active connections
        for conversation_id, websocket in self.connections.items():
            try:
                await websocket.close()
                logger.debug(f"Closed WebSocket for conversation {conversation_id}")
            except Exception as e:
                logger.warning(f"Error closing WebSocket {conversation_id}: {str(e)}")

        self.connections.clear()
        self.sessions.clear()
        self._set_connected(False)
        logger.info("Web platform disconnected")

    async def send_message(self, message: OutgoingMessage) -> bool:
        """
        Send message to web client via WebSocket.

        Args:
            message: Message to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        websocket = self.connections.get(message.conversation_id)
        if not websocket:
            logger.warning(
                f"No WebSocket connection for conversation {message.conversation_id}"
            )
            return False

        try:
            # Format message for web client
            web_message = {
                "type": "message",
                "text": message.text,
                "timestamp": datetime.now().isoformat(),
                "thread_id": message.thread_id,
                "metadata": message.metadata or {},
            }
            
            # Add UI elements if present in metadata
            if message.metadata and "ui_elements" in message.metadata:
                web_message["ui_elements"] = message.metadata["ui_elements"]

            # Send JSON message to WebSocket
            await websocket.send_json(web_message)
            websocket_logger.info(
                f"[WS_SEND] conversation={message.conversation_id} type=message "
                f"size={len(message.text)} metadata={message.metadata}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error sending message to web client {message.conversation_id}: {str(e)}"
            )
            # Remove dead connection
            self.connections.pop(message.conversation_id, None)
            return False

    async def get_conversation(self, conversation_id: str) -> Conversation:
        """
        Get conversation details.

        Args:
            conversation_id: Web conversation identifier

        Returns:
            Conversation object
        """
        session = self.sessions.get(conversation_id, {})

        # Create participant from session data
        participant = Participant(
            platform_id=session.get("user_id", "anonymous"),
            display_name=session.get("display_name", "Web User"),
            metadata={
                "ip_address": session.get("ip_address"),
                "user_agent": session.get("user_agent"),
                "session_start": session.get("session_start"),
            },
        )

        return Conversation(
            platform=self.platform_type,
            conversation_id=conversation_id,
            participants=[participant],
            is_group=False,  # Web conversations are always 1:1
            metadata={
                "session_timeout": self.session_timeout,
                "connection_active": conversation_id in self.connections,
            },
        )

    async def handle_websocket_connection(self, websocket: WebSocket):
        """
        Handle new WebSocket connection.

        Args:
            websocket: WebSocket connection object
        """
        await self.websocket_handler.handle_connection(websocket)

    async def send_error(self, websocket: WebSocket, error_message: str):
        """Send error message to web client"""
        try:
            error_msg = {
                "type": "error",
                "text": error_message,
                "timestamp": datetime.now().isoformat(),
            }
            await websocket.send_json(error_msg)
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}")

    def get_active_connections(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active connections"""
        return {
            conversation_id: {
                "session": self.sessions.get(conversation_id, {}),
                "connected": conversation_id in self.connections,
            }
            for conversation_id in set(
                list(self.connections.keys()) + list(self.sessions.keys())
            )
        }

    async def broadcast_to_all(self, message: str):
        """
        Broadcast message to all connected web clients.

        Args:
            message: Message to broadcast
        """
        if not self.connections:
            logger.info("No active web connections for broadcast")
            return

        broadcast_msg = OutgoingMessage(
            conversation_id="",  # Will be set per connection
            text=message,
            metadata={"type": "broadcast"},
        )

        results = []
        for conversation_id in list(self.connections.keys()):
            broadcast_msg.conversation_id = conversation_id
            success = await self.send_message(broadcast_msg)
            results.append((conversation_id, success))

        successful = sum(1 for _, success in results if success)
        logger.info(f"Broadcast sent to {successful}/{len(results)} web clients")
