"""Unit tests for MessageProcessor focusing on SDK type handling."""
# pyright: reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportMissingParameterType=false

import pytest
from unittest.mock import Mock
from src.core.message_processor import MessageProcessor


@pytest.fixture
def processor():
    """Create a MessageProcessor instance for testing."""
    return MessageProcessor()


class TestExtractSessionId:
    """Test get_session_id method with different message types."""

    def test_get_session_id_with_sdk_system_message(self, processor):
        """Test extracting session_id from a real SDK SystemMessage."""
        from claude_code_sdk.types import SystemMessage

        # Create a mock SystemMessage with session_id
        message = Mock(spec=SystemMessage)
        message.data = {"session_id": "test-session-123"}

        result = processor.get_session_id(message)
        assert result == "test-session-123"

    def test_get_session_id_no_data(self, processor):
        """Test with SystemMessage that has no data."""
        from claude_code_sdk.types import SystemMessage

        message = Mock(spec=SystemMessage)
        message.data = None

        result = processor.get_session_id(message)
        assert result is None

    def test_get_session_id_empty_data(self, processor):
        """Test with SystemMessage that has empty data dict."""
        from claude_code_sdk.types import SystemMessage

        message = Mock(spec=SystemMessage)
        message.data = {}

        result = processor.get_session_id(message)
        assert result is None

    def test_get_session_id_non_string_value(self, processor):
        """Test with session_id that is not a string."""
        from claude_code_sdk.types import SystemMessage

        message = Mock(spec=SystemMessage)
        message.data = {"session_id": 12345}  # Non-string value

        result = processor.get_session_id(message)
        assert result is None  # Should return None for non-string

    def test_get_session_id_with_non_sdk_message(self, processor):
        """Test with a non-SDK message that has data attribute."""
        # Create a mock that has data but isn't a SystemMessage
        message = Mock()
        message.data = {"session_id": "protocol-session-456"}

        result = processor.get_session_id(message)
        # Should return None since it's not a SystemMessage
        assert result is None

    def test_get_session_id_non_system_message(self, processor):
        """Test with a message that is not a SystemMessage."""
        # Create a message that doesn't match SystemMessage
        message = Mock()
        # Don't set data attribute

        result = processor.get_session_id(message)
        assert result is None

    def test_get_session_id_with_other_data(self, processor):
        """Test with SystemMessage that has other data but no session_id."""
        from claude_code_sdk.types import SystemMessage

        message = Mock(spec=SystemMessage)
        message.data = {"other_key": "other_value", "timestamp": 123456}

        result = processor.get_session_id(message)
        assert result is None


class TestTrackMessage:
    """Test track_message and extraction methods with SDK types."""

    def test_track_user_message(self, processor):
        """Test tracking a UserMessage with content."""
        from claude_code_sdk.types import UserMessage

        message = Mock(spec=UserMessage)
        message.content = "Hello, world!"

        processor.track_message(message)
        content = processor.extract_content(message)

        assert processor.message_count == 1
        assert "Hello, world!" in content

    def test_track_result_message(self, processor):
        """Test tracking a ResultMessage with cost info."""
        from claude_code_sdk.types import ResultMessage

        message = Mock(spec=ResultMessage)
        message.result = "Task completed successfully"
        message.total_cost_usd = 0.05

        processor.track_message(message)
        content = processor.extract_content(message)

        assert processor.message_count == 1
        assert "Task completed successfully" in content
