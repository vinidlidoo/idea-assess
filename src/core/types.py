"""Type definitions for the idea assessment system.

This module defines project-specific types used across the codebase.
"""

from __future__ import annotations

from typing import Literal, TypedDict

__all__ = [
    # Project types
    "FeedbackDict",
    "FeedbackIssue",
    "ReviewerRecommendation",
    "PipelineResult",
]

# Type aliases
ReviewerRecommendation = Literal["accept", "reject", "conditional"]


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
