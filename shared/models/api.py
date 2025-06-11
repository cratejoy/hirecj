"""Shared Pydantic models for internal API communication."""

from pydantic import BaseModel
from typing import Optional


class OAuthHandoffRequest(BaseModel):
    """
    Request model for the internal OAuth handoff from Auth Service to Agent Service.
    """
    shop_domain: str
    is_new: bool
    conversation_id: str
    email: Optional[str] = None
