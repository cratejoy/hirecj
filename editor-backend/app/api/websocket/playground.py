import asyncio
import json
import uuid
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError
import websockets

from app.config import settings

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
        # Use persona_id as shop_subdomain for anonymous sessions
        data = StartConversationData(
            workflow=msg.workflow,
            shop_subdomain=msg.persona_id,  # Use persona_id as shop identifier
            scenario_id=msg.scenario_id
        )
        
        # Create the start conversation message
        start_msg = StartConversationMsg(
            type="start_conversation",
            data=data
        )
        
        return start_msg
        
    elif isinstance(msg, PlaygroundResetMsg):
        # Transform reset to end conversation
        return EndConversationMsg(type="end_conversation")
        
    # Pass through other messages unchanged
    return msg


@router.websocket("/ws/playground")
async def playground_websocket(websocket: WebSocket):
    """Handle WebSocket connections from the editor playground."""
    connection_time = asyncio.get_event_loop().time()
    client_host = websocket.client.host if websocket.client else "unknown"
    
    await websocket.accept()
    session_id = f"playground_{uuid.uuid4()}"
    logging.info(f"[{session_id}] ✅ Editor WebSocket connected from {client_host}")
    logging.info(f"[{session_id}] Headers: {dict(websocket.headers)}")
    
    # Connect to agent service
    # Use the agents service URL from configuration
    agents_url = urlparse(settings.agents_service_url)
    # Convert http/https to ws/wss
    ws_scheme = 'wss' if agents_url.scheme == 'https' else 'ws'
    agent_ws_uri = f"{ws_scheme}://{agents_url.netloc}/ws/chat"
    logging.info(f"[{session_id}] 🔄 Connecting to agent service at: {agent_ws_uri}")
    
    agent_connection_start = asyncio.get_event_loop().time()
    
    try:
        async with websockets.connect(agent_ws_uri) as agent_ws:
            agent_connection_time = asyncio.get_event_loop().time() - agent_connection_start
            logging.info(f"[{session_id}] ✅ Connected to agent service (took {agent_connection_time:.2f}s)")
            
            # Bridge connections
            bridge_start_time = asyncio.get_event_loop().time()
            await bridge_connections(websocket, agent_ws, session_id)
            
            bridge_duration = asyncio.get_event_loop().time() - bridge_start_time
            total_duration = asyncio.get_event_loop().time() - connection_time
            logging.info(f"[{session_id}] 🔒 Bridge closed after {bridge_duration:.2f}s (total connection time: {total_duration:.2f}s)")
            
    except (ConnectionRefusedError, OSError) as e:
        logging.error(f"[{session_id}] ❌ Failed to connect to agent service at {agent_ws_uri}: {e}")
        error_msg = ErrorMsg(
            type="error",
            text="Agent service unavailable"
        )
        await websocket.send_text(error_msg.model_dump_json())
        await websocket.close(code=1011, reason="Agent service unavailable")
        
    except WebSocketDisconnect:
        disconnect_time = asyncio.get_event_loop().time() - connection_time
        logging.info(f"[{session_id}] 🔌 Editor client disconnected after {disconnect_time:.2f}s")
        
    except Exception as e:
        error_time = asyncio.get_event_loop().time() - connection_time
        logging.error(f"[{session_id}] ❌ WebSocket error after {error_time:.2f}s: {e}", exc_info=True)
        await websocket.close(code=1011, reason=str(e))


async def bridge_connections(editor_ws: WebSocket, agent_ws, session_id: str):
    """Bridge messages between editor and agent WebSocket connections."""
    logging.info(f"[{session_id}] 🌉 Starting message bridge")
    
    messages_forwarded = {"editor_to_agent": 0, "agent_to_editor": 0}
    
    # Run both forwarding tasks concurrently
    # If either task completes (due to disconnection), cancel the other
    editor_task = asyncio.create_task(
        editor_to_agent(editor_ws, agent_ws, session_id),
        name="editor_to_agent"
    )
    agent_task = asyncio.create_task(
        agent_to_editor(editor_ws, agent_ws, session_id),
        name="agent_to_editor"
    )
    
    try:
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [editor_task, agent_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Log which task completed first
        for task in done:
            task_name = task.get_name()
            logging.info(f"[{session_id}] 🏁 Task '{task_name}' completed first")
            
            try:
                # Get the result/exception to understand why it completed
                result = task.result()
                logging.info(f"[{session_id}] Task '{task_name}' completed normally")
            except Exception as e:
                logging.error(f"[{session_id}] Task '{task_name}' failed with: {type(e).__name__}: {e}")
        
        # Cancel the other task
        for task in pending:
            task_name = task.get_name()
            logging.info(f"[{session_id}] 🛑 Cancelling task '{task_name}'")
            task.cancel()
            
    except Exception as e:
        logging.error(f"[{session_id}] ❌ Bridge error: {e}", exc_info=True)
        
    finally:
        # Ensure both tasks are cleaned up
        for task in [editor_task, agent_task]:
            if not task.done():
                task.cancel()
                
        logging.info(f"[{session_id}] 🌉 Message bridge closed")


async def editor_to_agent(editor_ws: WebSocket, agent_ws, session_id: str):
    """Forward messages from editor to agent service."""
    message_count = 0
    
    try:
        while True:
            # Receive message from editor
            raw_msg = await editor_ws.receive_text()
            message_count += 1
            msg_preview = raw_msg[:200] + "..." if len(raw_msg) > 200 else raw_msg
            logging.info(f"[{session_id}] 📨 Editor->Agent msg #{message_count}: {msg_preview}")
            
            try:
                # Validate the incoming message
                msg = incoming_adapter.validate_json(raw_msg)
                logging.info(f"[{session_id}] Message type: {msg.type}, size: {len(raw_msg)} bytes")
                
                # Transform the message for agent service
                transformed_msg = await transform_to_agent_message(msg, session_id)
                
                # Send the transformed message
                send_start = asyncio.get_event_loop().time()
                if isinstance(transformed_msg, dict):
                    # If it's already a dict (from transformation), send as JSON
                    await agent_ws.send(json.dumps(transformed_msg))
                else:
                    # If it's a model instance, dump to JSON
                    await agent_ws.send(transformed_msg.model_dump_json())
                
                send_time = asyncio.get_event_loop().time() - send_start
                logging.info(f"[{session_id}] ✅ Forwarded to agent in {send_time:.3f}s")
                
            except ValidationError as e:
                # Send error back to editor
                logging.error(f"[{session_id}] ❌ Validation error: {e}")
                error_msg = ErrorMsg(
                    type="error",
                    text=f"Invalid message format: {str(e)}"
                )
                await editor_ws.send_text(error_msg.model_dump_json())
            
    except WebSocketDisconnect as e:
        logging.info(f"[{session_id}] 🔌 Editor disconnected (code: {e.code}, reason: {e.reason}) after {message_count} messages")
        logging.info(f"[{session_id}] Closing agent connection...")
        await agent_ws.close()
        
    except websockets.exceptions.ConnectionClosed as e:
        logging.info(f"[{session_id}] 🔌 Agent connection closed (code: {e.code}, reason: {e.reason}) while forwarding from editor after {message_count} messages")
        
    except Exception as e:
        logging.error(f"[{session_id}] ❌ Error forwarding editor->agent after {message_count} messages: {type(e).__name__}: {e}")
        raise


async def agent_to_editor(editor_ws: WebSocket, agent_ws, session_id: str):
    """Forward messages from agent to editor."""
    message_count = 0
    
    try:
        async for raw_msg in agent_ws:
            message_count += 1
            
            if isinstance(raw_msg, bytes):
                raw_msg = raw_msg.decode('utf-8')
            
            msg_preview = raw_msg[:200] + "..." if len(raw_msg) > 200 else raw_msg
            logging.info(f"[{session_id}] 📨 Agent->Editor msg #{message_count}: {msg_preview}")
            
            try:
                # Validate the outgoing message
                msg = outgoing_adapter.validate_json(raw_msg)
                logging.info(f"[{session_id}] Message type: {msg.type}, size: {len(raw_msg)} bytes")
            except ValidationError as e:
                # Log validation errors but still forward the message
                # Agent should always send valid messages
                logging.warning(f"[{session_id}] ⚠️ Agent sent invalid message: {e}")
            
            # Forward the message regardless of validation
            send_start = asyncio.get_event_loop().time()
            await editor_ws.send_text(raw_msg)
            send_time = asyncio.get_event_loop().time() - send_start
            logging.info(f"[{session_id}] ✅ Forwarded to editor in {send_time:.3f}s")
            
    except websockets.exceptions.ConnectionClosed as e:
        logging.info(f"[{session_id}] 🔌 Agent disconnected (code: {e.code}, reason: {e.reason}) after {message_count} messages")
        logging.info(f"[{session_id}] Closing editor connection with code 1000 (normal closure)")
        await editor_ws.close(code=1000, reason="Agent disconnected")
        
    except WebSocketDisconnect as e:
        logging.info(f"[{session_id}] 🔌 Editor disconnected (code: {e.code}, reason: {e.reason}) while forwarding from agent after {message_count} messages")
        
    except Exception as e:
        logging.error(f"[{session_id}] ❌ Error forwarding agent->editor after {message_count} messages: {type(e).__name__}: {e}")
        raise