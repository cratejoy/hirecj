"""Tests for MerchantMemoryService class."""

import yaml
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

from app.services.merchant_memory import MerchantMemory, MerchantMemoryService


class TestMerchantMemoryService:
    """Test MerchantMemoryService class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock the directory creation
        with patch("app.services.merchant_memory.Path.mkdir"):
            self.service = MerchantMemoryService()
        self.merchant_id = "test_merchant"
        
    def test_initialization_creates_directory(self):
        """Test that service creates directory on init."""
        with patch("app.services.merchant_memory.Path.mkdir") as mock_mkdir:
            service = MerchantMemoryService()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            assert service.memory_dir == Path("data/merchant_memory")
            
    def test_load_memory_file_not_exists(self):
        """Test loading memory when file doesn't exist."""
        with patch("app.services.merchant_memory.Path.exists", return_value=False):
            memory = self.service.load_memory(self.merchant_id)
            
            assert isinstance(memory, MerchantMemory)
            assert memory.merchant_id == self.merchant_id
            assert memory.facts == []
            
    def test_load_memory_success(self):
        """Test successfully loading memory from YAML file."""
        test_data = {
            'merchant_id': self.merchant_id,
            'last_updated': '2024-01-15T10:30:00',
            'facts': [
                {
                    'fact': 'Owns outdoor gear store',
                    'learned_at': '2024-01-01T10:00:00',
                    'source': 'conv_001'
                },
                {
                    'fact': 'Has 50 employees',
                    'learned_at': '2024-01-02T11:00:00',
                    'source': 'conv_002'
                }
            ]
        }
        
        with patch("app.services.merchant_memory.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=yaml.dump(test_data))):
                memory = self.service.load_memory(self.merchant_id)
                
                assert memory.merchant_id == self.merchant_id
                assert len(memory.facts) == 2
                assert memory.get_all_facts() == ['Owns outdoor gear store', 'Has 50 employees']
                
    def test_load_memory_empty_file(self):
        """Test loading memory from empty YAML file."""
        with patch("app.services.merchant_memory.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="")):
                memory = self.service.load_memory(self.merchant_id)
                
                assert memory.merchant_id == self.merchant_id
                assert memory.facts == []
                
    def test_load_memory_malformed_yaml_raises(self):
        """Test that malformed YAML raises exception."""
        with patch("app.services.merchant_memory.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="[invalid yaml: {")):
                with pytest.raises(yaml.YAMLError):
                    self.service.load_memory(self.merchant_id)
                    
    def test_load_memory_io_error_raises(self):
        """Test that IO errors are raised."""
        with patch("app.services.merchant_memory.Path.exists", return_value=True):
            with patch("builtins.open", side_effect=IOError("Permission denied")):
                with pytest.raises(IOError):
                    self.service.load_memory(self.merchant_id)
                    
    def test_save_memory_success(self):
        """Test successfully saving memory to YAML file."""
        memory = MerchantMemory(self.merchant_id)
        memory.add_fact("Test fact 1", "source1")
        memory.add_fact("Test fact 2", "source2")
        
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            with patch("app.services.merchant_memory.datetime") as mock_datetime:
                mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T10:30:00"
                
                self.service.save_memory(memory)
                
                # Verify file was opened for writing
                mock_file.assert_called_once()
                call_args = mock_file.call_args
                assert call_args[0][0] == Path("data/merchant_memory/test_merchant_memory.yaml")
                assert call_args[0][1] == 'w'
                
                # Get what was written
                handle = mock_file()
                written_calls = handle.write.call_args_list
                written_data = ''.join(call[0][0] for call in written_calls)
                
                # Parse the written YAML
                saved_data = yaml.safe_load(written_data)
                assert saved_data['merchant_id'] == self.merchant_id
                assert saved_data['last_updated'] == "2024-01-15T10:30:00"
                assert len(saved_data['facts']) == 2
                
    def test_save_memory_empty_facts(self):
        """Test saving memory with no facts."""
        memory = MerchantMemory(self.merchant_id)
        
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            self.service.save_memory(memory)
            
            # Get what was written
            handle = mock_file()
            written_calls = handle.write.call_args_list
            written_data = ''.join(call[0][0] for call in written_calls)
            
            saved_data = yaml.safe_load(written_data)
            assert saved_data['facts'] == []
            
    def test_save_memory_io_error_raises(self):
        """Test that IO errors during save are raised."""
        memory = MerchantMemory(self.merchant_id)
        
        with patch("builtins.open", side_effect=IOError("Disk full")):
            with pytest.raises(IOError):
                self.service.save_memory(memory)
                
                
    def test_integration_save_and_load(self, tmp_path):
        """Integration test: save and load memory."""
        # Use a real temporary directory
        service = MerchantMemoryService()
        service.memory_dir = tmp_path / "merchant_memory"
        service.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Create and save memory
        original_memory = MerchantMemory(self.merchant_id)
        original_memory.add_fact("Integration test fact 1", "test_source_1")
        original_memory.add_fact("Integration test fact 2", "test_source_2")
        
        service.save_memory(original_memory)
        
        # Load it back
        loaded_memory = service.load_memory(self.merchant_id)
        
        # Verify
        assert loaded_memory.merchant_id == self.merchant_id
        assert loaded_memory.get_all_facts() == [
            "Integration test fact 1",
            "Integration test fact 2"
        ]
        assert len(loaded_memory.facts) == 2