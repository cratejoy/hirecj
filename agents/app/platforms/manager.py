"""
Platform Manager

Manages messaging platform integrations and provides unified interface.
Simplified to only include essential functionality.
"""

from typing import Dict, Optional, Union, Callable, List
import asyncio

from .base import Platform, PlatformType, IncomingMessage, OutgoingMessage
from shared.logging_config import get_logger

logger = get_logger(__name__)


class PlatformManager:
    """Manages messaging platform integrations"""

    def __init__(self):
        """Initialize platform manager"""
        self.platforms: Dict[PlatformType, Platform] = {}
        self.conversation_map: Dict[str, PlatformType] = {}
        self.unified_handler: Optional[Callable[[IncomingMessage], None]] = None

        logger.info("Platform manager initialized")

    def register_platform(self, platform: Platform):
        """
        Register a messaging platform.

        Args:
            platform: Platform instance to register
        """
        platform.on_message(self._route_message)
        self.platforms[platform.platform_type] = platform
        logger.info(f"Registered {platform.platform_type.value} platform")

    async def start_all(self):
        """Connect all registered platforms"""
        logger.info(f"Starting {len(self.platforms)} platforms...")

        connection_tasks = []
        for platform in self.platforms.values():
            task = asyncio.create_task(self._safe_connect(platform))
            connection_tasks.append(task)

        # Wait for all platforms to attempt connection
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)

        # Log results
        connected_count = 0
        for platform, result in zip(self.platforms.values(), results):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to connect {platform.platform_type.value}: {str(result)}"
                )
            elif result:
                connected_count += 1
                logger.info(f"Successfully connected {platform.platform_type.value}")
            else:
                logger.warning(f"Failed to connect {platform.platform_type.value}")

        logger.info(f"Connected {connected_count}/{len(self.platforms)} platforms")

    async def stop_all(self):
        """Disconnect all platforms"""
        logger.info("Stopping all platforms...")

        disconnection_tasks = []
        for platform in self.platforms.values():
            if platform.is_connected:
                task = asyncio.create_task(self._safe_disconnect(platform))
                disconnection_tasks.append(task)

        if disconnection_tasks:
            await asyncio.gather(*disconnection_tasks, return_exceptions=True)

        logger.info("All platforms stopped")

    async def send_message(
        self, platform: Union[PlatformType, str], message: OutgoingMessage
    ) -> bool:
        """
        Send message through specific platform.

        Args:
            platform: Platform type or string identifier
            message: Message to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        # Handle platform lookup
        if isinstance(platform, str):
            try:
                platform = PlatformType(platform)
            except ValueError:
                logger.error(f"Invalid platform type: {platform}")
                return False

        platform_instance = self.platforms.get(platform)
        if not platform_instance:
            logger.error(f"Platform {platform.value} not registered")
            return False

        if not platform_instance.is_connected:
            logger.error(f"Platform {platform.value} not connected")
            return False

        try:
            success = await platform_instance.send_message(message)
            if success:
                logger.debug(
                    f"Message sent via {platform.value}: {message.text[:50]}..."
                )
            else:
                logger.warning(f"Failed to send message via {platform.value}")
            return success
        except Exception as e:
            logger.error(f"Error sending message via {platform.value}: {str(e)}")
            return False

    async def send_to_conversation(
        self, conversation_id: str, message: OutgoingMessage
    ) -> bool:
        """
        Send message to a conversation, auto-detecting platform.

        Args:
            conversation_id: Conversation identifier
            message: Message to send (conversation_id will be set)

        Returns:
            True if message was sent successfully, False otherwise
        """
        platform_type = self.conversation_map.get(conversation_id)
        if not platform_type:
            logger.error(f"No platform found for conversation: {conversation_id}")
            return False

        # Ensure conversation_id is set correctly
        message.conversation_id = conversation_id

        return await self.send_message(platform_type, message)

    async def _route_message(self, message: IncomingMessage):
        """Route incoming messages to unified handler"""
        # Track which platform this conversation is on
        self.conversation_map[message.conversation_id] = message.platform

        logger.debug(
            f"Routing message from {message.platform.value} conversation {message.conversation_id}"
        )

        if self.unified_handler:
            try:
                await self.unified_handler(message)
            except Exception as e:
                logger.error(f"Error in unified message handler: {str(e)}")
        else:
            logger.warning("No unified message handler registered")

    def on_message(self, handler: Callable[[IncomingMessage], None]):
        """
        Register unified message handler.

        Args:
            handler: Function to call for all incoming messages
        """
        self.unified_handler = handler
        logger.info("Unified message handler registered")

    async def _safe_connect(self, platform: Platform) -> bool:
        """Safely connect a platform with error handling"""
        try:
            await platform.connect()
            return platform.is_connected
        except Exception as e:
            logger.error(f"Error connecting {platform.platform_type.value}: {str(e)}")
            return False

    async def _safe_disconnect(self, platform: Platform):
        """Safely disconnect a platform with error handling"""
        try:
            await platform.disconnect()
        except Exception as e:
            logger.error(
                f"Error disconnecting {platform.platform_type.value}: {str(e)}"
            )

    def get_connected_platforms(self) -> List[PlatformType]:
        """Get list of connected platform types"""
        return [
            platform_type
            for platform_type, platform in self.platforms.items()
            if platform.is_connected
        ]
