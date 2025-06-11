"""OAuth completion handling for web platform."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime

from fastapi import WebSocket

from app.logging_config import get_logger
from app.utils.supabase_util import get_db_session
from shared.db_models import OAuthCompletionState
from shared.user_identity import get_or_create_user

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)


class OAuthHandler:
    """Handles OAuth completion flow."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform

    async def check_oauth_completion(self, conversation_id: str) -> Dict[str, Any]:
        """Check for OAuth completion status in database."""
        try:
            with get_db_session() as db_session:
                # Find an unprocessed, non-expired record for this conversation
                oauth_record = db_session.query(OAuthCompletionState).filter(
                    OAuthCompletionState.conversation_id == conversation_id,
                    OAuthCompletionState.processed == False,
                    OAuthCompletionState.expires_at > datetime.utcnow()
                ).first()

                if oauth_record:
                    logger.info(f"[OAUTH_CHECK] Found OAuth completion data in DB for {conversation_id}")
                    oauth_data = oauth_record.data
                    
                    # Mark as processed to prevent reuse
                    oauth_record.processed = True
                    db_session.commit()
                    
                    return oauth_data
                    
        except Exception as e:
            logger.error(f"[OAUTH_CHECK] Error checking DB for OAuth status: {e}")
        
        return None

    async def process_oauth_completion(
        self, websocket: WebSocket, session: Any, oauth_data: Dict[str, Any]
    ):
        """Process OAuth completion data retrieved from database."""
        conversation_id = session.conversation.id
        logger.info(f"[OAUTH_PROCESS] Processing for conversation {conversation_id}: {oauth_data}")

        # Update session with OAuth data
        provider = oauth_data.get("provider", "shopify")
        is_new = oauth_data.get("is_new", True)
        merchant_id = oauth_data.get("merchant_id")
        shop_domain = oauth_data.get("shop_domain")

        # Store OAuth metadata in the session
        session.oauth_metadata = {
            "provider": provider,
            "is_new_merchant": is_new,
            "shop_domain": shop_domain,
            "authenticated": True,
            "authenticated_at": datetime.now().isoformat()
        }
        session.merchant_name = merchant_id or (shop_domain.replace(".myshopify.com", "") if shop_domain else 'unknown')
        
        # Backend authority for user ID generation
        if shop_domain:
            try:
                user_id, _ = get_or_create_user(shop_domain)
                session.user_id = user_id
                logger.info(f"[OAUTH_PROCESS] Updated session with user_id: {user_id}")
            except Exception as e:
                logger.error(f"[OAUTH_PROCESS] Failed to get/create user: {e}")

        # Transition to the post-auth workflow
        target_workflow = "shopify_post_auth"
        previous_workflow = session.conversation.workflow
        success = self.platform.session_manager.update_workflow(conversation_id, target_workflow)

        if not success:
            logger.error(f"[OAUTH_PROCESS] Failed to transition workflow for {conversation_id}")
            await self.platform.send_error(websocket, "Failed to update workflow state")
            return
            
        # Notify frontend of the workflow transition
        await websocket.send_json({
            "type": "workflow_updated",
            "data": {"workflow": target_workflow, "previous": previous_workflow }
        })
        
        # Generate the system message that the workflow expects
        if is_new:
            system_message = f"SYSTEM_EVENT: New Shopify merchant authenticated from {shop_domain}"
        else:
            system_message = f"SYSTEM_EVENT: Returning Shopify merchant authenticated from {shop_domain}"
        
        # Process the system message to get CJ's response
        response = await self.platform.message_processor.process_message(
            session=session,
            message=system_message,
            sender="system",
        )
        
        # Send CJ's response back to the user
        if response:
            if isinstance(response, dict) and response.get("type") == "message_with_ui":
                response_data = {
                    "content": response["content"],
                    "factCheckStatus": "available",
                    "timestamp": datetime.now().isoformat(),
                    "ui_elements": response.get("ui_elements", [])
                }
            else:
                response_data = {
                    "content": response,
                    "factCheckStatus": "available",
                    "timestamp": datetime.now().isoformat(),
                }
            
            await websocket.send_json({"type": "cj_message", "data": response_data})
        
        # Send confirmation that OAuth was processed by the backend
        await websocket.send_json({
            "type": "oauth_processed",
            "data": {"success": True, "merchant_id": merchant_id, "shop_domain": shop_domain, "is_new": is_new}
        })
