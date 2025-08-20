"""Configuration management for the idea assessment system.

This module separates concerns into three levels:
1. System-wide configuration (AnalysisConfig)
2. Agent-specific configuration (AnalystConfig, ReviewerConfig, etc.)
3. Runtime context (AnalystContext, ReviewerContext, etc.)

Design Principles:
- Configs are immutable after startup, contexts are mutable during operation
- Configs define defaults and limits, contexts hold runtime state
- Contexts can override config defaults where appropriate
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .types import PipelineMode

if TYPE_CHECKING:
    from .run_analytics import RunAnalytics


# ==============================================================================
# MODULE-LEVEL CONSTANTS
# ==============================================================================
# Only true system limits that never change should be here.
# Agent-specific settings belong in their respective config classes.

# Hard system limits (unchangeable boundaries)
MAX_CONTENT_SIZE = 10_000_000  # Maximum content size in bytes (10MB)
MAX_FILE_READ_RETRIES = 3  # Maximum retries for file read operations
FILE_RETRY_DELAY = 1.0  # Initial delay for file operation retries (seconds)


# ==============================================================================
# PIPELINE CONFIGURATION
# ==============================================================================


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution modes."""

    max_iterations_by_mode: dict[PipelineMode, int] = field(
        default_factory=lambda: {
            PipelineMode.ANALYZE: 1,
            PipelineMode.ANALYZE_AND_REVIEW: 3,
            PipelineMode.ANALYZE_REVIEW_AND_JUDGE: 3,
            PipelineMode.FULL_EVALUATION: 3,
        }
    )


# ==============================================================================
# SYSTEM-WIDE CONFIGURATION
# ==============================================================================


@dataclass
class AnalysisConfig:
    """System-wide configuration for the entire analysis system.

    This is the top-level configuration that:
    - Defines system paths and directories
    - Sets global limits and defaults
    - Contains configurations for each agent type
    """

    # System paths
    project_root: Path
    prompts_dir: Path
    analyses_dir: Path
    logs_dir: Path

    # System limits (references to module constants - true immutable boundaries)
    max_content_size: int = MAX_CONTENT_SIZE
    max_file_read_retries: int = MAX_FILE_READ_RETRIES
    file_retry_delay: float = FILE_RETRY_DELAY

    # System-wide configurable settings (may vary by deployment)
    max_idea_length: int = 500  # Maximum length for idea input
    slug_max_length: int = 50  # Maximum length for generated slugs
    preview_lines: int = 20  # Lines to show in file previews
    preview_char_limit: int = 200  # Characters to show in content preview

    # Pipeline configuration
    default_pipeline_mode: PipelineMode = PipelineMode.ANALYZE_AND_REVIEW
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    # Agent configurations
    analyst: AnalystConfig = field(default_factory=lambda: AnalystConfig())
    reviewer: ReviewerConfig = field(default_factory=lambda: ReviewerConfig())
    # judge: JudgeConfig = field(default_factory=lambda: JudgeConfig())  # Phase 3
    # synthesizer: SynthesizerConfig = field(default_factory=lambda: SynthesizerConfig())  # Phase 4

    @classmethod
    def from_project_root(cls, root: Path | None = None) -> AnalysisConfig:
        """Create config from project root directory."""
        if root is None:
            root = Path(__file__).parent.parent.parent

        # Create the config with paths
        config = cls(
            project_root=root,
            prompts_dir=root / "config" / "prompts",
            analyses_dir=root / "analyses",
            logs_dir=root / "logs",
        )

        # Pass system paths to agent configs
        config.analyst.prompts_dir = config.prompts_dir
        config.reviewer.prompts_dir = config.prompts_dir

        return config


# ==============================================================================
# AGENT-SPECIFIC CONFIGURATIONS
# ==============================================================================


@dataclass
class AnalystConfig:
    """Configuration specific to the Analyst agent.

    Defines defaults and limits for analyst operations.
    These can be overridden at runtime via AnalystContext.
    """

    # Agent-specific limits
    max_turns: int = 30
    max_websearches: int = 5
    min_analysis_words: int = 900
    max_analysis_words: int = 1200

    # Default settings
    prompt_variant: str = "main"  # Can be: "main" (active), "v1"/"v2"/"v3" (historical), "revision" (workflow)
    default_tools: list[str] = field(default_factory=lambda: ["WebSearch"])
    message_log_interval: int = 2  # Log progress every N messages (e.g., "2 messages processed", "4 messages processed")

    # System paths (from parent config)
    prompts_dir: Path | None = None

    # Section word limits
    section_word_limits: dict[str, int] = field(
        default_factory=lambda: {
            "executive_summary": 150,
            "market_opportunity": 250,
            "competition_analysis": 200,
            "business_model": 200,
            "risks_challenges": 200,
            "next_steps": 100,
        }
    )


@dataclass
class ReviewerConfig:
    """Configuration specific to the Reviewer agent.

    Defines defaults and limits for review operations.
    """

    # Agent-specific limits
    max_turns: int = 10  # Increased from 3 to allow Read→Edit workflow
    max_review_iterations: int = 3
    min_review_iterations: int = 1

    # Default settings
    prompt_variant: str = "main"  # Can be: "main" (active), "v1" (historical), etc.
    default_tools: list[str] = field(default_factory=list)  # No tools by default
    default_strictness: str = "normal"  # "lenient", "normal", "strict"
    message_log_interval: int = (
        5  # Log progress every N messages (reviewer typically has fewer messages)
    )

    # System paths (from parent config)
    prompts_dir: Path | None = None


# ==============================================================================
# RUNTIME CONTEXTS (simplified based on feedback)
# ==============================================================================

# NAMING CONVENTION FOR OVERRIDES:
# - Fields ending in "_override" replace the agent's config default when set
# - None means "use the agent's default from config"
# - This makes it clear that None ≠ "no tools/features"
# - Example: tools_override=None → use default_tools from config
#           tools_override=[] → explicitly set to no tools
#           tools_override=["WebSearch"] → use only WebSearch


@dataclass
class BaseContext:
    """Base context with common fields for all agent operations.

    Contains fields that all agents need for runtime state and config overrides.
    """

    # Runtime state
    output_dir: Path | None = None
    """Custom output directory (None = use default)"""

    revision_context: RevisionContext | None = None
    """Revision context if this is an iterative improvement"""

    # Config overrides (None means "use agent's default from config")
    tools_override: list[str] | None = None
    """Custom tool list for this operation (None = use agent's default_tools)"""

    prompt_version_override: str | None = None
    """Custom prompt version for this operation (None = use agent's prompt_version)"""

    # Analytics tracking (injected by pipeline)
    run_analytics: RunAnalytics | None = None
    """Analytics engine for tracking messages and artifacts"""


@dataclass
class RevisionContext:
    """Tracks the state of a multi-iteration analysis/review cycle.

    This is shared across agents during revision cycles.
    """

    iteration: int
    """Current iteration number (1-based)"""

    previous_analysis_path: Path | None = None
    """Path to the most recent analysis file"""

    feedback_path: Path | None = None
    """Path to the most recent feedback JSON file"""

    history: list[tuple[Path, Path]] = field(default_factory=list)
    """History of (analysis_path, feedback_path) tuples"""

    def add_iteration(self, analysis_path: Path, feedback_path: Path) -> None:
        """Record a completed iteration."""
        self.history.append((analysis_path, feedback_path))
        self.previous_analysis_path = analysis_path
        self.feedback_path = feedback_path
        self.iteration += 1


@dataclass
class AnalystContext(BaseContext):
    """Runtime context for a single analyst operation.

    Extends BaseContext with analyst-specific fields.
    """

    # Analyst-specific runtime state
    idea_slug: str | None = None
    """Pre-computed slug for the idea"""

    iteration: int = 1
    """Current iteration number (1-based, 1 = first iteration)"""


@dataclass
class ReviewerContext(BaseContext):
    """Runtime context for a single reviewer operation.

    Extends BaseContext with reviewer-specific fields.
    """

    # Reviewer-specific runtime state
    analysis_path: Path | None = None
    """Path to the analysis file to review (required at runtime)"""

    # Reviewer-specific config overrides
    strictness_override: str | None = None
    """Custom strictness level (None = use agent's default_strictness)"""

    def __post_init__(self) -> None:
        """Validate required fields."""
        if self.analysis_path is None:
            raise ValueError("analysis_path is required for ReviewerContext")


# Helper function for backward compatibility during migration
def get_default_config() -> AnalysisConfig:
    """Get the default configuration."""
    return AnalysisConfig.from_project_root()
