# Phase 2: Backend Alignment

## Overview
Replace oauth_complete handler with system_event handler that generates proper system messages.

## Changes

### web_platform.py

```python
# REMOVE THIS ENTIRE BLOCK:
elif message_type == "oauth_complete":
    # All this code including debug halt
    
# ADD THIS:
elif message_type == "system_event":
    event_data = data.get("data", {})
    event_type = event_data.get("event_type")
    
    if event_type == "oauth_complete":
        await self._handle_oauth_system_event(
            websocket, conversation_id, event_data
        )

async def _handle_oauth_system_event(
    self, websocket, conversation_id: str, event_data: Dict[str, Any]
):
    """Convert OAuth completion to system event."""
    
    # Get session using original conversation_id
    original_conversation_id = event_data.get("conversation_id")
    session_id = original_conversation_id or conversation_id
    session = self.session_manager.get_session(session_id)
    
    if not session:
        await self._send_error(websocket, "Session expired")
        return
    
    # Update session with OAuth data
    shop_domain = event_data.get("shop_domain")
    is_new = event_data.get("is_new", True)
    
    # Generate system message workflow expects
    system_message = (
        f"New Shopify merchant authenticated from {shop_domain}"
        if is_new else
        f"Returning Shopify merchant authenticated from {shop_domain}"
    )
    
    # Process as system message
    response = await self.message_processor.process_message(
        session=session,
        message=system_message,
        sender="system"
    )
    
    # Send response
    await websocket.send_json({
        "type": "cj_message",
        "data": {
            "content": response,
            "factCheckStatus": "available",
            "timestamp": datetime.now().isoformat(),
        }
    })
```

## Key Points
1. Generates exact system message workflow expects
2. Uses original conversation_id from frontend
3. Processes through message_processor as system sender
4. Clean, simple implementation