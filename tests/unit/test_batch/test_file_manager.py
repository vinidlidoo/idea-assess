"""Unit tests for the batch file manager module."""

from pathlib import Path
from src.batch.file_manager import move_idea_to_completed, move_idea_to_failed


class TestFileManager:
    """Test the file management functions."""
    
    def test_move_to_completed_new_file(self, tmp_path: Path) -> None:
        """Test moving an idea to a new completed file."""
        pending_file = tmp_path / "pending.md"
        completed_file = tmp_path / "completed.md"
        
        # Create pending file with one idea
        _ = pending_file.write_text("# Test Idea\n\nDescription of the idea.")
        
        # Move to completed
        move_idea_to_completed(
            "Test Idea",
            "Description of the idea.",
            pending_file,
            completed_file
        )
        
        # Check pending is empty
        assert pending_file.read_text().strip() == ""
        
        # Check completed has the idea with timestamp
        completed_content = completed_file.read_text()
        assert "# Test Idea" in completed_content
        assert "Description of the idea." in completed_content
        assert "*Processed:" in completed_content
    
    def test_move_to_completed_existing_file(self, tmp_path: Path) -> None:
        """Test appending to an existing completed file."""
        pending_file = tmp_path / "pending.md"
        completed_file = tmp_path / "completed.md"
        
        # Create existing completed file
        _ = completed_file.write_text("# Old Idea\n\nPrevious content.")
        
        # Create pending file
        _ = pending_file.write_text("# New Idea\n\nNew description.")
        
        # Move to completed
        move_idea_to_completed(
            "New Idea",
            "New description.",
            pending_file,
            completed_file
        )
        
        # Check both ideas are in completed
        completed_content = completed_file.read_text()
        assert "# Old Idea" in completed_content
        assert "# New Idea" in completed_content
        assert "Previous content." in completed_content
        assert "New description." in completed_content
    
    def test_move_to_failed_with_error(self, tmp_path: Path) -> None:
        """Test moving an idea to failed with error message."""
        pending_file = tmp_path / "pending.md"
        failed_file = tmp_path / "failed.md"
        
        # Create pending file
        _ = pending_file.write_text("# Failed Idea\n\nThis will fail.")
        
        # Move to failed
        move_idea_to_failed(
            "Failed Idea",
            "This will fail.",
            pending_file,
            failed_file,
            "Test error message"
        )
        
        # Check pending is empty
        assert pending_file.read_text().strip() == ""
        
        # Check failed has the idea with error
        failed_content = failed_file.read_text()
        assert "# Failed Idea" in failed_content
        assert "This will fail." in failed_content
        assert "**Error:** Test error message" in failed_content
        assert "*Processed:" in failed_content
    
    def test_move_idea_without_description(self, tmp_path: Path) -> None:
        """Test moving an idea that has no description."""
        pending_file = tmp_path / "pending.md"
        completed_file = tmp_path / "completed.md"
        
        # Create pending file with idea without description
        _ = pending_file.write_text("# No Description Idea\n\n# Another Idea\n\nWith description.")
        
        # Move to completed
        move_idea_to_completed(
            "No Description Idea",
            "",
            pending_file,
            completed_file
        )
        
        # Check only the other idea remains in pending
        pending_content = pending_file.read_text()
        assert "No Description Idea" not in pending_content
        assert "Another Idea" in pending_content
        assert "With description." in pending_content
        
        # Check completed has the idea
        completed_content = completed_file.read_text()
        assert "# No Description Idea" in completed_content
    
    def test_multiple_ideas_in_pending(self, tmp_path: Path) -> None:
        """Test removing one idea from multiple in pending file."""
        pending_file = tmp_path / "pending.md"
        completed_file = tmp_path / "completed.md"
        
        # Create pending file with multiple ideas
        content = """# First Idea

First description.

# Second Idea

Second description.

# Third Idea

Third description."""
        _ = pending_file.write_text(content)
        
        # Move second idea to completed
        move_idea_to_completed(
            "Second Idea",
            "Second description.",
            pending_file,
            completed_file
        )
        
        # Check pending still has first and third
        pending_content = pending_file.read_text()
        assert "First Idea" in pending_content
        assert "Second Idea" not in pending_content
        assert "Third Idea" in pending_content
        assert "First description." in pending_content
        assert "Second description." not in pending_content
        assert "Third description." in pending_content
    
    def test_atomic_file_operations(self, tmp_path: Path) -> None:
        """Test that file operations are atomic (using temp files)."""
        pending_file = tmp_path / "pending.md"
        completed_file = tmp_path / "completed.md"
        
        # Create pending file
        _ = pending_file.write_text("# Atomic Test\n\nTest atomicity.")
        
        # Move to completed
        move_idea_to_completed(
            "Atomic Test",
            "Test atomicity.",
            pending_file,
            completed_file
        )
        
        # Files should exist and be valid
        assert pending_file.exists()
        assert completed_file.exists()
        
        # No temp files should remain
        temp_files = list(tmp_path.glob("tmp*"))
        assert len(temp_files) == 0
    
    def test_special_characters_in_title(self, tmp_path: Path) -> None:
        """Test handling special characters in idea titles."""
        pending_file = tmp_path / "pending.md"
        failed_file = tmp_path / "failed.md"
        
        # Create pending with special characters
        _ = pending_file.write_text("# AI & ML: The $100 Solution!\n\nWith special chars.")
        
        # Move to failed
        move_idea_to_failed(
            "AI & ML: The $100 Solution!",
            "With special chars.",
            pending_file,
            failed_file,
            "Special char error"
        )
        
        # Check it was moved correctly
        assert pending_file.read_text().strip() == ""
        failed_content = failed_file.read_text()
        assert "AI & ML: The $100 Solution!" in failed_content
        assert "With special chars." in failed_content
        assert "Special char error" in failed_content