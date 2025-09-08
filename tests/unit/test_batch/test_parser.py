"""Unit tests for the batch parser module."""

import pytest
from pathlib import Path
from src.batch.parser import parse_ideas_file


class TestParseIdeasFile:
    """Test the markdown ideas file parser."""
    
    def test_parse_valid_file(self, tmp_path: Path) -> None:
        """Test parsing a valid markdown file with multiple ideas."""
        content = """# AI Fitness App

An AI-powered fitness application that provides personalized workout plans 
based on user goals and fitness levels.

# B2B Marketplace

Connect businesses with suppliers for bulk purchasing.

# Virtual Reality Training

"""
        file_path = tmp_path / "ideas.md"
        _ = file_path.write_text(content)
        
        ideas = parse_ideas_file(file_path)
        
        assert len(ideas) == 3
        assert ideas[0] == (
            "AI Fitness App",
            "An AI-powered fitness application that provides personalized workout plans \nbased on user goals and fitness levels."
        )
        assert ideas[1] == (
            "B2B Marketplace", 
            "Connect businesses with suppliers for bulk purchasing."
        )
        assert ideas[2] == ("Virtual Reality Training", "")
    
    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Test parsing an empty file."""
        file_path = tmp_path / "empty.md"
        _ = file_path.write_text("")
        
        ideas = parse_ideas_file(file_path)
        assert ideas == []
    
    def test_parse_file_with_only_whitespace(self, tmp_path: Path) -> None:
        """Test parsing a file with only whitespace."""
        file_path = tmp_path / "whitespace.md"
        _ = file_path.write_text("   \n  \n   ")
        
        ideas = parse_ideas_file(file_path)
        assert ideas == []
    
    def test_parse_single_idea(self, tmp_path: Path) -> None:
        """Test parsing a file with a single idea."""
        content = """# Solo Idea

This is the only idea in the file."""
        file_path = tmp_path / "single.md"
        _ = file_path.write_text(content)
        
        ideas = parse_ideas_file(file_path)
        assert len(ideas) == 1
        assert ideas[0] == ("Solo Idea", "This is the only idea in the file.")
    
    def test_parse_idea_without_description(self, tmp_path: Path) -> None:
        """Test parsing ideas without descriptions."""
        content = """# Idea One

# Idea Two

# Idea Three"""
        file_path = tmp_path / "no_desc.md"
        _ = file_path.write_text(content)
        
        ideas = parse_ideas_file(file_path)
        assert len(ideas) == 3
        assert all(desc == "" for _, desc in ideas)
    
    def test_parse_multiline_descriptions(self, tmp_path: Path) -> None:
        """Test parsing ideas with multi-paragraph descriptions."""
        content = """# Complex Idea

First paragraph of the description.

Second paragraph with more details.

Third paragraph concluding the idea."""
        file_path = tmp_path / "multiline.md"
        _ = file_path.write_text(content)
        
        ideas = parse_ideas_file(file_path)
        assert len(ideas) == 1
        assert "First paragraph" in ideas[0][1]
        assert "Second paragraph" in ideas[0][1]
        assert "Third paragraph" in ideas[0][1]
    
    def test_file_not_found(self) -> None:
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Ideas file not found"):
            _ = parse_ideas_file(Path("/nonexistent/file.md"))
    
    def test_content_before_first_header(self, tmp_path: Path) -> None:
        """Test error when content appears before first header."""
        content = """Some content before header

# First Idea

Description"""
        file_path = tmp_path / "malformed.md"
        _ = file_path.write_text(content)
        
        with pytest.raises(ValueError, match="Malformed ideas file"):
            _ = parse_ideas_file(file_path)
    
    def test_word_limit_exceeded(self, tmp_path: Path) -> None:
        """Test error when description exceeds 300 words."""
        # Generate a description with more than 300 words
        long_description = " ".join(["word"] * 301)
        content = f"""# Long Idea

{long_description}"""
        file_path = tmp_path / "too_long.md"
        _ = file_path.write_text(content)
        
        with pytest.raises(ValueError, match="exceeds 300 words"):
            _ = parse_ideas_file(file_path)
    
    def test_special_characters_in_title(self, tmp_path: Path) -> None:
        """Test parsing ideas with special characters in titles."""
        content = """# AI & ML: The Future!

Description with special chars.

# $100M Business Idea #2

Another description."""
        file_path = tmp_path / "special.md"
        _ = file_path.write_text(content)
        
        ideas = parse_ideas_file(file_path)
        assert len(ideas) == 2
        assert ideas[0][0] == "AI & ML: The Future!"
        assert ideas[1][0] == "$100M Business Idea #2"
    
    def test_consecutive_empty_ideas(self, tmp_path: Path) -> None:
        """Test handling of consecutive headers without content."""
        content = """# First
# Second
# Third
Some content for third."""
        file_path = tmp_path / "consecutive.md"
        _ = file_path.write_text(content)
        
        ideas = parse_ideas_file(file_path)
        assert len(ideas) == 3
        assert ideas[0] == ("First", "")
        assert ideas[1] == ("Second", "")
        assert ideas[2] == ("Third", "Some content for third.")