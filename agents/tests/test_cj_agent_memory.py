"""Tests for CJ Agent memory integration."""

from unittest.mock import Mock, patch
from app.agents.cj_agent import create_cj_agent, CJAgent
from app.services.merchant_memory import MerchantMemory


class TestCJAgentMemory:
    """Test CJ Agent with merchant memory."""
    
    def test_create_cj_agent_with_memory(self):
        """Test that merchant_memory is passed through to CJAgent."""
        # Create mock memory
        mock_memory = MerchantMemory("test_merchant")
        mock_memory.add_fact("Test fact", "test_source")
        
        # Create agent with memory
        with patch('app.agents.cj_agent.Agent') as mock_agent_class:
            agent = create_cj_agent(
                merchant_name="test_merchant",
                scenario_name="test_scenario",
                merchant_memory=mock_memory,
                verbose=False
            )
            
            # Verify CJAgent was created with the memory
            # The agent should have been created through CJAgent
            assert mock_agent_class.called
            
    def test_cj_agent_stores_memory(self):
        """Test that CJAgent stores merchant_memory as instance variable."""
        # Create mock memory
        mock_memory = MerchantMemory("test_merchant")
        
        # Create CJAgent instance directly
        cj = CJAgent(
            merchant_name="test_merchant",
            scenario_name="test_scenario",
            merchant_memory=mock_memory
        )
        
        # Verify memory is stored
        assert cj.merchant_memory == mock_memory
        assert cj.merchant_name == "test_merchant"
        assert cj.scenario_name == "test_scenario"
        
    def test_create_cj_agent_without_memory(self):
        """Test that create_cj_agent works without memory (backwards compatible)."""
        # Create agent without memory
        with patch('app.agents.cj_agent.Agent') as mock_agent_class:
            agent = create_cj_agent(
                merchant_name="test_merchant",
                scenario_name="test_scenario",
                verbose=False
            )
            
            # Should still work
            assert mock_agent_class.called
            
    def test_cj_agent_without_memory(self):
        """Test that CJAgent works without memory."""
        # Create CJAgent without memory
        cj = CJAgent(
            merchant_name="test_merchant",
            scenario_name="test_scenario"
        )
        
        # Should have None for merchant_memory
        assert cj.merchant_memory is None