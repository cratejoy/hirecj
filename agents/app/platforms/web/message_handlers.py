"""WebSocket message routing and coordination."""

from typing import Dict, Any, TYPE_CHECKING

from fastapi import WebSocket

from app.logging_config import get_logger

from .conversation_handlers import ConversationHandlers
from .session_handlers import SessionHandlers
from .workflow_handlers import WorkflowHandlers
from .utility_handlers import UtilityHandlers

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)


class MessageHandlers:
    """Routes WebSocket messages to appropriate handlers."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform
        
        # Initialize domain-specific handlers
        self.conversation = ConversationHandlers(platform)
        self.session = SessionHandlers(platform)
        self.workflow = WorkflowHandlers(platform)
        self.utility = UtilityHandlers(platform)

    # Route to session handlers
    async def handle_start_conversation(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Route to session handler."""
        await self.session.handle_start_conversation(websocket, conversation_id, data)

    async def handle_session_update(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Route to session handler."""
        await self.session.handle_session_update(websocket, conversation_id, data)

    async def handle_logout(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Route to session handler."""
        await self.session.handle_logout(websocket, conversation_id, data)

    # Route to conversation handlers
    async def handle_message(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Route to conversation handler."""
        await self.conversation.handle_message(websocket, conversation_id, data)

    async def handle_fact_check(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Route to conversation handler."""
        await self.conversation.handle_fact_check(websocket, conversation_id, data)

    async def handle_end_conversation(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Route to conversation handler."""
        await self.conversation.handle_end_conversation(websocket, conversation_id, data)

    # Route to workflow handlers
    async def handle_workflow_transition(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Route to workflow handler."""
        await self.workflow.handle_workflow_transition(websocket, conversation_id, data)

    # Route to utility handlers
    async def handle_ping(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Route to utility handler."""
        await self.utility.handle_ping(websocket, conversation_id, data)

    async def handle_debug_request(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Route to utility handler."""
        await self.utility.handle_debug_request(websocket, conversation_id, data)
