"""Configuration system for the idea assessment pipeline."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SystemConfig:
    """System-level configuration for paths and limits."""

    # Core paths
    project_root: Path
    analyses_dir: Path
    config_dir: Path
    logs_dir: Path
    template_dir: Path | None = None  # Directory for file templates

    # System limits
    output_limit: int = 50000

    def __post_init__(self):
        """Ensure all paths are absolute."""
        self.project_root = Path(self.project_root).resolve()
        self.analyses_dir = Path(self.analyses_dir).resolve()
        self.config_dir = Path(self.config_dir).resolve()
        self.logs_dir = Path(self.logs_dir).resolve()

        # Set default template_dir if not provided
        if self.template_dir is None:
            self.template_dir = self.config_dir / "templates"
        else:
            self.template_dir = Path(self.template_dir).resolve()


@dataclass
class BaseAgentConfig:
    """Base configuration shared by all agents."""

    # Common settings
    max_turns: int = 50
    prompts_dir: Path = Path("config/prompts")
    system_prompt: str = "system.md"  # Relative to agent's prompt dir

    # Tools configuration
    allowed_tools: list[str] = field(default_factory=list)

    def get_allowed_tools(self) -> list[str]:
        """Get the list of allowed tools for this agent."""
        return self.allowed_tools.copy()


@dataclass
class AnalystConfig(BaseAgentConfig):
    """Configuration specific to the Analyst agent."""

    # Analyst-specific settings
    max_websearches: int = 4
    min_words: int = 800

    # Default tools for analyst: web research + task organization
    allowed_tools: list[str] = field(
        default_factory=lambda: ["WebSearch", "WebFetch", "TodoWrite"]
    )


@dataclass
class ReviewerConfig(BaseAgentConfig):
    """Configuration specific to the Reviewer agent."""

    # Reviewer-specific settings
    max_iterations: int = 3
    strictness: str = "normal"  # normal, strict, lenient

    # Reviewer typically doesn't need external tools
    allowed_tools: list[str] = field(default_factory=list)


def create_default_configs(
    project_root: Path,
) -> tuple[SystemConfig, AnalystConfig, ReviewerConfig]:
    """Create default configuration instances."""
    system_config = SystemConfig(
        project_root=project_root,
        analyses_dir=project_root / "analyses",
        config_dir=project_root / "config",
        logs_dir=project_root / "logs",
    )

    analyst_config = AnalystConfig(prompts_dir=project_root / "config" / "prompts")

    reviewer_config = ReviewerConfig(prompts_dir=project_root / "config" / "prompts")

    return system_config, analyst_config, reviewer_config
