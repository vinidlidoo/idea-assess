"""Context classes for agents in the pipeline."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.run_analytics import RunAnalytics


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
    feedback_input_path: Path | None = None  # Only on iteration 2+

    # Analyst-specific state
    idea_slug: str = ""
    websearch_count: int = 0


@dataclass
class ReviewerContext(BaseContext):
    """Context specific to the Reviewer agent."""

    # Explicit typed paths
    analysis_input_path: Path = Path("analysis.md")
    feedback_output_path: Path = Path("feedback.md")
