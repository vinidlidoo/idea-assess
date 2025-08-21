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

