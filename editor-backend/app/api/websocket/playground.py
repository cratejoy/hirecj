import asyncio
import json
import uuid
import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError
import websockets

# Import protocol models - the shared module is installed in the venv
# When running with uvicorn, the PYTHONPATH will be set correctly
if TYPE_CHECKING:
    from shared.protocol.models import (
        IncomingMessage, OutgoingMessage,
        PlaygroundStartMsg, StartConversationMsg, StartConversationData,
        PlaygroundResetMsg, EndConversationMsg,
        UserMsg, ErrorMsg
    )
else:
    try:
        from shared.protocol.models import (
            IncomingMessage, OutgoingMessage,
            PlaygroundStartMsg, StartConversationMsg, StartConversationData,
            PlaygroundResetMsg, EndConversationMsg,
            UserMsg, ErrorMsg
        )
    except ImportError:
        # This helps with development/testing - the actual app will have proper paths
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
        from shared.protocol.models import (
            IncomingMessage, OutgoingMessage,
            PlaygroundStartMsg, StartConversationMsg, StartConversationData,
            PlaygroundResetMsg, EndConversationMsg,
            UserMsg, ErrorMsg
        )

router = APIRouter()

# Validation adapters
incoming_adapter = TypeAdapter(IncomingMessage)
outgoing_adapter = TypeAdapter(OutgoingMessage)


async def transform_to_agent_message(msg: Any, session_id: str) -> Any:
    """Transform playground messages to agent service messages.
    
    Args:
        msg: The validated incoming message
        session_id: The playground session ID
        
    Returns:
        The transformed message ready for the agent service
    """
    if isinstance(msg, PlaygroundStartMsg):
        # Transform playground start to conversation start
        # For now, use test data - real implementation would load from files
        test_persona = {
            "id": msg.persona_id,
            "name": "Test Persona",
            "description": "A test user persona for playground",
        }
        
        test_scenario = {
            "id": msg.scenario_id,
            "name": "Test Scenario",
            "description": "A test scenario for playground",
        }
        
        # Create the start conversation data with test mode flag
        data = StartConversationData(
            workflow=msg.workflow,
            scenario_id=msg.scenario_id
        )
        
        # Create the start conversation message with test context
        start_msg = StartConversationMsg(
            type="start_conversation",
            data=data
        )
        
        # Add test mode fields as a dict that we'll merge
        # This is a workaround since StartConversationData doesn't have test_mode field
        start_msg_dict = start_msg.model_dump()
        start_msg_dict["data"]["test_mode"] = True
        start_msg_dict["data"]["test_context"] = {
            "persona": test_persona,
            "scenario": test_scenario,
            "trust_level": msg.trust_level,
            "session_id": session_id
        }
        
        return start_msg_dict
        
    elif isinstance(msg, PlaygroundResetMsg):
        # Transform reset to end conversation
        return EndConversationMsg(type="end_conversation")
        
    # Pass through other messages unchanged
    return msg


@router.websocket("/ws/playground")
async def playground_websocket(websocket: WebSocket):
    """Handle WebSocket connections from the editor playground."""
    await websocket.accept()
    session_id = f"playground_{uuid.uuid4()}"
    logging.info(f"Playground WebSocket connected: {session_id}")
    
    # Connect to agent service
    agent_ws_uri = "ws://localhost:8000/ws/chat"
    
    try:
        async with websockets.connect(agent_ws_uri) as agent_ws:
            logging.info(f"Connected to agent service for session {session_id}")
            
            # Bridge connections
            await bridge_connections(websocket, agent_ws, session_id)
            
    except websockets.exceptions.ConnectionRefusedError:
        logging.error(f"Failed to connect to agent service at {agent_ws_uri}")
        error_msg = ErrorMsg(
            type="error",
            text="Agent service unavailable"
        )
        await websocket.send_text(error_msg.model_dump_json())
        await websocket.close(code=1011, reason="Agent service unavailable")
        
    except WebSocketDisconnect:
        logging.info(f"Editor client disconnected: {session_id}")
        
    except Exception as e:
        logging.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.close(code=1011, reason=str(e))


async def bridge_connections(editor_ws: WebSocket, agent_ws, session_id: str):
    """Bridge messages between editor and agent WebSocket connections."""
    logging.info(f"Starting message bridge for session {session_id}")
    
    # Run both forwarding tasks concurrently
    # If either task completes (due to disconnection), cancel the other
    editor_task = asyncio.create_task(
        editor_to_agent(editor_ws, agent_ws, session_id)
    )
    agent_task = asyncio.create_task(
        agent_to_editor(editor_ws, agent_ws, session_id)
    )
    
    try:
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [editor_task, agent_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel the other task
        for task in pending:
            task.cancel()
            
    except Exception as e:
        logging.error(f"Bridge error for session {session_id}: {e}")
        
    finally:
        # Ensure both tasks are cleaned up
        for task in [editor_task, agent_task]:
            if not task.done():
                task.cancel()
                
        logging.info(f"Message bridge closed for session {session_id}")


async def editor_to_agent(editor_ws: WebSocket, agent_ws, session_id: str):
    """Forward messages from editor to agent service."""
    try:
        while True:
            # Receive message from editor
            raw_msg = await editor_ws.receive_text()
            logging.debug(f"[{session_id}] Editor -> Agent: {raw_msg}")
            
            try:
                # Validate the incoming message
                msg = incoming_adapter.validate_json(raw_msg)
                logging.info(f"[{session_id}] Valid message type: {msg.type}")
                
                # Transform the message for agent service
                transformed_msg = await transform_to_agent_message(msg, session_id)
                
                # Send the transformed message
                if isinstance(transformed_msg, dict):
                    # If it's already a dict (from transformation), send as JSON
                    await agent_ws.send(json.dumps(transformed_msg))
                else:
                    # If it's a model instance, dump to JSON
                    await agent_ws.send(transformed_msg.model_dump_json())
                
            except ValidationError as e:
                # Send error back to editor
                logging.error(f"[{session_id}] Validation error: {e}")
                error_msg = ErrorMsg(
                    type="error",
                    text=f"Invalid message format: {str(e)}"
                )
                await editor_ws.send_text(error_msg.model_dump_json())
            
    except WebSocketDisconnect:
        logging.info(f"[{session_id}] Editor disconnected")
        await agent_ws.close()
        
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"[{session_id}] Agent connection closed while forwarding from editor")
        
    except Exception as e:
        logging.error(f"[{session_id}] Error forwarding editor->agent: {e}")
        raise


async def agent_to_editor(editor_ws: WebSocket, agent_ws, session_id: str):
    """Forward messages from agent to editor."""
    try:
        async for raw_msg in agent_ws:
            if isinstance(raw_msg, bytes):
                raw_msg = raw_msg.decode('utf-8')
                
            logging.debug(f"[{session_id}] Agent -> Editor: {raw_msg}")
            
            try:
                # Validate the outgoing message
                msg = outgoing_adapter.validate_json(raw_msg)
                logging.info(f"[{session_id}] Valid agent message type: {msg.type}")
            except ValidationError as e:
                # Log validation errors but still forward the message
                # Agent should always send valid messages
                logging.warning(f"[{session_id}] Agent sent invalid message: {e}")
            
            # Forward the message regardless of validation
            await editor_ws.send_text(raw_msg)
            
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"[{session_id}] Agent disconnected")
        await editor_ws.close()
        
    except WebSocketDisconnect:
        logging.info(f"[{session_id}] Editor connection closed while forwarding from agent")
        
    except Exception as e:
        logging.error(f"[{session_id}] Error forwarding agent->editor: {e}")
        raise