"""Conversation-related message handlers."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
import asyncio

from fastapi import WebSocket, BackgroundTasks

from app.logging_config import get_logger
from app.config import settings
from shared.protocol.models import (
    UserMsg,
    EndConversationMsg,
    FactCheckMsg,
    CJMessageMsg,
    CJMessageData,
    SystemMsg,
    FactCheckStartedMsg,
    FactCheckStartedData,
    FactCheckCompleteMsg,
    FactCheckCompleteData,
    FactCheckErrorMsg,
    FactCheckErrorData,
)

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class ConversationHandlers:
    """Handles conversation-related WebSocket messages."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform

    async def handle_message(
        self, websocket: WebSocket, conversation_id: str, message: UserMsg
    ):
        """Handle regular message."""
        text = message.text.strip()
        
        websocket_logger.info(
            f"[MESSAGE_DEBUG] Processing message - conversation_id: {conversation_id}, text: '{text}'"
        )

        # Validate message
        if not text:
            await self.platform.send_error(websocket, "Empty message")
            return

        if len(text) > self.platform.max_message_length:
            await self.platform.send_error(
                websocket,
                f"Message too long (max {self.platform.max_message_length} chars)",
            )
            return

        # Get or create session
        websocket_logger.info(
            f"[SESSION_DEBUG] Attempting to get session for message - conversation_id: {conversation_id}"
        )
        session = self.platform.session_manager.get_session(conversation_id)
        if not session:
            websocket_logger.error(
                f"[SESSION_ERROR] No session found for conversation_id: {conversation_id}"
            )
            await self.platform.send_error(
                websocket,
                "No active session. Please start a conversation first using 'start_conversation' message type.",
            )
            return
        else:
            websocket_logger.info(
                f"[SESSION_DEBUG] Found existing session - conversation_id: {conversation_id}, messages: {len(session.conversation.messages)}, context_window: {len(session.conversation.state.context_window)}"
            )

        # Process message with CrewAI
        response = await self.platform.message_processor.process_message(
            session=session, message=text, sender="merchant"
        )

        # Handle structured response with UI elements
        if isinstance(response, dict) and response.get("type") == "message_with_ui":
            # Send response with UI elements
            cj_msg = CJMessageMsg(
                type="cj_message",
                data=CJMessageData(
                    content=response["content"],
                    factCheckStatus="available",
                    timestamp=datetime.now(),
                    ui_elements=response.get("ui_elements", [])
                )
            )
            websocket_logger.info(
                f"[WS_SEND] Sending CJ message with UI elements: content='{cj_msg.data.content[:100]}...' "
                f"ui_elements={len(cj_msg.data.ui_elements or [])} full_data={cj_msg.model_dump()}"
            )
        else:
            # Regular text response
            cj_msg = CJMessageMsg(
                type="cj_message",
                data=CJMessageData(
                    content=response,
                    factCheckStatus="available",
                    timestamp=datetime.now()
                )
            )
            websocket_logger.info(
                f"[WS_SEND] Sending CJ message response: content='{cj_msg.data.content[:100]}...' "
                f"full_data={cj_msg.model_dump()}"
            )
        
        # Check for suspicious content
        if cj_msg.data.content == "0" or cj_msg.data.content == 0:
            websocket_logger.error(
                f"[WS_ERROR] Sending message with content '0': {cj_msg.model_dump()}"
            )
        await self.platform.send_validated_message(websocket, cj_msg)

    async def handle_fact_check(
        self, websocket: WebSocket, conversation_id: str, message: FactCheckMsg
    ):
        """Handle fact-check request."""
        message_index = message.data.messageIndex
        force_refresh = message.data.forceRefresh

        # Get current session
        session = self.platform.session_manager.get_session(conversation_id)
        if session:
            # Import fact-checking API functions
            from app.api.routes.fact_checking import (
                create_fact_check,
                FactCheckRequest,
            )

            # Create background tasks handler
            background_tasks = BackgroundTasks()

            # Create fact check request
            request = FactCheckRequest(
                merchant_name=session.merchant_name,
                scenario_name=session.scenario_name,
                force_refresh=force_refresh,
            )

            # Start fact-checking
            try:
                await create_fact_check(
                    conversation_id=conversation_id,
                    message_index=message_index,
                    request=request,
                    background_tasks=background_tasks,
                )

                # Send initial status
                fact_check_started = FactCheckStartedMsg(
                    type="fact_check_started",
                    data=FactCheckStartedData(
                        messageIndex=message_index,
                        status="checking"
                    )
                )
                await self.platform.send_validated_message(websocket, fact_check_started)

                # Create a task to poll for completion and send updates
                asyncio.create_task(
                    self._monitor_fact_check(
                        websocket, conversation_id, message_index
                    )
                )

            except Exception as e:
                fact_check_error = FactCheckErrorMsg(
                    type="fact_check_error",
                    data=FactCheckErrorData(
                        messageIndex=message_index,
                        error=str(e)
                    )
                )
                await self.platform.send_validated_message(websocket, fact_check_error)

    async def handle_end_conversation(
        self, websocket: WebSocket, conversation_id: str, message: EndConversationMsg
    ):
        """Handle end_conversation message."""
        # Save conversation
        session = self.platform.session_manager.get_session(conversation_id)
        if session:
            self.platform.conversation_storage.save_session(session)
            
            # Real-time extraction already handles fact extraction
            logger.info(f"[CONVERSATION] Conversation {conversation_id} ended. Facts already extracted in real-time.")
                    
        system_msg = SystemMsg(
            type="system",
            text="Conversation saved. Goodbye!"
        )
        await self.platform.send_validated_message(websocket, system_msg)
        await websocket.close()

    async def _monitor_fact_check(
        self, websocket: WebSocket, conversation_id: str, message_index: int
    ) -> None:
        """Monitor fact-check progress and send completion notification."""
        from app.api.routes.fact_checking import _fact_check_results

        max_wait = settings.websocket_response_timeout
        check_interval = settings.websocket_check_interval
        elapsed = 0

        while elapsed < max_wait:
            # Check if result is available
            if conversation_id in _fact_check_results:
                if message_index in _fact_check_results[conversation_id]:
                    result = _fact_check_results[conversation_id][message_index]

                    # Send completion message
                    try:
                        fact_check_complete = FactCheckCompleteMsg(
                            type="fact_check_complete",
                            data=FactCheckCompleteData(
                                messageIndex=message_index,
                                result={
                                    "overall_status": result.overall_status,
                                    "claim_count": len(result.claims),
                                    "execution_time": getattr(
                                        result, "execution_time", 0
                                    ),
                                }
                            )
                        )
                        await self.platform.send_validated_message(websocket, fact_check_complete)
                    except Exception:
                        # WebSocket might be closed
                        pass
                    return

            await asyncio.sleep(check_interval)
            elapsed += check_interval

        # Timeout - fact check is taking too long
        try:
            fact_check_error = FactCheckErrorMsg(
                type="fact_check_error",
                data=FactCheckErrorData(
                    messageIndex=message_index,
                    error="Fact check timed out after 30 seconds"
                )
            )
            await self.platform.send_validated_message(websocket, fact_check_error)
        except Exception:
            pass
