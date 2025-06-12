"""Internal API endpoints for service-to-service communication."""

from fastapi import APIRouter, HTTPException
from app.logging_config import get_logger
from app.constants import HTTPStatus
from shared.models.api import OAuthHandoffRequest
from app.services.post_oauth_handler import post_oauth_handler

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


@router.post("/oauth/completed")
async def handle_oauth_completion(request: OAuthHandoffRequest):
    """
    Internal endpoint called by the Auth Service after successful OAuth completion.
    
    This endpoint prepares the appropriate workflow state (e.g., shopify_post_auth)
    so that when the user's WebSocket connects, they see the right content immediately.
    """
    logger.info(
        f"[INTERNAL_API] OAuth completion notification for conversation: {request.conversation_id}"
    )
    logger.info(
        f"[INTERNAL_API] OAuth data: shop_domain={request.shop_domain}, is_new={request.is_new}"
    )

    # Handle the OAuth completion
    success = await post_oauth_handler.handle_oauth_completion(request)

    if not success:
        logger.error(
            f"[INTERNAL_API] Failed to handle OAuth completion for {request.conversation_id}"
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to prepare post-OAuth workflow state",
        )

    return {
        "status": "oauth_handled",
        "conversation_id": request.conversation_id,
        "workflow": "shopify_post_auth"
    }
