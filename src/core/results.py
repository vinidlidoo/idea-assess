"""Result types for agents and pipeline."""

from dataclasses import dataclass
from typing import TypedDict


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
