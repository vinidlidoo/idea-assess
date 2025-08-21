"""Type definitions for the idea assessment system.

This module consolidates all type definitions used across the codebase.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NamedTuple, TypedDict

__all__ = [
    # Core agent types
    "AgentResult",
    # Pipeline types
    "PipelineMode",
    "PipelineResult",
    # Analysis types
    "AnalysisResult",
]


# ==============================================================================
# CORE TYPES
# ==============================================================================


class AnalysisResult(NamedTuple):
    """Container for analysis results and metadata."""

    content: str
    idea: str
    slug: str
    timestamp: datetime
    interrupted: bool = False


@dataclass
class AgentResult:
    """Standard result container for all agents."""

    content: str
    metadata: dict[str, object]
    success: bool
    error: str | None = None


class PipelineMode(Enum):
    """Pipeline execution modes using verb-based naming."""

    ANALYZE = "analyze"  # Analyst only
    ANALYZE_AND_REVIEW = "analyze_and_review"  # Analyst + Reviewer loop
    ANALYZE_REVIEW_AND_JUDGE = "analyze_review_and_judge"  # + Judge (Phase 3)
    FULL_EVALUATION = "full_evaluation"  # All agents (Phase 4)


class PipelineResult(TypedDict, total=False):
    """Result from running the analysis pipeline."""

    # Required fields
    success: bool
    idea: str

    # Success fields
    slug: str
    analysis_file: str
    iterations_completed: int
    iteration_count: int
    metadata: dict[str, object]
    file_path: str
    final_status: str
    final_analysis: str

    # Error fields
    error: str
    error_context: str
    timestamp: str
