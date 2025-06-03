"""Tests for Session with merchant memory integration."""

from datetime import datetime
from unittest.mock import Mock

from app.services.session_manager import Session
from app.models import Conversation
from app.services.merchant_memory import MerchantMemory


class TestSessionWithMemory:
    """Test Session class with merchant memory."""

    def test_session_with_merchant_memory(self):
        """Test session creation with merchant memory."""
        conversation = Conversation(
            id="test-123",
            created_at=datetime.utcnow(),
            scenario_name="test_scenario",
            merchant_name="test_merchant",
        )
        
        # Create a merchant memory
        memory = MerchantMemory("test_merchant")
        memory.add_fact("Test fact", "test_source")

        session = Session(conversation, merchant_memory=memory)

        assert session.merchant_memory == memory
        assert session.merchant_memory.merchant_id == "test_merchant"
        assert len(session.merchant_memory.get_all_facts()) == 1
        
    def test_session_without_merchant_memory(self):
        """Test session creation without merchant memory (default None)."""
        conversation = Conversation(
            id="test-123",
            created_at=datetime.utcnow(),
            scenario_name="test_scenario",
            merchant_name="test_merchant",
        )

        session = Session(conversation)

        assert session.merchant_memory is None