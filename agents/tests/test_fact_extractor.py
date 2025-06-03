"""Tests for FactExtractor service."""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.services.fact_extractor import FactExtractor
from app.services.merchant_memory import MerchantMemory
from app.models import Conversation, Message


class TestFactExtractor:
    """Test FactExtractor class."""
    
    def test_init_default_model(self):
        """Test initialization with default model."""
        extractor = FactExtractor()
        assert extractor.model == "gpt-4o-mini"
        assert extractor.prompt_loader is not None
        
    def test_init_custom_model(self):
        """Test initialization with custom model."""
        extractor = FactExtractor(model="gpt-4")
        assert extractor.model == "gpt-4"
        
    def test_format_conversation_basic(self):
        """Test basic conversation formatting."""
        # Create test conversation
        conversation = Conversation(
            id="test-123",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        
        # Add messages
        conversation.messages = [
            Message(
                timestamp=datetime.utcnow(),
                sender="merchant",
                content="Hello, I need help"
            ),
            Message(
                timestamp=datetime.utcnow(),
                sender="cj",
                content="Hi! I'm CJ, how can I help?"
            ),
            Message(
                timestamp=datetime.utcnow(),
                sender="merchant",
                content="My shipping is delayed"
            ),
        ]
        
        extractor = FactExtractor()
        formatted = extractor._format_conversation(conversation.messages)
        
        # Check formatting - should only have messages, no metadata
        assert "Conversation ID:" not in formatted
        assert "Scenario:" not in formatted
        assert "Merchant: Hello, I need help" in formatted
        assert "CJ: Hi! I'm CJ, how can I help?" in formatted
        assert "Merchant: My shipping is delayed" in formatted
        
    def test_format_conversation_empty(self):
        """Test conversation formatting with no messages."""
        conversation = Conversation(
            id="test-456",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            workflow="daily_briefing",
            created_at=datetime.utcnow()
        )
        conversation.messages = []
        
        extractor = FactExtractor()
        formatted = extractor._format_conversation(conversation.messages)
        
        # Should return empty string for empty conversation
        assert formatted == ""
        
    def test_build_prompt_no_existing_facts(self):
        """Test prompt building with no existing facts."""
        extractor = FactExtractor()
        
        prompts = extractor._build_prompt(
            conversation="Test conversation",
            existing_facts=[]
        )
        
        # Should return dict with system and user prompts
        assert isinstance(prompts, dict)
        assert "system" in prompts
        assert "user" in prompts
        assert "Test conversation" in prompts["user"]
        assert "Facts I already know" not in prompts["user"]
        
    def test_build_prompt_with_existing_facts(self):
        """Test prompt building with existing facts."""
        extractor = FactExtractor()
        
        existing_facts = [
            "Prefers email communication",
            "Peak season is November-December",
            "Uses Shopify Plus"
        ]
        
        prompts = extractor._build_prompt(
            conversation="Test conversation",
            existing_facts=existing_facts
        )
        
        # Check prompt includes existing facts
        assert isinstance(prompts, dict)
        assert "Facts I already know about this merchant:" in prompts["user"]
        assert "- Prefers email communication" in prompts["user"]
        assert "- Peak season is November-December" in prompts["user"]
        assert "- Uses Shopify Plus" in prompts["user"]
        
    @pytest.mark.asyncio
    async def test_extract_and_add_facts_structure(self):
        """Test extract_and_add_facts method structure (no LLM yet)."""
        # Create test data
        conversation = Conversation(
            id="test-789",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        conversation.messages = [
            Message(
                timestamp=datetime.utcnow(),
                sender="merchant",
                content="We use Shopify Plus"
            ),
        ]
        
        memory = MerchantMemory("test_merchant")
        memory.add_fact("Existing fact", "old_conv")
        
        # Create extractor
        extractor = FactExtractor()
        
        # Call extract_and_add_facts (should return empty list in Phase 8)
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        # In Phase 8, no facts are extracted yet
        assert new_facts == []
        assert len(memory.facts) == 1  # Only the existing fact
        
    @pytest.mark.asyncio
    async def test_extract_and_add_facts_error_handling(self):
        """Test error handling in extract_and_add_facts."""
        # Create conversation with no messages (will cause error)
        conversation = Mock()
        conversation.id = "error-test"
        conversation.messages = None  # This will cause an error
        
        memory = MerchantMemory("test_merchant")
        
        extractor = FactExtractor()
        
        # Should handle error gracefully
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        assert new_facts == []  # Returns empty list on error
        
    @patch('app.services.fact_extractor.PromptLoader')
    def test_prompt_loader_integration(self, mock_prompt_loader_class):
        """Test that PromptLoader is properly initialized and used."""
        # Create mock prompt loader
        mock_loader = Mock()
        mock_prompt_loader_class.return_value = mock_loader
        
        # Create extractor
        extractor = FactExtractor()
        
        # Verify prompt loader was created
        mock_prompt_loader_class.assert_called_once()
        assert extractor.prompt_loader == mock_loader
        
        # Test that it tries to load prompt
        mock_loader.load_prompt.return_value = {
            "system": "Test system prompt",
            "user": "Test prompt {conversation} {existing_facts}"
        }
        
        prompts = extractor._build_prompt("conv", [])
        
        # Verify load_prompt was called
        mock_loader.load_prompt.assert_called_once_with("fact_extraction", version="latest")
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_extract_facts_with_llm_success(self, mock_acompletion):
        """Test successful LLM fact extraction."""
        # Mock LLM response with JSON format
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": [
                "Uses Shopify Plus for their online store",
                "Peak season is November-December",
                "Prefers email communication",
                "Ships internationally to 15 countries"
            ]
        })
        mock_acompletion.return_value = mock_response
        
        extractor = FactExtractor()
        prompts = {"system": "Test system prompt", "user": "Test user prompt"}
        facts = await extractor._extract_facts_with_llm(prompts)
        
        assert len(facts) == 4
        assert "Uses Shopify Plus for their online store" in facts
        assert "Peak season is November-December" in facts
        assert "Prefers email communication" in facts
        assert "Ships internationally to 15 countries" in facts
        
        # Verify LLM was called correctly
        mock_acompletion.assert_called_once()
        call_args = mock_acompletion.call_args
        assert call_args.kwargs['model'] == 'gpt-4o-mini'
        assert call_args.kwargs['temperature'] == 0.2
        assert call_args.kwargs['response_format'] == {"type": "json_object"}
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_extract_facts_with_llm_no_bullets(self, mock_acompletion):
        """Test LLM fact extraction without bullet points."""
        # Mock LLM response with JSON format
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": [
                "Uses Shopify Plus",
                "Peak season is November-December",
                "Prefers email communication"
            ]
        })
        mock_acompletion.return_value = mock_response
        
        extractor = FactExtractor()
        prompts = {"system": "Test system prompt", "user": "Test user prompt"}
        facts = await extractor._extract_facts_with_llm(prompts)
        
        assert len(facts) == 3
        assert "Uses Shopify Plus" in facts
        assert "Peak season is November-December" in facts
        assert "Prefers email communication" in facts
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_extract_facts_with_llm_error(self, mock_acompletion):
        """Test LLM fact extraction error handling."""
        # Mock LLM error
        mock_acompletion.side_effect = Exception("LLM API error")
        
        extractor = FactExtractor()
        prompts = {"system": "Test system prompt", "user": "Test user prompt"}
        facts = await extractor._extract_facts_with_llm(prompts)
        
        # Should return empty list on error
        assert facts == []
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_extract_facts_with_llm_empty_facts(self, mock_acompletion):
        """Test LLM fact extraction when no facts are found."""
        # Mock LLM response with empty facts array
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": []
        })
        mock_acompletion.return_value = mock_response
        
        extractor = FactExtractor()
        prompts = {"system": "Test system prompt", "user": "Test user prompt"}
        facts = await extractor._extract_facts_with_llm(prompts)
        
        # Should return empty list
        assert facts == []
        assert len(facts) == 0
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_extract_and_add_facts_full_flow(self, mock_acompletion):
        """Test complete fact extraction and adding flow."""
        # Mock LLM response with JSON format
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": ["Uses custom shipping integration"]
        })
        mock_acompletion.return_value = mock_response
        
        # Create test data
        conversation = Conversation(
            id="test-full",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        conversation.messages = [
            Message(
                timestamp=datetime.utcnow(),
                sender="merchant",
                content="We built our own shipping integration"
            ),
        ]
        
        memory = MerchantMemory("test_merchant")
        memory.add_fact("Existing fact", "old_conv")
        
        # Create extractor
        extractor = FactExtractor()
        
        # Extract and add facts
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        # Verify results
        assert len(new_facts) == 1
        assert "Uses custom shipping integration" in new_facts
        
        # Verify fact was added to memory
        all_facts = memory.get_all_facts()
        assert len(all_facts) == 2  # Existing + new
        assert "Uses custom shipping integration" in all_facts