"""File operation utilities for the idea assessment system."""

from pathlib import Path
from datetime import datetime
from typing import NamedTuple


class AnalysisResult(NamedTuple):
    """Container for analysis results and metadata."""
    content: str
    idea: str
    slug: str
    timestamp: datetime
    search_count: int = 0
    message_count: int = 0
    duration: float = 0.0
    interrupted: bool = False


def save_analysis(result: AnalysisResult, analyses_dir: Path) -> Path:
    """
    Save analysis result to a markdown file.
    
    Args:
        result: The analysis result to save
        analyses_dir: Directory to save analyses
        
    Returns:
        Path to the saved file
    """
    # Create directory for this idea
    idea_dir = analyses_dir / result.slug
    idea_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S")
    output_file = idea_dir / f"analysis_{timestamp_str}.md"
    
    # Add metadata header
    interrupted_note = "\nNote: Analysis was interrupted by user" if result.interrupted else ""
    websearch_note = f"\nWebSearches: {result.search_count}" if result.search_count > 0 else "\nWebSearch: Disabled"
    
    header = f"""<!-- 
Original Idea: {result.idea}
Generated: {result.timestamp.isoformat()}
Agent: Analyst (Phase 1)
Duration: {result.duration:.1f}s
Messages: {result.message_count}{websearch_note}{interrupted_note}
-->

"""
    
    with open(output_file, 'w') as f:
        f.write(header + result.content)
    
    # Create/update symlink to latest analysis
    latest_link = idea_dir / "analysis.md"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(output_file.name)
    
    return output_file


def load_prompt(prompt_file: str, prompts_dir: Path) -> str:
    """
    Load a prompt template from the prompts directory.
    
    Args:
        prompt_file: Name of the prompt file to load
        prompts_dir: Directory containing prompt files
        
    Returns:
        The prompt template content
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    prompt_path = prompts_dir / prompt_file
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r') as f:
        return f.read()