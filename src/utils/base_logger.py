"""
Base logging functionality shared between production and test logging.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import TypedDict, TextIO, Any, cast
import logging
import sys


class EventData(TypedDict, total=False):
    """Data for logged events."""

    idea: str
    slug: str
    word_count: int
    character_count: int
    search_count: int
    iteration: int
    feedback_count: int
    file: str
    size: int
    duration: float
    message_count: int
    search_number: int
    query: str
    # Allow any additional fields
    use_websearch: bool
    analysis_file: str
    idea_slug: str
    message_type: str
    has_content_attr: bool
    has_content: bool
    content_preview: str | None
    review_complete: bool
    feedback_file_expected: str
    error: str | None
    attempting_fix: bool
    feedback_file: str
    recommendation: Any
    critical_issues: int
    improvements: int


class LogMetrics(TypedDict, total=False):
    """Metrics tracked during logging."""

    events: list[dict[str, object]]
    errors: list[dict[str, object]]
    milestones: list[dict[str, object]]
    start_time: str
    run_id: str
    name: str
    run_type: str
    end_time: str
    total_elapsed_seconds: float
    success: bool
    result: dict[str, object] | None


class BaseStructuredLogger:
    """
    Base class for structured logging that creates organized, readable logs.
    """

    def __init__(self, run_id: str, name: str, run_type: str, log_base_dir: str):
        """
        Initialize base logger.

        Args:
            run_id: Unique identifier for this run (timestamp)
            name: Name for the log directory (idea slug or test scenario)
            run_type: Type of run (test, production, debug)
            log_base_dir: Base directory for logs (e.g., "logs/runs" or "logs/tests")
        """
        self.run_id: str = run_id
        self.name: str = name[:30]  # Truncate for directory naming
        self.run_type: str = run_type
        self.start_time: datetime = datetime.now()

        # Create organized log directory structure
        self.log_dir: Path = Path(log_base_dir) / f"{run_id}_{self.name}"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup log files
        self.summary_file: Path = self.log_dir / "summary.md"
        self.events_file: Path = self.log_dir / "events.jsonl"
        self.metrics_file: Path = self.log_dir / "metrics.json"
        self.debug_file: Path = self.log_dir / "debug.log"

        # Track metrics
        self.metrics: LogMetrics = {
            "start_time": self.start_time.isoformat(),
            "run_id": run_id,
            "name": name,
            "run_type": run_type,
            "events": [],
            "errors": [],
            "milestones": [],
        }

        # Setup debug logger
        self.debug_logger: logging.Logger = self._setup_debug_logger()

        # Write initial summary header
        self._write_summary_header()

    def _setup_debug_logger(self) -> logging.Logger:
        """Setup Python logger for debug output."""
        logger = logging.getLogger(f"run_{self.run_id}")
        logger.setLevel(logging.DEBUG)

        # File handler for detailed logs
        debug_handler = logging.FileHandler(self.debug_file)
        debug_handler.setLevel(logging.DEBUG)

        # Console handler for important messages (only in production mode)
        if self.run_type != "test":
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)

            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # Format for file
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )
        debug_handler.setFormatter(file_formatter)
        logger.addHandler(debug_handler)

        return logger

    def _write_summary_header(self):
        """Write the header for the summary file."""
        with open(self.summary_file, "w") as f:
            title = self._get_summary_title()
            _ = f.write(f"# {title}\n\n")
            _ = f.write(f"**Run ID:** `{self.run_id}`  \n")
            _ = f.write(f"**Type:** {self.run_type}  \n")
            _ = f.write(
                f"**Started:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}  \n\n"
            )
            _ = f.write("## Timeline\n\n")

    def _get_summary_title(self) -> str:
        """Get title for summary file. Override in subclasses."""
        return f"Run Summary: {self.name}"

    def log_event(self, event_type: str, agent: str, data: EventData) -> None:
        """
        Log a structured event.

        Args:
            event_type: Type of event (e.g., "analysis_start", "review_complete")
            agent: Agent that generated the event
            data: Event data
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()

        event = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "event_type": event_type,
            "agent": agent,
            "data": data,
        }

        # Write to JSON lines file
        with open(self.events_file, "a") as f:
            _ = f.write(json.dumps(event) + "\n")

        # Add to metrics
        if "events" in self.metrics:
            self.metrics["events"].append(cast(dict[str, object], event))

        # Log to debug logger
        self.debug_logger.debug(f"[{agent}] {event_type}: {data}")

        # Update summary for important events
        if self._is_important_event(event_type):
            self._update_summary(elapsed, agent, event_type, data)

    def _is_important_event(self, event_type: str) -> bool:
        """Determine if event should be added to summary. Override in subclasses."""
        return event_type in [
            "analysis_complete",
            "review_complete",
            "iteration_complete",
            "error",
            "test_result",
        ]

    def log_milestone(self, milestone: str, details: str = ""):
        """
        Log a major milestone in the process.

        Args:
            milestone: Description of the milestone
            details: Additional details
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if "milestones" in self.metrics:
            self.metrics["milestones"].append(  # type: ignore[arg-type]
                {
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_seconds": round(elapsed, 2),
                    "milestone": milestone,
                    "details": details,
                }
            )

        # Log to console and debug
        self.debug_logger.info(f"🎯 MILESTONE: {milestone}")
        if details:
            self.debug_logger.info(f"   {details}")

        # Update summary
        with open(self.summary_file, "a") as f:
            _ = f.write(f"- **[{self._format_time(elapsed)}]** 🎯 {milestone}")
            if details:
                _ = f.write(f" - {details}")
            _ = f.write("\n")

    def log_error(self, error: str, agent: str, traceback: str | None = None) -> None:
        """
        Log an error.

        Args:
            error: Error message
            agent: Agent where error occurred
            traceback: Optional traceback
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()

        error_data = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "agent": agent,
            "error": error,
            "traceback": traceback,
        }

        if "errors" in self.metrics:
            self.metrics["errors"].append(cast(dict[str, object], error_data))

        # Log to debug logger
        self.debug_logger.error(f"[{agent}] ERROR: {error}")
        if traceback:
            self.debug_logger.error(f"Traceback:\n{traceback}")

        # Update summary
        with open(self.summary_file, "a") as f:
            _ = f.write(
                f"- **[{self._format_time(elapsed)}]** ❌ ERROR in {agent}: {error}\n"
            )

    def _update_summary(
        self, elapsed: float, agent: str, event_type: str, data: EventData
    ) -> None:
        """Update the summary file with important events."""
        with open(self.summary_file, "a") as f:
            time_str = self._format_time(elapsed)
            summary_line = self._format_summary_line(time_str, agent, event_type, data)
            if summary_line:
                _ = f.write(summary_line)

    def _format_summary_line(
        self, time_str: str, agent: str, event_type: str, data: EventData
    ) -> str:
        _ = agent  # Unused parameter
        """Format a summary line for an event. Override in subclasses for custom formatting."""
        if event_type == "analysis_complete":
            size = data.get("size", 0)
            return f"- **[{time_str}]** ✅ Analysis complete ({size:,} chars)\n"
        elif event_type == "review_complete":
            recommendation = data.get("recommendation", "unknown")
            issues = data.get("critical_issues", 0)
            emoji = "✅" if recommendation == "accept" else "⚠️"
            return f"- **[{time_str}]** {emoji} Review: {recommendation.upper()} ({issues} critical issues)\n"
        elif event_type == "iteration_complete":
            iteration = data.get("iteration", 0)
            return f"- **[{time_str}]** 🔄 Iteration {iteration} complete\n"
        elif event_type == "test_result":
            result = data.get("result", "UNKNOWN")
            emoji = "✅" if result == "PASSED" else "❌" if result == "FAILED" else "⏱️"
            return f"- **[{time_str}]** {emoji} Test {result}\n"
        return ""

    def _format_time(self, seconds: float) -> str:
        """Format elapsed time nicely."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        else:
            return f"{seconds / 3600:.1f}h"

    def finalize(self, success: bool, result: dict[str, object] | None = None) -> None:
        """
        Finalize the logging session.

        Args:
            success: Whether the run was successful
            result: Final result data
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()

        # Update metrics
        self.metrics["end_time"] = datetime.now().isoformat()
        self.metrics["total_elapsed_seconds"] = round(elapsed, 2)
        self.metrics["success"] = success
        self.metrics["result"] = result

        # Write final metrics
        with open(self.metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)

        # Update summary
        self._write_final_summary(elapsed, success, result)

        # Log completion
        self.debug_logger.info(f"Run completed in {self._format_time(elapsed)}")

        # Archive old logs if needed
        self._archive_old_logs()

    def _write_final_summary(
        self, elapsed: float, success: bool, result: dict[str, object] | None
    ) -> None:
        """Write final summary section."""
        with open(self.summary_file, "a") as f:
            _ = f.write("\n## Final Result\n\n")
            _ = f.write(f"**Status:** {'✅ Success' if success else '❌ Failed'}  \n")
            _ = f.write(f"**Total Time:** {self._format_time(elapsed)}  \n")

            if result:
                self._write_result_details(f, result)

            if "errors" in self.metrics and self.metrics["errors"]:
                _ = f.write("\n### Errors Encountered\n\n")
                for error in self.metrics["errors"]:
                    _ = f.write(f"- {error['agent']}: {error['error']}\n")

    def _write_result_details(self, f: TextIO, result: dict[str, object]) -> None:
        """Write result details to summary. Override in subclasses."""
        if "file_path" in result:
            _ = f.write(f"**Output:** `{result['file_path']}`  \n")
        if "iteration_count" in result:
            _ = f.write(f"**Iterations:** {result['iteration_count']}  \n")
        if "final_status" in result:
            _ = f.write(f"**Final Status:** {result['final_status']}  \n")

    def _archive_old_logs(self):
        """Archive old log runs, keeping only recent ones."""
        log_parent = self.log_dir.parent
        if not log_parent.exists():
            return

        # Get all directories in the parent
        all_dirs = sorted(
            [d for d in log_parent.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )

        # Keep only the 10 most recent
        MAX_LOGS = 10
        if len(all_dirs) > MAX_LOGS:
            # Determine archive path based on log type
            if "tests" in str(log_parent):
                archive_dir = Path("logs/archive/tests")
            else:
                archive_dir = Path("logs/archive/runs")

            archive_dir.mkdir(parents=True, exist_ok=True)

            for old_dir in all_dirs[MAX_LOGS:]:
                # Move to archive
                _ = shutil.move(str(old_dir), str(archive_dir / old_dir.name))
                self.debug_logger.info(f"Archived old log: {old_dir.name}")

    def write_events(self, events: list[dict[str, object]]) -> None:
        """Write multiple events at once (useful for test logs parsing)."""
        with open(self.events_file, "w") as f:
            for event in events:
                _ = f.write(json.dumps(event) + "\n")
        self.metrics["events"] = events
