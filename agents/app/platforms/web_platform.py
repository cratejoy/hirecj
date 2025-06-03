"""
Web Platform Implementation

Handles WebSocket connections for the web chat interface.
This is the primary platform for Demo 1.
"""

from typing import Dict, Any
from datetime import datetime
import uuid
import asyncio

from fastapi import WebSocket

from .base import (
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
from app.services.fact_extractor import FactExtractor
from app.services.merchant_memory import MerchantMemoryService
from app.constants import WebSocketCloseCodes
from app.config import settings
from app.models import Message

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
            "max_message_length", settings.max_message_length
        )
        self.session_timeout = config.get(
            "session_timeout", settings.session_cleanup_timeout
        )

        # Initialize managers
        self.session_manager = SessionManager()
        self.message_processor = MessageProcessor()
        self.conversation_storage = ConversationStorage()

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

    async def handle_websocket_connection(self, websocket, conversation_id: str = None):
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
        self.connections[conversation_id] = websocket

        # Initialize session
        self.sessions[conversation_id] = {
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
            # Extract facts on disconnect if session exists
            if conversation_id in self.session_manager._sessions:
                session = self.session_manager._sessions[conversation_id]
                
                # Only extract facts if conversation has messages
                if session.merchant_memory and session.conversation.messages:
                    try:
                        logger.info(f"[FACT_EXTRACTION] Processing conversation {conversation_id} on disconnect")
                        fact_extractor = FactExtractor()
                        new_facts = await fact_extractor.extract_and_add_facts(
                            session.conversation, 
                            session.merchant_memory
                        )
                        
                        if new_facts:
                            # Save updated memory
                            memory_service = MerchantMemoryService()
                            memory_service.save_memory(session.merchant_memory)
                            logger.info(f"[FACT_EXTRACTION] Extracted {len(new_facts)} facts on disconnect")
                        else:
                            logger.info(f"[FACT_EXTRACTION] No new facts extracted on disconnect")
                    except Exception as e:
                        logger.error(f"[FACT_EXTRACTION] Error extracting facts on disconnect: {e}", exc_info=True)
                
                # Save session
                self.conversation_storage.save_session(session)
                logger.info(f"[CONVERSATION] Saved conversation {conversation_id} on disconnect")
            
            # Cleanup on disconnect
            self.connections.pop(conversation_id, None)
            logger.info(f"WebSocket connection {conversation_id} disconnected")

    async def _handle_websocket_message(
        self, websocket, conversation_id: str, data: Dict[str, Any]
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
                await self._send_error(
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
            ]
            if message_type not in valid_types:
                logger.warning(
                    f"Invalid message type from {conversation_id}: {message_type}"
                )
                await self._send_error(
                    websocket, f"Invalid message type: {message_type}"
                )
                return

            if message_type == "start_conversation":
                # Initialize conversation with CrewAI
                start_data = data.get("data", {})
                if not isinstance(start_data, dict):
                    await self._send_error(
                        websocket, "Invalid start_conversation data format"
                    )
                    return

                # For onboarding workflow, we don't require merchant/scenario upfront
                workflow = start_data.get("workflow")
                if workflow == "shopify_onboarding":
                    merchant = start_data.get("merchant_id", "onboarding_user")
                    scenario = start_data.get("scenario", "onboarding")
                else:
                    merchant = start_data.get("merchant_id", "demo_merchant")
                    scenario = start_data.get("scenario", "normal_day")
                # cj_version = start_data.get("cj_version", settings.default_cj_version)  # TODO: Pass to session when supported

                # Check for existing session first
                logger.info(
                    f"[SESSION_CHECK] Looking for existing session: {conversation_id}"
                )
                # Check for existing session
                existing_session = self.session_manager.get_session(conversation_id)
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
                        session = self.session_manager.create_session(
                            merchant_name=merchant,
                            scenario_name=scenario,
                            workflow_name=workflow,
                        )
                        # Store the session with the conversation_id
                        self.session_manager._sessions[conversation_id] = session
                    except ValueError as e:
                        # Handle missing universe or other critical errors
                        error_msg = str(e)
                        logger.error(f"Failed to start conversation: {error_msg}")
                        await self._send_error(
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
                        await self._send_error(
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

                # Register progress callback for this WebSocket connection (all workflows)
                async def progress_callback(update):
                    # Transform progress event to WebSocket message format
                    if update and update.get("type") == "thinking":
                        ws_message = {
                            "type": "cj_thinking",
                            "data": update.get("data", {}),
                        }
                        websocket_logger.info(
                            f"[WS_PROGRESS] Sending progress update: {ws_message}"
                        )
                        try:
                            await websocket.send_json(ws_message)
                        except Exception as e:
                            # WebSocket might be closed, ignore
                            logger.debug(f"Could not send progress update: {e}")

                # Clear any old callbacks and register new one
                self.message_processor.clear_progress_callbacks()
                self.message_processor.on_progress(progress_callback)

                # If workflow starts with CJ, generate initial message
                if workflow in ["daily_briefing", "weekly_review", "ad_hoc_support"]:
                    # Get initial message based on workflow
                    if workflow == "daily_briefing":
                        response = await self.message_processor.process_message(
                            session=session,
                            message="Provide daily briefing",
                            sender="merchant",
                        )
                    elif workflow == "ad_hoc_support":
                        response = (
                            "Hey boss, what's up? 👋 Need help with anything today?"
                        )

                        # Add greeting to conversation history so it's part of future context
                        greeting_msg = Message(
                            timestamp=datetime.utcnow(),
                            sender="CJ",
                            content=response,
                        )
                        session.conversation.add_message(greeting_msg)
                    else:
                        response = None

                    if response:
                        # Create response message
                        response_with_fact_check = {
                            "content": response,
                            "factCheckStatus": "available",
                            "timestamp": datetime.now().isoformat(),
                        }
                        websocket_logger.info(
                            f"[WS_SEND] Sending initial CJ message: content='{response_with_fact_check.get('content', '')[:100]}...' "
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

            elif message_type == "message":
                text = data.get("text", "").strip()
                merchant = data.get("merchant_id", "demo_merchant")
                scenario = data.get("scenario", "normal_day")

                websocket_logger.info(
                    f"[MESSAGE_DEBUG] Processing message - conversation_id: {conversation_id}, text: '{text}', merchant: {merchant}, scenario: {scenario}"
                )

                # Validate message
                if not text:
                    await self._send_error(websocket, "Empty message")
                    return

                if len(text) > self.max_message_length:
                    await self._send_error(
                        websocket,
                        f"Message too long (max {self.max_message_length} chars)",
                    )
                    return

                # Get or create session
                websocket_logger.info(
                    f"[SESSION_DEBUG] Attempting to get session for message - conversation_id: {conversation_id}"
                )
                session = self.session_manager.get_session(conversation_id)
                if not session:
                    websocket_logger.error(
                        f"[SESSION_ERROR] No session found for conversation_id: {conversation_id}"
                    )
                    await self._send_error(
                        websocket,
                        "No active session. Please start a conversation first using 'start_conversation' message type.",
                    )
                    return
                else:
                    websocket_logger.info(
                        f"[SESSION_DEBUG] Found existing session - conversation_id: {conversation_id}, messages: {len(session.conversation.messages)}, context_window: {len(session.conversation.state.context_window)}"
                    )

                # Process message with CrewAI
                response = await self.message_processor.process_message(
                    session=session, message=text, sender="merchant"
                )

                # Send response with fact-check status
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

            elif message_type == "fact_check":
                # Handle fact-check request
                fact_check_data = data.get("data", {})
                if not isinstance(fact_check_data, dict):
                    await self._send_error(websocket, "Invalid fact_check data format")
                    return

                message_index = fact_check_data.get("messageIndex")
                if message_index is None:
                    await self._send_error(
                        websocket, "messageIndex is required for fact_check"
                    )
                    return

                if not isinstance(message_index, int) or message_index < 0:
                    await self._send_error(
                        websocket, "messageIndex must be a non-negative integer"
                    )
                    return

                if message_index is not None:
                    # Get current session
                    session = self.session_manager.get_session(conversation_id)
                    if session:
                        # Import fact-checking API functions
                        from app.api.routes.fact_checking import (
                            create_fact_check,
                            FactCheckRequest,
                        )
                        from fastapi import BackgroundTasks

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

                            # Background tasks are automatically handled by FastAPI
                            # No need to await them - they run in background

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

            elif message_type == "ping":
                # Handle ping/pong for connection keepalive
                await websocket.send_json(
                    {"type": "pong", "timestamp": datetime.now().isoformat()}
                )

            elif message_type == "end_conversation":
                # Save conversation and close connection
                # Save conversation
                if conversation_id in self.session_manager._sessions:
                    session = self.session_manager._sessions[conversation_id]
                    self.conversation_storage.save_session(session)
                    
                    # Real-time extraction already handles fact extraction
                    # No need to extract here - facts are extracted after each merchant message
                    logger.info(f"[CONVERSATION] Conversation {conversation_id} ended. Facts already extracted in real-time.")
                            
                await websocket.send_json(
                    {"type": "system", "text": "Conversation saved. Goodbye!"}
                )
                await websocket.close()

            elif message_type == "session_update":
                # Update session information
                session = self.sessions.get(conversation_id, {})
                session.update(data.get("data", {}))
                self.sessions[conversation_id] = session
                logger.debug(f"Updated session for {conversation_id}")

            else:
                logger.warning(f"Unknown message type from web client: {message_type}")

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

            await self._send_error(websocket, error_msg)

    async def _monitor_fact_check(
        self, websocket: WebSocket, conversation_id: str, message_index: int
    ) -> None:
        """Monitor fact-check progress and send completion notification."""
        from app.api.routes.fact_checking import _fact_check_results

        from app.config import settings

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

    async def _send_error(self, websocket, error_message: str):
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
