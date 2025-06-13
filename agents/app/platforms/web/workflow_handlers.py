"""Workflow-related message handlers."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
import asyncio

from fastapi import WebSocket

from app.logging_config import get_logger
from app.models import Message

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class WorkflowHandlers:
    """Handles workflow-related WebSocket messages."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform

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
                from .session_handler import SessionHandler
                session_handler = SessionHandler(self.platform)
                shop_domain = session_handler.get_shop_domain(session)
                
                # Handle the transition
                success = await session_handler.handle_workflow_transition(
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
