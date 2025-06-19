"""WebSocket heartbeat service to keep connections alive."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import WebSocket

from shared.logging_config import get_logger

logger = get_logger(__name__)


class WebSocketHeartbeat:
    """Manages heartbeat (ping/pong) for WebSocket connections."""
    
    def __init__(self, interval: float = 15.0, timeout: float = 10.0):
        """
        Initialize heartbeat service.
        
        Args:
            interval: Seconds between heartbeat pings
            timeout: Seconds to wait for pong response before considering connection dead
        """
        self.interval = interval
        self.timeout = timeout
        self._tasks: Dict[str, asyncio.Task] = {}
        
    async def start_heartbeat(self, conversation_id: str, websocket: WebSocket) -> None:
        """Start heartbeat monitoring for a WebSocket connection."""
        # Cancel any existing heartbeat for this conversation
        if conversation_id in self._tasks:
            self._tasks[conversation_id].cancel()
            
        # Create new heartbeat task
        task = asyncio.create_task(self._heartbeat_loop(conversation_id, websocket))
        self._tasks[conversation_id] = task
        
        logger.info(
            f"[HEARTBEAT] Started heartbeat for {conversation_id} "
            f"(interval={self.interval}s, timeout={self.timeout}s)"
        )
        
    async def stop_heartbeat(self, conversation_id: str) -> None:
        """Stop heartbeat monitoring for a conversation."""
        if conversation_id in self._tasks:
            self._tasks[conversation_id].cancel()
            del self._tasks[conversation_id]
            logger.info(f"[HEARTBEAT] Stopped heartbeat for {conversation_id}")
            
    async def _heartbeat_loop(self, conversation_id: str, websocket: WebSocket) -> None:
        """Run heartbeat loop for a WebSocket connection."""
        ping_count = 0
        start_time = datetime.now()
        
        try:
            while True:
                # Wait for interval
                await asyncio.sleep(self.interval)
                
                ping_count += 1
                ping_time = datetime.now()
                elapsed = (ping_time - start_time).total_seconds()
                
                logger.debug(
                    f"[HEARTBEAT] Sending ping #{ping_count} to {conversation_id} "
                    f"after {elapsed:.1f}s total connection time"
                )
                
                try:
                    # Send WebSocket ping frame
                    pong_waiter = await websocket.ping()
                    
                    # Wait for pong with timeout
                    await asyncio.wait_for(pong_waiter, timeout=self.timeout)
                    
                    pong_time = datetime.now()
                    latency = (pong_time - ping_time).total_seconds() * 1000
                    
                    logger.debug(
                        f"[HEARTBEAT] Received pong #{ping_count} from {conversation_id} "
                        f"(latency={latency:.1f}ms)"
                    )
                    
                except asyncio.TimeoutError:
                    logger.warning(
                        f"[HEARTBEAT] Ping #{ping_count} timeout for {conversation_id} "
                        f"after {self.timeout}s - connection may be dead"
                    )
                    # Connection is likely dead, stop heartbeat
                    break
                    
                except Exception as e:
                    logger.error(
                        f"[HEARTBEAT] Error during ping/pong for {conversation_id}: "
                        f"{type(e).__name__}: {str(e)}"
                    )
                    # Connection error, stop heartbeat
                    break
                    
        except asyncio.CancelledError:
            logger.debug(f"[HEARTBEAT] Heartbeat cancelled for {conversation_id}")
            raise
            
        except Exception as e:
            logger.error(
                f"[HEARTBEAT] Unexpected error in heartbeat loop for {conversation_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            
        finally:
            total_duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"[HEARTBEAT] Heartbeat ended for {conversation_id} after "
                f"{ping_count} pings over {total_duration:.1f}s"
            )