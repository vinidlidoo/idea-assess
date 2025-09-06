"""File management for batch processing workflow."""

import tempfile
from datetime import datetime
from pathlib import Path


def move_idea_to_completed(
    idea_title: str, 
    idea_description: str,
    pending_file: Path,
    completed_file: Path
) -> None:
    """Move a successfully processed idea from pending to completed.
    
    Args:
        idea_title: Title of the idea to move
        idea_description: Description of the idea
        pending_file: Path to pending.md
        completed_file: Path to completed.md
    """
    _move_idea_between_files(
        idea_title, 
        idea_description,
        pending_file,
        completed_file,
        add_timestamp=True
    )


def move_idea_to_failed(
    idea_title: str,
    idea_description: str,
    pending_file: Path,
    failed_file: Path,
    error_message: str
) -> None:
    """Move a failed idea from pending to failed with error message.
    
    Args:
        idea_title: Title of the idea to move
        idea_description: Description of the idea
        pending_file: Path to pending.md
        failed_file: Path to failed.md
        error_message: Error message to append
    """
    # Add error message to description
    enhanced_description = f"{idea_description}\n\n**Error:** {error_message}" if idea_description else f"**Error:** {error_message}"
    
    _move_idea_between_files(
        idea_title,
        enhanced_description,
        pending_file,
        failed_file,
        add_timestamp=True
    )


def _move_idea_between_files(
    idea_title: str,
    idea_description: str,
    source_file: Path,
    target_file: Path,
    add_timestamp: bool = False
) -> None:
    """Internal helper to move idea between files atomically.
    
    Args:
        idea_title: Title of the idea
        idea_description: Description of the idea
        source_file: Source file path
        target_file: Target file path
        add_timestamp: Whether to add timestamp to the idea
    """
    # Remove from source file
    if source_file.exists():
        content = source_file.read_text()
        
        # Find and remove the idea section
        # This is a simplified approach - may need refinement
        lines = content.split('\n')
        new_lines: list[str] = []
        skip_until_next_header = False
        
        for line in lines:
            if line.startswith('# '):
                if line[2:].strip() == idea_title:
                    skip_until_next_header = True
                    continue
                else:
                    skip_until_next_header = False
            
            if not skip_until_next_header:
                new_lines.append(line)
        
        # Write back atomically
        with tempfile.NamedTemporaryFile(mode='w', dir=source_file.parent, delete=False) as tmp:
            tmp.write('\n'.join(new_lines).strip())
            tmp.write('\n')
            tmp_path = Path(tmp.name)
        
        tmp_path.replace(source_file)
    
    # Add to target file
    if not target_file.exists():
        target_file.write_text("")
    
    existing = target_file.read_text()
    
    # Build the new entry
    if add_timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n# {idea_title}\n\n*Processed: {timestamp}*\n"
    else:
        entry = f"\n# {idea_title}\n"
    
    if idea_description:
        entry += f"\n{idea_description}\n"
    
    # Append atomically
    with tempfile.NamedTemporaryFile(mode='w', dir=target_file.parent, delete=False) as tmp:
        tmp.write(existing)
        if existing and not existing.endswith('\n'):
            tmp.write('\n')
        tmp.write(entry)
        tmp_path = Path(tmp.name)
    
    tmp_path.replace(target_file)