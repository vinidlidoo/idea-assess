"""File operation utilities for the idea assessment system."""

from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=10)
def load_prompt(prompt_file: str, prompts_dir: Path) -> str:
    """
    Load a prompt template from the prompts directory with caching.

    Args:
        prompt_file: Path to the prompt file relative to prompts_dir (e.g., 'agents/analyst/main.md')
        prompts_dir: Directory containing prompt files

    Returns:
        The prompt template content (cached after first load)

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    # Check if it's a new-style path (contains '/')
    if "/" in prompt_file:
        # Direct path - use as is
        prompt_path = prompts_dir / prompt_file
    else:
        # Legacy path - just use as is (for backwards compatibility)
        prompt_path = prompts_dir / prompt_file

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r") as f:
        return f.read()


def load_prompt_with_includes(prompt_file: str, prompts_dir: Path) -> str:
    """
    Load a prompt template with include support.

    Supports {{include:path/to/file.md}} syntax to include other prompt files.

    Args:
        prompt_file: Path to the prompt file relative to prompts_dir
        prompts_dir: Directory containing prompt files

    Returns:
        The prompt content with all includes processed

    Raises:
        FileNotFoundError: If the prompt file or any included file doesn't exist
    """
    import re

    # Load the base prompt
    content = load_prompt(prompt_file, prompts_dir)

    # Process includes - replace {{include:path}} with file contents
    def replace_include(match: re.Match[str]) -> str:
        include_path = match.group(1).strip()
        try:
            return load_prompt(include_path, prompts_dir)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Include file not found: {include_path} (referenced from {prompt_file})"
            )

    # Replace all {{include:path}} with file contents
    content = re.sub(r"\{\{include:([^}]+)\}\}", replace_include, content)

    return content


# Template operations (for creating files from templates)


@lru_cache(maxsize=32)
def load_template(template_path: Path) -> str:
    """Load and cache a template file.

    Args:
        template_path: Path to the template file

    Returns:
        Template content as string
    """
    return template_path.read_text()


def create_file_from_template(template_path: Path, output_path: Path) -> None:
    """Create a file from a template.

    Args:
        template_path: Path to the template file
        output_path: Path where the file should be created
    """
    template_content = load_template(template_path)
    _ = output_path.write_text(template_content)


def append_metadata_to_analysis(
    analysis_file: Path,
    idea: str,
    slug: str,
    iteration: int,
    websearch_count: int = 0,
    webfetch_count: int = 0,
) -> None:
    """Append metadata comment to completed analysis.

    Args:
        analysis_file: Path to the analysis file
        idea: Original business idea text
        slug: Generated slug for the idea
        iteration: Current iteration number
        websearch_count: Number of websearches performed
        webfetch_count: Number of WebFetch verifications performed
    """
    from datetime import datetime

    metadata = f"""
---
<!-- Analysis Metadata - Auto-generated, Do Not Edit -->
<!-- 
Idea Input: "{idea}"
Idea Slug: {slug}
Iteration: {iteration}
Timestamp: {datetime.now().isoformat()}
Websearches Used: {websearch_count}
Webfetches Used: {webfetch_count}
-->
"""

    with open(analysis_file, "a") as f:
        _ = f.write(metadata)
