"""Tests for CJ Agent memory context building."""

from unittest.mock import Mock, patch, MagicMock
from app.agents.cj_agent import CJAgent
from app.services.merchant_memory import MerchantMemory


class TestCJAgentMemoryContext:
    """Test CJ Agent builds context with merchant memory."""
    
    @patch('app.agents.cj_agent.Agent')
    def test_backstory_includes_memory_facts(self, mock_agent_class):
        """Test that merchant memory facts are included in backstory."""
        # Create mock memory with facts
        mock_memory = MerchantMemory("test_merchant")
        mock_memory.add_fact("Merchant prefers email communication", "conv_123")
        mock_memory.add_fact("Peak season is November-December", "conv_456")
        mock_memory.add_fact("Uses Shopify Plus with custom integrations", "conv_789")
        
        # Create CJAgent with memory
        cj = CJAgent(
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            merchant_memory=mock_memory
        )
        
        # Check that Agent was called
        assert mock_agent_class.called
        
        # Get the backstory that was passed to Agent
        agent_call_args = mock_agent_class.call_args
        backstory = agent_call_args[1]['backstory']
        
        # Verify memory facts are in backstory
        assert "Things I know about this merchant from previous conversations:" in backstory
        assert "Merchant prefers email communication" in backstory
        assert "Peak season is November-December" in backstory
        assert "Uses Shopify Plus with custom integrations" in backstory
        
    @patch('app.agents.cj_agent.Agent')
    def test_backstory_without_memory(self, mock_agent_class):
        """Test that backstory works without memory."""
        # Create CJAgent without memory
        cj = CJAgent(
            merchant_name="test_merchant",
            scenario_name="test_scenario"
        )
        
        # Check that Agent was called
        assert mock_agent_class.called
        
        # Get the backstory
        agent_call_args = mock_agent_class.call_args
        backstory = agent_call_args[1]['backstory']
        
        # Verify no memory section
        assert "Things I know about this merchant from previous conversations:" not in backstory
        
    @patch('app.agents.cj_agent.Agent')
    def test_memory_facts_limited_to_20(self, mock_agent_class):
        """Test that only 20 most recent facts are included."""
        # Create mock memory with many facts
        mock_memory = MerchantMemory("test_merchant")
        for i in range(30):
            mock_memory.add_fact(f"Fact number {i}", f"conv_{i}")
        
        # Create CJAgent with memory
        cj = CJAgent(
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            merchant_memory=mock_memory
        )
        
        # Get the backstory
        agent_call_args = mock_agent_class.call_args
        backstory = agent_call_args[1]['backstory']
        
        # Should include facts 10-29 (the 20 most recent)
        assert "Fact number 29" in backstory
        assert "Fact number 10" in backstory
        assert "Fact number 9" not in backstory  # Should not include older facts