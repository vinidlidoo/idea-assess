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
    # Archive and utility types
    "AnalysisResult",
    "ArchiveMetadata",
    "ArchiveSummaryItem",
    "ArchiveSummary",
    "CleanupStats",
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


# ==============================================================================
# ARCHIVE AND UTILITY TYPES
# ==============================================================================


class ArchiveMetadata(TypedDict, total=False):
    """Metadata for archived runs."""

    archived_at: str
    run_type: str
    run_number: int
    created_at: str
    final_status: str
    iteration_count: int
    word_count: int
    character_count: int
    reviewer_decision: str
    critical_issues: int
    improvements: int
    assessment: str
    iterations: list[dict[str, object]]
    # Future fields for Phase 3
    grade: str  # A-D grade from Judge
    score: float  # Numeric score from Judge


class ArchiveSummaryItem(TypedDict):
    """Single archive summary item."""

    name: str
    run_type: str
    archived_at: str
    run_number: int


class ArchiveSummary(TypedDict):
    """Summary of all archives."""

    archives: list[ArchiveSummaryItem]
    total: int
    test_runs: int
    production_runs: int


class CleanupStats(TypedDict):
    """Statistics from cleanup operations."""

    status: str
    files_moved: int
    files_deleted: int
    duplicates_removed: int
    files_archived: int
