"""Individual message type handlers for web platform."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
import asyncio

from fastapi import WebSocket, BackgroundTasks

from app.logging_config import get_logger
from app.models import Message
from app.constants import WebSocketCloseCodes, WorkflowConstants
from app.config import settings

from .oauth_handler import OAuthHandler
from .session_handler import SessionHandler

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class MessageHandlers:
    """Handles different WebSocket message types."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform
        self.oauth_handler = OAuthHandler(platform)
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

        workflow = start_data.get("workflow", "ad_hoc_support")
        
        # Get workflow requirements
        workflow_data = self.platform.workflow_loader.get_workflow(workflow)
        requirements = workflow_data.get('requirements', {})
        
        # Use requirements to determine defaults and validation
        if not requirements.get('merchant', True):
            # Workflow doesn't require merchant
            merchant = start_data.get("merchant_id", "onboarding_user")
        else:
            # Workflow requires merchant
            merchant = start_data.get("merchant_id")
            if not merchant:
                await self.platform.send_error(websocket, "Merchant ID required for this workflow")
                return
        
        if not requirements.get('scenario', True):
            # Workflow doesn't require scenario
            scenario = start_data.get("scenario", "default")
        else:
            # Workflow requires scenario
            scenario = start_data.get("scenario")
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
        else:
            logger.info(
                f"[NEW_SESSION] Creating new session for {conversation_id}"
            )
            # Create conversation session
            try:
                ws_session = self.platform.sessions.get(conversation_id, {})
                session = await self.session_handler.create_session(
                    conversation_id, merchant, scenario, workflow, ws_session
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
        
        # Check for OAuth completion status
        oauth_data = await self.oauth_handler.check_oauth_completion(conversation_id)
        if oauth_data:
            await self.oauth_handler.process_oauth_completion(websocket, session, oauth_data)
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
        
        # Check if starting onboarding workflow but already authenticated
        await self._check_already_authenticated(
            websocket, conversation_id, session, workflow, requirements, conversation_data
        )

        # Register progress callback
        await self._setup_progress_callback(websocket)

        # Handle initial workflow action
        await self._handle_initial_workflow_action(websocket, session, workflow)

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

    async def handle_ping(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle ping/pong for connection keepalive."""
        await websocket.send_json(
            {"type": "pong", "timestamp": datetime.now().isoformat()}
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

    async def handle_session_update(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle session_update message."""
        update_data = data.get("data", {})
        
        # Validate frontend is NOT sending user_id (it shouldn't)
        if "user_id" in update_data:
            logger.warning(f"[SESSION_UPDATE] Frontend sent user_id - this is incorrect! "
                         f"User IDs must be generated by backend only.")
        
        # Store raw data in WebSocket session for later use
        session = self.platform.sessions.get(conversation_id, {})
        session.update(update_data)
        self.platform.sessions[conversation_id] = session
        
        logger.info(f"[SESSION_UPDATE] Stored merchant data for {conversation_id}")
        logger.info(f"[SESSION_UPDATE] Data: merchant_id={update_data.get('merchant_id')}, "
                   f"shop_domain={update_data.get('shop_domain')}")

    async def handle_debug_request(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle debug_request message."""
        debug_type = data.get("data", {}).get("type", "snapshot")
        session = self.platform.session_manager.get_session(conversation_id)
        
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

    async def handle_workflow_transition(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle workflow_transition message."""
        transition_data = data.get("data", {})
        if not isinstance(transition_data, dict):
            await self.platform.send_error(websocket, "Invalid workflow_transition data format")
            return
        
        new_workflow = transition_data.get("new_workflow")
        if not new_workflow:
            await self.platform.send_error(websocket, "Missing new_workflow in transition request")
            return
        
        # Get current session
        session = self.platform.session_manager.get_session(conversation_id)
        if not session:
            await self.platform.send_error(websocket, "No active session for workflow transition")
            return
        
        # Validate workflow exists
        if not self.platform.workflow_loader.workflow_exists(new_workflow):
            await self.platform.send_error(websocket, f"Unknown workflow: {new_workflow}")
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
        
        # IMMEDIATE: Update the workflow first for instant feedback
        success = self.platform.session_manager.update_workflow(conversation_id, new_workflow)
        if not success:
            await self.platform.send_error(websocket, "Failed to update workflow")
            return
        
        # IMMEDIATE: Notify frontend of successful transition
        await websocket.send_json({
            "type": "workflow_updated",
            "data": {
                "workflow": new_workflow,
                "previous": current_workflow
            }
        })
        
        logger.info(f"[WORKFLOW_TRANSITION] Successfully transitioned {conversation_id} to {new_workflow}")
        
        # ASYNC: Handle farewell and arrival messages without blocking
        async def handle_transition_messages():
            try:
                # Prepare transition message
                if transition_data.get("user_initiated"):
                    transition_msg = f"User requested transition to {new_workflow} workflow"
                else:
                    transition_msg = f"System requested transition to {new_workflow} workflow"
                
                # Let current workflow say goodbye
                logger.info(f"[WORKFLOW_TRANSITION] Generating farewell from {current_workflow}")
                farewell_response = await self.platform.message_processor.process_message(
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
                
                # Let new workflow say hello
                logger.info(f"[WORKFLOW_TRANSITION] Generating arrival for {new_workflow}")
                arrival_msg = f"Transitioned from {current_workflow} workflow"
                arrival_response = await self.platform.message_processor.process_message(
                    session=session,
                    message=arrival_msg,
                    sender="system"
                )
                
                # Send arrival message if any
                if arrival_response:
                    response_data = {
                        "content": arrival_response if isinstance(arrival_response, str) else arrival_response.get("content", arrival_response),
                        "factCheckStatus": "available",
                        "timestamp": datetime.now().isoformat(),
                    }
                    await websocket.send_json(
                        {"type": "cj_message", "data": response_data}
                    )
                    
            except Exception as e:
                logger.error(f"[WORKFLOW_TRANSITION] Error handling transition messages: {e}")
        
        # Create async task to handle messages without blocking
        asyncio.create_task(handle_transition_messages())

    async def _check_already_authenticated(
        self,
        websocket: WebSocket,
        conversation_id: str,
        session: Any,
        workflow: str,
        requirements: Dict[str, Any],
        conversation_data: Dict[str, Any]
    ):
        """Check if user is already authenticated but starting a non-auth workflow."""
        logger.info(f"[ALREADY_AUTH_CHECK] Checking authentication for {conversation_id}")
        logger.info(f"[ALREADY_AUTH_CHECK] workflow={workflow}, has_session={bool(session)}, "
                   f"user_id={getattr(session, 'user_id', 'NONE')}")
        
        # Check for workflow transitions
        workflow_behavior = self.platform.workflow_loader.get_workflow_behavior(workflow)
        transitions = workflow_behavior.get('transitions', {})
        
        # Check if user is already authenticated but trying a workflow that doesn't require auth
        if not requirements.get('authentication', True) and session and session.user_id:
            transition_config = transitions.get('already_authenticated')
            if transition_config:
                target_workflow = transition_config.get('target_workflow', 'ad_hoc_support')
                transition_message = transition_config.get('message')
                
                # Get shop domain from session
                shop_domain = self.session_handler.get_shop_domain(session)
                
                # Handle the transition
                success = await self.session_handler.handle_workflow_transition(
                    conversation_id, session, workflow, target_workflow,
                    transition_message, shop_domain
                )
                
                if success:
                    # Update conversation data for frontend
                    conversation_data["workflow"] = target_workflow
                    
                    # Notify frontend of workflow change
                    await websocket.send_json({
                        "type": "workflow_updated",
                        "data": {
                            "workflow": target_workflow,
                            "previous": workflow
                        }
                    })
                    
                    logger.info(f"[ALREADY_AUTH] Skipping {workflow} initial action - user transitioned to {target_workflow}")
                    return True
        
        return False

    async def _setup_progress_callback(self, websocket: WebSocket):
        """Setup progress callback for WebSocket."""
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
        self.platform.message_processor.clear_progress_callbacks()
        self.platform.message_processor.on_progress(progress_callback)

    async def _handle_initial_workflow_action(
        self, websocket: WebSocket, session: Any, workflow: str
    ):
        """Handle initial workflow action."""
        # Get workflow behavior
        workflow_behavior = self.platform.workflow_loader.get_workflow_behavior(workflow)
        initial_action = workflow_behavior.get('initial_action')
        
        if initial_action:
            action_type = initial_action.get('type')
            
            if action_type == 'process_message':
                response = await self.platform.message_processor.process_message(
                    session=session,
                    message=initial_action.get('message'),
                    sender=initial_action.get('sender', 'merchant'),
                )
                
                # Handle cleanup if specified
                if initial_action.get('cleanup_trigger') and session.conversation.messages:
                    trigger_message = initial_action.get('message')
                    if (len(session.conversation.messages) >= 2 and 
                        session.conversation.messages[-2].content == trigger_message):
                        session.conversation.messages.pop(-2)
                        if session.conversation.state.context_window and len(session.conversation.state.context_window) > 1:
                            session.conversation.state.context_window.pop(-2)
            
            elif action_type == 'static_message':
                response = initial_action.get('content')
                
                if initial_action.get('add_to_history', False):
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
