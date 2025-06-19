"""Utility message handlers (ping, debug, etc)."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime

from fastapi import WebSocket

from shared.logging_config import get_logger
from shared.protocol.models import (
    PingMsg,
    DebugRequestMsg,
    SystemEventMsg,
    PongMsg,
    DebugResponseMsg,
)

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)


class UtilityHandlers:
    """Handles utility WebSocket messages."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform

    async def handle_ping(
        self, websocket: WebSocket, conversation_id: str, message: PingMsg
    ):
        """Handle ping/pong for connection keepalive."""
        pong = PongMsg(
            type="pong",
            timestamp=datetime.now()
        )
        await self.platform.send_validated_message(websocket, pong)

    async def handle_debug_request(
        self, websocket: WebSocket, conversation_id: str, message: DebugRequestMsg
    ):
        """Handle debug_request message."""
        debug_type = message.data.type
        session = self.platform.session_manager.get_session(conversation_id)
        
        if not session:
            debug_response = DebugResponseMsg(
                type="debug_response",
                data={
                    "error": "No active session",
                    "conversation_id": conversation_id
                }
            )
            await self.platform.send_validated_message(websocket, debug_response)
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
                # Return the last 10 conversation messages unfiltered so the
                # frontend always receives useful context.
                recent_prompts = []
                if hasattr(session, "conversation") and hasattr(session.conversation, "messages"):
                    for msg in session.conversation.messages[-10:]:
                        ts = getattr(msg, "timestamp", "unknown")
                        if isinstance(ts, datetime):
                            ts = ts.isoformat()
                        recent_prompts.append(
                            {
                                "timestamp": ts,
                                "sender": msg.sender,
                                "content": msg.content[:500],  # Truncate long text
                            }
                        )
                debug_data["prompts"] = recent_prompts
            
            # New debug types for comprehensive agent debugging
            if debug_type == "llm_prompts" or debug_type == "snapshot":
                # Get stored LLM prompts from debug data
                debug_storage = getattr(session, 'debug_data', {})
                llm_prompts = debug_storage.get('llm_prompts', [])
                if debug_type == "llm_prompts":
                    debug_data["llm_prompts"] = llm_prompts
                elif debug_type == "snapshot" and llm_prompts:
                    # Include last prompt in snapshot
                    debug_data["last_llm_prompt"] = llm_prompts[-1] if llm_prompts else None
            
            if debug_type == "llm_responses" or debug_type == "snapshot":
                # Get stored LLM responses from debug data
                debug_storage = getattr(session, 'debug_data', {})
                llm_responses = debug_storage.get('llm_responses', [])
                if debug_type == "llm_responses":
                    debug_data["llm_responses"] = llm_responses
                elif debug_type == "snapshot" and llm_responses:
                    # Include last response in snapshot
                    debug_data["last_llm_response"] = llm_responses[-1] if llm_responses else None
            
            if debug_type == "tool_calls" or debug_type == "snapshot":
                # Get tool call history from debug data
                debug_storage = getattr(session, 'debug_data', {})
                tool_calls = debug_storage.get('tool_calls', [])
                if debug_type == "tool_calls":
                    debug_data["tool_calls"] = tool_calls
                elif debug_type == "snapshot":
                    # Include summary in snapshot
                    debug_data["tool_calls_count"] = len(tool_calls)
                    debug_data["recent_tools"] = [tc.get('tool_name', 'unknown') for tc in tool_calls[-3:]]
            
            if debug_type == "crew_output":
                # Get CrewAI execution logs from debug data
                debug_storage = getattr(session, 'debug_data', {})
                crew_output = debug_storage.get('crew_output', [])
                debug_data["crew_output"] = crew_output
            
            if debug_type == "timing" or debug_type == "snapshot":
                # Get timing metrics from debug data
                debug_storage = getattr(session, 'debug_data', {})
                timing_data = debug_storage.get('timing', {})
                if debug_type == "timing":
                    debug_data["timing"] = timing_data
                elif debug_type == "snapshot" and timing_data:
                    # Include summary in snapshot
                    debug_data["last_response_time"] = timing_data.get('last_response_time')
                    debug_data["avg_response_time"] = timing_data.get('avg_response_time')
            
            if debug_type == "message_details":
                message_id = message.data.message_id
                if not message_id:
                    debug_response = DebugResponseMsg(
                        type="debug_response",
                        data={"error": "message_id required for message_details request"}
                    )
                    await self.platform.send_validated_message(websocket, debug_response)
                    return
                
                # Aggregate all debug data for this message
                debug_data["message_id"] = message_id
                
                # Find matching prompt
                for prompt in session.debug_data.get("llm_prompts", []):
                    if prompt.get("message_id") == message_id:
                        debug_data["prompt"] = prompt
                        break
                
                # Find matching response
                for response in session.debug_data.get("llm_responses", []):
                    if response.get("message_id") == message_id:
                        debug_data["response"] = response
                        # Log thinking content if present
                        if response.get("thinking_content"):
                            logger.info(f"[DEBUG_REQUEST] Found thinking content for {message_id}: {len(response['thinking_content'])} chars")
                            logger.info(f"[DEBUG_REQUEST] Thinking preview: {response['thinking_content'][:100]}...")
                        else:
                            logger.info(f"[DEBUG_REQUEST] No thinking content found for {message_id}")
                        
                        # Also log clean_content if present
                        if response.get("clean_content"):
                            logger.info(f"[DEBUG_REQUEST] Found clean_content: {len(response.get('clean_content', ''))} chars")
                        break
                
                # Find matching tool calls
                debug_data["tool_calls"] = [
                    tc for tc in session.debug_data.get("tool_calls", [])
                    if tc.get("message_id") == message_id
                ]
                
                # Find matching crew output
                debug_data["crew_output"] = [
                    co for co in session.debug_data.get("crew_output", [])
                    if co.get("message_id") == message_id
                ]
            
            # Send debug response
            debug_response = DebugResponseMsg(
                type="debug_response",
                data=debug_data
            )
            await self.platform.send_validated_message(websocket, debug_response)
            
            logger.info(f"[DEBUG_REQUEST] Sent debug info for {conversation_id}: type={debug_type}")
            
        except Exception as e:
            logger.error(f"[DEBUG_ERROR] Failed to generate debug info: {str(e)}")
            error_response = DebugResponseMsg(
                type="debug_response",
                data={
                    "error": f"Failed to generate debug info: {str(e)}",
                    "conversation_id": conversation_id
                }
            )
            await self.platform.send_validated_message(websocket, error_response)
    
    async def handle_system_event(
        self, websocket: WebSocket, conversation_id: str, message: SystemEventMsg
    ):
        """Handle system event message."""
        # Log system event
        logger.info(f"[SYSTEM_EVENT] Received system event for conversation {conversation_id}: {message.data}")
        
        # For now, just acknowledge the event
        # In the future, this could be used for various system-level operations
        await self.platform.send_error(websocket, "System events not yet implemented")
