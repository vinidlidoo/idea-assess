"""Text processing utilities for the idea assessment system."""

import re


def create_slug(idea: str, max_length: int = 50) -> str:
    """
    Create a filesystem-safe slug from an idea.

    Args:
        idea: The business idea text
        max_length: Maximum length for the slug

    Returns:
        A sanitized slug suitable for directory names
    """
    slug = re.sub(r"[^\w\s-]", "", idea.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug[:max_length].strip("-")

