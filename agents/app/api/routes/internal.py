"""Internal API endpoints for service-to-service communication."""

from fastapi import APIRouter, HTTPException
from app.logging_config import get_logger
from app.constants import HTTPStatus
from shared.models.api import OAuthHandoffRequest
from app.services.session_initiator import session_initiator

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


@router.post("/session/initiate")
async def initiate_session(request: OAuthHandoffRequest):
    """
    Internal endpoint called by the Auth Service to pre-warm a session
    after a successful OAuth completion.
    """
    logger.info(
        f"[INTERNAL_API] Received session initiation request for conversation_id: {request.conversation_id}"
    )
    logger.info(
        f"[INTERNAL_API] Handoff data: shop_domain={request.shop_domain}, is_new={request.is_new}"
    )

    # Call the SessionInitiator service to prepare the session.
    success = await session_initiator.prepare_oauth_session(request)

    if not success:
        logger.error(
            f"[INTERNAL_API] SessionInitiator failed to prepare session for {request.conversation_id}"
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to prepare user session on the agent service.",
        )

    return {"status": "session_prepared", "conversation_id": request.conversation_id}
