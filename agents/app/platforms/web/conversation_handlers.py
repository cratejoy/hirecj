"""Conversation-related message handlers."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
import asyncio

from fastapi import WebSocket, BackgroundTasks

from app.logging_config import get_logger
from app.config import settings

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class ConversationHandlers:
    """Handles conversation-related WebSocket messages."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform

    async def handle_message(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle regular message."""
        text = data.get("text", "").strip()
        merchant = data.get("merchant_id", "demo_merchant")
        scenario = data.get("scenario", "normal_day")

        websocket_logger.info(
            f"[MESSAGE_DEBUG] Processing message - conversation_id: {conversation_id}, text: '{text}', merchant: {merchant}, scenario: {scenario}"
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
            response_with_fact_check = {
                "content": response["content"],
                "factCheckStatus": "available",
                "timestamp": datetime.now().isoformat(),
                "ui_elements": response.get("ui_elements", [])
            }
            websocket_logger.info(
                f"[WS_SEND] Sending CJ message with UI elements: content='{response_with_fact_check.get('content', '')[:100]}...' "
                f"ui_elements={len(response_with_fact_check.get('ui_elements', []))} full_data={response_with_fact_check}"
            )
        else:
            # Regular text response
            response_with_fact_check = {
                "content": response,
                "factCheckStatus": "available",
                "timestamp": datetime.now().isoformat(),
            }
            websocket_logger.info(
                f"[WS_SEND] Sending CJ message response: content='{response_with_fact_check.get('content', '')[:100]}...' "
                f"full_data={response_with_fact_check}"
            )
        
        # Check for suspicious content
        if (
            response_with_fact_check.get("content") == "0"
            or response_with_fact_check.get("content") == 0
        ):
            websocket_logger.error(
                f"[WS_ERROR] Sending message with content '0': {response_with_fact_check}"
            )
        await websocket.send_json(
            {"type": "cj_message", "data": response_with_fact_check}
        )

    async def handle_fact_check(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle fact-check request."""
        fact_check_data = data.get("data", {})
        if not isinstance(fact_check_data, dict):
            await self.platform.send_error(websocket, "Invalid fact_check data format")
            return

        message_index = fact_check_data.get("messageIndex")
        if message_index is None:
            await self.platform.send_error(
                websocket, "messageIndex is required for fact_check"
            )
            return

        if not isinstance(message_index, int) or message_index < 0:
            await self.platform.send_error(
                websocket, "messageIndex must be a non-negative integer"
            )
            return

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
                force_refresh=fact_check_data.get("forceRefresh", False),
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
                await websocket.send_json(
                    {
                        "type": "fact_check_started",
                        "data": {
                            "messageIndex": message_index,
                            "status": "checking",
                        },
                    }
                )

                # Create a task to poll for completion and send updates
                asyncio.create_task(
                    self._monitor_fact_check(
                        websocket, conversation_id, message_index
                    )
                )

            except Exception as e:
                await websocket.send_json(
                    {
                        "type": "fact_check_error",
                        "data": {
                            "messageIndex": message_index,
                            "error": str(e),
                        },
                    }
                )

    async def handle_end_conversation(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle end_conversation message."""
        # Save conversation
        session = self.platform.session_manager.get_session(conversation_id)
        if session:
            self.platform.conversation_storage.save_session(session)
            
            # Real-time extraction already handles fact extraction
            logger.info(f"[CONVERSATION] Conversation {conversation_id} ended. Facts already extracted in real-time.")
                    
        await websocket.send_json(
            {"type": "system", "text": "Conversation saved. Goodbye!"}
        )
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
                        await websocket.send_json(
                            {
                                "type": "fact_check_complete",
                                "data": {
                                    "messageIndex": message_index,
                                    "result": {
                                        "overall_status": result.overall_status,
                                        "claim_count": len(result.claims),
                                        "execution_time": getattr(
                                            result, "execution_time", 0
                                        ),
                                    },
                                },
                            }
                        )
                    except Exception:
                        # WebSocket might be closed
                        pass
                    return

            await asyncio.sleep(check_interval)
            elapsed += check_interval

        # Timeout - fact check is taking too long
        try:
            await websocket.send_json(
                {
                    "type": "fact_check_error",
                    "data": {
                        "messageIndex": message_index,
                        "error": "Fact check timed out after 30 seconds",
                    },
                }
            )
        except Exception:
            pass
