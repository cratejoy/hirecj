"""Session-related message handlers."""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta
from sqlalchemy import select, update
from shared.db_models import WebSession, MerchantToken
from app.utils.supabase_util import get_db_session

from fastapi import WebSocket

from app.logging_config import get_logger
from app.models import Message
from app.constants import WebSocketCloseCodes

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

        # 1. explicit override set by auth-callback
        override = (ws_session.get("data") or {}).pop("next_workflow", None)
        if override:
            workflow = override
            await self._clear_session_flag(ws_session)

        # 2. client-requested workflow
        elif w := start_data.get("workflow"):
            workflow = w

        # 3. recent OAuth heuristic
        elif user_id:
            mt = self._get_latest_token(user_id)
            if mt:
                merchant = mt.shop_domain.replace(".myshopify.com", "")
                if mt.created_at > datetime.utcnow() - timedelta(minutes=5):
                    workflow = "shopify_post_auth"
                    scenario = "post_auth"

        # 4. skip onboarding when already authed
        if user_id and workflow == "shopify_onboarding":
            workflow = "ad_hoc_support"

        # fallback merchant for non-auth flows
        if not merchant:
            merchant = "onboarding_user"

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

    def _get_latest_token(self, user_id: str):
        """Return latest MerchantToken row or None."""
        with get_db_session() as db:
            return db.scalar(
                select(MerchantToken)
                .where(MerchantToken.user_id == user_id)
                .order_by(MerchantToken.created_at.desc())
                .limit(1)
            )

    async def handle_start_conversation(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
    ):
        """Handle start_conversation message."""
        # Initialize conversation with CrewAI
        start_data = data.get("data", {})
        if not isinstance(start_data, dict):
            await self.platform.send_error(
                websocket, "Invalid start_conversation data format"
            )
            return

        ws_session = self.platform.sessions.get(conversation_id, {})
        is_authenticated = ws_session.get("authenticated", False)
        user_id = ws_session.get("user_id") if is_authenticated else None

        merchant, scenario, workflow = await self._select_workflow(
            ws_session, start_data, user_id
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

        conversation_data = {
            "conversationId": conversation_id,
            "merchantId": merchant,
            "scenario": scenario,
            "workflow": workflow,
            "sessionId": session.id,
            "workflow_requirements": requirements,
            "user_id": session.user_id,
        }

        if existing_session:
            # Include message history for resumed conversations
            conversation_data["resumed"] = True
            conversation_data["messageCount"] = len(
                session.conversation.messages
            )
            conversation_data["messages"] = [
                {
                    "sender": msg.sender,
                    "content": msg.content,
                    "timestamp": (
                        msg.timestamp.isoformat()
                        if hasattr(msg.timestamp, "isoformat")
                        else str(msg.timestamp)
                    ),
                }
                for msg in session.conversation.messages[
                    -10:
                ]  # Last 10 messages
            ]

        await websocket.send_json(
            {
                "type": "conversation_started",
                "data": conversation_data,
            }
        )

        from .workflow_handlers import WorkflowHandlers
        workflow_handlers = WorkflowHandlers(self.platform)

        await workflow_handlers._setup_progress_callback(websocket)
        await workflow_handlers._handle_initial_workflow_action(websocket, session, workflow)


    async def handle_logout(
        self, websocket: WebSocket, conversation_id: str, data: Dict[str, Any]
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
        await websocket.send_json({
            "type": "logout_complete",
            "data": {
                "message": "Successfully logged out"
            }
        })
        
        # Close WebSocket connection
        await websocket.close()
        logger.info(f"[LOGOUT] Logout complete, connection closed")
