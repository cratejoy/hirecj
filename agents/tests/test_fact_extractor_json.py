"""Comprehensive tests for JSON-based FactExtractor service."""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.services.fact_extractor import FactExtractor
from app.services.merchant_memory import MerchantMemory
from app.models import Conversation, Message


class TestFactExtractorJSON:
    """Test FactExtractor with JSON response format."""
    
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_extract_durable_business_facts(self, mock_acompletion):
        """Test extraction of durable business facts."""
        # Create conversation with good facts
        conversation = Conversation(
            id="test-business",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        
        conversation.messages = [
            Message(timestamp=datetime.utcnow(), sender="cj", content="Hi! Tell me about your business"),
            Message(timestamp=datetime.utcnow(), sender="merchant", content="I'm Sarah Chen, I run TechGear Pro"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="Nice to meet you Sarah!"),
            Message(timestamp=datetime.utcnow(), sender="merchant", content="We've been selling electronics since 2019. Based in Austin."),
        ]
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": [
                "My name is Sarah Chen",
                "I run TechGear Pro",
                "We've been selling electronics since 2019",
                "Based in Austin"
            ]
        })
        mock_acompletion.return_value = mock_response
        
        # Test extraction
        extractor = FactExtractor()
        memory = MerchantMemory(merchant_id="test_merchant")
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        assert len(new_facts) == 4
        assert "My name is Sarah Chen" in new_facts
        assert "I run TechGear Pro" in new_facts
        assert "We've been selling electronics since 2019" in new_facts
        assert "Based in Austin" in new_facts
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_ignore_temporal_facts(self, mock_acompletion):
        """Test that temporal/current state facts are not extracted."""
        # Create conversation with mix of good and bad facts
        conversation = Conversation(
            id="test-temporal",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        
        conversation.messages = [
            Message(timestamp=datetime.utcnow(), sender="merchant", content="I have 50 tickets in my queue right now"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="That's a lot! Tell me about your business"),
            Message(timestamp=datetime.utcnow(), sender="merchant", content="I'm the founder of CloudSync. Our CSAT is 4.5 today"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="Great score!"),
        ]
        
        # Mock LLM response (should only extract durable fact)
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": ["I'm the founder of CloudSync"]
        })
        mock_acompletion.return_value = mock_response
        
        # Test extraction
        extractor = FactExtractor()
        memory = MerchantMemory(merchant_id="test_merchant")
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        assert len(new_facts) == 1
        assert "I'm the founder of CloudSync" in new_facts
        # Temporal facts should NOT be extracted
        assert not any("50 tickets" in fact for fact in new_facts)
        assert not any("CSAT" in fact for fact in new_facts)
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_empty_facts_response(self, mock_acompletion):
        """Test handling of conversations with no extractable facts."""
        # Create conversation with no facts
        conversation = Conversation(
            id="test-empty",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        
        conversation.messages = [
            Message(timestamp=datetime.utcnow(), sender="merchant", content="hi"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="Hello! How can I help?"),
            Message(timestamp=datetime.utcnow(), sender="merchant", content="just checking in"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="All good?"),
        ]
        
        # Mock LLM response with empty facts
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": []
        })
        mock_acompletion.return_value = mock_response
        
        # Test extraction
        extractor = FactExtractor()
        memory = MerchantMemory(merchant_id="test_merchant")
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        assert new_facts == []
        assert len(memory.facts) == 0
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_ignore_cj_observations(self, mock_acompletion):
        """Test that CJ's observations are not extracted as facts."""
        # Create conversation where CJ makes observations
        conversation = Conversation(
            id="test-cj-obs",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        
        conversation.messages = [
            Message(timestamp=datetime.utcnow(), sender="cj", content="You seem to prefer casual communication"),
            Message(timestamp=datetime.utcnow(), sender="merchant", content="yeah whatever works"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="I notice you're online in the evenings"),
            Message(timestamp=datetime.utcnow(), sender="merchant", content="yep"),
        ]
        
        # Mock LLM response (should be empty)
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": []
        })
        mock_acompletion.return_value = mock_response
        
        # Test extraction
        extractor = FactExtractor()
        memory = MerchantMemory(merchant_id="test_merchant")
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        assert new_facts == []
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_incremental_extraction(self, mock_acompletion):
        """Test incremental extraction with last_n_messages."""
        # Create conversation with many messages
        conversation = Conversation(
            id="test-incremental",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        
        # Add 6 messages
        conversation.messages = [
            Message(timestamp=datetime.utcnow(), sender="merchant", content="I'm John from earlier"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="Hi John!"),
            Message(timestamp=datetime.utcnow(), sender="merchant", content="Remember I told you about my store?"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="Yes, tell me more"),
            Message(timestamp=datetime.utcnow(), sender="merchant", content="We just moved to Denver"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="Great location!"),
        ]
        
        # Mock LLM response (only from last 4 messages)
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": ["We just moved to Denver"]
        })
        mock_acompletion.return_value = mock_response
        
        # Test extraction with last_n_messages
        extractor = FactExtractor()
        memory = MerchantMemory(merchant_id="test_merchant")
        new_facts = await extractor.extract_and_add_facts(
            conversation, 
            memory, 
            last_n_messages=4
        )
        
        assert len(new_facts) == 1
        assert "We just moved to Denver" in new_facts
        
        # Verify LLM was called with only last 4 messages
        call_args = mock_acompletion.call_args
        user_prompt = call_args.kwargs['messages'][1]['content']
        assert "We just moved to Denver" in user_prompt
        assert "I'm John from earlier" not in user_prompt  # Should not include old messages
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_malformed_json_response(self, mock_acompletion):
        """Test handling of malformed JSON responses."""
        # Create test conversation
        conversation = Conversation(
            id="test-malformed",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        conversation.add_message(Message(
            timestamp=datetime.utcnow(),
            sender="merchant",
            content="My name is Test"
        ))
        
        # Mock malformed JSON response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is not valid JSON"
        mock_acompletion.return_value = mock_response
        
        # Test extraction
        extractor = FactExtractor()
        memory = MerchantMemory(merchant_id="test_merchant")
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        # Should return empty list on JSON parse error
        assert new_facts == []
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_missing_facts_key_in_json(self, mock_acompletion):
        """Test handling when JSON response doesn't have 'facts' key."""
        # Create test conversation
        conversation = Conversation(
            id="test-missing-key",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        conversation.add_message(Message(
            timestamp=datetime.utcnow(),
            sender="merchant",
            content="My name is Test"
        ))
        
        # Mock JSON response without 'facts' key
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "results": ["Some fact"]  # Wrong key
        })
        mock_acompletion.return_value = mock_response
        
        # Test extraction
        extractor = FactExtractor()
        memory = MerchantMemory(merchant_id="test_merchant")
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        # Should return empty list when 'facts' key is missing
        assert new_facts == []
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_facts_not_list_in_json(self, mock_acompletion):
        """Test handling when 'facts' is not a list in JSON response."""
        # Create test conversation
        conversation = Conversation(
            id="test-not-list",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        conversation.add_message(Message(
            timestamp=datetime.utcnow(),
            sender="merchant",
            content="My name is Test"
        ))
        
        # Mock JSON response where facts is not a list
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": "This should be a list"  # String instead of list
        })
        mock_acompletion.return_value = mock_response
        
        # Test extraction
        extractor = FactExtractor()
        memory = MerchantMemory(merchant_id="test_merchant")
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        # Should return empty list when facts is not a list
        assert new_facts == []
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_existing_facts_not_duplicated(self, mock_acompletion):
        """Test that existing facts are passed to LLM to avoid duplicates."""
        # Create conversation
        conversation = Conversation(
            id="test-existing",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        
        conversation.messages = [
            Message(timestamp=datetime.utcnow(), sender="merchant", content="I'm Sarah Chen"),
            Message(timestamp=datetime.utcnow(), sender="cj", content="Hi Sarah!"),
        ]
        
        # Create memory with existing facts
        memory = MerchantMemory(merchant_id="test_merchant")
        memory.add_fact("I run TechGear Pro", "previous-conv")
        memory.add_fact("Based in Austin", "previous-conv")
        
        # Mock LLM response (only new fact)
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": ["My name is Sarah Chen"]
        })
        mock_acompletion.return_value = mock_response
        
        # Test extraction
        extractor = FactExtractor()
        new_facts = await extractor.extract_and_add_facts(conversation, memory)
        
        assert len(new_facts) == 1
        assert "My name is Sarah Chen" in new_facts
        
        # Verify existing facts were passed to LLM
        call_args = mock_acompletion.call_args
        user_prompt = call_args.kwargs['messages'][1]['content']
        assert "I run TechGear Pro" in user_prompt
        assert "Based in Austin" in user_prompt
        
    @pytest.mark.asyncio
    @patch('app.services.fact_extractor.litellm.acompletion')
    async def test_response_format_parameter(self, mock_acompletion):
        """Test that response_format is set correctly in LLM call."""
        # Create minimal conversation
        conversation = Conversation(
            id="test-format",
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            created_at=datetime.utcnow()
        )
        conversation.add_message(Message(
            timestamp=datetime.utcnow(),
            sender="merchant",
            content="Test"
        ))
        
        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({"facts": []})
        mock_acompletion.return_value = mock_response
        
        # Test extraction
        extractor = FactExtractor()
        memory = MerchantMemory(merchant_id="test_merchant")
        await extractor.extract_and_add_facts(conversation, memory)
        
        # Verify response_format was set
        call_args = mock_acompletion.call_args
        assert call_args.kwargs['response_format'] == {"type": "json_object"}
        assert call_args.kwargs['model'] == 'gpt-4o-mini'
        assert call_args.kwargs['temperature'] == 0.2