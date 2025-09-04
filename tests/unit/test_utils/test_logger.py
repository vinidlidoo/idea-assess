"""Tests for logger utility."""

import logging


from src.utils.logger import setup_logging, is_sdk_error, Logger


class TestLogging:
    """Test logging functionality."""

    def test_setup_logging_creates_file(self, tmp_path, monkeypatch):
        """Test that setup_logging creates log file with correct structure."""
        monkeypatch.chdir(tmp_path)

        log_file = setup_logging(
            debug=False, idea_slug="test-idea", run_type="test", console_output=False
        )

        assert log_file.exists()
        assert "test-idea" in str(log_file)
        assert log_file.parent.parent.name == "tests"

        # Verify content is written
        content = log_file.read_text()
        assert "Log started for:" in content

    def test_debug_mode_enables_debug_logging(self, tmp_path, monkeypatch):
        """Test that debug=True enables DEBUG level logging."""
        monkeypatch.chdir(tmp_path)

        _ = setup_logging(debug=True, console_output=False)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_is_sdk_error_detection(self):
        """Test SDK error detection for critical error handling."""
        from claude_code_sdk._errors import CLINotFoundError, ProcessError

        # SDK errors should be detected
        assert is_sdk_error(CLINotFoundError("test")) is True
        assert is_sdk_error(ProcessError("test", exit_code=1, stderr="")) is True

        # Non-SDK errors should not be detected
        assert is_sdk_error(ValueError("test")) is False
        assert is_sdk_error(Exception("test")) is False

    def test_logger_basic_functionality(self, tmp_path, monkeypatch):
        """Test Logger class creates files and logs messages."""
        monkeypatch.chdir(tmp_path)

        logger = Logger(slug="test-slug", console_output=False)

        # Test file creation
        assert logger.log_file.exists()
        assert "test-slug" in str(logger.log_file)

        # Test logging at different levels
        logger.info("Info message")
        logger.error("Error message")

        content = logger.log_file.read_text()
        assert "Info message" in content
        assert "Error message" in content

    def test_logger_sdk_error_formatting(self, tmp_path, monkeypatch):
        """Test SDK error formatting for better error messages."""
        from claude_code_sdk._errors import ProcessError

        monkeypatch.chdir(tmp_path)
        logger = Logger(slug="sdk-test", console_output=False)

        error = ProcessError("Process failed", exit_code=1, stderr="stderr output")
        logger.log_sdk_error(error)

        content = logger.log_file.read_text()
        assert "exit code 1" in content

    def test_logger_finalization(self, tmp_path, monkeypatch):
        """Test logger finalization writes summary."""
        monkeypatch.chdir(tmp_path)
        logger = Logger(slug="finalize-test", console_output=False)

        result: dict[str, object] = {
            "total_time": 42.5,
            "message_count": 10,
        }

        logger.finalize(success=True, result=result)

        content = logger.log_file.read_text()
        assert "SUCCESS ✅" in content
        assert "Duration: 42.5s" in content
