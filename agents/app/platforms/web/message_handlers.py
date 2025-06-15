"""WebSocket message routing and coordination."""

from typing import Dict, Any, TYPE_CHECKING, Union

from fastapi import WebSocket

from shared.logging_config import get_logger
from shared.protocol.models import (
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
)

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
        self, websocket: WebSocket, conversation_id: str, message: StartConversationMsg
    ):
        """Route to session handler."""
        await self.session.handle_start_conversation(websocket, conversation_id, message)


    async def handle_logout(
        self, websocket: WebSocket, conversation_id: str, message: LogoutMsg
    ):
        """Route to session handler."""
        await self.session.handle_logout(websocket, conversation_id, message)

    # Route to conversation handlers
    async def handle_message(
        self, websocket: WebSocket, conversation_id: str, message: UserMsg
    ):
        """Route to conversation handler."""
        await self.conversation.handle_message(websocket, conversation_id, message)

    async def handle_fact_check(
        self, websocket: WebSocket, conversation_id: str, message: FactCheckMsg
    ):
        """Route to conversation handler."""
        await self.conversation.handle_fact_check(websocket, conversation_id, message)

    async def handle_end_conversation(
        self, websocket: WebSocket, conversation_id: str, message: EndConversationMsg
    ):
        """Route to conversation handler."""
        await self.conversation.handle_end_conversation(websocket, conversation_id, message)

    # Route to workflow handlers
    async def handle_workflow_transition(
        self, websocket: WebSocket, conversation_id: str, message: WorkflowTransitionMsg
    ):
        """Route to workflow handler."""
        await self.workflow.handle_workflow_transition(websocket, conversation_id, message)

    # Route to utility handlers
    async def handle_ping(
        self, websocket: WebSocket, conversation_id: str, message: PingMsg
    ):
        """Route to utility handler."""
        await self.utility.handle_ping(websocket, conversation_id, message)

    async def handle_debug_request(
        self, websocket: WebSocket, conversation_id: str, message: DebugRequestMsg
    ):
        """Route to utility handler."""
        await self.utility.handle_debug_request(websocket, conversation_id, message)
    
    async def handle_system_event(
        self, websocket: WebSocket, conversation_id: str, message: SystemEventMsg
    ):
        """Route to utility handler."""
        await self.utility.handle_system_event(websocket, conversation_id, message)
    
    async def handle_oauth_complete(
        self, websocket: WebSocket, conversation_id: str, message: OAuthCompleteMsg
    ):
        """Route to session handler."""
        await self.session.handle_oauth_complete(websocket, conversation_id, message)
