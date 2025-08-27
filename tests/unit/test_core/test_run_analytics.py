"""Tests for RunAnalytics class."""

import json

import pytest
from claude_code_sdk.types import (
    UserMessage,
    AssistantMessage,
    SystemMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ThinkingBlock,
    ToolResultBlock,
)

from src.core.run_analytics import RunAnalytics


class TestRunAnalytics:
    """Test the RunAnalytics class."""

    @pytest.fixture
    def analytics(self, tmp_path):
        """Create a RunAnalytics instance for testing."""
        return RunAnalytics(run_id="test_run_123", output_dir=tmp_path)

    def test_initialization(self, analytics, tmp_path):
        """Test proper initialization of RunAnalytics."""
        assert analytics.start_time is not None
        assert analytics.run_id == "test_run_123"
        assert analytics.output_dir == tmp_path / "test_run_123"
        assert analytics.output_dir.exists()
        assert analytics.message_count == 0
        assert analytics.global_tool_count == 0
        assert analytics.search_count == 0
        assert analytics.agent_metrics == {}
        assert analytics.messages_file.name == "messages.jsonl"

    def test_track_user_message(self, analytics):
        """Test tracking user messages."""
        msg = UserMessage(content="Test user message")
        analytics.track_message(msg, agent_name="analyst", iteration=1)

        assert analytics.message_count == 1
        assert ("analyst", 1) in analytics.agent_metrics

        metrics = analytics.agent_metrics[("analyst", 1)]
        assert metrics.message_count == 1
        assert metrics.agent_name == "analyst"
        assert metrics.iteration == 1
        assert metrics.total_text_length > 0

        # Check that message was written to file
        assert analytics.messages_file.exists()

    def test_track_assistant_message_with_blocks(self, analytics):
        """Test tracking assistant messages with multiple content blocks."""
        msg = AssistantMessage(
            content=[
                TextBlock(text="Hello world"),
                ToolUseBlock(
                    id="tool1", name="WebSearch", input={"query": "test search"}
                ),
                ThinkingBlock(thinking="Thinking about this...", signature="test_sig"),
            ],
            model="claude-3-opus",
        )

        analytics.track_message(msg, agent_name="assistant", iteration=1)

        assert analytics.message_count == 1
        assert analytics.global_tool_count == 1
        assert analytics.search_count == 1

        # Check agent metrics
        metrics = analytics.agent_metrics[("assistant", 1)]
        assert metrics.text_blocks == 1
        assert metrics.thinking_blocks == 1
        assert metrics.tool_uses["WebSearch"] == 1
        assert "test search" in metrics.search_queries[0]
        assert metrics.total_text_length > 0
        assert metrics.total_thinking_length > 0

    def test_track_multiple_tools(self, analytics):
        """Test tracking multiple tool uses across messages."""
        msg1 = AssistantMessage(
            content=[
                ToolUseBlock(id="t1", name="WebSearch", input={"query": "query1"}),
                ToolUseBlock(id="t2", name="WebSearch", input={"query": "query2"}),
            ],
            model="claude-3-opus",
        )
        msg2 = AssistantMessage(
            content=[
                ToolUseBlock(id="t3", name="Read", input={"file_path": "/test.py"}),
                ToolUseBlock(
                    id="t4",
                    name="Write",
                    input={"file_path": "/output.txt", "content": "test"},
                ),
            ],
            model="claude-3-opus",
        )

        analytics.track_message(msg1, agent_name="agent", iteration=1)
        analytics.track_message(msg2, agent_name="agent", iteration=1)

        assert analytics.global_tool_count == 4
        assert analytics.search_count == 2

        metrics = analytics.agent_metrics[("agent", 1)]
        assert metrics.tool_uses["WebSearch"] == 2
        assert metrics.tool_uses["Read"] == 1
        assert metrics.tool_uses["Write"] == 1
        assert len(metrics.search_queries) == 2
        assert "/test.py" in metrics.files_read
        assert "/output.txt" in metrics.files_written

    def test_track_file_operations(self, analytics):
        """Test tracking various file operations."""
        msg = AssistantMessage(
            content=[
                ToolUseBlock(id="r1", name="Read", input={"file_path": "/src/main.py"}),
                ToolUseBlock(
                    id="w1",
                    name="Write",
                    input={"file_path": "/output.txt", "content": "data"},
                ),
                ToolUseBlock(
                    id="e1",
                    name="Edit",
                    input={"file_path": "/config.json", "old": "a", "new": "b"},
                ),
                ToolUseBlock(
                    id="m1",
                    name="MultiEdit",
                    input={"file_path": "/multi.py", "edits": []},
                ),
            ],
            model="claude-3-opus",
        )

        analytics.track_message(msg, agent_name="editor", iteration=1)

        metrics = analytics.agent_metrics[("editor", 1)]
        assert "/src/main.py" in metrics.files_read
        assert "/output.txt" in metrics.files_written
        assert "/config.json" in metrics.files_written
        assert "/multi.py" in metrics.files_written

    def test_multiple_agents_and_iterations(self, analytics):
        """Test tracking messages for multiple agents and iterations."""
        msg1 = UserMessage(content="Start")
        msg2 = AssistantMessage(
            content=[TextBlock(text="Response")], model="claude-3-opus"
        )

        # Different agents and iterations
        analytics.track_message(msg1, agent_name="analyst", iteration=1)
        analytics.track_message(msg2, agent_name="analyst", iteration=1)
        analytics.track_message(msg1, agent_name="reviewer", iteration=1)
        analytics.track_message(msg2, agent_name="reviewer", iteration=2)

        assert len(analytics.agent_metrics) == 3
        assert ("analyst", 1) in analytics.agent_metrics
        assert ("reviewer", 1) in analytics.agent_metrics
        assert ("reviewer", 2) in analytics.agent_metrics

        analyst_metrics = analytics.agent_metrics[("analyst", 1)]
        assert analyst_metrics.message_count == 2

    def test_tool_correlation(self, analytics):
        """Test that tool uses are correlated for later results."""
        tool_id = "search_123"
        msg = AssistantMessage(
            content=[
                ToolUseBlock(
                    id=tool_id, name="WebSearch", input={"query": "test query"}
                )
            ],
            model="claude-3-opus",
        )

        analytics.track_message(msg, agent_name="searcher", iteration=1)

        assert tool_id in analytics.tool_correlations
        correlation = analytics.tool_correlations[tool_id]
        assert correlation["tool_name"] == "WebSearch"
        assert correlation["agent"] == "searcher"
        assert correlation["iteration"] == 1
        assert correlation["input"]["query"] == "test query"

    def test_system_message_tracking(self, analytics):
        """Test tracking system messages with session data."""
        msg = SystemMessage(
            subtype="session_start",
            data={"session_id": "session_456", "model": "claude-3-opus"},
        )

        analytics.track_message(msg, agent_name="system", iteration=0)

        assert analytics.message_count == 1
        metrics = analytics.agent_metrics[("system", 0)]
        assert metrics.session_id == "session_456"

    def test_result_message_tracking(self, analytics):
        """Test tracking ResultMessage with execution metrics."""
        result_msg = ResultMessage(
            subtype="final",
            duration_ms=1500,
            duration_api_ms=1200,
            is_error=False,
            num_turns=3,
            session_id="session_123",
            total_cost_usd=0.05,
            usage={"input_tokens": 1000, "output_tokens": 500},
        )

        analytics.track_message(result_msg, agent_name="finisher", iteration=1)

        metrics = analytics.agent_metrics[("finisher", 1)]
        assert metrics.total_cost_usd == 0.05
        assert metrics.token_usage == {"input_tokens": 1000, "output_tokens": 500}
        # Note: session_id from ResultMessage doesn't update metrics.session_id
        assert metrics.end_time is not None
        assert metrics.duration_seconds is not None

    def test_messages_jsonl_file(self, analytics):
        """Test that messages are properly written to JSONL file."""
        msg1 = UserMessage(content="First message")
        msg2 = AssistantMessage(
            content=[TextBlock(text="Second message")], model="claude-3-opus"
        )

        analytics.track_message(msg1, agent_name="test", iteration=1)
        analytics.track_message(msg2, agent_name="test", iteration=1)

        assert analytics.messages_file.exists()

        # Read and verify JSONL content
        with open(analytics.messages_file) as f:
            lines = f.readlines()

        assert len(lines) == 2

        entry1 = json.loads(lines[0])
        assert entry1["run_id"] == "test_run_123"
        assert entry1["agent"] == "test"
        assert entry1["iteration"] == 1
        assert entry1["message_type"] == "UserMessage"
        assert entry1["message_index"] == 1

        entry2 = json.loads(lines[1])
        assert entry2["message_type"] == "AssistantMessage"
        assert entry2["message_index"] == 2

    def test_thinking_blocks_accumulation(self, analytics):
        """Test tracking multiple thinking blocks."""
        msg1 = AssistantMessage(
            content=[
                ThinkingBlock(thinking="First thought", signature="sig1"),
                TextBlock(text="Some text"),
                ThinkingBlock(
                    thinking="Second thought which is longer", signature="sig2"
                ),
            ],
            model="claude-3-opus",
        )

        analytics.track_message(msg1, agent_name="thinker", iteration=1)

        metrics = analytics.agent_metrics[("thinker", 1)]
        assert metrics.thinking_blocks == 2
        assert metrics.text_blocks == 1
        assert metrics.total_thinking_length == len("First thought") + len(
            "Second thought which is longer"
        )

    def test_tool_result_correlation(self, analytics):
        """Test correlation between tool use and tool results."""
        tool_id = "web_search_1"

        # First, track a tool use
        msg1 = AssistantMessage(
            content=[
                ToolUseBlock(id=tool_id, name="WebSearch", input={"query": "python"})
            ],
            model="claude-3-opus",
        )
        analytics.track_message(msg1, agent_name="searcher", iteration=1)

        # Then track the tool result
        msg2 = AssistantMessage(
            content=[
                ToolResultBlock(
                    tool_use_id=tool_id,
                    content='Links: [{"title": "Python.org", "url": "https://python.org"}]',
                    is_error=False,
                )
            ],
            model="claude-3-opus",
        )
        analytics.track_message(msg2, agent_name="searcher", iteration=1)

        # Check that search results were extracted
        metrics = analytics.agent_metrics[("searcher", 1)]
        assert len(metrics.search_results) > 0
        assert metrics.search_results[0]["title"] == "Python.org"
        assert metrics.search_results[0]["url"] == "https://python.org"

    def test_empty_content_handling(self, analytics):
        """Test handling of messages with empty or minimal content."""
        # Empty string content
        msg1 = UserMessage(content="")
        analytics.track_message(msg1, agent_name="test", iteration=1)

        # Empty blocks list
        msg2 = AssistantMessage(content=[], model="claude-3-opus")
        analytics.track_message(msg2, agent_name="test", iteration=1)

        assert analytics.message_count == 2
        assert analytics.messages_file.exists()
