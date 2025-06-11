"""Internal API endpoints for service-to-service communication."""

from fastapi import APIRouter, HTTPException
from app.logging_config import get_logger
from app.constants import HTTPStatus
from shared.models.api import OAuthHandoffRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


@router.post("/session/initiate")
async def initiate_session(request: OAuthHandoffRequest):
    """
    Internal endpoint called by the Auth Service to pre-warm a session
    after a successful OAuth completion.
    """
    logger.info(f"[INTERNAL_API] Received session initiation request for conversation_id: {request.conversation_id}")
    logger.info(f"[INTERNAL_API] Handoff data: shop_domain={request.shop_domain}, is_new={request.is_new}")
    
    # In Phase 6.2, this will call the SessionInitiator service.
    
    return {"status": "received", "conversation_id": request.conversation_id}
