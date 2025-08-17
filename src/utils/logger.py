"""
Simplified logging system for the idea-assess project.

This module provides a unified Logger class that replaces the previous
complex multi-file logging system with a single, simple approach:
- One log file per run
- Console mirroring (optional)
- Standard Python logging module
- SDK error awareness
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Literal


class Logger:
    """
    Simple logger using Python's logging module.

    Creates a single log file per run and optionally mirrors to console.
    Thread-safe through Python's logging module.
    """

    def __init__(
        self,
        run_id: str | None = None,
        slug: str = "unnamed",
        run_type: Literal["run", "test"] = "run",
        console_output: bool = True,
        level: int = logging.INFO,
    ):
        """
        Initialize the logger.

        Args:
            run_id: Timestamp identifier (YYYYMMDD_HHMMSS format).
                    If None, generates one automatically.
            slug: Idea slug or test name for the log filename
            run_type: Whether this is a normal run or test
            console_output: Whether to also print to stderr
            level: Minimum logging level (logging.DEBUG, INFO, WARNING, ERROR)
        """
        # Generate run_id if not provided
        if run_id is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.run_id: str = run_id
        self.slug: str = slug
        self.console_output: bool = console_output

        # Create unique logger name to avoid conflicts
        self.logger_name: str = f"{run_id}_{slug}"
        self.logger: logging.Logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(level)

        # Clear any existing handlers (in case of re-initialization)
        self.logger.handlers.clear()

        # Prevent propagation to root logger to avoid duplicate messages
        self.logger.propagate = False

        # Create log directory structure: logs/runs/ or logs/tests/
        log_dir = Path("logs") / f"{run_type}s"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Single log file per run
        self.log_file: Path = log_dir / f"{run_id}_{slug}.log"

        # File handler - always write to file
        file_handler = logging.FileHandler(self.log_file, mode="w", encoding="utf-8")
        file_handler.setLevel(level)

        # Use Python's standard format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler - optional stderr output
        if console_output:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # Log header
        self._log_header()

    def _log_header(self) -> None:
        """Write initial header to log."""
        self.logger.info("=" * 60)
        self.logger.info(f"Log started for: {self.slug}")
        self.logger.info(f"Run ID: {self.run_id}")
        self.logger.info(f"Started: {datetime.now().isoformat()}")
        self.logger.info("=" * 60)

    def log(
        self, message: str, level: int = logging.INFO, agent: str | None = None
    ) -> None:
        """
        Log a message at the specified level.

        Args:
            message: The message to log
            level: Log level (logging.DEBUG, INFO, WARNING, ERROR)
            agent: Optional agent name for context
        """
        # Prepend agent name if provided
        if agent:
            message = f"[{agent.upper()}] {message}"

        self.logger.log(level, message)

    def debug(self, message: str, agent: str | None = None) -> None:
        """Log a debug message."""
        self.log(message, logging.DEBUG, agent)

    def info(self, message: str, agent: str | None = None) -> None:
        """Log an info message."""
        self.log(message, logging.INFO, agent)

    def warning(self, message: str, agent: str | None = None) -> None:
        """Log a warning message."""
        self.log(message, logging.WARNING, agent)

    def error(
        self, message: str, agent: str | None = None, exc_info: bool = False
    ) -> None:
        """
        Log an error message with optional exception info.

        Args:
            message: Error message
            agent: Agent where error occurred
            exc_info: If True, adds current exception's traceback to the log
        """
        if agent:
            message = f"[{agent.upper()}] {message}"

        self.logger.error(message, exc_info=exc_info)

    def log_sdk_error(self, error: Exception, agent: str | None = None) -> None:
        """
        Log SDK-specific errors with appropriate detail level.

        Args:
            error: The exception to log
            agent: Agent where error occurred
        """
        from claude_code_sdk._errors import (
            CLINotFoundError,
            CLIConnectionError,
            ProcessError,
            CLIJSONDecodeError,
            MessageParseError,
        )

        if isinstance(error, CLINotFoundError):
            self.error(
                "Claude Code is not installed. Please install it from https://claude.ai/code",
                agent,
            )

        elif isinstance(error, CLIConnectionError):
            self.error(f"Cannot connect to Claude Code: {error}", agent)
            self.debug("This may be temporary. Consider retrying.", agent)

        elif isinstance(error, ProcessError):
            self.error(
                f"Claude Code process failed (exit code {error.exit_code}): {error}",
                agent,
            )
            if error.stderr:
                self.debug(f"Process stderr: {error.stderr}", agent)

        elif isinstance(error, (CLIJSONDecodeError, MessageParseError)):
            self.error(f"Invalid response from Claude Code: {error}", agent)
            if isinstance(error, CLIJSONDecodeError):
                self.debug(f"Problematic line: {error.line[:200]}", agent)
            elif isinstance(error, MessageParseError) and error.data:
                self.debug(f"Problematic data: {str(error.data)[:200]}", agent)

        else:
            # Fallback for other exceptions
            self.error(f"Unexpected error: {error}", agent, exc_info=True)

    def finalize(
        self, success: bool = True, result: dict[str, object] | None = None
    ) -> None:
        """
        Close the logger and write final summary.

        Args:
            success: Whether the run was successful
            result: Optional result data (mostly minimal extraction)
        """
        self.logger.info("=" * 60)
        status = "SUCCESS ✅" if success else "FAILED ❌"
        self.logger.info(f"Run {status}")

        if result:
            # Only log the most useful metrics
            if "total_time" in result:
                duration = result["total_time"]
                if isinstance(duration, (int, float)):
                    self.logger.info(f"Duration: {duration:.1f}s")
            if "message_count" in result:
                self.logger.info(f"Total messages: {result['message_count']}")
            if "search_count" in result:
                self.logger.info(f"WebSearches: {result['search_count']}")
            if "interrupted" in result and result["interrupted"]:
                self.logger.warning("Run was interrupted by user")

        self.logger.info(f"Log saved to: {self.log_file}")
        self.logger.info(f"Ended: {datetime.now().isoformat()}")
        self.logger.info("=" * 60)

        # Close and remove all handlers
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
