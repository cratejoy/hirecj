"""
Fact extraction service for learning from merchant conversations.

This service analyzes completed conversations and extracts new facts
about merchants that should be remembered for future interactions.
"""

from typing import List, Optional, Dict
import json
import litellm
from app.models import Conversation, Message
from shared.user_identity import get_user_facts, append_fact
from app.prompts.loader import PromptLoader
from app.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)


class FactExtractor:
    """Extract facts from conversations using LLM analysis."""
    
    def __init__(self, model: str = None):
        """Initialize the fact extractor.
        
        Args:
            model: LLM model to use (default: gpt-4o-mini for efficiency)
        """
        self.prompt_loader = PromptLoader()
        self.model = model or settings.fact_extraction_model or "gpt-4o-mini"
        logger.info(f"[FACT_EXTRACTOR] Initialized with model: {self.model}")
    
    async def extract_and_add_facts(
        self, 
        conversation: Conversation, 
        user_id: str,
        last_n_messages: Optional[int] = None
    ) -> List[str]:
        """Extract new facts from conversation and add to user's facts.
        
        Args:
            conversation: The completed conversation to analyze
            user_id: The user ID to add facts to
            last_n_messages: Only analyze the last N messages (for incremental extraction)
            
        Returns:
            List of newly extracted facts
        """
        try:
            # Get existing facts to avoid duplicates
            user_facts = get_user_facts(user_id)
            existing_facts = [f['fact'] for f in user_facts]
            
            # Debug logging
            logger.info(f"[FACT_EXTRACTOR] ====== FACT EXTRACTION CALLED ======")
            logger.info(f"[FACT_EXTRACTOR] Conversation ID: {conversation.id}")
            logger.info(f"[FACT_EXTRACTOR] Processing mode: {'Incremental (last ' + str(last_n_messages) + ' messages)' if last_n_messages else 'Full conversation'}")
            logger.info(f"[FACT_EXTRACTOR] Total existing facts: {len(existing_facts)}")
            
            if existing_facts:
                logger.info(f"[FACT_EXTRACTOR] === EXISTING FACTS ===")
                for i, fact in enumerate(existing_facts, 1):
                    logger.info(f"[FACT_EXTRACTOR]   {i}. {fact}")
            else:
                logger.info(f"[FACT_EXTRACTOR] No existing facts for this merchant")
            
            # Determine which messages to analyze
            messages_to_analyze = conversation.messages
            if last_n_messages:
                messages_to_analyze = conversation.messages[-last_n_messages:]
                logger.info(f"[FACT_EXTRACTOR] Analyzing only last {last_n_messages} messages")
            
            # Format conversation for analysis
            conversation_text = self._format_conversation(messages_to_analyze)
            
            # Build prompts with existing facts
            prompts = self._build_prompt(
                conversation_text,
                existing_facts
            )
            
            # Extract facts using LLM
            new_facts = await self._extract_facts_with_llm(prompts)
            
            # Add new facts to user's facts
            for fact in new_facts:
                append_fact(user_id, fact, f"conversation_{conversation.id}")
                
            if new_facts:
                logger.info(f"[FACT_EXTRACTOR] === NEW FACTS EXTRACTED ===")
                logger.info(f"[FACT_EXTRACTOR] Extracted {len(new_facts)} new facts:")
                for i, fact in enumerate(new_facts, 1):
                    logger.info(f"[FACT_EXTRACTOR]   {i}. {fact}")
            else:
                logger.info(f"[FACT_EXTRACTOR] No new facts extracted")
            
            logger.info(f"[FACT_EXTRACTOR] ====== FACT EXTRACTION COMPLETE ======")
                
            return new_facts
            
        except Exception as e:
            logger.error(f"[FACT_EXTRACTOR] Error extracting facts: {e}", exc_info=True)
            return []
    
    def _format_conversation(self, messages: List[Message]) -> str:
        """Format conversation messages for extraction.
        
        Args:
            messages: List of messages to format
            
        Returns:
            Formatted conversation text
        """
        lines = []
        
        # Format messages
        for msg in messages:
            # Determine speaker based on sender field
            if msg.sender == "cj":
                speaker = "CJ"
            elif msg.sender == "merchant":
                speaker = "Merchant"
            else:
                speaker = msg.sender.title()
                
            # Add message
            lines.append(f"{speaker}: {msg.content}")
            
        conversation_text = "\n".join(lines)
        logger.debug(f"[FACT_EXTRACTOR] Formatted conversation ({len(lines)} lines, {len(conversation_text)} chars)")
        
        return conversation_text
    
    def _build_prompt(
        self, 
        conversation: str, 
        existing_facts: List[str]
    ) -> Dict[str, str]:
        """Build extraction prompt with existing facts.
        
        Args:
            conversation: Formatted conversation text
            existing_facts: List of already known facts
            
        Returns:
            Dict with 'system' and 'user' prompts for fact extraction
        """
        # Load prompt template
        try:
            prompt_data = self.prompt_loader.load_prompt("fact_extraction", version="latest")
            system_prompt = prompt_data.get("system", "")
            user_prompt_template = prompt_data.get("user", "")
            logger.debug(f"[FACT_EXTRACTOR] Loaded fact extraction prompt template")
        except Exception as e:
            logger.error(f"[FACT_EXTRACTOR] Failed to load prompt template: {e}")
            raise
        
        # Format existing facts section
        existing_facts_text = ""
        if existing_facts:
            existing_facts_text = "\n\nFacts I already know about this merchant:\n"
            existing_facts_text += "\n".join(f"- {fact}" for fact in existing_facts)
            logger.debug(f"[FACT_EXTRACTOR] Including {len(existing_facts)} existing facts in prompt")
        
        # Build final user prompt
        user_prompt = user_prompt_template.format(
            conversation=conversation,
            existing_facts=existing_facts_text
        )
        
        logger.debug(f"[FACT_EXTRACTOR] Built prompts (system: {len(system_prompt)} chars, user: {len(user_prompt)} chars)")
        return {"system": system_prompt, "user": user_prompt}
    
    async def _extract_facts_with_llm(self, prompts: Dict[str, str]) -> List[str]:
        """Extract facts using LLM.
        
        Args:
            prompts: Dict containing 'system' and 'user' prompts
            
        Returns:
            List of extracted facts
        """
        try:
            logger.info(f"[FACT_EXTRACTOR] Calling LLM for fact extraction with model: {self.model}")
            
            # Call LLM with JSON response format
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                temperature=0.2,
                max_tokens=settings.max_tokens_evaluation,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            content = response.choices[0].message.content.strip()
            logger.debug(f"[FACT_EXTRACTOR] LLM response: {content[:200]}..." if len(content) > 200 else f"[FACT_EXTRACTOR] LLM response: {content}")
            
            try:
                # Parse JSON
                data = json.loads(content)
                
                # Extract facts array
                facts = data.get("facts", [])
                
                # Ensure facts is a list
                if not isinstance(facts, list):
                    logger.error(f"[FACT_EXTRACTOR] Invalid response format - facts is not a list: {type(facts)}")
                    return []
                
                # Filter out any non-string facts
                valid_facts = [f for f in facts if isinstance(f, str) and f.strip()]
                
                logger.info(f"[FACT_EXTRACTOR] Extracted {len(valid_facts)} facts from LLM response")
                return valid_facts
                
            except json.JSONDecodeError as e:
                logger.error(f"[FACT_EXTRACTOR] Failed to parse JSON response: {e}")
                logger.error(f"[FACT_EXTRACTOR] Raw response: {content}")
                return []
            
        except Exception as e:
            logger.error(f"[FACT_EXTRACTOR] Error calling LLM: {e}")
            return []