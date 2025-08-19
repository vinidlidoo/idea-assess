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


# ==============================================================================
# MODULE-LEVEL CONSTANTS (from constants.py)
# ==============================================================================

# Review iteration limits
MAX_REVIEW_ITERATIONS = 3  # Maximum number of review-revision cycles
MIN_REVIEW_ITERATIONS = 1  # Minimum iterations before accepting

# Content size limits
PREVIEW_CHAR_LIMIT = 200  # Characters to show in content preview
MAX_CONTENT_SIZE = 10_000_000  # Maximum content size in bytes (10MB)
MAX_IDEA_LENGTH = 500  # Maximum length for idea input

# Timing constants
PROGRESS_UPDATE_INTERVAL = 2  # Update progress every N messages

# File operation constants
MAX_FILE_READ_RETRIES = 3  # Maximum retries for file read operations
FILE_RETRY_DELAY = 1.0  # Initial delay for file operation retries (seconds)

# Agent configuration
DEFAULT_MAX_TURNS = 30  # Default maximum turns for agent interactions
REVIEWER_MAX_TURNS = 3  # Maximum turns for reviewer agent
ANALYST_MAX_TURNS = 30  # Maximum turns for analyst agent

# Analysis word limits
MIN_ANALYSIS_WORDS = 900  # Minimum words for analysis
MAX_ANALYSIS_WORDS = 1200  # Maximum words for analysis
SECTION_WORD_LIMITS = {
    "executive_summary": 150,
    "market_opportunity": 250,
    "competition_analysis": 200,
    "business_model": 200,
    "risks_challenges": 200,
    "next_steps": 100,
}


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

    # System limits (from constants.py - immutable boundaries)
    max_content_size: int = 10_000_000  # 10MB
    max_idea_length: int = 500
    max_file_read_retries: int = 3
    file_retry_delay: float = 1.0

    # Global defaults
    slug_max_length: int = 50
    preview_lines: int = 20
    progress_interval: int = 2

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

        # Pass prompts_dir to agent configs
        config.analyst.prompts_dir = config.prompts_dir
        config.analyst.progress_interval = config.progress_interval
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
    prompt_version: str = "v3"
    default_tools: list[str] = field(default_factory=lambda: ["WebSearch"])

    # System paths (from parent config)
    prompts_dir: Path | None = None
    progress_interval: int = 2

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
    max_turns: int = 3
    max_review_iterations: int = 3
    min_review_iterations: int = 1

    # Default settings
    prompt_version: str = "v1"
    default_tools: list[str] = field(default_factory=list)  # No tools by default
    default_strictness: str = "normal"  # "lenient", "normal", "strict"

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
