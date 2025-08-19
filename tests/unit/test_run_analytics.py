"""Unit tests for RunAnalytics.

Note: Due to complex SDK type dependencies, most RunAnalytics functionality
is tested via integration tests. See tests/README.md for testing strategy.
"""

import tempfile
from pathlib import Path

from src.core.run_analytics import RunAnalytics, AgentMetrics


class TestRunAnalytics:
    """Basic unit tests for RunAnalytics initialization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.run_id = "test_run_123"
        self.analytics = RunAnalytics(self.run_id, Path(self.temp_dir))

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test RunAnalytics initialization."""
        assert self.analytics.run_id == self.run_id
        assert self.analytics.output_dir == Path(self.temp_dir)
        assert len(self.analytics.agent_metrics) == 0
        assert self.analytics.global_message_count == 0
        assert self.analytics.global_tool_count == 0
        assert self.analytics.global_search_count == 0

    def test_output_directory_creation(self):
        """Test that output directory is created."""
        test_dir = Path(self.temp_dir) / "nested" / "path"
        _ = RunAnalytics("test_nested", test_dir)  # Creating instance creates directory
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_messages_file_path(self):
        """Test messages file path is set correctly."""
        expected_path = Path(self.temp_dir) / f"{self.run_id}_messages.jsonl"
        assert self.analytics.messages_file == expected_path

    def test_get_current_stats(self):
        """Test get_current_stats returns correct initial values."""
        stats = self.analytics.get_current_stats()
        assert stats["message_count"] == 0
        assert stats["search_count"] == 0
        assert stats["tool_count"] == 0

    def test_finalize_creates_summary_file(self):
        """Test that finalize() creates a run_summary.json file."""
        # Add some agent metrics
        self.analytics.agent_metrics[("analyst", 0)] = AgentMetrics(
            agent_name="analyst", iteration=0
        )

        # Call finalize
        self.analytics.finalize()

        # Check summary file was created
        summary_file = Path(self.temp_dir) / f"{self.run_id}_run_summary.json"
        assert summary_file.exists()

        # Verify JSON structure
        import json

        with open(summary_file) as f:
            summary = json.load(f)

        assert summary["run_id"] == self.run_id
        assert "global_stats" in summary
        assert "agent_metrics" in summary
        assert "aggregated_stats" in summary


class TestAgentMetrics:
    """Test suite for AgentMetrics dataclass."""

    def test_default_values(self):
        """Test AgentMetrics default values."""
        metrics = AgentMetrics(agent_name="test", iteration=0)

        assert metrics.agent_name == "test"
        assert metrics.iteration == 0
        assert metrics.message_count == 0
        assert metrics.tool_uses == {}
        assert metrics.search_queries == []
        assert metrics.search_results == []
        assert metrics.files_read == []
        assert metrics.files_written == []
        assert metrics.text_blocks == 0
        assert metrics.thinking_blocks == 0
        assert metrics.total_text_length == 0
        assert metrics.total_thinking_length == 0
        # start_time is set in __init__
        assert metrics.start_time is not None
        assert metrics.end_time is None
        assert metrics.duration_seconds is None
        assert metrics.session_id is None
        assert metrics.total_cost_usd is None
        assert metrics.token_usage == {}

    def test_mutable_defaults(self):
        """Test that mutable defaults don't share state."""
        metrics1 = AgentMetrics(agent_name="agent1", iteration=0)
        metrics2 = AgentMetrics(agent_name="agent2", iteration=0)

        # Modify metrics1
        metrics1.tool_uses["Read"] = 1
        metrics1.search_queries.append("query1")
        metrics1.files_read.append("/file1.txt")

        # metrics2 should not be affected
        assert metrics2.tool_uses == {}
        assert metrics2.search_queries == []
        assert metrics2.files_read == []

    def test_metrics_independence(self):
        """Test that metrics for different agents are independent."""
        analyst_metrics = AgentMetrics(agent_name="analyst", iteration=0)
        reviewer_metrics = AgentMetrics(agent_name="reviewer", iteration=0)

        analyst_metrics.message_count = 5
        reviewer_metrics.message_count = 3

        assert analyst_metrics.message_count == 5
        assert reviewer_metrics.message_count == 3
        assert analyst_metrics.agent_name != reviewer_metrics.agent_name
