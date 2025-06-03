"""Tests for MerchantMemory class."""

from datetime import datetime
from unittest.mock import patch

from app.services.merchant_memory import MerchantMemory


class TestMerchantMemory:
    """Test MerchantMemory class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.merchant_id = "test_merchant"
        self.memory = MerchantMemory(self.merchant_id)
        
    def test_initialization_empty(self):
        """Test that MerchantMemory initializes with empty facts."""
        memory = MerchantMemory("merchant_123")
        assert memory.merchant_id == "merchant_123"
        assert memory.facts == []
        assert memory.get_all_facts() == []
        
    def test_initialization_with_facts(self):
        """Test initialization with existing facts."""
        existing_facts = [
            {
                'fact': "Owns an outdoor gear store",
                'learned_at': "2024-01-01T10:00:00",
                'source': "conv_001"
            }
        ]
        memory = MerchantMemory("merchant_123", existing_facts)
        assert len(memory.facts) == 1
        assert memory.get_all_facts() == ["Owns an outdoor gear store"]
        
    def test_add_fact(self):
        """Test adding a fact to memory."""
        with patch('app.services.merchant_memory.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T10:30:00"
            
            self.memory.add_fact("Prefers email communication", "conv_123")
            
            assert len(self.memory.facts) == 1
            fact = self.memory.facts[0]
            assert fact['fact'] == "Prefers email communication"
            assert fact['learned_at'] == "2024-01-15T10:30:00"
            assert fact['source'] == "conv_123"
            
    def test_add_multiple_facts(self):
        """Test adding multiple facts."""
        facts_to_add = [
            ("Uses Shopify Plus", "conv_123"),
            ("Has 50 employees", "conv_124"),
            ("Founded in 2015", "conv_125")
        ]
        
        for fact_text, source in facts_to_add:
            self.memory.add_fact(fact_text, source)
            
        assert len(self.memory.facts) == 3
        all_facts = self.memory.get_all_facts()
        assert "Uses Shopify Plus" in all_facts
        assert "Has 50 employees" in all_facts
        assert "Founded in 2015" in all_facts
        
    def test_get_all_facts(self):
        """Test getting all facts as strings."""
        self.memory.add_fact("Fact 1", "source1")
        self.memory.add_fact("Fact 2", "source2")
        
        facts = self.memory.get_all_facts()
        assert len(facts) == 2
        assert facts[0] == "Fact 1"
        assert facts[1] == "Fact 2"
        
    def test_get_recent_facts_default_limit(self):
        """Test getting recent facts with default limit."""
        # Add 25 facts
        for i in range(25):
            self.memory.add_fact(f"Fact {i}", f"source_{i}")
            
        recent_facts = self.memory.get_recent_facts()
        assert len(recent_facts) == 20  # Default limit
        assert recent_facts[0] == "Fact 5"  # First of last 20
        assert recent_facts[-1] == "Fact 24"  # Last fact
        
    def test_get_recent_facts_custom_limit(self):
        """Test getting recent facts with custom limit."""
        # Add 10 facts
        for i in range(10):
            self.memory.add_fact(f"Fact {i}", f"source_{i}")
            
        recent_facts = self.memory.get_recent_facts(limit=5)
        assert len(recent_facts) == 5
        assert recent_facts[0] == "Fact 5"
        assert recent_facts[-1] == "Fact 9"
        
    def test_get_recent_facts_fewer_than_limit(self):
        """Test getting recent facts when total facts < limit."""
        self.memory.add_fact("Fact 1", "source1")
        self.memory.add_fact("Fact 2", "source2")
        
        recent_facts = self.memory.get_recent_facts(limit=10)
        assert len(recent_facts) == 2
        assert recent_facts == ["Fact 1", "Fact 2"]
        
    def test_facts_are_append_only(self):
        """Test that facts are truly append-only (no modification)."""
        self.memory.add_fact("Original fact", "source1")
        original_fact = self.memory.facts[0].copy()
        
        # Add another fact
        self.memory.add_fact("New fact", "source2")
        
        # Verify original fact unchanged
        assert self.memory.facts[0] == original_fact
        assert len(self.memory.facts) == 2