"""Message processing and agent interaction."""

import asyncio
from datetime import datetime
from typing import List, Callable, Dict, Any, Union
import uuid

from crewai import Crew, Task
import litellm

from app.models import Message
from app.agents.cj_agent import create_cj_agent
from app.services.session_manager import Session
from shared.logging_config import get_logger
from app.config import settings
from shared.user_identity import save_conversation_message
from app.agents.tool_output_parser import ToolOutputParser
from app.services.debug_callback import DebugCallback
from app.services.tool_logger import ToolLogger

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

        # Generate unique message ID
        message_id = f"msg_{uuid.uuid4().hex[:8]}"

        # Create debug callback
        debug_callback = DebugCallback(session.id, session.debug_data)
        debug_callback.set_message_id(message_id)
        
        # Store the message_id in session for debugging
        session.debug_data["current_message_id"] = message_id

        # Register with LiteLLM's actual callback lists
        if debug_callback not in litellm.input_callback:
            litellm.input_callback.append(debug_callback)
        if debug_callback not in litellm.success_callback:
            litellm.success_callback.append(debug_callback)
        
        # Debug logging
        logger.info(f"[DEBUG_REGISTRATION] Registered callbacks for {message_id}")
        logger.info(f"[DEBUG_REGISTRATION] input_callback count: {len(litellm.input_callback)}")
        logger.info(f"[DEBUG_REGISTRATION] success_callback count: {len(litellm.success_callback)}")
        logger.info(f"[DEBUG_REGISTRATION] success_callback types: {[type(cb).__name__ for cb in litellm.success_callback]}")

        # Set debug callback for tool logger
        ToolLogger.set_debug_callback(debug_callback)

        try:
            # Create CJ agent
            logger.info(f"[CJ_AGENT] ====== COMPOSING RESPONSE ======")
            logger.info(f"[CJ_AGENT] Merchant: {session.conversation.merchant_name}")
            if session.user_id:
                logger.info(f"[CJ_AGENT] User ID: {session.user_id}")
            else:
                logger.info(f"[CJ_AGENT] No user ID available")
                
            # Pass OAuth metadata if available
            oauth_metadata = getattr(session, 'oauth_metadata', None)
            
            # Create agent (no debug_callback parameter needed!)
            cj_agent = create_cj_agent(
                merchant_name=session.conversation.merchant_name,
                scenario_name=session.conversation.scenario_name,
                workflow_name=session.conversation.workflow,
                conversation_state=session.conversation.state,
                data_agent=session.data_agent,
                user_id=session.user_id,
                oauth_metadata=oauth_metadata,
                verbose=settings.enable_verbose_logging,
                # debug_callback parameter removed - we register directly with LiteLLM
            )
        
            # Set up thinking token callback for this agent BEFORE creating the task
            # Use the conversation_id from the session, not session.id
            from app.services.conversation_thinking_callback import ConversationThinkingCallback
            conversation_id = getattr(session, 'conversation_id', session.id)
            thinking_callback = ConversationThinkingCallback(conversation_id)
            cj_agent.set_thinking_callback(thinking_callback)

            # Create task
            if is_system:
                # For system messages (OAuth context), provide clear instruction
                task_description = f"Context update: {message}\n\nRespond appropriately to this authentication update."
            else:
                # Check if this is from the initial workflow action
                if message.startswith("Start by showing me the daily support snapshot"):
                    task_description = (
                        f"{message}\n\n"
                        "IMPORTANT: You MUST use the get_daily_snapshot tool to fetch yesterday's metrics. "
                        "Do not generate generic content - use the actual tool to get real data."
                    )
                else:
                    task_description = f"Respond to: {message}"
                
            task = Task(
                description=task_description,
                agent=cj_agent,
                expected_output="A helpful response using the appropriate tools when requested",
            )

            # Create crew and execute
            logger.info(f"[MESSAGE_PROCESSOR] Before creating Crew - success callbacks: {[type(cb).__name__ for cb in litellm.success_callback]}")
            
            crew = Crew(agents=[cj_agent], tasks=[task], verbose=settings.enable_verbose_logging)
            
            logger.info(f"[MESSAGE_PROCESSOR] After creating Crew - success callbacks: {[type(cb).__name__ for cb in litellm.success_callback]}")

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
            
            logger.info(f"[MESSAGE_PROCESSOR] Before crew.kickoff() - success callbacks: {[type(cb).__name__ for cb in litellm.success_callback]}")
            
            result = crew.kickoff()
            
            logger.info(f"[MESSAGE_PROCESSOR] After crew.kickoff() - success callbacks: {[type(cb).__name__ for cb in litellm.success_callback]}")

            # Extract response
            response = str(result)
            if hasattr(result, "output"):
                response = result.output

            logger.info(
                f"[LLM_RESPONSE] Got response ({len(response)} chars): {response[:200]}{'...' if len(response) > 200 else ''}"
            )
            logger.info(f"[CJ_AGENT] ====== RESPONSE COMPLETE ======")
            
            # DIAGNOSTIC: Log response generation  
            from datetime import datetime
            has_oauth_complete = "authentication complete" in response.lower()
            logger.warning(f"[MSG_GEN] Message generated - has_oauth_complete={has_oauth_complete}, "
                          f"oauth_metadata_present={bool(session.oauth_metadata)}, "
                          f"workflow={session.conversation.workflow}, timestamp={datetime.now()}, "
                          f"content_preview={response[:100]}...")

            # Only add Shopify OAuth button when store not yet connected
            if session.conversation.workflow == "shopify_onboarding" and session.oauth_metadata is None:
                from app.services.ui_components import UIComponentParser
                parser = UIComponentParser()
                clean_content, ui_components = parser.parse_oauth_buttons(response)

                if ui_components:
                    logger.info(f"[UI_PARSER] Found {len(ui_components)} UI components in response")
                    return {
                        "type": "message_with_ui",
                        "content": clean_content,
                        "ui_elements": ui_components,
                        "message_id": message_id
                    }

            # Consolidate all debug data under the final message_id
            # This ensures thinking content from intermediate LLM calls is available
            all_responses = session.debug_data.get("llm_responses", [])
            
            # First, ensure all responses have the correct message_id
            for resp in all_responses:
                if not resp.get("message_id") or resp.get("message_id") != message_id:
                    logger.info(f"[DEBUG_CONSOLIDATION] Updating response message_id from {resp.get('message_id')} to {message_id}")
                    resp["message_id"] = message_id
            
            # Then consolidate thinking content
            if len(all_responses) > 0:
                logger.info(f"[DEBUG_CONSOLIDATION] Found {len(all_responses)} responses")
                
                # Collect all thinking content from all responses
                all_thinking = []
                for resp in all_responses:
                    if resp.get("thinking_content"):
                        all_thinking.append(resp["thinking_content"])
                
                # If we have thinking content, update the last response
                if all_thinking and all_responses:
                    target_response = all_responses[-1]
                    # Combine all thinking content
                    target_response["thinking_content"] = "\n\n---\n\n".join(all_thinking)
                    logger.info(f"[DEBUG_CONSOLIDATION] Consolidated {len(all_thinking)} thinking sections into message {message_id}")
            
            # Include message_id in response
            if isinstance(response, dict):
                response["message_id"] = message_id
            else:
                # Convert to dict format with message_id
                response = {
                    "type": "message_with_ui",
                    "content": response,
                    "ui_elements": [],
                    "message_id": message_id
                }
            
            return response
            
        finally:
            # Clean up callbacks
            logger.info(f"[DEBUG_CLEANUP] Cleaning up callbacks for {message_id}")
            logger.info(f"[DEBUG_CLEANUP] Before cleanup - input: {len(litellm.input_callback)}, success: {len(litellm.success_callback)}")
            logger.info(f"[DEBUG_CLEANUP] Debug callback in success_callback: {debug_callback in litellm.success_callback}")
            
            if debug_callback in litellm.input_callback:
                litellm.input_callback.remove(debug_callback)
            if debug_callback in litellm.success_callback:
                litellm.success_callback.remove(debug_callback)
                logger.info(f"[DEBUG_CLEANUP] Removed debug callback from success_callback")
            else:
                logger.info(f"[DEBUG_CLEANUP] Debug callback NOT in success_callback!")
                
            logger.info(f"[DEBUG_CLEANUP] After cleanup - input: {len(litellm.input_callback)}, success: {len(litellm.success_callback)}")
            
            debug_callback.finalize()
            ToolLogger.set_debug_callback(None)

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
