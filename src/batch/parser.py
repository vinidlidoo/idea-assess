"""Parser for markdown-formatted ideas file."""

import re
from pathlib import Path


def parse_ideas_file(file_path: Path) -> list[tuple[str, str]]:
    """Parse markdown file into list of (title, description) tuples.
    
    Expected format:
    # Idea Title
    Optional description paragraph(s)...
    
    # Another Idea
    More description...
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        List of (title, description) tuples
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is malformed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Ideas file not found: {file_path}")
    
    content = file_path.read_text().strip()
    if not content:
        return []
    
    # Split by H1 headers (# at start of line)
    # Pattern matches lines starting with single # followed by space
    sections = re.split(r'^# ', content, flags=re.MULTILINE)
    
    # First element might be empty or contain pre-header content
    if sections[0].strip():
        # Content before first header is invalid
        raise ValueError(f"Malformed ideas file: content before first header in {file_path}")
    
    ideas: list[tuple[str, str]] = []
    for section in sections[1:]:  # Skip first empty element
        if not section.strip():
            continue
            
        lines = section.strip().split('\n')
        if not lines:
            continue
            
        # First line is the title (everything after the #)
        title = lines[0].strip()
        if not title:
            continue
            
        # Rest is description (if any)
        description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
        
        # Enforce 300 word limit on description
        if description:
            word_count = len(description.split())
            if word_count > 300:
                raise ValueError(
                    f"Description for '{title}' exceeds 300 words ({word_count} words)"
                )
        
        ideas.append((title, description))
    
    return ideas