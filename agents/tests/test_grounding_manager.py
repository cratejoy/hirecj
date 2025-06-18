"""Tests for GroundingManager."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.grounding_manager import GroundingManager, GroundingDirective
from app.models import Message


class TestGroundingManager:
    """Test cases for GroundingManager."""
    
    def test_extract_grounding_directives_simple(self):
        """Test extracting simple grounding directives."""
        manager = GroundingManager()
        content = "Hello {{grounding: npr}} world"
        
        directives = manager.extract_grounding_directives(content)
        
        assert len(directives) == 1
        assert directives[0].namespace == "npr"
        assert directives[0].limit == 10  # default
        assert directives[0].mode == "hybrid"  # default
    
    def test_extract_grounding_directives_with_params(self):
        """Test extracting grounding directives with parameters."""
        manager = GroundingManager()
        content = """
        {{grounding: npr, limit: 5}}
        {{grounding: docs, mode: global, limit: 3}}
        """
        
        directives = manager.extract_grounding_directives(content)
        
        assert len(directives) == 2
        
        # First directive
        assert directives[0].namespace == "npr"
        assert directives[0].limit == 5
        assert directives[0].mode == "hybrid"
        
        # Second directive
        assert directives[1].namespace == "docs"
        assert directives[1].limit == 3
        assert directives[1].mode == "global"
    
    def test_extract_grounding_directives_invalid_params(self):
        """Test extracting directives with invalid parameters."""
        manager = GroundingManager()
        content = "{{grounding: npr, limit: invalid, mode: bad}}"
        
        directives = manager.extract_grounding_directives(content)
        
        assert len(directives) == 1
        assert directives[0].namespace == "npr"
        assert directives[0].limit == 10  # default due to invalid
        assert directives[0].mode == "hybrid"  # default due to invalid
    
    def test_build_query_from_context(self):
        """Test building query from conversation context."""
        manager = GroundingManager()
        
        messages = [
            Message(sender="merchant", content="Tell me about Fresh Air", timestamp=datetime.now()),
            Message(sender="CJ", content="I'd be happy to help!", timestamp=datetime.now()),
            Message(sender="merchant", content="Who is Terry Gross?", timestamp=datetime.now()),
        ]
        
        query = manager._build_query_from_context(messages, limit=5)
        
        assert "Fresh Air" in query
        assert "Terry Gross" in query
        # Should prioritize merchant messages
        assert "happy to help" not in query
    
    def test_format_grounding_result(self):
        """Test formatting grounding results."""
        manager = GroundingManager()
        
        result = manager._format_grounding_result("npr", "Some NPR knowledge here")
        
        assert "[Knowledge from NPR database]:" in result
        assert "Some NPR knowledge here" in result
    
    def test_replace_grounding_markers(self):
        """Test replacing grounding markers with content."""
        manager = GroundingManager()
        
        content = "Hello {{grounding: npr}} and {{grounding: docs}}"
        grounding_results = {
            "npr": "\n\n[Knowledge from NPR database]:\nNPR content\n",
            "docs": "\n\n[Knowledge from DOCS database]:\nDocs content\n"
        }
        
        result = manager.replace_grounding_markers(content, grounding_results)
        
        assert "[Knowledge from NPR database]:\nNPR content\n" in result
        assert "[Knowledge from DOCS database]:\nDocs content\n" in result
        assert "{{grounding:" not in result  # All markers replaced
    
    def test_caching(self):
        """Test result caching."""
        manager = GroundingManager()
        
        # Cache a result
        manager._cache_result("npr:hybrid", "Cached content")
        
        # Should get cached result
        cached = manager._get_cached_result("npr:hybrid")
        assert cached == "Cached content"
        
        # Clear cache
        manager.clear_cache()
        
        # Should not get cached result
        cached = manager._get_cached_result("npr:hybrid")
        assert cached is None
    
    def test_process_grounding_integration(self):
        """Test full grounding processing flow."""
        manager = GroundingManager()
        
        # Mock the knowledge client
        with patch.object(manager.knowledge_client, 'query') as mock_query:
            mock_query.return_value = "NPR knowledge result"
            
            directives = [GroundingDirective("npr", limit=5, mode="hybrid")]
            messages = [
                Message(sender="merchant", content="Tell me about NPR shows", timestamp=datetime.now())
            ]
            
            results = manager.process_grounding(directives, messages)
            
            assert "npr" in results
            assert "NPR knowledge result" in results["npr"]
            assert "[Knowledge from NPR database]:" in results["npr"]
            
            # Verify query was called correctly
            mock_query.assert_called_once_with(
                namespace="npr",
                query="Tell me about NPR shows",
                mode="hybrid"
            )