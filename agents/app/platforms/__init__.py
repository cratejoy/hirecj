# Platform abstraction layer
from .base import (
    PlatformType,
    Participant,
    Conversation,
    IncomingMessage,
    OutgoingMessage,
    Platform,
)
from .manager import PlatformManager

__all__ = [
    "PlatformType",
    "Participant",
    "Conversation",
    "IncomingMessage",
    "OutgoingMessage",
    "Platform",
    "PlatformManager",
]
