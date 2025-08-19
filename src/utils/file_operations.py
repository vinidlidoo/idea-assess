"""File operation utilities for the idea assessment system."""

from pathlib import Path
from datetime import datetime
from typing import NamedTuple
from functools import lru_cache
from filelock import FileLock, Timeout
import json

# Prompt registry import moved to load_prompt function for lazy loading


class AnalysisResult(NamedTuple):
    """Container for analysis results and metadata."""

    content: str
    idea: str
    slug: str
    timestamp: datetime
    interrupted: bool = False
    # Note: search_count, message_count, duration removed - now tracked by RunAnalytics


def create_or_update_symlink(link_path: Path, target: Path | str) -> None:
    """
    Create or update a symbolic link.

    Args:
        link_path: Path where the symlink should be created
        target: Target path (can be relative or absolute)
    """
    link_path = Path(link_path)

    # Remove existing link if it exists
    if link_path.exists():
        link_path.unlink()

    # Create symlink
    if isinstance(target, Path) and target.is_absolute():
        # Convert absolute path to relative for cleaner symlinks
        try:
            target = target.relative_to(link_path.parent)
        except (ValueError, TypeError):
            # If can't make relative, use the name only
            target = target.name

    link_path.symlink_to(target)


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
    interrupted_note = (
        "\nNote: Analysis was interrupted by user" if result.interrupted else ""
    )
    # Note: search_count, message_count, duration now tracked by RunAnalytics
    # These metrics are available in the run_summary.json file

    header = f"""<!-- 
Original Idea: {result.idea}
Generated: {result.timestamp.isoformat()}
Agent: Analyst (Phase 1){interrupted_note}
-->

"""

    # Write with file locking for safety
    safe_write_file(output_file, header + result.content)

    # Create/update symlink to latest analysis
    latest_link = idea_dir / "analysis.md"
    create_or_update_symlink(latest_link, output_file.name)

    return output_file


def safe_write_file(path: Path, content: str, timeout: float = 10.0) -> None:
    """
    Write to a file with file locking for concurrent safety.

    Args:
        path: Path to the file to write
        content: Content to write to the file
        timeout: Maximum time to wait for lock in seconds

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    lock_path = f"{path}.lock"
    lock = FileLock(lock_path, timeout=timeout)

    try:
        with lock:
            with open(path, "w", encoding="utf-8") as f:
                _ = f.write(content)
    except Timeout:
        raise TimeoutError(
            f"Could not acquire lock for {path} within {timeout} seconds"
        )


def safe_read_file(path: Path, timeout: float = 10.0) -> str:
    """
    Read from a file with file locking for concurrent safety.

    Args:
        path: Path to the file to read
        timeout: Maximum time to wait for lock in seconds

    Returns:
        Content of the file

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
        FileNotFoundError: If file doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    lock_path = f"{path}.lock"
    lock = FileLock(lock_path, timeout=timeout)

    try:
        with lock:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Timeout:
        raise TimeoutError(
            f"Could not acquire lock for {path} within {timeout} seconds"
        )


def safe_write_json(path: Path, data: object, timeout: float = 10.0) -> None:
    """
    Write JSON data to a file with file locking.

    Args:
        path: Path to the JSON file
        data: Data to serialize to JSON
        timeout: Maximum time to wait for lock in seconds

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    lock_path = f"{path}.lock"
    lock = FileLock(lock_path, timeout=timeout)

    try:
        with lock:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    except Timeout:
        raise TimeoutError(
            f"Could not acquire lock for {path} within {timeout} seconds"
        )


def safe_read_json(
    path: Path, timeout: float = 10.0
) -> dict[str, object] | list[object] | str | int | float | bool | None:
    """
    Read JSON data from a file with file locking.

    Args:
        path: Path to the JSON file
        timeout: Maximum time to wait for lock in seconds

    Returns:
        Parsed JSON data

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    lock_path = f"{path}.lock"
    lock = FileLock(lock_path, timeout=timeout)

    try:
        with lock:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)  # pyright: ignore[reportAny]
    except Timeout:
        raise TimeoutError(
            f"Could not acquire lock for {path} within {timeout} seconds"
        )


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
