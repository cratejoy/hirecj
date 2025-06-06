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
from app.constants import WebSocketCloseCodes
from app.config import settings
from app.models import Message
from shared.user_identity import generate_user_id

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
                "oauth_complete",
                "debug_request",
                "workflow_transition",
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
                        # Get user_id from the WebSocket session
                        ws_session = self.sessions.get(conversation_id, {})
                        user_id = ws_session.get("user_id", "anonymous")
                        
                        logger.info(f"[SESSION_CREATE] WebSocket session data: {ws_session}")
                        logger.info(f"[SESSION_CREATE] Creating session with user_id={user_id}")
                        
                        session = self.session_manager.create_session(
                            merchant_name=merchant,
                            scenario_name=scenario,
                            workflow_name=workflow,
                            user_id=user_id if user_id != "anonymous" else None,
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
                
                # Check if starting onboarding workflow but already authenticated
                logger.info(f"[ALREADY_AUTH_CHECK] Checking authentication for {conversation_id}")
                logger.info(f"[ALREADY_AUTH_CHECK] workflow={workflow}, has_session={bool(session)}, "
                           f"user_id={getattr(session, 'user_id', 'NONE')}, "
                           f"existing_session={bool(existing_session)}")
                
                if workflow == "shopify_onboarding" and session and session.user_id:
                    # Get shop domain from session or OAuth metadata
                    shop_domain = "your store"
                    if hasattr(session, 'oauth_metadata') and session.oauth_metadata:
                        shop_domain = session.oauth_metadata.get('shop_domain', shop_domain)
                    elif hasattr(session, 'shop_domain'):
                        shop_domain = session.shop_domain
                    elif session.merchant_name and session.merchant_name != "onboarding_user":
                        shop_domain = session.merchant_name
                    
                    logger.info(f"[ALREADY_AUTH] Detected authenticated user {session.user_id} starting onboarding workflow, transitioning to ad_hoc_support")
                    
                    # Send transition notification
                    transition_msg = f"Existing session detected: {shop_domain} with workflow transition to ad_hoc_support"
                    
                    # Let CJ acknowledge before switching
                    response = await self.message_processor.process_message(
                        session=session,
                        message=transition_msg,
                        sender="system"
                    )
                    
                    # Send CJ's acknowledgment
                    if response:
                        response_data = {
                            "content": response if isinstance(response, str) else response.get("content", response),
                            "factCheckStatus": "available",
                            "timestamp": datetime.now().isoformat(),
                        }
                        await websocket.send_json(
                            {"type": "cj_message", "data": response_data}
                        )
                    
                    # Update workflow after CJ responds
                    success = self.session_manager.update_workflow(conversation_id, "ad_hoc_support")
                    if success:
                        # Notify the new workflow about the transition
                        arrival_msg = "Transitioned from shopify_onboarding workflow"
                        await self.message_processor.process_message(
                            session=session,
                            message=arrival_msg,
                            sender="system"
                        )
                        
                        # Update the workflow in conversation_data for frontend
                        conversation_data["workflow"] = "ad_hoc_support"
                        
                        # Notify frontend of workflow change
                        await websocket.send_json({
                            "type": "workflow_updated",
                            "data": {
                                "workflow": "ad_hoc_support",
                                "previous": "shopify_onboarding"
                            }
                        })
                    else:
                        logger.error(f"[ALREADY_AUTH] Failed to update workflow for {conversation_id}")

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
                if workflow in ["daily_briefing", "weekly_review", "ad_hoc_support", "shopify_onboarding", "support_daily"]:
                    # Get initial message based on workflow
                    if workflow == "daily_briefing":
                        response = await self.message_processor.process_message(
                            session=session,
                            message="Provide daily briefing using the get_support_dashboard tool to fetch current metrics",
                            sender="merchant",
                        )
                    elif workflow == "shopify_onboarding":
                        # For onboarding, we want CJ to start with a natural greeting
                        # The workflow details will guide CJ on what to say
                        logger.info(f"[SHOPIFY_ONBOARDING] Triggering initial greeting for conversation {conversation_id}")
                        # Use a clear instruction that won't appear in conversation history
                        # Similar to how daily_briefing uses "Provide daily briefing"
                        response = await self.message_processor.process_message(
                            session=session,
                            message="Begin onboarding introduction",
                            sender="merchant",
                        )
                        greeting_preview = response["content"][:100] if isinstance(response, dict) and "content" in response else str(response)[:100] if response else 'None'
                        logger.info(f"[SHOPIFY_ONBOARDING] Generated greeting: {greeting_preview}...")
                        
                        # Don't add the trigger message to conversation history
                        # Remove it so the conversation starts cleanly with CJ's greeting
                        if session.conversation.messages and session.conversation.messages[-2].content == "Begin onboarding introduction":
                            # Remove the trigger message (should be second to last, before CJ's response)
                            session.conversation.messages.pop(-2)
                            # Also remove from context window
                            if session.conversation.state.context_window and len(session.conversation.state.context_window) > 1:
                                session.conversation.state.context_window.pop(-2)
                    elif workflow == "support_daily":
                        response = await self.message_processor.process_message(
                            session=session,
                            message="Show me the most recent open support ticket using the get_recent_ticket_from_db tool",
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
                        # Handle structured response with UI elements
                        if isinstance(response, dict) and response.get("type") == "message_with_ui":
                            response_with_fact_check = {
                                "content": response["content"],
                                "factCheckStatus": "available",
                                "timestamp": datetime.now().isoformat(),
                                "ui_elements": response.get("ui_elements", [])
                            }
                            websocket_logger.info(
                                f"[WS_SEND] Sending initial CJ message with UI elements: content='{response_with_fact_check.get('content', '')[:100]}...' "
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
                update_data = data.get("data", {})
                session = self.sessions.get(conversation_id, {})
                session.update(update_data)
                self.sessions[conversation_id] = session
                
                # Log what we're updating
                logger.info(f"[SESSION_UPDATE] Updating session for {conversation_id}")
                logger.info(f"[SESSION_UPDATE] Data received: {update_data}")
                logger.info(f"[SESSION_UPDATE] New session state: {session}")
                
                # Also update the backend session if it exists
                backend_session = self.session_manager.get_session(conversation_id)
                if backend_session and update_data.get("user_id"):
                    logger.info(f"[SESSION_UPDATE] Updating backend session user_id to: {update_data['user_id']}")
                    backend_session.user_id = update_data["user_id"]

            elif message_type == "oauth_complete":
                # Handle OAuth completion from Shopify
                oauth_data = data.get("data", {})
                if not isinstance(oauth_data, dict):
                    await self._send_error(websocket, "Invalid oauth_complete data format")
                    return
                
                provider = oauth_data.get("provider")
                is_new = oauth_data.get("is_new", True)
                merchant_id = oauth_data.get("merchant_id")
                shop_domain = oauth_data.get("shop_domain")
                
                logger.info(f"[OAUTH_COMPLETE] Processing OAuth completion for {conversation_id}: "
                           f"provider={provider}, is_new={is_new}, merchant_id={merchant_id}, "
                           f"shop_domain={shop_domain}")
                
                # Get the current session
                session = self.session_manager.get_session(conversation_id)
                if not session:
                    logger.error(f"[OAUTH_ERROR] No session found for conversation {conversation_id}")
                    await self._send_error(websocket, "No active session for OAuth completion")
                    return
                
                # Update session with real merchant information
                if merchant_id and merchant_id != "onboarding_user":
                    logger.info(f"[OAUTH_UPDATE] Updating session merchant from {session.merchant_name} to {merchant_id}")
                    session.merchant_name = merchant_id
                    
                    # Update the conversation's merchant context
                    if hasattr(session.conversation, 'merchant_name'):
                        session.conversation.merchant_name = merchant_id
                
                # Generate user_id from shop_domain
                if shop_domain:
                    user_id = generate_user_id(shop_domain)
                    logger.info(f"[OAUTH_UPDATE] Generated user_id {user_id} from shop {shop_domain}")
                    
                    # Update WebSocket session
                    if conversation_id in self.sessions:
                        self.sessions[conversation_id]["user_id"] = user_id
                    
                    # Update SessionManager session
                    session.user_id = user_id
                    logger.info(f"[OAUTH_UPDATE] Updated session with user_id: {user_id}")
                
                # Store OAuth metadata in session for context
                if not hasattr(session, 'oauth_metadata'):
                    session.oauth_metadata = {}
                
                session.oauth_metadata.update({
                    "provider": provider,
                    "is_new_merchant": is_new,
                    "shop_domain": shop_domain,
                    "authenticated": True,
                    "authenticated_at": datetime.now().isoformat()
                })
                
                # Process the OAuth completion with CJ
                # Generate a response based on whether it's a new or returning merchant
                if is_new:
                    oauth_context = f"New Shopify merchant authenticated from {shop_domain}"
                else:
                    oauth_context = f"Returning Shopify merchant authenticated from {shop_domain}"
                
                logger.info(f"[OAUTH_CONTEXT] Processing with context: {oauth_context}")
                
                # Let CJ respond to the OAuth completion naturally
                response = await self.message_processor.process_message(
                    session=session,
                    message=oauth_context,
                    sender="system",  # System message so CJ knows it's context, not user input
                )
                
                # Send CJ's response
                if response:
                    # Handle structured response with UI elements
                    if isinstance(response, dict) and response.get("type") == "message_with_ui":
                        response_data = {
                            "content": response["content"],
                            "factCheckStatus": "available",
                            "timestamp": datetime.now().isoformat(),
                            "ui_elements": response.get("ui_elements", [])
                        }
                        logger.info(f"[OAUTH_RESPONSE] Sent CJ response with UI elements after OAuth: {response['content'][:100]}...")
                    else:
                        # Regular text response
                        response_data = {
                            "content": response,
                            "factCheckStatus": "available",
                            "timestamp": datetime.now().isoformat(),
                        }
                        logger.info(f"[OAUTH_RESPONSE] Sent CJ response after OAuth: {response[:100]}...")
                    
                    await websocket.send_json({
                        "type": "cj_message",
                        "data": response_data
                    })
                
                # Also send confirmation that OAuth was processed
                await websocket.send_json({
                    "type": "oauth_processed",
                    "data": {
                        "success": True,
                        "merchant_id": merchant_id,
                        "is_new": is_new
                    }
                })

            elif message_type == "debug_request":
                # Handle debug information requests
                debug_type = data.get("data", {}).get("type", "snapshot")
                session = self.session_manager.get_session(conversation_id)
                
                if not session:
                    await websocket.send_json({
                        "type": "debug_response",
                        "data": {
                            "error": "No active session",
                            "conversation_id": conversation_id
                        }
                    })
                    return
                
                debug_data = {}
                
                try:
                    if debug_type == "snapshot" or debug_type == "session":
                        # Session information
                        debug_data["session"] = {
                            "id": getattr(session, 'id', conversation_id),
                            "merchant": getattr(session, 'merchant_name', 'unknown'),
                            "workflow": getattr(session, 'workflow_name', 'unknown'),
                            "scenario": getattr(session, 'scenario_name', 'unknown'),
                            "connected_at": None,  # Sessions don't track start time
                            "message_count": len(session.conversation.messages) if hasattr(session, 'conversation') else 0,
                            "context_window_size": 0,  # Not tracked in sessions
                        }
                        
                        # Add OAuth metadata if available
                        if hasattr(session, 'oauth_metadata'):
                            debug_data["session"]["oauth_metadata"] = session.oauth_metadata
                    
                    if debug_type == "snapshot" or debug_type == "state":
                        # CJ state information
                        debug_data["state"] = {
                            "model": "claude-3.5-sonnet",  # Default model
                            "temperature": 0.3,  # Default temperature from config
                            "tools_available": 0,  # Tools not exposed in session
                            "memory_facts": 0,  # Memory not directly accessible
                        }
                        
                        # Check if session has merchant memory
                        if session.user_id:
                            # Get fact count from database
                            from shared.user_identity import get_user_facts
                            user_facts = get_user_facts(session.user_id)
                            debug_data["state"]["memory_facts"] = len(user_facts)
                    
                    if debug_type == "snapshot" or debug_type == "metrics":
                        # Metrics if available
                        debug_data["metrics"] = getattr(session, 'metrics', {})
                    
                    if debug_type == "prompts":
                        # Recent prompts (last 5)
                        recent_prompts = []
                        if hasattr(session, 'conversation') and hasattr(session.conversation, 'messages'):
                            for msg in session.conversation.messages[-10:]:  # Check last 10 messages
                                if hasattr(msg, 'sender') and hasattr(msg, 'content'):
                                    if msg.sender.lower() == "system" or "prompt" in msg.content.lower():
                                        recent_prompts.append({
                                            "timestamp": getattr(msg, 'timestamp', 'unknown'),
                                            "content": msg.content[:500]  # First 500 chars
                                        })
                        debug_data["prompts"] = recent_prompts[-5:]  # Last 5 prompts
                    
                    # Send debug response
                    await websocket.send_json({
                        "type": "debug_response",
                        "data": debug_data
                    })
                    
                    logger.info(f"[DEBUG_REQUEST] Sent debug info for {conversation_id}: type={debug_type}")
                    
                except Exception as e:
                    logger.error(f"[DEBUG_ERROR] Failed to generate debug info: {str(e)}")
                    await websocket.send_json({
                        "type": "debug_response",
                        "data": {
                            "error": f"Failed to generate debug info: {str(e)}",
                            "conversation_id": conversation_id
                        }
                    })
            
            elif message_type == "workflow_transition":
                # Handle workflow transition requests
                transition_data = data.get("data", {})
                if not isinstance(transition_data, dict):
                    await self._send_error(websocket, "Invalid workflow_transition data format")
                    return
                
                new_workflow = transition_data.get("new_workflow")
                if not new_workflow:
                    await self._send_error(websocket, "Missing new_workflow in transition request")
                    return
                
                # Get current session
                session = self.session_manager.get_session(conversation_id)
                if not session:
                    await self._send_error(websocket, "No active session for workflow transition")
                    return
                
                # Validate workflow exists
                from app.workflows.loader import WorkflowLoader
                workflow_loader = WorkflowLoader()
                if not workflow_loader.workflow_exists(new_workflow):
                    await self._send_error(websocket, f"Unknown workflow: {new_workflow}")
                    return
                
                # Get current workflow for context
                current_workflow = session.conversation.workflow
                
                # Don't transition if already in target workflow
                if current_workflow == new_workflow:
                    logger.info(f"[WORKFLOW] Already in {new_workflow}, skipping transition")
                    await websocket.send_json({
                        "type": "workflow_transition_complete",
                        "data": {
                            "workflow": new_workflow,
                            "message": "Already in requested workflow"
                        }
                    })
                    return
                
                logger.info(f"[WORKFLOW_TRANSITION] Transitioning {conversation_id} from {current_workflow} to {new_workflow}")
                
                # Send transition announcement to current workflow
                if transition_data.get("user_initiated"):
                    transition_msg = f"User requested transition to {new_workflow} workflow"
                else:
                    transition_msg = f"System requested transition to {new_workflow} workflow"
                
                # Let current workflow say goodbye
                farewell_response = await self.message_processor.process_message(
                    session=session,
                    message=transition_msg,
                    sender="system"
                )
                
                # Send farewell message if any
                if farewell_response:
                    response_data = {
                        "content": farewell_response if isinstance(farewell_response, str) else farewell_response.get("content", farewell_response),
                        "factCheckStatus": "available",
                        "timestamp": datetime.now().isoformat(),
                    }
                    await websocket.send_json(
                        {"type": "cj_message", "data": response_data}
                    )
                
                # Update the workflow
                success = self.session_manager.update_workflow(conversation_id, new_workflow)
                if not success:
                    await self._send_error(websocket, "Failed to update workflow")
                    return
                
                # Let new workflow say hello
                arrival_msg = f"Transitioned from {current_workflow} workflow"
                await self.message_processor.process_message(
                    session=session,
                    message=arrival_msg,
                    sender="system"
                )
                
                # Notify frontend of successful transition
                await websocket.send_json({
                    "type": "workflow_updated",
                    "data": {
                        "workflow": new_workflow,
                        "previous": current_workflow
                    }
                })
                
                logger.info(f"[WORKFLOW_TRANSITION] Successfully transitioned {conversation_id} to {new_workflow}")

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
