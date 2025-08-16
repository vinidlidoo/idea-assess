"""Configuration management for the idea assessment system."""

from pathlib import Path
from dataclasses import dataclass


@dataclass
class AnalysisConfig:
    """Configuration for analysis operations."""
    project_root: Path
    prompts_dir: Path
    analyses_dir: Path
    logs_dir: Path
    max_turns: int = 15
    max_websearches: int = 5
    slug_max_length: int = 50
    preview_lines: int = 20
    progress_interval: int = 2
    default_prompt_version: str = "v3"
    default_prompt_file: str = "analyst_v1.md"
    
    @classmethod
    def from_project_root(cls, root: Path | None = None) -> 'AnalysisConfig':
        """Create config from project root directory."""
        if root is None:
            # Default to parent of src directory
            root = Path(__file__).parent.parent.parent
        
        return cls(
            project_root=root,
            prompts_dir=root / "config" / "prompts",
            analyses_dir=root / "analyses",
            logs_dir=root / "logs"
        )


def get_default_config() -> AnalysisConfig:
    """Get the default configuration."""
    return AnalysisConfig.from_project_root()