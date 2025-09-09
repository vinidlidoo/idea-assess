"""Type definitions for the idea assessment system.

This module consolidates all type definitions for the project,
including pipeline modes, result types, and context classes.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from src.core.run_analytics import RunAnalytics


# ============================================================================
# Pipeline Modes
# ============================================================================


class PipelineMode(Enum):
    """Pipeline execution modes using verb-based naming."""

    ANALYZE = "analyze"  # Analyst only
    ANALYZE_AND_REVIEW = "analyze_and_review"  # Analyst + Reviewer loop
    ANALYZE_REVIEW_AND_JUDGE = "analyze_review_and_judge"  # + Judge (Phase 3)
    ANALYZE_REVIEW_WITH_FACT_CHECK = (
        "analyze_review_with_fact_check"  # + FactChecker parallel
    )
    FULL_EVALUATION = "full_evaluation"  # All agents (Phase 4)


# ============================================================================
# Result Types
# ============================================================================


@dataclass
class Success:
    """Represents a successful agent execution."""

    # No data needed for success - the outputs are in files


@dataclass
class Error:
    """Represents a failed agent execution."""

    message: str


# Type alias for agent results
AgentResult = Success | Error


class PipelineResult(TypedDict):
    """Result from the full pipeline execution."""

    success: bool
    analysis_path: str | None
    feedback_path: str | None
    idea_slug: str
    iterations: int
    message: str | None


# ============================================================================
# Context Types
# ============================================================================


@dataclass
class BaseContext:
    """Base context shared by all agents."""

    # Common runtime state
    iteration: int = 1
    tools: list[str] | None = None
    run_analytics: "RunAnalytics | None" = None


@dataclass
class AnalystContext(BaseContext):
    """Context specific to the Analyst agent."""

    # Explicit typed paths
    analysis_output_path: Path = Path("analysis.md")
    previous_analysis_input_path: Path | None = None  # Only on iteration 2+
    feedback_input_path: Path | None = None  # Only on iteration 2+ (reviewer)
    fact_check_input_path: Path | None = None  # Only on iteration 2+ (fact-checker)

    # Analyst-specific state
    idea_slug: str = ""
    websearch_count: int = 0


@dataclass
class ReviewerContext(BaseContext):
    """Context specific to the Reviewer agent."""

    # Explicit typed paths
    analysis_input_path: Path = Path("analysis.md")
    feedback_output_path: Path = Path("feedback.md")
    previous_feedback_path: Path | None = None  # Path to previous iteration's feedback


@dataclass
class FactCheckContext(BaseContext):
    """Context specific to the FactChecker agent."""

    # Explicit typed paths
    analysis_input_path: Path = Path("analysis.md")
    fact_check_output_path: Path = Path("fact-check.json")

    # Max iterations from ReviewerConfig (shared between reviewer and fact-checker)
    max_iterations: int = 3


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Pipeline modes
    "PipelineMode",
    # Result types
    "Success",
    "Error",
    "AgentResult",
    "PipelineResult",
    # Context types
    "BaseContext",
    "AnalystContext",
    "ReviewerContext",
    "FactCheckContext",
]
