"""
Production logging system using the base structured logger.
"""

from datetime import datetime
from typing import override
from types import TracebackType
from .base_logger import BaseStructuredLogger


class StructuredLogger(BaseStructuredLogger):
    """
    Production logger for analysis runs.
    """

    def __init__(self, run_id: str, idea_slug: str, run_type: str = "production"):
        """
        Initialize a structured logger for a production run.

        Args:
            run_id: Unique identifier for this run (timestamp)
            idea_slug: Slug of the idea being analyzed
            run_type: Type of run (production, debug)
        """
        self.idea_slug: str = idea_slug  # Set this BEFORE calling super().__init__
        super().__init__(run_id, idea_slug, run_type, "logs/runs")

    @override
    def _get_summary_title(self) -> str:
        """Get title for summary file."""
        return f"Run Summary: {self.idea_slug}"


class LoggingContext:
    """Context manager for structured logging."""

    def __init__(self, idea: str, run_type: str = "production"):
        """
        Initialize logging context.

        Args:
            idea: Business idea being analyzed
            run_type: Type of run
        """
        from .text_processing import create_slug

        self.idea: str = idea
        self.idea_slug: str = create_slug(idea)
        self.run_type: str = run_type
        self.run_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger: StructuredLogger | None = None

    def __enter__(self) -> StructuredLogger:
        """Enter the context and return the logger."""
        self.logger = StructuredLogger(self.run_id, self.idea_slug, self.run_type)
        self.logger.log_milestone("Run started", f"Analyzing: {self.idea}")
        return self.logger

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Exit the context and finalize logging."""
        if self.logger:
            success = exc_type is None
            if not success and exc_val:
                self.logger.log_error(
                    str(exc_val), "Pipeline", traceback=str(exc_tb) if exc_tb else None
                )
            self.logger.finalize(success)
        return False  # Don't suppress exceptions
