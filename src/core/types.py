"""Type definitions for the idea assessment system.

This module leverages Claude SDK types and defines project-specific types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Import Claude SDK types we'll use
from claude_code_sdk.types import (
    Message,
    AssistantMessage,
    UserMessage,
    ResultMessage,
    ContentBlock,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

# Re-export commonly used SDK types for convenience
__all__ = [
    # SDK types
    "Message",
    "AssistantMessage",
    "UserMessage",
    "ResultMessage",
    "ContentBlock",
    "TextBlock",
    "ToolUseBlock",
    "ToolResultBlock",
    # Project types
    "AnalysisResult",
    "FeedbackDict",
    "ProcessedMessage",
    "ReviewerRecommendation",
    "PipelineResult",
    "AgentKwargs",
]


# Type aliases
ReviewerRecommendation = Literal["accept", "reject", "conditional"]


@dataclass
class AnalysisResult:
    """Result from analyzing a business idea."""

    content: str
    idea: str
    slug: str
    timestamp: datetime
    search_count: int
    message_count: int
    duration: float
    interrupted: bool = False


@dataclass
class ProcessedMessage:
    """Result from processing a Claude SDK message."""

    message_type: str
    content: list[str]
    metadata: dict[str, object]


class FeedbackIssue(TypedDict):
    """Structure for a single feedback issue."""

    section: str
    issue: str
    suggestion: str
    priority: Literal["critical", "important", "minor"]


class FeedbackDict(TypedDict):
    """Structure for reviewer feedback JSON."""

    overall_assessment: str
    iteration_recommendation: ReviewerRecommendation
    critical_issues: list[FeedbackIssue]
    improvements: list[FeedbackIssue]
    minor_suggestions: list[FeedbackIssue]
    strengths: list[str]
    metadata: dict[str, object]


class PipelineResult(TypedDict, total=False):
    """Result from running the analysis pipeline."""

    # Required fields
    success: bool
    idea: str

    # Success fields
    slug: str
    analysis_file: str
    idea_slug: str
    iterations_completed: int
    iteration_count: int
    feedback_history: list[FeedbackDict]
    metadata: dict[str, object]
    file_path: str
    final_status: str
    history_path: str
    final_analysis: str
    analysis: str

    # Error fields
    error: str
    error_context: str
    iterations: list[dict[str, object]]
    timestamp: str


class AgentKwargs(TypedDict, total=False):
    """Common kwargs passed to agent process methods."""

    debug: bool
    use_websearch: bool
    iteration_count: int
    idea_slug: str
    revision_context: dict[str, str] | None
    logger: object  # StructuredLogger | ConsoleLogger | None


class AnalysisConfigDict(TypedDict):
    """Configuration dictionary for analysis system."""

    max_turns: int
    max_websearches: int
    max_review_iterations: int
    progress_interval: int
    prompts_dir: str
    analyses_dir: str
    logs_dir: str
