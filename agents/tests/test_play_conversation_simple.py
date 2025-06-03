"""
Unit tests for play_conversation_simple.py script.
"""

import sys
from pathlib import Path
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestPlayConversationSimple:
    """Test the play conversation simple script."""

    def test_load_fact_check_messages_correct_path(self):
        """Test that load_fact_check_messages uses the correct path and loads data."""
        # Import here to avoid module-level issues

        # First ensure the error_messages.yaml exists with correct content
        expected_path = (
            project_root / "prompts" / "fact_checking" / "error_messages.yaml"
        )
        assert (
            expected_path.exists()
        ), f"error_messages.yaml should exist at {expected_path}"

        # Load and verify content
        with open(expected_path, "r") as f:
            data = yaml.safe_load(f)

        assert "status_messages" in data
        assert "PASS" in data["status_messages"]
        assert "WARNING" in data["status_messages"]
        assert "FAIL" in data["status_messages"]

        # Now test the script loads it correctly
        # Clear any cached imports
        modules_to_clear = [
            k for k in sys.modules.keys() if k.startswith("scripts.demos")
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

        # Import should now work
        from scripts.demos.play_conversation_simple import FACT_CHECK_MESSAGES

        # Verify the messages were loaded
        assert "PASS" in FACT_CHECK_MESSAGES
        assert "WARNING" in FACT_CHECK_MESSAGES
        assert "FAIL" in FACT_CHECK_MESSAGES
        assert FACT_CHECK_MESSAGES["PASS"] == "✅ All facts verified correctly"

    def test_script_imports_successfully(self):
        """Test that the script can be imported without errors."""
        # Clear any cached imports
        modules_to_clear = [
            k
            for k in sys.modules.keys()
            if k.startswith("scripts.demos.play_conversation_simple")
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

        # This should not raise any exceptions
        import scripts.demos.play_conversation_simple

        # Basic checks
        assert hasattr(
            scripts.demos.play_conversation_simple, "load_fact_check_messages"
        )
        assert hasattr(scripts.demos.play_conversation_simple, "FACT_CHECK_MESSAGES")
        assert hasattr(scripts.demos.play_conversation_simple, "ConversationMetrics")
        assert hasattr(scripts.demos.play_conversation_simple, "ProgressMonitor")

    def test_fact_check_messages_structure(self):
        """Test that FACT_CHECK_MESSAGES has the expected structure."""
        from scripts.demos.play_conversation_simple import FACT_CHECK_MESSAGES

        # Check required keys
        required_keys = ["PASS", "WARNING", "FAIL"]
        for key in required_keys:
            assert key in FACT_CHECK_MESSAGES, f"Missing required key: {key}"

        # Check values are strings
        for key, value in FACT_CHECK_MESSAGES.items():
            assert isinstance(value, str), f"Value for {key} should be a string"

        # Check specific values
        assert "✅" in FACT_CHECK_MESSAGES["PASS"]
        assert "⚠️" in FACT_CHECK_MESSAGES["WARNING"]
        assert "❌" in FACT_CHECK_MESSAGES["FAIL"]
