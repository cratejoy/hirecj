import asyncio
import websockets
import json
import time
from typing import Dict, Any
import uuid
import os
import threading
import nest_asyncio

from app.config import settings
from app.logging_config import get_logger

# Allow nested event loops
nest_asyncio.apply()

logger = get_logger(__name__)


class ConversationAPI:
    """API client with simplified connection management that works across event loops."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or f"ws://localhost:{settings.app_port}"

        # Global state (thread-safe)
        self._sessions = {}  # Track conversation IDs by (merchant, scenario, workflow)
        self._session_lock = threading.Lock()

        # Performance metrics (thread-safe)
        self._request_count = 0
        self._total_response_time = 0.0
        self._metrics_lock = threading.Lock()

    def kickoff(self, merchant: str, scenario: str, workflow: str, message: str) -> str:
        """Synchronous interface matching CrewAI's crew.kickoff()."""
        # Use asyncio.run() for clean async-to-sync conversion
        return asyncio.run(self._send_message(merchant, scenario, workflow, message))

    async def _send_message(
        self, merchant: str, scenario: str, workflow: str, message: str
    ) -> str:
        """Send a single message and get response."""
        start_time = time.time()
        session_key = (merchant, scenario, workflow)

        # Get or create conversation ID
        with self._session_lock:
            if session_key not in self._sessions:
                if self._is_test_mode():
                    conversation_id = f"{merchant}_{scenario}_{workflow}_test"
                else:
                    conversation_id = (
                        f"{merchant}_{scenario}_{workflow}_{uuid.uuid4().hex[:8]}"
                    )
                self._sessions[session_key] = conversation_id
            else:
                conversation_id = self._sessions[session_key]

        ws = None
        try:
            # Connect to WebSocket
            url = f"{self.base_url}/ws/chat/{conversation_id}"
            ws = await websockets.connect(
                url,
                ping_interval=settings.websocket_ping_interval,
                ping_timeout=settings.websocket_ping_timeout,
            )
            logger.info(f"Connected to conversation: {conversation_id}")

            # Wait for initial system message
            async with asyncio.timeout(float(settings.websocket_timeout / 2)):
                data = json.loads(await ws.recv())
                if data["type"] == "system":
                    logger.debug(f"System message: {data.get('text', '')}")

            # Check if we need to start the conversation
            need_start = False
            with self._session_lock:
                start_key = f"{session_key}_started"
                if start_key not in self._sessions:
                    need_start = True
                    self._sessions[start_key] = True

            if need_start:
                # Send start_conversation message
                await ws.send(
                    json.dumps(
                        {
                            "type": "start_conversation",
                            "data": {
                                "merchant_id": merchant,
                                "scenario": scenario,
                                "workflow": workflow,
                            },
                        }
                    )
                )

                # Wait for conversation_started confirmation
                async with asyncio.timeout(float(settings.websocket_timeout)):
                    while True:
                        data = json.loads(await ws.recv())
                        if data["type"] == "conversation_started":
                            logger.info("Conversation started successfully")
                            break
                        elif data["type"] == "error":
                            raise Exception(
                                f"Failed to start conversation: {data.get('text', 'Unknown error')}"
                            )

            # Send the actual message
            await ws.send(
                json.dumps(
                    {
                        "type": "message",
                        "text": message,
                        "merchant_id": merchant,
                        "scenario": scenario,
                        "conversation_id": conversation_id,
                    }
                )
            )

            # Wait for response
            async with asyncio.timeout(settings.websocket_response_timeout):
                while True:
                    raw_data = await ws.recv()
                    data = json.loads(raw_data)
                    logger.debug(f"Received: type={data.get('type')}")

                    if data["type"] == "cj_message":
                        response_data = data.get("data", {})
                        response_text = response_data.get("content", "")
                        logger.info(f"Got CJ response: {len(response_text)} chars")
                        return response_text
                    elif data["type"] == "error":
                        logger.error(f"API Error: {data.get('text', 'Unknown error')}")
                        raise Exception(
                            f"API Error: {data.get('text', 'Unknown error')}"
                        )
                    elif data["type"] in ["system", "cj_thinking", "progress"]:
                        logger.debug(f"{data['type']}: {data.get('text', '')}")

        except asyncio.TimeoutError:
            logger.error(
                f"Response timeout after {settings.websocket_response_timeout}s"
            )
            raise Exception(
                f"Timeout: No response received within {settings.websocket_response_timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Error in API communication: {e}")
            raise
        finally:
            # Always close the WebSocket
            if ws:
                await ws.close()

            # Record performance metrics
            response_time = time.time() - start_time
            with self._metrics_lock:
                self._request_count += 1
                self._total_response_time += response_time

            if response_time > settings.slow_response_threshold:
                logger.warning(
                    f"Slow response: {response_time:.2f}s for {merchant}/{scenario}/{workflow}"
                )

    def _is_test_mode(self) -> bool:
        """Check if running in test mode."""
        return os.environ.get("HIRECJ_TEST_MODE", "").lower() == "true"

    def reset_session(
        self, merchant: str = None, scenario: str = None, workflow: str = None
    ):
        """Reset a specific session or all sessions."""
        with self._session_lock:
            if merchant and scenario and workflow:
                session_key = (merchant, scenario, workflow)
                self._sessions.pop(session_key, None)
                self._sessions.pop(f"{session_key}_started", None)
            else:
                self._sessions.clear()

    def close(self):
        """Clean up resources."""
        with self._session_lock:
            self._sessions.clear()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        with self._metrics_lock:
            return {
                "request_count": self._request_count,
                "average_response_time": (
                    self._total_response_time / self._request_count
                    if self._request_count > 0
                    else 0
                ),
            }
