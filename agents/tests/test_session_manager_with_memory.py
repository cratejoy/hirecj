"""Tests for SessionManager with merchant memory integration."""

from datetime import datetime
from unittest.mock import Mock, patch
from pathlib import Path

from app.services.session_manager import SessionManager
from app.services.merchant_memory import MerchantMemory, MerchantMemoryService


class TestSessionManagerWithMemory:
    """Test SessionManager with merchant memory loading."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SessionManager()
        
    @patch('app.services.session_manager.MerchantMemoryService')
    def test_create_session_loads_memory(self, mock_memory_service_class):
        """Test that create_session loads merchant memory."""
        # Setup mock
        mock_service = Mock()
        mock_memory = MerchantMemory("test_merchant")
        mock_memory.add_fact("Test fact", "test_source")
        mock_service.load_memory.return_value = mock_memory
        mock_memory_service_class.return_value = mock_service
        
        # Create session
        session = self.manager.create_session(
            merchant_name="test_merchant",
            scenario_name="test_scenario"
        )
        
        # Verify memory service was instantiated
        mock_memory_service_class.assert_called_once()
        
        # Verify load_memory was called with merchant name
        mock_service.load_memory.assert_called_once_with("test_merchant")
        
        # Verify session has the loaded memory
        assert session.merchant_memory == mock_memory
        assert len(session.merchant_memory.get_all_facts()) == 1
        
    @patch('app.services.session_manager.MerchantMemoryService')
    def test_create_session_with_empty_memory(self, mock_memory_service_class):
        """Test creating session when merchant has no existing memory."""
        # Setup mock for empty memory
        mock_service = Mock()
        mock_empty_memory = MerchantMemory("new_merchant")
        mock_service.load_memory.return_value = mock_empty_memory
        mock_memory_service_class.return_value = mock_service
        
        # Create session
        session = self.manager.create_session(
            merchant_name="new_merchant",
            scenario_name="test_scenario"
        )
        
        # Verify memory is loaded but empty
        assert session.merchant_memory.merchant_id == "new_merchant"
        assert len(session.merchant_memory.get_all_facts()) == 0
        
    @patch('app.services.session_manager.MerchantMemoryService')
    @patch('app.services.session_manager.UniverseDataAgent')
    def test_create_session_loads_both_universe_and_memory(self, mock_universe_class, mock_memory_service_class):
        """Test that both universe data and memory are loaded."""
        # Setup mocks
        mock_universe_agent = Mock()
        mock_universe_class.return_value = mock_universe_agent
        
        mock_service = Mock()
        mock_memory = MerchantMemory("test_merchant")
        mock_service.load_memory.return_value = mock_memory
        mock_memory_service_class.return_value = mock_service
        
        # Create session
        session = self.manager.create_session(
            merchant_name="test_merchant",
            scenario_name="test_scenario"
        )
        
        # Verify both were loaded
        assert session.data_agent == mock_universe_agent
        assert session.merchant_memory == mock_memory
        
    def test_integration_with_real_memory_service(self, tmp_path):
        """Integration test with real MerchantMemoryService."""
        # Create a temporary directory for memory storage
        test_memory_dir = tmp_path / "merchant_memory"
        test_memory_dir.mkdir()
        
        # Patch the memory directory path
        with patch('app.services.merchant_memory.Path') as mock_path:
            mock_path.return_value = test_memory_dir
            
            # Create some test memory
            service = MerchantMemoryService()
            service.memory_dir = test_memory_dir
            test_memory = MerchantMemory("test_merchant")
            test_memory.add_fact("Existing fact", "previous_conversation")
            service.save_memory(test_memory)
            
            # Create session - should load the existing memory
            session = self.manager.create_session(
                merchant_name="test_merchant",
                scenario_name="test_scenario"
            )
            
            # Verify memory was loaded
            assert session.merchant_memory is not None
            assert session.merchant_memory.merchant_id == "test_merchant"
            facts = session.merchant_memory.get_all_facts()
            assert len(facts) == 1
            assert facts[0] == "Existing fact"