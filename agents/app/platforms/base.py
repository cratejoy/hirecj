"""
Platform Base Classes

Unified messaging architecture with platform-agnostic naming.
Defines abstract interfaces for all messaging platform integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import enum

from shared.logging_config import get_logger

logger = get_logger(__name__)


class PlatformType(enum.Enum):
    """Supported messaging platforms"""

    SLACK = "slack"
    TEAMS = "teams"
    WHATSAPP = "whatsapp"
    WEB = "web"
    EMAIL = "email"
    SMS = "sms"


@dataclass
class Participant:
    """Person in a conversation"""

    platform_id: str  # User ID on the platform
    display_name: str  # Human-readable name
    metadata: Dict[str, Any] = field(default_factory=dict)  # Platform-specific data


@dataclass
class Conversation:
    """Represents a conversation/channel/chat across platforms"""

    platform: PlatformType
    conversation_id: str  # Platform's ID for this conversation
    participants: List[Participant]
    is_group: bool  # Group chat vs 1:1
    metadata: Dict[str, Any] = field(default_factory=dict)  # Platform-specific data


@dataclass
class IncomingMessage:
    """Normalized message from any platform"""

    platform: PlatformType
    conversation_id: str
    message_id: str
    sender: Participant
    text: str
    timestamp: datetime
    thread_id: Optional[str] = None
    attachments: Optional[List[Dict]] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutgoingMessage:
    """Message to send to a platform"""

    conversation_id: str
    text: str
    thread_id: Optional[str] = None
    attachments: Optional[List[Dict]] = None
    metadata: Optional[Dict[str, Any]] = None


class Platform(ABC):
    """Base class for all messaging platform integrations"""

    def __init__(self, platform_type: PlatformType, config: Dict[str, Any]):
        """
        Initialize platform with configuration.

        Args:
            platform_type: The type of platform (Slack, Teams, etc.)
            config: Platform-specific configuration
        """
        self.platform_type = platform_type
        self.config = config
        self.message_handler: Optional[Callable[[IncomingMessage], None]] = None
        self._connected = False

        logger.info(f"Initialized {platform_type.value} platform")

    @abstractmethod
    async def connect(self) -> None:
        """Initialize platform connection"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanup platform resources"""
        pass

    @abstractmethod
    async def send_message(self, message: OutgoingMessage) -> bool:
        """
        Send a message through this platform.

        Args:
            message: The message to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Conversation:
        """
        Get conversation details.

        Args:
            conversation_id: Platform-specific conversation identifier

        Returns:
            Conversation object with details
        """
        pass

    def on_message(self, handler: Callable[[IncomingMessage], None]):
        """
        Register callback for incoming messages.

        Args:
            handler: Function to call when message is received
        """
        self.message_handler = handler
        logger.debug(f"Message handler registered for {self.platform_type.value}")

    @property
    def is_connected(self) -> bool:
        """Check if platform is connected"""
        return self._connected

    def _set_connected(self, connected: bool):
        """Set connection status"""
        self._connected = connected
        status = "connected" if connected else "disconnected"
        logger.info(f"{self.platform_type.value} platform {status}")

    async def _handle_message(self, message: IncomingMessage):
        """Internal message handler that adds logging"""
        logger.debug(
            f"Received message from {message.platform.value}: {message.text[:50]}..."
        )

        if self.message_handler:
            try:
                await self.message_handler(message)
            except Exception as e:
                logger.error(
                    f"Error handling message from {message.platform.value}: {str(e)}"
                )
        else:
            logger.warning(
                f"No message handler registered for {self.platform_type.value}"
            )

    def validate_config(self, required_keys: List[str]) -> bool:
        """
        Validate that required configuration keys are present.

        Args:
            required_keys: List of required configuration keys

        Returns:
            True if all required keys present, False otherwise
        """
        missing_keys = [key for key in required_keys if key not in self.config]

        if missing_keys:
            logger.error(
                f"{self.platform_type.value} missing required config keys: {missing_keys}"
            )
            return False

        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get platform health status"""
        return {
            "platform": self.platform_type.value,
            "connected": self.is_connected,
            "config_valid": bool(self.config),
            "handler_registered": self.message_handler is not None,
        }
