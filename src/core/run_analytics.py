"""Comprehensive analytics engine for multi-agent pipeline runs.

This module provides detailed tracking and analysis of all messages
and artifacts during pipeline execution, replacing MessageProcessor.
"""
# pyright: reportExplicitAny=false
# pyright: reportAny=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field, asdict

from claude_code_sdk.types import (
    ContentBlock,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    """Metrics for a single agent's execution."""

    agent_name: str
    iteration: int
    message_count: int = 0
    tool_uses: dict[str, int] = field(default_factory=dict)
    text_blocks: int = 0
    thinking_blocks: int = 0
    total_text_length: int = 0
    total_thinking_length: int = 0
    search_queries: list[str] = field(default_factory=list)
    search_results: list[dict[str, str]] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    duration_seconds: float | None = None
    session_id: str | None = None
    total_cost_usd: float | None = None
    token_usage: dict[str, int] = field(default_factory=dict)


class RunAnalytics:
    """
    Comprehensive analytics engine for multi-agent pipeline runs.

    Primary responsibilities:
    1. Track messages, tools, and timing across all agents
    2. Extract and correlate artifacts from SDK messages
    3. Aggregate statistics per agent and globally
    4. Persist analytics data for post-run analysis

    Outputs:
    - messages.jsonl: Detailed message log with extracted artifacts
    - run_summary.json: Aggregated metrics for the entire run
    """

    def __init__(self, run_id: str, output_dir: Path) -> None:
        """
        Initialize analytics for a pipeline run.

        Args:
            run_id: Unique identifier for this run (typically timestamp_slug)
            output_dir: Directory to write output files (typically logs/runs)
        """
        self.run_id: str = run_id
        # Create a subfolder for this run using the run_id
        self.output_dir: Path = Path(output_dir) / run_id
        self.start_time: datetime = datetime.now()

        # Tracking structures
        self.agent_metrics: dict[tuple[str, int], AgentMetrics] = {}
        self.tool_correlations: dict[
            str, dict[str, Any]
        ] = {}  # tool_use_id -> result mapping
        # Use simple filenames within the run subfolder
        self.messages_file: Path = self.output_dir / "messages.jsonl"

        # Global counters
        self.message_count: int = 0
        self.global_tool_count: int = 0
        self.search_count: int = 0
        self.webfetch_count: int = 0

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"RunAnalytics initialized for run: {run_id}")
        logger.debug(f"Output directory: {self.output_dir}")

    def track_message(
        self, message: object, agent_name: str, iteration: int = 0
    ) -> None:
        """
        Track a message and extract artifacts.

        Args:
            message: SDK message to track
            agent_name: Name of the agent processing this message
            iteration: Current iteration number (for multi-iteration workflows)
        """
        self.message_count += 1

        # Get or create agent metrics
        key = (agent_name, iteration)
        if key not in self.agent_metrics:
            self.agent_metrics[key] = AgentMetrics(agent_name, iteration)

        metrics = self.agent_metrics[key]
        metrics.message_count += 1

        # Extract artifacts based on message type
        artifacts = {}

        if isinstance(message, SystemMessage):
            artifacts = self._extract_system_artifacts(message)
            if artifacts.get("session_id"):
                metrics.session_id = artifacts["session_id"]

        elif isinstance(message, (UserMessage, AssistantMessage)):
            artifacts = self._extract_content_artifacts(message, metrics)

        elif isinstance(message, ResultMessage):
            artifacts = self._extract_result_artifacts(message, metrics)
            metrics.end_time = datetime.now()
            metrics.duration_seconds = (
                metrics.end_time - metrics.start_time
            ).total_seconds()

        # Write to messages.jsonl
        self._write_message_log(message, agent_name, iteration, artifacts)

        # Log progress periodically
        if self.message_count % 10 == 0:
            logger.debug(f"Tracked {self.message_count} messages")

    def _extract_system_artifacts(self, message: SystemMessage) -> dict[str, Any]:
        """Extract artifacts from SystemMessage."""
        artifacts = {"subtype": message.subtype, "data": message.data or {}}
        if message.data and "session_id" in message.data:
            artifacts["session_id"] = message.data["session_id"]
        return artifacts

    def _extract_content_artifacts(
        self, message: UserMessage | AssistantMessage, metrics: AgentMetrics
    ) -> dict[str, Any]:
        """Extract artifacts from content messages."""
        artifacts: dict[str, Any] = {"blocks": []}

        content = message.content
        if isinstance(content, str):
            artifacts["content_type"] = "string"
            artifacts["content_length"] = len(content)
            metrics.total_text_length += len(content)
        else:  # list[ContentBlock]
            artifacts["content_type"] = "blocks"
            for block in content:
                block_artifacts = self._extract_block_artifacts(block, metrics)
                artifacts["blocks"].append(block_artifacts)

        return artifacts

    def _extract_block_artifacts(
        self, block: ContentBlock, metrics: AgentMetrics
    ) -> dict[str, Any]:
        """Extract artifacts from a single content block."""
        if isinstance(block, TextBlock):
            metrics.text_blocks += 1
            metrics.total_text_length += len(block.text)
            return {
                "type": "TextBlock",
                "text_length": len(block.text),
                "text_preview": block.text[:200] + "..."
                if len(block.text) > 200
                else block.text,
            }

        elif isinstance(block, ThinkingBlock):
            metrics.thinking_blocks += 1
            metrics.total_thinking_length += len(block.thinking)
            return {
                "type": "ThinkingBlock",
                "thinking_length": len(block.thinking),
                "thinking_signature": block.signature,
                "thinking_preview": block.thinking[:200] + "..."
                if len(block.thinking) > 200
                else block.thinking,
            }

        elif isinstance(block, ToolUseBlock):
            tool_name = block.name
            metrics.tool_uses[tool_name] = metrics.tool_uses.get(tool_name, 0) + 1
            self.global_tool_count += 1

            tool_artifacts: dict[str, Any] = {
                "type": "ToolUseBlock",
                "tool_id": block.id,
                "tool_name": tool_name,
                "tool_input": {},
            }

            # Extract tool-specific inputs
            if tool_name == "WebSearch" and block.input:
                query = block.input.get("query", "")
                metrics.search_queries.append(query)
                self.search_count += 1
                if "tool_input" in tool_artifacts and isinstance(
                    tool_artifacts["tool_input"], dict
                ):
                    tool_artifacts["tool_input"]["query"] = query
            elif tool_name == "WebFetch":
                self.webfetch_count += 1
            elif tool_name == "Read" and block.input:
                file_path = block.input.get("file_path", "")
                if file_path:
                    metrics.files_read.append(file_path)
                if "tool_input" in tool_artifacts and isinstance(
                    tool_artifacts["tool_input"], dict
                ):
                    tool_artifacts["tool_input"]["file_path"] = file_path
            elif tool_name in ["Write", "Edit", "MultiEdit"] and block.input:
                file_path = block.input.get("file_path", "")
                if file_path:
                    metrics.files_written.append(file_path)
                if "tool_input" in tool_artifacts and isinstance(
                    tool_artifacts["tool_input"], dict
                ):
                    tool_artifacts["tool_input"]["file_path"] = file_path

            # Store for correlation with results
            self.tool_correlations[block.id] = {
                "tool_name": tool_name,
                "input": block.input,
                "agent": metrics.agent_name,
                "iteration": metrics.iteration,
            }

            return tool_artifacts

        else:  # Must be ToolResultBlock - the only remaining ContentBlock type
            result_artifacts: dict[str, Any] = {
                "type": "ToolResultBlock",
                "tool_use_id": getattr(block, "tool_use_id", None),
                "is_error": block.is_error,
                "content_preview": str(block.content)[:500] if block.content else None,
            }

            # Correlate with tool use
            tool_use_id = getattr(block, "tool_use_id", None)
            if tool_use_id and tool_use_id in self.tool_correlations:
                tool_info = self.tool_correlations[tool_use_id]
                result_artifacts["correlated_tool"] = tool_info["tool_name"]

                # Extract WebSearch results
                if tool_info["tool_name"] == "WebSearch" and block.content:
                    if isinstance(block.content, str) and "Links:" in block.content:
                        links_match = re.search(
                            r"Links:\s*(\[.*?\])", block.content, re.DOTALL
                        )
                        if links_match:
                            try:
                                links_data = json.loads(links_match.group(1))
                                search_results = [
                                    {
                                        "title": link.get("title", ""),
                                        "url": link.get("url", ""),
                                    }
                                    for link in links_data
                                ]
                                result_artifacts["search_results"] = search_results
                                metrics.search_results.extend(search_results)
                            except json.JSONDecodeError:
                                logger.debug(
                                    f"Failed to parse search results JSON for tool {tool_use_id}"
                                )

            return result_artifacts

    def _extract_result_artifacts(
        self, message: ResultMessage, metrics: AgentMetrics
    ) -> dict[str, Any]:
        """Extract final execution metrics from result message."""
        artifacts = {
            "subtype": message.subtype,
            "duration_ms": message.duration_ms,
            "duration_api_ms": message.duration_api_ms,
            "is_error": message.is_error,
            "num_turns": message.num_turns,
            "session_id": message.session_id,
            "total_cost_usd": message.total_cost_usd,
            "usage": message.usage,
        }

        # Update agent metrics
        if message.total_cost_usd:
            metrics.total_cost_usd = message.total_cost_usd
        if message.usage:
            metrics.token_usage = message.usage

        return artifacts

    def _write_message_log(
        self,
        message: object,
        agent_name: str,
        iteration: int,
        artifacts: dict[str, Any],
    ) -> None:
        """Write message and artifacts to JSONL file."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "agent": agent_name,
            "iteration": iteration,
            "message_index": self.message_count,
            "message_type": type(message).__name__,
            "artifacts": artifacts,
            "message": self._serialize_message(message),
        }

        try:
            with open(self.messages_file, "a") as f:
                _ = f.write(json.dumps(entry, default=str) + "\n")
        except (IOError, OSError) as e:
            logger.error(f"Failed to write message log: {e}", exc_info=True)

    def _serialize_message(
        self, message: object, max_length: int = 1000
    ) -> dict[str, Any]:
        """
        Serialize SDK message for logging with truncation.

        Args:
            message: SDK message to serialize
            max_length: Maximum length for text content

        Returns:
            Dictionary representation of the message
        """
        if isinstance(message, (UserMessage, AssistantMessage)):
            msg_type = type(message).__name__
            content = message.content

            if isinstance(content, str):
                truncated = (
                    content[:max_length] + "..."
                    if len(content) > max_length
                    else content
                )
                return {"type": msg_type, "content": truncated}
            else:  # list[ContentBlock]
                return {
                    "type": msg_type,
                    "content": [
                        self._serialize_block(block) for block in content[:5]
                    ],  # Max 5 blocks
                }

        elif isinstance(message, SystemMessage):
            return {
                "type": "SystemMessage",
                "subtype": message.subtype,
                "data": message.data,  # Usually small metadata
            }

        elif isinstance(message, ResultMessage):
            result_text = (
                message.result[:max_length] + "..."
                if message.result and len(message.result) > max_length
                else message.result
            )
            return {
                "type": "ResultMessage",
                "subtype": message.subtype,
                "duration_ms": message.duration_ms,
                "is_error": message.is_error,
                "result": result_text,
            }

        return {"type": "Unknown"}

    def _serialize_block(self, block: ContentBlock) -> dict[str, Any]:
        """Serialize content blocks with truncation."""
        if isinstance(block, TextBlock):
            text = block.text[:500] + "..." if len(block.text) > 500 else block.text
            return {"type": "TextBlock", "text": text}

        elif isinstance(block, ThinkingBlock):
            thinking = (
                block.thinking[:500] + "..."
                if len(block.thinking) > 500
                else block.thinking
            )
            return {
                "type": "ThinkingBlock",
                "thinking": thinking,
                "signature": block.signature,
            }

        elif isinstance(block, ToolUseBlock):
            return {
                "type": "ToolUseBlock",
                "name": block.name,
                "id": block.id,
                "input": block.input,
            }

        else:  # isinstance(block, ToolResultBlock)
            content_str = str(block.content) if block.content else None
            truncated = (
                content_str[:500] + "..."
                if content_str and len(content_str) > 500
                else content_str
            )
            return {
                "type": "ToolResultBlock",
                "content": truncated,
                "is_error": block.is_error,
            }

    def log_system_prompt(self, agent_name: str, iteration: int, prompt: str) -> None:
        """
        Log the formatted system prompt for an agent (only once per agent per run).

        Args:
            agent_name: Name of the agent (e.g., "analyst")
            iteration: Current iteration number (kept for API compatibility but not used in filename)
            prompt: The fully formatted system prompt
        """
        from datetime import datetime

        # Create filename without iteration (one per agent per run)
        prompt_file = self.output_dir / f"{agent_name}_system_prompt.md"

        # Skip if already logged for this agent in this run
        if prompt_file.exists():
            logger.debug(f"System prompt already logged for {agent_name}, skipping")
            return

        try:
            with open(prompt_file, "w") as f:
                # Write header with metadata (no iteration)
                _ = f.write(f"# {agent_name.title()} System Prompt\n\n")
                _ = f.write(f"**Timestamp:** {datetime.now().isoformat()}\n")
                _ = f.write(f"**Run ID:** {self.run_id}\n\n")
                _ = f.write("---\n\n")
                # Write the actual prompt
                _ = f.write(prompt)

            logger.debug(f"System prompt written to: {prompt_file}")
        except (IOError, OSError) as e:
            logger.error(f"Failed to write system prompt: {e}", exc_info=True)

    def finalize(self) -> None:
        """Write final run summary when pipeline completes."""
        agent_metrics_data: dict[str, Any] = {}

        summary = {
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "global_stats": {
                "total_messages": self.message_count,
                "total_tool_uses": self.global_tool_count,
                "total_searches": self.search_count,
                "total_webfetches": self.webfetch_count,
            },
            "agent_metrics": agent_metrics_data,
        }

        # Add per-agent metrics
        for (agent_name, iteration), metrics in self.agent_metrics.items():
            key = f"{agent_name}_iteration_{iteration}"
            # Convert dataclass to dict, handling datetime objects
            metrics_dict = asdict(metrics)
            # Convert datetime objects to strings
            for field_name in ["start_time", "end_time"]:
                if field_name in metrics_dict and metrics_dict[field_name]:
                    if hasattr(metrics_dict[field_name], "isoformat"):
                        metrics_dict[field_name] = metrics_dict[field_name].isoformat()
            agent_metrics_data[key] = metrics_dict

        # Calculate aggregated statistics
        summary["aggregated_stats"] = self._calculate_aggregated_stats()

        # Use simple filename within the run subfolder
        summary_file = self.output_dir / "run_summary.json"
        try:
            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2, default=str)
            logger.info(f"Run summary written to {summary_file}")
        except (IOError, OSError, TypeError) as e:
            logger.error(f"Failed to write run summary: {e}", exc_info=True)

    def _calculate_aggregated_stats(self) -> dict[str, Any]:
        """Calculate aggregated statistics across all agents."""
        stats: dict[str, Any] = {
            "total_text_generated": 0,
            "total_thinking_generated": 0,
            "total_searches": 0,
            "total_files_read": 0,
            "total_files_written": 0,
            "total_cost_usd": 0.0,
            "unique_files_read": set(),
            "unique_files_written": set(),
            "all_search_queries": [],
            "all_search_results": [],
        }

        for metrics in self.agent_metrics.values():
            stats["total_text_generated"] = (
                stats["total_text_generated"] + metrics.total_text_length
            )
            stats["total_thinking_generated"] = (
                stats["total_thinking_generated"] + metrics.total_thinking_length
            )
            stats["total_searches"] = stats["total_searches"] + len(
                metrics.search_queries
            )
            stats["total_files_read"] = stats["total_files_read"] + len(
                metrics.files_read
            )
            stats["total_files_written"] = stats["total_files_written"] + len(
                metrics.files_written
            )
            if metrics.total_cost_usd:
                stats["total_cost_usd"] = (
                    stats["total_cost_usd"] + metrics.total_cost_usd
                )
            if isinstance(stats["unique_files_read"], set):
                stats["unique_files_read"].update(metrics.files_read)
            if isinstance(stats["unique_files_written"], set):
                stats["unique_files_written"].update(metrics.files_written)
            if isinstance(stats["all_search_queries"], list):
                stats["all_search_queries"].extend(metrics.search_queries)
            if isinstance(stats["all_search_results"], list):
                stats["all_search_results"].extend(metrics.search_results)

        # Convert sets to lists for JSON serialization
        if isinstance(stats["unique_files_read"], set):
            stats["unique_files_read"] = list(stats["unique_files_read"])
        if isinstance(stats["unique_files_written"], set):
            stats["unique_files_written"] = list(stats["unique_files_written"])

        return stats

    def get_current_stats(self) -> dict[str, int]:
        """
        Get current statistics for display.

        Returns:
            Dictionary with current message and search counts
        """
        return {
            "message_count": self.message_count,
            "search_count": self.search_count,
            "webfetch_count": self.webfetch_count,
            "tool_count": self.global_tool_count,
        }
