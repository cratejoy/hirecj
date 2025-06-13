"""
Shared Web-Socket protocol – single source of truth
"""
from .models import IncomingMessage, OutgoingMessage  # re-export
__all__ = ["IncomingMessage", "OutgoingMessage"]
