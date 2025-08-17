"""Unit tests for the simplified Logger class."""

import pytest
import logging
from unittest.mock import Mock, patch

from src.utils.logger import Logger


class TestLoggerInitialization:
    """Test Logger initialization and setup."""

    def test_logger_creates_log_file(self, tmp_path, monkeypatch):
        """Test that Logger creates the correct log file structure."""
        # Use tmp_path for isolated testing
        monkeypatch.chdir(tmp_path)

        logger = Logger("20250817_120000", "test-idea", "run")

        # Check file was created in correct location
        expected_file = tmp_path / "logs" / "runs" / "20250817_120000_test-idea.log"
        assert expected_file.exists()
        # Logger uses relative paths, so compare just the path parts
        assert logger.log_file.name == "20250817_120000_test-idea.log"
        assert logger.log_file.parent.name == "runs"

        logger.finalize()

    def test_logger_auto_generates_run_id(self, tmp_path, monkeypatch):
        """Test that Logger generates run_id when not provided."""
        monkeypatch.chdir(tmp_path)

        with patch("src.utils.logger.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20250817_130000"
            logger = Logger(slug="auto-test")

            assert logger.run_id == "20250817_130000"
            expected_file = tmp_path / "logs" / "runs" / "20250817_130000_auto-test.log"
            assert expected_file.exists()
            # Logger uses relative paths, so compare just the path parts
            assert logger.log_file.name == "20250817_130000_auto-test.log"
            assert logger.log_file.parent.name == "runs"

        logger.finalize()

    def test_logger_test_mode(self, tmp_path, monkeypatch):
        """Test that test mode creates logs in logs/tests/."""
        monkeypatch.chdir(tmp_path)

        logger = Logger("20250817_140000", "unit-test", run_type="test")

        expected_file = tmp_path / "logs" / "tests" / "20250817_140000_unit-test.log"
        assert expected_file.exists()
        # Logger uses relative paths, so compare just the path parts
        assert logger.log_file.name == "20250817_140000_unit-test.log"
        assert logger.log_file.parent.name == "tests"

        logger.finalize()

    def test_logger_no_console_output(self, tmp_path, monkeypatch, capsys):
        """Test that console_output=False doesn't print to stderr."""
        monkeypatch.chdir(tmp_path)

        logger = Logger("20250817_150000", "quiet-test", console_output=False)
        logger.info("This should not appear on console")

        captured = capsys.readouterr()
        assert "This should not appear on console" not in captured.err

        # But it should be in the file
        log_content = logger.log_file.read_text()
        assert "This should not appear on console" in log_content

        logger.finalize()


class TestLoggingMethods:
    """Test various logging methods."""

    @pytest.fixture
    def logger(self, tmp_path, monkeypatch):
        """Create a Logger instance for testing."""
        monkeypatch.chdir(tmp_path)
        logger = Logger("20250817_160000", "test", console_output=False)
        yield logger
        logger.finalize()

    def test_log_levels(self, logger):
        """Test different log levels."""
        logger.debug("Debug message", "TestAgent")
        logger.info("Info message", "TestAgent")
        logger.warning("Warning message", "TestAgent")
        logger.error("Error message", "TestAgent")

        log_content = logger.log_file.read_text()

        # Debug should not appear (default level is INFO)
        assert "Debug message" not in log_content

        # Others should appear with correct levels
        assert "[TESTAGENT] Info message" in log_content
        assert "INFO" in log_content
        assert "[TESTAGENT] Warning message" in log_content
        assert "WARNING" in log_content
        assert "[TESTAGENT] Error message" in log_content
        assert "ERROR" in log_content

    def test_debug_level_logging(self, tmp_path, monkeypatch):
        """Test that debug level shows debug messages."""
        monkeypatch.chdir(tmp_path)

        logger = Logger(
            "20250817_170000", "debug-test", console_output=False, level=logging.DEBUG
        )

        logger.debug("Debug message should appear")
        log_content = logger.log_file.read_text()
        assert "Debug message should appear" in log_content

        logger.finalize()

    def test_error_with_exc_info(self, logger):
        """Test error logging with exception info."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("Error with traceback", exc_info=True)

        log_content = logger.log_file.read_text()
        assert "Error with traceback" in log_content
        assert "Traceback (most recent call last):" in log_content
        assert "ValueError: Test exception" in log_content


class TestSDKErrorHandling:
    """Test SDK-specific error handling."""

    @pytest.fixture
    def logger(self, tmp_path, monkeypatch):
        """Create a Logger instance for testing."""
        monkeypatch.chdir(tmp_path)
        logger = Logger("20250817_180000", "sdk-test", console_output=False)
        yield logger
        logger.finalize()

    def test_cli_not_found_error(self, logger):
        """Test CLINotFoundError handling."""
        from claude_code_sdk._errors import CLINotFoundError

        error = CLINotFoundError("Claude Code not found", "/usr/local/bin/claude")
        logger.log_sdk_error(error, "TestAgent")

        log_content = logger.log_file.read_text()
        assert "Claude Code is not installed" in log_content
        assert "https://claude.ai/code" in log_content

    def test_cli_connection_error(self, logger):
        """Test CLIConnectionError handling."""
        from claude_code_sdk._errors import CLIConnectionError

        error = CLIConnectionError("Connection refused")
        logger.log_sdk_error(error, "TestAgent")

        log_content = logger.log_file.read_text()
        assert "Cannot connect to Claude Code" in log_content
        assert "Connection refused" in log_content

    def test_process_error(self, logger):
        """Test ProcessError handling with exit code and stderr."""
        from claude_code_sdk._errors import ProcessError

        error = ProcessError("Process failed", exit_code=1, stderr="Error output")
        logger.log_sdk_error(error, "TestAgent")

        log_content = logger.log_file.read_text()
        assert "Claude Code process failed (exit code 1)" in log_content
        # stderr would be at debug level, which is filtered out by default

    def test_json_decode_error(self, logger):
        """Test CLIJSONDecodeError handling."""
        from claude_code_sdk._errors import CLIJSONDecodeError

        original_error = ValueError("Invalid JSON")
        error = CLIJSONDecodeError('{"invalid": json', original_error)
        logger.log_sdk_error(error, "TestAgent")

        log_content = logger.log_file.read_text()
        assert "Invalid response from Claude Code" in log_content

    def test_message_parse_error(self, logger):
        """Test MessageParseError handling."""
        from claude_code_sdk._errors import MessageParseError

        error = MessageParseError("Invalid message", data={"type": "unknown"})
        logger.log_sdk_error(error, "TestAgent")

        log_content = logger.log_file.read_text()
        assert "Invalid response from Claude Code" in log_content

    def test_generic_exception(self, logger):
        """Test handling of non-SDK exceptions."""
        error = RuntimeError("Something went wrong")
        logger.log_sdk_error(error, "TestAgent")

        log_content = logger.log_file.read_text()
        assert "Unexpected error: Something went wrong" in log_content


class TestCompatibilityMethods:
    """Test compatibility methods for old logger interface."""

    @pytest.fixture
    def logger(self, tmp_path, monkeypatch):
        """Create a Logger instance for testing."""
        monkeypatch.chdir(tmp_path)
        logger = Logger("20250817_190000", "compat-test", console_output=False)
        yield logger
        logger.finalize()

    def test_log_event_analysis_start(self, logger):
        """Test log_event with analysis_start."""
        logger.log_event(
            "analysis_start",
            "Analyst",
            {"idea": "AI fitness app", "use_websearch": True},
        )

        log_content = logger.log_file.read_text()
        assert "Starting analysis: AI fitness app (WebSearch: enabled)" in log_content

    def test_log_event_websearch(self, logger):
        """Test log_event with websearch_query."""
        logger.log_event(
            "websearch_query",
            "MessageProcessor",
            {"query": "fitness market size", "search_number": 1},
        )

        log_content = logger.log_file.read_text()
        assert "WebSearch #1: fitness market size" in log_content

    def test_log_event_ignored(self, logger):
        """Test that redundant events are ignored."""
        logger.log_event("analysis_complete", "Analyst", {})
        logger.log_event("review_complete", "Reviewer", {})

        log_content = logger.log_file.read_text()
        # These should not appear
        assert "analysis_complete" not in log_content
        assert "review_complete" not in log_content

    def test_log_error_compatibility(self, logger):
        """Test log_error compatibility method."""
        logger.log_error("Test error", "TestAgent", traceback="Line 1\nLine 2")

        log_content = logger.log_file.read_text()
        assert "[TESTAGENT] Test error" in log_content
        # Traceback is at debug level, won't appear with INFO level

    def test_log_milestone(self, logger):
        """Test log_milestone compatibility method."""
        logger.log_milestone("Starting phase 2", "Processing data")

        log_content = logger.log_file.read_text()
        assert "🎯 Starting phase 2 - Processing data" in log_content


class TestFinalization:
    """Test logger finalization."""

    def test_finalize_success(self, tmp_path, monkeypatch):
        """Test successful finalization."""
        monkeypatch.chdir(tmp_path)

        logger = Logger("20250817_200000", "final-test", console_output=False)
        logger.info("Some work done")

        logger.finalize(
            success=True,
            result={"total_time": 45.678, "message_count": 23, "search_count": 3},
        )

        log_content = logger.log_file.read_text()
        assert "SUCCESS ✅" in log_content
        assert "Duration: 45.7s" in log_content
        assert "Total messages: 23" in log_content
        assert "WebSearches: 3" in log_content

    def test_finalize_failure(self, tmp_path, monkeypatch):
        """Test failure finalization."""
        monkeypatch.chdir(tmp_path)

        logger = Logger("20250817_210000", "fail-test", console_output=False)

        logger.finalize(success=False)

        log_content = logger.log_file.read_text()
        assert "FAILED ❌" in log_content

    def test_finalize_interrupted(self, tmp_path, monkeypatch):
        """Test finalization with interrupted flag."""
        monkeypatch.chdir(tmp_path)

        logger = Logger("20250817_220000", "interrupt-test", console_output=False)

        logger.finalize(success=False, result={"interrupted": True})

        log_content = logger.log_file.read_text()
        assert "Run was interrupted by user" in log_content


class TestLoggerHeader:
    """Test logger header generation."""

    def test_header_content(self, tmp_path, monkeypatch):
        """Test that header contains expected information."""
        monkeypatch.chdir(tmp_path)

        with patch("src.utils.logger.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.isoformat.return_value = "2025-08-17T12:00:00"
            mock_datetime.now.return_value = mock_now

            logger = Logger("20250817_120000", "header-test", console_output=False)

            log_content = logger.log_file.read_text()
            assert "=" * 60 in log_content
            assert "Log started for: header-test" in log_content
            assert "Run ID: 20250817_120000" in log_content
            assert "Started: 2025-08-17T12:00:00" in log_content

            logger.finalize()
