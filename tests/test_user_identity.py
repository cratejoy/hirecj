"""
Unit tests for simplified user identity library.

Phase 4.5: User Identity & Persistence - SIMPLIFIED
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

# Import the simplified library functions
from shared.user_identity import (
    generate_user_id,
    get_or_create_user,
    save_conversation_message,
    get_user_conversations,
    append_fact,
    get_user_facts,
)


class TestFactStorage:
    """Test fact storage functions."""
    
    @patch('shared.user_identity.get_db')
    def test_append_fact(self, mock_get_db):
        """Test appending facts to user's fact array."""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn
        
        # Import here to avoid issues with mocking
        from shared.user_identity import append_fact
        
        # Call function
        append_fact("usr_12345678", "Customer prefers email support", "conv_123")
        
        # Verify
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO user_facts" in call_args[0]
        assert "ON CONFLICT" in call_args[0]
        assert call_args[1][0] == "usr_12345678"
        mock_conn.commit.assert_called_once()
    
    @patch('shared.user_identity.get_db')
    def test_get_user_facts_empty(self, mock_get_db):
        """Test getting facts for user with no facts."""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn
        
        # Mock no facts found
        mock_cursor.fetchone.return_value = None
        
        from shared.user_identity import get_user_facts
        facts = get_user_facts("usr_12345678")
        
        # Verify
        assert facts == []
        mock_cursor.execute.assert_called_once()
        assert "SELECT facts" in mock_cursor.execute.call_args[0][0]
    
    @patch('shared.user_identity.get_db')
    def test_get_user_facts_with_data(self, mock_get_db):
        """Test getting facts for user with existing facts."""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn
        
        # Mock facts found
        test_facts = [
            {"fact": "Prefers email", "source": "conv_1", "learned_at": "2024-01-01T00:00:00"},
            {"fact": "Ships weekly", "source": "conv_2", "learned_at": "2024-01-02T00:00:00"}
        ]
        mock_cursor.fetchone.return_value = {"facts": test_facts}
        
        from shared.user_identity import get_user_facts
        facts = get_user_facts("usr_12345678")
        
        # Verify
        assert len(facts) == 2
        assert facts[0]["fact"] == "Prefers email"
        assert facts[1]["fact"] == "Ships weekly"


class TestUserIdentitySimple:
    """Test simplified user identity functions."""
    
    def test_generate_user_id(self):
        """Test consistent user ID generation."""
        # Same domain should generate same ID
        shop1 = "example.myshopify.com"
        id1 = generate_user_id(shop1)
        id2 = generate_user_id(shop1)
        assert id1 == id2
        assert id1.startswith("usr_")
        assert len(id1) == 12  # usr_ + 8 chars
        
        # Different domains should generate different IDs
        shop2 = "different.myshopify.com"
        id3 = generate_user_id(shop2)
        assert id3 != id1
        
        # Should normalize domains
        assert generate_user_id("Example.myshopify.com") == generate_user_id("example.myshopify.com")
        assert generate_user_id("https://example.myshopify.com/") == generate_user_id("example.myshopify.com")
        assert generate_user_id("www.example.myshopify.com") == generate_user_id("example.myshopify.com")
    
    @patch('shared.user_identity.get_db')
    def test_get_or_create_user_new(self, mock_get_db):
        """Test creating a new user."""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn
        
        # Mock query returns no existing user
        mock_cursor.fetchone.return_value = None
        
        # Call function
        user_id, is_new = get_or_create_user(
            "test.myshopify.com",
            email="test@example.com"
        )
        
        # Verify
        assert is_new is True
        assert user_id.startswith("usr_")
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
    
    @patch('shared.user_identity.get_db')
    def test_get_or_create_user_existing(self, mock_get_db):
        """Test getting an existing user."""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn
        
        # Mock existing user
        mock_cursor.fetchone.return_value = {"id": "usr_12345678"}
        
        # Call function
        user_id, is_new = get_or_create_user("test.myshopify.com")
        
        # Verify
        assert is_new is False
        assert user_id == "usr_12345678"
        # Should only execute SELECT, not INSERT
        assert mock_cursor.execute.call_count == 1
        assert "SELECT" in mock_cursor.execute.call_args[0][0]
    
    @patch('shared.user_identity.get_db')
    def test_save_conversation_message(self, mock_get_db):
        """Test saving a conversation message."""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn
        
        # Call function
        message = {
            "role": "user",
            "content": "Hello CJ",
            "workflow": "shopify_onboarding"
        }
        save_conversation_message("usr_12345678", message)
        
        # Verify
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO conversations" in call_args[0]
        assert call_args[1][0] == "usr_12345678"
        assert json.loads(call_args[1][1]) == message
        mock_conn.commit.assert_called_once()
    
    @patch('shared.user_identity.get_db')
    def test_get_user_conversations(self, mock_get_db):
        """Test retrieving user conversations."""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn
        
        # Mock conversation results
        now = datetime.utcnow()
        mock_cursor.fetchall.return_value = [
            {
                "message": {"role": "user", "content": "Hello"},
                "created_at": now
            },
            {
                "message": {"role": "assistant", "content": "Hi there!"},
                "created_at": now
            }
        ]
        
        # Call function
        conversations = get_user_conversations("usr_12345678", limit=10)
        
        # Verify
        assert len(conversations) == 2
        assert conversations[0]["message"]["role"] == "user"
        assert conversations[1]["message"]["role"] == "assistant"
        assert "created_at" in conversations[0]
        mock_cursor.execute.assert_called_once()
        assert "SELECT message, created_at" in mock_cursor.execute.call_args[0][0]
    
    def test_connection_string_fix(self):
        """Test that postgres:// URLs are fixed to postgresql://"""
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = "postgres://user:pass@host:5432/db"
            
            with patch('psycopg2.connect') as mock_connect:
                from shared.user_identity import get_db
                get_db()
                
                # Verify the URL was fixed
                mock_connect.assert_called_once()
                call_args = mock_connect.call_args[0][0]
                assert call_args.startswith("postgresql://")
                assert not call_args.startswith("postgres://")


class TestSimplifiedDesign:
    """Test that the simplified design meets requirements."""
    
    def test_no_redis_dependency(self):
        """Verify no Redis imports or usage."""
        import shared.user_identity
        source = shared.user_identity.__file__
        
        with open(source, 'r') as f:
            content = f.read()
            assert 'redis' not in content.lower()
            assert 'archival' not in content.lower()
    
    def test_minimal_dependencies(self):
        """Verify only essential dependencies."""
        import shared.user_identity
        source = shared.user_identity.__file__
        
        with open(source, 'r') as f:
            content = f.read()
            # Should only import stdlib and psycopg2
            assert 'import hashlib' in content
            assert 'import json' in content
            assert 'import os' in content
            assert 'import psycopg2' in content
            # Should NOT import complex libraries
            assert 'sqlalchemy' not in content.lower()
            assert 'import redis' not in content
    
    def test_line_count(self):
        """Verify the implementation is truly minimal."""
        import shared.user_identity
        source = shared.user_identity.__file__
        
        with open(source, 'r') as f:
            lines = f.readlines()
            # Filter out empty lines and pure comment lines
            code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
            # Should be around 140-160 lines of actual code with fact storage and logging
            assert len(code_lines) < 200  # Allow some wiggle room for logging


def test_user_identity_imports():
    """Test that only the simplified exports are available."""
    from shared import user_identity
    
    # Should have these 6 functions
    assert hasattr(user_identity, 'generate_user_id')
    assert hasattr(user_identity, 'get_or_create_user')
    assert hasattr(user_identity, 'save_conversation_message')
    assert hasattr(user_identity, 'get_user_conversations')
    assert hasattr(user_identity, 'append_fact')
    assert hasattr(user_identity, 'get_user_facts')
    
    # Should NOT have complex library stuff
    assert not hasattr(user_identity, 'User')  # No SQLAlchemy models
    assert not hasattr(user_identity, 'ConversationArchiver')  # No archival
    assert not hasattr(user_identity, 'log_user_event')  # No event tracking