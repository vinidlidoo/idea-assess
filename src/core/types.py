"""Type definitions for the idea assessment system.

This module contains only the pipeline mode enum.
Other types have been moved to their respective modules.
"""

from enum import Enum

__all__ = [
    "PipelineMode",
]


class PipelineMode(Enum):
    """Pipeline execution modes using verb-based naming."""

    ANALYZE = "analyze"  # Analyst only
    ANALYZE_AND_REVIEW = "analyze_and_review"  # Analyst + Reviewer loop
    ANALYZE_REVIEW_AND_JUDGE = "analyze_review_and_judge"  # + Judge (Phase 3)
    FULL_EVALUATION = "full_evaluation"  # All agents (Phase 4)
