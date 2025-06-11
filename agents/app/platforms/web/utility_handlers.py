"""Utility message handlers (ping, debug, etc)."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime

from fastapi import WebSocket

from app.logging_config import get_logger

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)


class UtilityHandlers:
    """Handles utility WebSocket messages."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform

    async def handle_ping(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle ping/pong for connection keepalive."""
        await websocket.send_json(
            {"type": "pong", "timestamp": datetime.now().isoformat()}
        )

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
