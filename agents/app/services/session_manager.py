"""Session lifecycle management."""

from datetime import datetime
from typing import Dict, Optional
import uuid

from app.models import Conversation, ConversationState
from app.agents.universe_data_agent import UniverseDataAgent
from app.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)


class Session:
    """Lightweight session object."""

    def __init__(
        self,
        conversation: Conversation,
        data_agent: Optional[UniverseDataAgent] = None,
        merchant_name: Optional[str] = None,
        scenario_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.conversation = conversation
        self.data_agent = data_agent
        self.merchant_name = merchant_name or conversation.merchant_name
        self.scenario_name = scenario_name or conversation.scenario_name
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.is_active = True
        self.metrics = {
            "messages": 0,
            "errors": 0,
            "response_time_total": 0.0,
        }


class SessionManager:
    """Manages conversation sessions."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(
        self,
        merchant_name: str,
        scenario_name: str,
        workflow_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Session:
        """Create a new session."""
        conversation = Conversation(
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            scenario_name=scenario_name,
            merchant_name=merchant_name,
            workflow=workflow_name,
            state=ConversationState(workflow=workflow_name),
        )

        # Load universe data if provided
        data_agent = None
        if merchant_name and scenario_name:
            try:
                data_agent = UniverseDataAgent(merchant_name, scenario_name)
                logger.info(f"Loaded universe for {merchant_name}/{scenario_name}")
            except FileNotFoundError:
                # This is expected - not all scenarios have universe data
                logger.info(f"No universe data for {merchant_name}/{scenario_name}")
                data_agent = None
            except Exception as e:
                # Real errors should fail fast
                logger.error(f"Failed to load universe for {merchant_name}/{scenario_name}: {e}")
                raise

        session = Session(
            conversation, 
            data_agent, 
            merchant_name, 
            scenario_name,
            user_id=user_id
        )
        self._sessions[session.id] = session
        logger.info(f"Created session {session.id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get active session by ID."""
        return self._sessions.get(session_id)

    def suspend_session(self, session_id: str) -> None:
        """Mark session as inactive."""
        if session_id in self._sessions:
            self._sessions[session_id].is_active = False
            logger.info(f"Suspended session {session_id}")

    def resume_session(self, session_id: str) -> bool:
        """Resume suspended session."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.is_active = True
            session.last_activity = datetime.utcnow()
            logger.info(f"Resumed session {session_id}")
            return True
        return False
    
    def update_workflow(self, session_id: str, new_workflow: str) -> bool:
        """Update session workflow mid-conversation."""
        session = self.get_session(session_id)
        if session:
            # Store previous workflow for logging
            previous_workflow = session.conversation.workflow
            
            # Update both places workflow is stored
            session.conversation.workflow = new_workflow
            session.conversation.state.workflow = new_workflow
            
            # Load new workflow data
            from app.workflows.loader import WorkflowLoader
            workflow_loader = WorkflowLoader()
            workflow_data = workflow_loader.load_workflow(new_workflow)
            if workflow_data:
                session.conversation.state.workflow_details = workflow_data.get("workflow", "")
            
            logger.info(f"[WORKFLOW_SWITCH] {session_id}: {previous_workflow} → {new_workflow}")
            return True
        return False

    def end_session(self, session_id: str) -> Optional[Session]:
        """End and remove session."""
        return self._sessions.pop(session_id, None)

    def cleanup_inactive(self, timeout_minutes: int = None) -> int:
        """Remove inactive sessions."""
        if timeout_minutes is None:
            timeout_minutes = settings.session_cleanup_timeout // 60

        now = datetime.utcnow()
        to_remove = []

        for session_id, session in self._sessions.items():
            inactive_minutes = (now - session.last_activity).total_seconds() / 60
            if inactive_minutes > timeout_minutes:
                to_remove.append(session_id)

        for session_id in to_remove:
            self.end_session(session_id)

        logger.info(f"Cleaned up {len(to_remove)} inactive sessions")
        return len(to_remove)
