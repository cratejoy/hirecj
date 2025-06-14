"""Session-related message handlers."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import select, update          # NEW
from shared.db_models import WebSession, MerchantToken, MerchantIntegration, Merchant  # NEW
from app.utils.supabase_util import get_db_session
from typing import Optional, Dict

from fastapi import WebSocket

from app.logging_config import get_logger
from app.models import Message
from app.constants import WebSocketCloseCodes
from shared.protocol.models import (
    StartConversationMsg,
    LogoutMsg,
    OAuthCompleteMsg,
    ConversationStartedMsg,
    ConversationStartedData,
    LogoutCompleteMsg,
    LogoutCompleteData,
    OAuthProcessedMsg,          #  <-- NEW
    OAuthProcessedData,         #  <-- NEW
)

from .session_handler import SessionHandler

if TYPE_CHECKING:
    from .platform import WebPlatform

logger = get_logger(__name__)
websocket_logger = get_logger("websocket")


class SessionHandlers:
    """Handles session-related WebSocket messages."""

    def __init__(self, platform: 'WebPlatform'):
        self.platform = platform
        self.session_handler = SessionHandler(platform)

    async def _select_workflow(
        self,
        ws_session: dict,
        start_data: dict,
        user_id: str | None,
    ) -> tuple[str | None, str | None, str]:
        """Return (merchant, scenario, workflow) to start with – single authority."""
        merchant  = start_data.get("merchant_id")
        scenario  = start_data.get("scenario") or "default"
        workflow  = "shopify_onboarding"

        logger.info(f"[WORKFLOW] _select_workflow called with user_id={user_id}, ws_session.data={ws_session.get('data', {})}")
        logger.info(f"[WORKFLOW] start_data from client: {start_data}")

        # 1. explicit override set by auth-callback
        override = (ws_session.get("data") or {}).pop("next_workflow", None)
        if override:
            logger.info(f"[WORKFLOW] Using explicit next_workflow override: {override}")
            workflow = override
            # If we're switching to post_auth workflow, also update scenario
            if workflow == "shopify_post_auth":
                scenario = "post_auth"
                # Also try to get merchant from active integration
                if user_id:
                    shop_domain = self._get_active_shopify_domain(user_id)
                    if shop_domain:
                        merchant = shop_domain.replace(".myshopify.com", "")
                        logger.info(f"[WORKFLOW] Set merchant to {merchant} from active integration")
            await self._clear_session_flag(ws_session)

        # 2. client-requested workflow
        elif w := start_data.get("workflow"):
            workflow = w

        # 3. user already has an active Shopify integration ⇒ start in post-auth
        elif user_id:
            shop_domain = self._get_active_shopify_domain(user_id)
            if shop_domain:
                merchant = shop_domain.replace(".myshopify.com", "")
                workflow = "shopify_post_auth"
                scenario = "post_auth"

        # 4. skip onboarding when already authed
        if user_id and workflow == "shopify_onboarding":
            workflow = "ad_hoc_support"

        # fallback merchant for non-auth flows
        if not merchant:
            merchant = "onboarding_user"

        logger.info(f"[WORKFLOW] Final selection: merchant={merchant}, scenario={scenario}, workflow={workflow}")
        return merchant, scenario, workflow

    async def _clear_session_flag(self, ws_session: dict):
        """Remove next_workflow flag from DB (one-shot)."""
        sess_id = ws_session.get("session_id")
        if not sess_id:
            return
        with get_db_session() as db:
            db.execute(
                update(WebSession)
                .where(WebSession.session_id == sess_id)
                .values(data={})
            )
            db.commit()

    def _get_active_shopify_domain(self, user_id: str) -> str | None:
        """Return shop_domain if this user already has an active Shopify integration."""
        with get_db_session() as db:
            return db.scalar(
                select(MerchantToken.shop_domain)
                .join(
                    MerchantIntegration,
                    MerchantIntegration.merchant_id == MerchantToken.merchant_id
                )
                .where(MerchantToken.user_id == user_id)
                .where(MerchantIntegration.platform == "shopify")
                .where(MerchantIntegration.is_active.is_(True))
                .limit(1)
            )

    async def handle_start_conversation(
        self, websocket: WebSocket, conversation_id: str, message: StartConversationMsg
    ):
        """Handle start_conversation message."""
        # Initialize conversation with CrewAI
        start_data = message.data

        ws_session = self.platform.sessions.get(conversation_id, {})
        is_authenticated = ws_session.get("authenticated", False)
        user_id = ws_session.get("user_id") if is_authenticated else None

        merchant, scenario, workflow = await self._select_workflow(
            ws_session, start_data.model_dump(), user_id
        )

        # Get workflow requirements
        workflow_data = self.platform.workflow_loader.get_workflow(workflow)
        requirements = workflow_data.get('requirements', {})

        # Use server-determined values with appropriate defaults
        if not requirements.get('merchant', True):
            if not merchant:
                merchant = "onboarding_user"
        else:
            if not merchant:
                await self.platform.send_error(websocket, "Merchant ID required for this workflow")
                return

        if not requirements.get('scenario', True):
            if not scenario:
                scenario = "default"
        else:
            if not scenario:
                await self.platform.send_error(websocket, "Scenario required for this workflow")
                return

        # Check for existing session first
        logger.info(
            f"[SESSION_CHECK] Looking for existing session: {conversation_id}"
        )
        existing_session = self.platform.session_manager.get_session(conversation_id)
        if existing_session:
            logger.info(
                f"[RECONNECT] Resuming existing session for {conversation_id}"
            )
            logger.info(
                f"[RECONNECT] Session has {len(existing_session.conversation.messages)} messages"
            )
            session = existing_session
            workflow = session.conversation.workflow
            logger.info(f"[RECONNECT] Preserving existing session workflow: {workflow}")
        else:
            logger.info(
                f"[NEW_SESSION] Creating new session for {conversation_id}"
            )
            try:
                ws_session = self.platform.sessions.get(conversation_id, {})
                user_id = ws_session.get("user_id") if ws_session.get("user_id") != "anonymous" else None

                session = await self.session_handler.create_session(
                    conversation_id, merchant, scenario, workflow, ws_session, user_id
                )
            except ValueError as e:
                error_msg = str(e)
                logger.error(f"Failed to start conversation: {error_msg}")
                await self.platform.send_error(
                    websocket, f"Cannot start conversation: {error_msg}"
                )
                await websocket.close(
                    code=WebSocketCloseCodes.INTERNAL_ERROR,
                    reason="Universe not found",
                )
                return
            except Exception as e:
                logger.error(f"Unexpected error starting conversation: {e}")
                await self.platform.send_error(
                    websocket,
                    "Failed to start conversation due to internal error",
                )
                await websocket.close(
                    code=WebSocketCloseCodes.INTERNAL_ERROR,
                    reason="Internal error",
                )
                return

        conversation_started_data = ConversationStartedData(
            conversationId=conversation_id,
            merchantId=merchant,
            scenario=scenario,
            workflow=workflow,
            sessionId=session.id,
            workflow_requirements=requirements,
            user_id=session.user_id,
        )

        if existing_session:
            # Include message history for resumed conversations
            conversation_started_data.resumed = True
            conversation_started_data.messageCount = len(session.conversation.messages)
            conversation_started_data.messages = [
                {
                    "sender": msg.sender,
                    "content": msg.content,
                    "timestamp": (
                        msg.timestamp.isoformat()
                        if hasattr(msg.timestamp, "isoformat")
                        else str(msg.timestamp)
                    ),
                }
                for msg in session.conversation.messages[-10:]  # Last 10 messages
            ]

        conversation_started_msg = ConversationStartedMsg(
            type="conversation_started",
            data=conversation_started_data
        )
        await self.platform.send_validated_message(websocket, conversation_started_msg)

        from .workflow_handlers import WorkflowHandlers
        workflow_handlers = WorkflowHandlers(self.platform)

        await workflow_handlers._setup_progress_callback(websocket)
        await workflow_handlers._handle_initial_workflow_action(websocket, session, workflow)


    async def handle_logout(
        self, websocket: WebSocket, conversation_id: str, message: LogoutMsg
    ):
        """Handle logout message."""
        logger.info(f"[LOGOUT] Processing logout request for conversation {conversation_id}")
        
        # End any active session
        session = self.platform.session_manager.get_session(conversation_id)
        if session:
            # Save conversation before logout
            self.platform.conversation_storage.save_session(session)
            # Remove session
            self.platform.session_manager.end_session(conversation_id)
            logger.info(f"[LOGOUT] Ended session for conversation {conversation_id}")
        
        # Clear WebSocket session data
        if conversation_id in self.platform.sessions:
            del self.platform.sessions[conversation_id]
            logger.info(f"[LOGOUT] Cleared WebSocket session data")
        
        # Send logout confirmation
        logout_complete = LogoutCompleteMsg(
            type="logout_complete",
            data=LogoutCompleteData(
                message="Successfully logged out"
            )
        )
        await self.platform.send_validated_message(websocket, logout_complete)
        
        # Close WebSocket connection
        await websocket.close()
        logger.info(f"[LOGOUT] Logout complete, connection closed")
    
    async def handle_oauth_complete(
        self, websocket: WebSocket, conversation_id: str, message: OAuthCompleteMsg
    ):
        """
        Persist OAuth completion info in-memory and acknowledge.

        After this call, session.oauth_metadata is populated so that
        create_cj_agent() will load Shopify tools automatically.
        """
        # ---------------------------------------------------------------
        # ❶ Try to get identifiers from payload, fall back to DB lookup
        # ---------------------------------------------------------------
        data          = message.data or {}
        shop_domain   = data.get("shop_domain")
        merchant_id   = data.get("merchant_id")
        is_new        = data.get("is_new", False)

        # Look-up via authenticated user when anything missing
        ws_session = self.platform.sessions.setdefault(conversation_id, {})
        user_id    = ws_session.get("user_id") if ws_session.get("authenticated") else None

        if (not shop_domain or not merchant_id) and user_id:
            # → find active Shopify integration for this user
            shop_domain_db = self._get_active_shopify_domain(user_id)
            if shop_domain_db and not shop_domain:
                shop_domain = shop_domain_db

            if shop_domain and not merchant_id:
                merchant_name = shop_domain.replace(".myshopify.com", "")
                with get_db_session() as db:
                    merchant_id_db = db.scalar(
                        select(Merchant.id).where(Merchant.name == merchant_name)
                    )
                    if merchant_id_db:
                        merchant_id = merchant_id_db

        # If still no shop_domain we can’t proceed
        if not shop_domain:
            await self.platform.send_error(
                websocket,
                "OAuth completed but no active Shopify store found for this user"
            )
            return

        if merchant_id is None:
            raise RuntimeError(
                f"OAuth finished but merchant_id missing for {shop_domain}"
            )

        # Build unified metadata object
        oauth_metadata = {
            "provider": "shopify",
            "authenticated": True,
            "shop_domain": shop_domain,
            "is_new_merchant": is_new,
            "merchant_id": merchant_id,
        }

        # ── 1. Update websocket-session dict ─────────────────────────────
        ws_session = self.platform.sessions.setdefault(conversation_id, {})
        ws_session["oauth_metadata"] = oauth_metadata
        ws_session["shop_domain"] = shop_domain          # NEW
        ws_session["merchant_id"] = merchant_id          # NEW

        # ── 2. Update live Session object if it already exists ───────────
        session_obj = self.platform.session_manager.get_session(conversation_id)
        if session_obj:
            session_obj.oauth_metadata = oauth_metadata

        logger.info(
            f"[OAUTH] Stored oauth_metadata for {conversation_id}: {oauth_metadata}"
        )

        # ── 3. Acknowledge to frontend ───────────────────────────────────
        processed_msg = OAuthProcessedMsg(
            type="oauth_processed",
            data=OAuthProcessedData(
                success=True,
                is_new=is_new,
                merchant_id=merchant_id,
                shop_domain=shop_domain,
            )
        )
        await self.platform.send_validated_message(websocket, processed_msg)
