import asyncio
import uuid
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError
import websockets

# Import protocol models - the shared module is installed in the venv
# When running with uvicorn, the PYTHONPATH will be set correctly
if TYPE_CHECKING:
    from shared.protocol.models import (
        IncomingMessage, OutgoingMessage,
        PlaygroundStartMsg, StartConversationMsg,
        PlaygroundResetMsg, EndConversationMsg,
        ErrorMsg
    )
else:
    try:
        from shared.protocol.models import (
            IncomingMessage, OutgoingMessage,
            PlaygroundStartMsg, StartConversationMsg,
            PlaygroundResetMsg, EndConversationMsg,
            ErrorMsg
        )
    except ImportError:
        # This helps with development/testing - the actual app will have proper paths
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
        from shared.protocol.models import (
            IncomingMessage, OutgoingMessage,
            PlaygroundStartMsg, StartConversationMsg,
            PlaygroundResetMsg, EndConversationMsg,
            ErrorMsg
        )

router = APIRouter()

# Validation adapters
incoming_adapter = TypeAdapter(IncomingMessage)
outgoing_adapter = TypeAdapter(OutgoingMessage)

@router.websocket("/ws/playground")
async def playground_websocket(websocket: WebSocket):
    await websocket.accept()
    logging.info("Playground WebSocket connected")
    # Implementation continues in next phase