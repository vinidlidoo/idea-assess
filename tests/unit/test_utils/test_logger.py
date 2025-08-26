"""Tests for logger utility."""

import logging
from unittest.mock import patch

import pytest

from src.utils.logger import setup_logging, is_sdk_error, Logger


class TestSetupLogging:
    """Test the setup_logging function."""

    def test_setup_logging_basic(self, tmp_path, monkeypatch):
        """Test basic logging setup."""
        monkeypatch.chdir(tmp_path)

        log_file = setup_logging(
            debug=False, idea_slug="test-idea", run_type="test", console_output=False
        )

        assert log_file.exists()
        assert "test-idea" in str(log_file)
        assert log_file.parent.parent.name == "tests"

        # Test that logger is configured
        logger = logging.getLogger("test")
        logger.info("Test message")

        # Check log file contains expected content
        content = log_file.read_text()
        assert "Test message" in content
        assert "test-idea" in content
        assert "Log started for:" in content

    def test_setup_logging_debug_mode(self, tmp_path, monkeypatch):
        """Test debug mode configuration."""
        monkeypatch.chdir(tmp_path)

        log_file = setup_logging(debug=True, console_output=False)

        # Check debug level is set
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        # Write debug message
        logger = logging.getLogger("test")
        logger.debug("Debug message")

        content = log_file.read_text()
        assert "DEBUG" in content
        assert "Debug message" in content

    def test_setup_logging_console_output(self, tmp_path, monkeypatch):
        """Test console output configuration."""
        monkeypatch.chdir(tmp_path)

        with patch("sys.stderr"):
            setup_logging(console_output=True)

            # Check that console handler was added
            root_logger = logging.getLogger()
            handlers = [
                h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)
            ]
            assert len(handlers) > 0


class TestIsSdkError:
    """Test the is_sdk_error function."""

    def test_is_sdk_error_true(self):
        """Test detection of SDK errors."""
        from claude_code_sdk._errors import CLINotFoundError, ProcessError

        assert is_sdk_error(CLINotFoundError("test")) is True
        assert (
            is_sdk_error(ProcessError("Process failed", exit_code=1, stderr="stderr"))
            is True
        )

    def test_is_sdk_error_false(self):
        """Test non-SDK errors return False."""
        assert is_sdk_error(ValueError("test")) is False
        assert is_sdk_error(RuntimeError("test")) is False
        assert is_sdk_error(Exception("test")) is False


class TestLogger:
    """Test the Logger class."""

    @pytest.fixture
    def temp_dir(self, tmp_path, monkeypatch):
        """Create temporary directory and change to it."""
        monkeypatch.chdir(tmp_path)
        return tmp_path

    def test_logger_initialization(self, temp_dir):
        """Test basic logger initialization."""
        logger = Logger(
            run_id="20250101_120000", slug="test-slug", console_output=False
        )

        assert logger.run_id == "20250101_120000"
        assert logger.slug == "test-slug"
        assert logger.log_file.exists()
        assert "test-slug" in str(logger.log_file)

        # Check header was written
        content = logger.log_file.read_text()
        assert "Log started for: test-slug" in content
        assert "Run ID: 20250101_120000" in content

    def test_logger_auto_run_id(self, temp_dir):
        """Test automatic run_id generation."""
        with patch("src.utils.logger.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20250102_150000"

            logger = Logger(slug="auto-id", console_output=False)
            assert logger.run_id == "20250102_150000"

    def test_logger_log_levels(self, temp_dir):
        """Test different log levels."""
        logger = Logger(slug="levels", console_output=False)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        content = logger.log_file.read_text()
        # Debug won't appear at INFO level
        assert "Debug message" not in content
        assert "Info message" in content
        assert "Warning message" in content
        assert "Error message" in content

    def test_logger_with_agent_context(self, temp_dir):
        """Test logging with agent name."""
        logger = Logger(slug="agent-test", console_output=False)

        logger.info("Processing", agent="analyst")
        logger.error("Failed", agent="reviewer")

        content = logger.log_file.read_text()
        assert "[ANALYST] Processing" in content
        assert "[REVIEWER] Failed" in content

    def test_logger_sdk_error_handling(self, temp_dir):
        """Test SDK error logging."""
        from claude_code_sdk._errors import (
            CLINotFoundError,
            ProcessError,
            CLIJSONDecodeError,
        )

        logger = Logger(slug="sdk-errors", console_output=False, level=logging.DEBUG)

        # Test different SDK error types
        logger.log_sdk_error(CLINotFoundError("not found"))
        logger.log_sdk_error(
            ProcessError("Process failed", exit_code=1, stderr="stderr")
        )

        json_error = CLIJSONDecodeError("invalid json line", ValueError("bad json"))
        logger.log_sdk_error(json_error)

        content = logger.log_file.read_text()
        assert "Claude Code is not installed" in content
        assert "exit code 1" in content
        assert "Invalid response from Claude Code" in content
        assert "Problematic line:" in content

    def test_logger_finalize(self, temp_dir):
        """Test logger finalization."""
        logger = Logger(slug="finalize", console_output=False)

        result: dict[str, object] = {
            "total_time": 42.5,
            "message_count": 10,
            "search_count": 3,
            "interrupted": False,
        }

        logger.finalize(success=True, result=result)

        content = logger.log_file.read_text()
        assert "SUCCESS ✅" in content
        assert "Duration: 42.5s" in content
        assert "Total messages: 10" in content
        assert "WebSearches: 3" in content

    def test_logger_finalize_failure(self, temp_dir):
        """Test finalization with failure."""
        logger = Logger(slug="fail", console_output=False)

        logger.finalize(success=False, result={"interrupted": True})

        content = logger.log_file.read_text()
        assert "FAILED ❌" in content
        assert "Run was interrupted by user" in content

    def test_logger_directory_structure(self, temp_dir):
        """Test correct directory structure creation."""
        # Test run type
        run_logger = Logger(slug="run-test", run_type="run", console_output=False)
        assert run_logger.log_file.parent.name == "runs"

        # Test test type
        test_logger = Logger(slug="test-test", run_type="test", console_output=False)
        assert test_logger.log_file.parent.name == "tests"

    def test_logger_no_propagation(self, temp_dir):
        """Test that logger doesn't propagate to root."""
        logger = Logger(slug="no-prop", console_output=False)
        assert logger.logger.propagate is False

        # Ensure no duplicate messages to root
        root_logger = logging.getLogger()
        root_handlers_before = len(root_logger.handlers)

        logger.info("Test message")

        # Root logger shouldn't have gained handlers
        assert len(root_logger.handlers) == root_handlers_before

    def test_logger_exception_info(self, temp_dir):
        """Test error logging with exception info."""
        logger = Logger(slug="exc-info", console_output=False)

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("Caught error", exc_info=True)

        content = logger.log_file.read_text()
        assert "Caught error" in content
        assert "Traceback" in content
        assert "ValueError: Test exception" in content
