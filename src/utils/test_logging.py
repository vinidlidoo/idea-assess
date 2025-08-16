"""
Test logging utilities using the base structured logger.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import TextIO, override
from .base_logger import BaseStructuredLogger


class TestLogger(BaseStructuredLogger):
    """
    Test logger for test harness runs.
    """

    def __init__(self, run_id: str, test_scenario: str, idea: str):
        """
        Initialize a test logger.

        Args:
            run_id: Unique identifier for this run (timestamp)
            test_scenario: Test scenario identifier (e.g., "5_review_basic")
            idea: Business idea being tested
        """
        # Set attributes BEFORE calling super().__init__
        self.test_scenario: str = test_scenario
        self.idea: str = idea

        # Clean idea for directory naming
        clean_idea = re.sub(r"[^a-zA-Z0-9_-]", "_", idea)[:30]
        name = f"{test_scenario}_{clean_idea}"

        super().__init__(run_id, name, "test", "logs/tests")

    @override
    def _get_summary_title(self) -> str:
        """Get title for summary file."""
        return f"Test Run: {self.test_scenario}"

    @override
    def _write_result_details(self, f: TextIO, result: dict[str, object]) -> None:
        """Write test-specific result details."""
        if "test_result" in result:
            _ = f.write(f"**Test Result:** {result['test_result']}  \n")
        if "output_files" in result:
            _ = f.write("\n### Output Files\n\n")
            files_raw = result.get("output_files", [])
            if isinstance(files_raw, list):
                # Type assertion: files_raw items should be strings or convertible to strings
                for item in files_raw:
                    if item is not None:
                        _ = f.write(f"- {item}\n")


def extract_events_from_output(content: str, idea: str) -> list[dict[str, object]]:
    """
    Extract events from test output.

    Args:
        content: Test output content
        idea: Business idea being tested

    Returns:
        List of events
    """
    events: list[dict[str, object]] = []
    lines = content.split("\n")

    # Track approximate timestamps based on line position
    base_time = datetime.now()

    for i, line in enumerate(lines):
        # Create a fake elapsed time based on line position
        elapsed = i * 0.1  # Assume 0.1s per line for fake timing

        if "Analyzing:" in line:
            events.append(
                {
                    "timestamp": base_time.isoformat(),
                    "elapsed_seconds": elapsed,
                    "event_type": "test_start",
                    "agent": "test_harness",
                    "data": {"idea": idea},
                }
            )
        elif "Analysis saved to:" in line or "Saved to:" in line:
            events.append(
                {
                    "timestamp": base_time.isoformat(),
                    "elapsed_seconds": elapsed,
                    "event_type": "analysis_complete",
                    "agent": "test_harness",
                    "data": {"file": line.split(":")[-1].strip()},
                }
            )
        elif "Decision:" in line:
            events.append(
                {
                    "timestamp": base_time.isoformat(),
                    "elapsed_seconds": elapsed,
                    "event_type": "review_decision",
                    "agent": "test_harness",
                    "data": {"decision": line.split(":")[-1].strip()},
                }
            )
        elif "Connecting to Claude" in line:
            events.append(
                {
                    "timestamp": base_time.isoformat(),
                    "elapsed_seconds": elapsed,
                    "event_type": "claude_connection",
                    "agent": "test_harness",
                    "data": {},
                }
            )
        elif "TEST PASSED" in line or "✅" in line:
            events.append(
                {
                    "timestamp": base_time.isoformat(),
                    "elapsed_seconds": elapsed,
                    "event_type": "test_result",
                    "agent": "test_harness",
                    "data": {"result": "PASSED"},
                }
            )
        elif "TEST FAILED" in line or "❌" in line:
            events.append(
                {
                    "timestamp": base_time.isoformat(),
                    "elapsed_seconds": elapsed,
                    "event_type": "test_result",
                    "agent": "test_harness",
                    "data": {"result": "FAILED"},
                }
            )
        elif "TIMEOUT" in line or "⏱️" in line:
            events.append(
                {
                    "timestamp": base_time.isoformat(),
                    "elapsed_seconds": elapsed,
                    "event_type": "test_result",
                    "agent": "test_harness",
                    "data": {"result": "TIMEOUT"},
                }
            )

    return events


def create_structured_logs(
    test_dir: str, output_file: str, test_scenario: str, idea: str
):
    """
    Create structured log files for a test run.

    Args:
        test_dir: Directory where test logs are stored
        output_file: Path to the output.log file
        test_scenario: Test scenario identifier (e.g., "5_review_basic")
        idea: Business idea being tested
    """
    test_path = Path(test_dir)
    output_path = Path(output_file)

    if not output_path.exists():
        print(f"Output file not found: {output_file}")
        return

    # Parse output for results
    with open(output_path, "r") as f:
        content = f.read()

    # Determine test result
    if "TEST PASSED" in content or "✅" in content:
        result = "PASSED"
        success = True
    elif "TIMEOUT" in content or "⏱️" in content:
        result = "TIMEOUT"
        success = False
    elif "TEST FAILED" in content or "❌" in content:
        result = "FAILED"
        success = False
    else:
        result = "UNKNOWN"
        success = False

    # Extract timestamp from directory name
    from datetime import datetime as dt

    dir_name = test_path.name
    timestamp_match = re.match(r"^(\d{8}_\d{6})_", dir_name)
    timestamp = (
        timestamp_match.group(1)
        if timestamp_match
        else dt.now().strftime("%Y%m%d_%H%M%S")
    )

    # Create log files directly in the test directory (don't create a new one)
    # Clean idea for naming
    clean_idea = re.sub(r"[^a-zA-Z0-9_-]", "_", idea)[:30]

    # Create the structured log files directly
    from datetime import datetime
    import json

    start_time = datetime.now()

    # Write summary.md
    summary_file = test_path / "summary.md"
    with open(summary_file, "w") as f:
        _ = f.write(f"# Test Run: {test_scenario}\n\n")
        _ = f.write(f"**Run ID:** `{timestamp}`  \n")
        _ = f.write("**Type:** test  \n")
        _ = f.write(f"**Idea:** {idea}  \n")
        _ = f.write(f"**Started:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
        _ = f.write("## Timeline\n\n")
        _ = f.write("- **[0.0s]** Test started\n")
        _ = f.write(f"- **[0.1s]** {result}\n\n")
        _ = f.write("## Final Result\n\n")
        _ = f.write(f"**Status:** {'✅ Success' if success else '❌ Failed'}  \n")
        _ = f.write(f"**Test Result:** {result}  \n")

    # Extract and write events
    events = extract_events_from_output(content, idea)

    # Write events.jsonl
    events_file = test_path / "events.jsonl"
    with open(events_file, "w") as f:
        for event in events:
            _ = f.write(json.dumps(event) + "\n")

    # Write metrics.json
    metrics_file = test_path / "metrics.json"
    metrics = {
        "start_time": start_time.isoformat(),
        "run_id": timestamp,
        "name": f"{test_scenario}_{clean_idea}",
        "run_type": "test",
        "events": events,
        "errors": [],
        "milestones": [],
        "success": success,
        "result": {"test_result": result},
    }
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=2)

    # Note: debug.log removed as it was redundant with output.log
