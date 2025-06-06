"""Message processing and agent interaction."""

import asyncio
from datetime import datetime
from typing import List, Callable, Dict, Any, Union

from crewai import Crew, Task

from app.models import Message
from app.agents.cj_agent import create_cj_agent
from app.services.session_manager import Session
from app.logging_config import get_logger
from app.config import settings
from shared.user_identity import save_conversation_message

logger = get_logger(__name__)


class MessageProcessor:
    """Processes messages between CJ and merchants."""

    def __init__(self):
        self._progress_callbacks: List[Callable] = []

    def on_progress(self, callback: Callable) -> None:
        """Register progress callback."""
        self._progress_callbacks.append(callback)

    def clear_progress_callbacks(self) -> None:
        """Clear all progress callbacks."""
        self._progress_callbacks.clear()

    async def process_message(
        self,
        session: Session,
        message: str,
        sender: str = "merchant",
    ) -> Union[str, Dict[str, Any]]:
        """Process a message and get response."""
        # Update session
        session.last_activity = datetime.utcnow()
        session.metrics["messages"] += 1

        # For system messages (like OAuth context), don't add to conversation history
        if sender != "system":
            # Add merchant message to conversation
            msg = Message(
                timestamp=datetime.utcnow(),
                sender=sender,
                content=message,
            )
            session.conversation.add_message(msg)
            
            # Save to database if user_id is available
            if session.user_id:
                asyncio.create_task(self._save_message_to_db(session.user_id, msg))
        
        # Extract facts immediately after merchant message (non-blocking)
        if sender == "merchant" and session.user_id:
            asyncio.create_task(self._extract_facts_background(session))

        # Get response
        start_time = datetime.utcnow()

        try:
            if sender in ["merchant", "system"]:
                response = await self._get_cj_response(session, message, is_system=sender=="system")
            else:
                # For now, only support merchant -> CJ flow
                raise ValueError("Only merchant/system -> CJ flow supported")

            # Track metrics
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            session.metrics["response_time_total"] += elapsed

            # Handle structured response with UI elements
            if isinstance(response, dict) and response.get("type") == "message_with_ui":
                # Add the clean content to conversation history
                response_msg = Message(
                    timestamp=datetime.utcnow(),
                    sender="CJ",
                    content=response["content"],
                )
                session.conversation.add_message(response_msg)
                
                # Save to database if user_id is available
                if session.user_id:
                    asyncio.create_task(self._save_message_to_db(session.user_id, response_msg))
                
                # Return the full structured response for the platform layer
                return response
            else:
                # Regular text response
                response_msg = Message(
                    timestamp=datetime.utcnow(),
                    sender="CJ",
                    content=response,
                )
                session.conversation.add_message(response_msg)
                
                # Save to database if user_id is available
                if session.user_id:
                    asyncio.create_task(self._save_message_to_db(session.user_id, response_msg))
                
                return response

        except Exception as e:
            session.metrics["errors"] += 1
            logger.error(f"Error processing message: {e}")
            raise

    async def _get_cj_response(self, session: Session, message: str, is_system: bool = False) -> Union[str, Dict[str, Any]]:
        """Get CJ's response to merchant message."""
        await self._report_progress(session.id, "thinking", {"status": "initializing"})

        # Update conversation state
        session.conversation.state.context_window = session.conversation.messages[-10:]

        # Create CJ agent
        logger.info(f"[CJ_AGENT] ====== COMPOSING RESPONSE ======")
        logger.info(f"[CJ_AGENT] Merchant: {session.conversation.merchant_name}")
        if session.user_id:
            logger.info(f"[CJ_AGENT] User ID: {session.user_id}")
        else:
            logger.info(f"[CJ_AGENT] No user ID available")
            
        # Pass OAuth metadata if available
        oauth_metadata = getattr(session, 'oauth_metadata', None)
        
        cj_agent = create_cj_agent(
            merchant_name=session.conversation.merchant_name,
            scenario_name=session.conversation.scenario_name,
            workflow_name=session.conversation.workflow,
            conversation_state=session.conversation.state,
            data_agent=session.data_agent,
            user_id=session.user_id,
            oauth_metadata=oauth_metadata,
            verbose=settings.enable_verbose_logging,
        )

        # Create task
        if is_system:
            # For system messages (OAuth context), provide clear instruction
            task_description = f"Context update: {message}\n\nRespond appropriately to this authentication update."
        else:
            task_description = f"Respond to: {message}"
            
        task = Task(
            description=task_description,
            agent=cj_agent,
            expected_output="A helpful response",
        )

        # Create crew and execute
        crew = Crew(agents=[cj_agent], tasks=[task], verbose=settings.enable_verbose_logging)

        await self._report_progress(session.id, "thinking", {"status": "generating"})

        # Log LLM prompt with chat history context
        context_messages = [
            f"{msg.sender}: {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}"
            for msg in session.conversation.state.context_window
        ]
        logger.info(
            f"[LLM_PROMPT] Prompting LLM for session {session.id}\n"
            f"  User message: '{message}'\n"
            f"  Chat history ({len(context_messages)} messages):\n"
            + "\n".join(f"    {msg}" for msg in context_messages)
        )

        result = crew.kickoff()

        # Extract response
        response = str(result)
        if hasattr(result, "output"):
            response = result.output

        logger.info(
            f"[LLM_RESPONSE] Got response ({len(response)} chars): {response[:200]}{'...' if len(response) > 200 else ''}"
        )
        logger.info(f"[CJ_AGENT] ====== RESPONSE COMPLETE ======")

        # Only parse UI components if workflow has them enabled
        if session.conversation.workflow == "shopify_onboarding":
            from app.services.ui_components import UIComponentParser
            parser = UIComponentParser()
            clean_content, ui_components = parser.parse_oauth_buttons(response)

            if ui_components:
                logger.info(f"[UI_PARSER] Found {len(ui_components)} UI components in response")
                return {
                    "type": "message_with_ui",
                    "content": clean_content,
                    "ui_elements": ui_components
                }

        return response

    async def _report_progress(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Report progress to callbacks."""
        event = {
            "session_id": session_id,
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        for callback in self._progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    async def _extract_facts_background(self, session: Session):
        """Extract facts in background without blocking conversation."""
        try:
            logger.info(f"[REAL_TIME_FACTS] Starting extraction for conversation {session.id}")
            
            # Only analyze last 4 messages (2 exchanges) for efficiency
            from app.services.fact_extractor import FactExtractor
            fact_extractor = FactExtractor()
            new_facts = await fact_extractor.extract_and_add_facts(
                session.conversation, 
                session.user_id,
                last_n_messages=4
            )
            
            if new_facts:
                logger.info(f"[REAL_TIME_FACTS] Extracted {len(new_facts)} new facts")
                    
        except Exception as e:
            logger.error(f"[REAL_TIME_FACTS] Error extracting facts: {e}", exc_info=True)
    
    async def _save_message_to_db(self, user_id: str, message: Message):
        """Save message to database in background without blocking conversation."""
        try:
            # Convert Message object to dict for database storage
            message_data = {
                "sender": message.sender,
                "content": message.content,
                "timestamp": message.timestamp.isoformat()
            }
            
            # Save to database (this is synchronous but runs in background task)
            save_conversation_message(user_id, message_data)
            logger.debug(f"[DB_SAVE] Saved message from {message.sender} for user {user_id}")
            
        except Exception as e:
            # Log error but don't fail the conversation
            logger.error(f"[DB_SAVE] Failed to save message to database: {e}", exc_info=True)
