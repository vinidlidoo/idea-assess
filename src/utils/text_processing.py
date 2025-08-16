"""Text processing utilities for the idea assessment system."""

import re

# Constants
SLUG_MAX_LENGTH = 50
PREVIEW_LINES = 20


def create_slug(idea: str, max_length: int = SLUG_MAX_LENGTH) -> str:
    """
    Create a filesystem-safe slug from an idea.
    
    Args:
        idea: The business idea text
        max_length: Maximum length for the slug
        
    Returns:
        A sanitized slug suitable for directory names
    """
    slug = re.sub(r'[^\w\s-]', '', idea.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:max_length].strip('-')


def show_preview(content: str, max_lines: int = PREVIEW_LINES) -> None:
    """
    Display a preview of the analysis content.
    
    Args:
        content: The full analysis text
        max_lines: Maximum number of lines to show
    """
    print("\n" + "=" * 60)
    print("ANALYSIS PREVIEW")
    print("=" * 60)
    
    lines = content.split('\n')[:max_lines]
    for line in lines:
        print(line)
    
    if len(content.split('\n')) > max_lines:
        print("...")
        print(f"\n[Preview shows first {max_lines} lines of {len(content.split('\n'))} total]")