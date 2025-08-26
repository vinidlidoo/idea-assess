"""Tests for file operations utilities."""

import pytest

from src.utils.file_operations import (
    load_prompt,
    load_prompt_with_includes,
    load_template,
    create_file_from_template,
    append_metadata_to_analysis,
)


class TestLoadPrompt:
    """Test the load_prompt function."""

    def test_load_prompt_basic(self, tmp_path):
        """Test loading an existing prompt file."""
        # Create a test prompt file
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test.md"
        prompt_content = "# Test Prompt\n\nThis is a test."
        prompt_file.write_text(prompt_content)

        result = load_prompt("test.md", prompts_dir)
        assert result == prompt_content

    def test_load_prompt_not_found(self, tmp_path):
        """Test FileNotFoundError when prompt doesn't exist."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            load_prompt("nonexistent.md", prompts_dir)

    def test_load_prompt_caching(self, tmp_path):
        """Test that second load uses cache."""
        # Clear cache first
        load_prompt.cache_clear()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "cached.md"
        prompt_file.write_text("Original content")

        # First load
        result1 = load_prompt("cached.md", prompts_dir)
        assert result1 == "Original content"

        # Modify file (should not affect cached result)
        prompt_file.write_text("Modified content")

        # Second load should return cached value
        result2 = load_prompt("cached.md", prompts_dir)
        assert result2 == "Original content"  # Still original due to cache

        # Clear cache and load again
        load_prompt.cache_clear()
        result3 = load_prompt("cached.md", prompts_dir)
        assert result3 == "Modified content"  # Now gets updated content

    def test_load_prompt_with_path_separator(self, tmp_path):
        """Test loading prompt with directory separator in path."""
        prompts_dir = tmp_path / "prompts"
        agents_dir = prompts_dir / "agents"
        agents_dir.mkdir(parents=True)

        prompt_file = agents_dir / "analyst.md"
        prompt_content = "Analyst prompt"
        prompt_file.write_text(prompt_content)

        result = load_prompt("agents/analyst.md", prompts_dir)
        assert result == prompt_content


class TestLoadPromptWithIncludes:
    """Test the load_prompt_with_includes function."""

    def test_load_prompt_with_includes_basic(self, tmp_path):
        """Test processing {{include:}} tags."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create included file
        include_file = prompts_dir / "shared.md"
        include_file.write_text("## Shared Content\nThis is shared.")

        # Create main file with include
        main_file = prompts_dir / "main.md"
        main_file.write_text("# Main\n{{include:shared.md}}\n## End")

        result = load_prompt_with_includes("main.md", prompts_dir)
        expected = "# Main\n## Shared Content\nThis is shared.\n## End"
        assert result == expected

    def test_load_prompt_with_includes_nested(self, tmp_path):
        """Test multiple includes in one file."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create included files
        header = prompts_dir / "header.md"
        header.write_text("# Header")

        footer = prompts_dir / "footer.md"
        footer.write_text("# Footer")

        # Main file with multiple includes
        main = prompts_dir / "main.md"
        main.write_text("{{include:header.md}}\n# Body\n{{include:footer.md}}")

        result = load_prompt_with_includes("main.md", prompts_dir)
        assert result == "# Header\n# Body\n# Footer"

    def test_load_prompt_with_includes_missing(self, tmp_path):
        """Test error when included file doesn't exist."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        main = prompts_dir / "main.md"
        main.write_text("{{include:missing.md}}")

        with pytest.raises(
            FileNotFoundError, match="Include file not found: missing.md"
        ):
            load_prompt_with_includes("main.md", prompts_dir)

    def test_load_prompt_with_includes_no_includes(self, tmp_path):
        """Test file without any includes."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        simple = prompts_dir / "simple.md"
        content = "Just plain content"
        simple.write_text(content)

        result = load_prompt_with_includes("simple.md", prompts_dir)
        assert result == content


class TestTemplateOperations:
    """Test template loading and file creation."""

    def test_load_template(self, tmp_path):
        """Test template loading and caching."""
        # Clear cache first
        load_template.cache_clear()

        template_path = tmp_path / "template.md"
        template_content = "# TODO: Title\n\nTODO: Content"
        template_path.write_text(template_content)

        result = load_template(template_path)
        assert result == template_content

        # Modify file and load again (should be cached)
        template_path.write_text("Modified")
        result2 = load_template(template_path)
        assert result2 == template_content  # Still cached

        # Clear cache
        load_template.cache_clear()
        result3 = load_template(template_path)
        assert result3 == "Modified"

    def test_create_file_from_template(self, tmp_path):
        """Test file creation from template."""
        template_path = tmp_path / "template.md"
        template_content = "# Analysis Template\n\nTODO: Write analysis"
        template_path.write_text(template_content)

        output_path = tmp_path / "output.md"
        create_file_from_template(template_path, output_path)

        assert output_path.exists()
        assert output_path.read_text() == template_content

    def test_append_metadata_to_analysis(self, tmp_path):
        """Test metadata appending to analysis file."""
        analysis_file = tmp_path / "analysis.md"
        analysis_file.write_text("# Analysis\nContent here")

        append_metadata_to_analysis(
            analysis_file=analysis_file,
            idea="AI fitness app",
            slug="ai-fitness-app",
            iteration=2,
            websearch_count=5,
        )

        content = analysis_file.read_text()
        assert "# Analysis\nContent here" in content
        assert "<!-- Analysis Metadata" in content
        assert 'Idea Input: "AI fitness app"' in content
        assert "Idea Slug: ai-fitness-app" in content
        assert "Iteration: 2" in content
        assert "Websearches Used: 5" in content
        assert "Timestamp:" in content

    def test_append_metadata_formatting(self, tmp_path):
        """Test that metadata is properly formatted."""
        analysis_file = tmp_path / "test.md"
        analysis_file.write_text("Content")

        append_metadata_to_analysis(
            analysis_file=analysis_file,
            idea="Test idea",
            slug="test-idea",
            iteration=1,
            websearch_count=0,
        )

        content = analysis_file.read_text()
        lines = content.split("\n")

        # Check formatting
        assert lines[0] == "Content"  # Original content preserved
        # The function appends with a newline, so separator comes next
        assert lines[1] == "---"  # Separator comes after newline
        assert "<!-- Analysis Metadata - Auto-generated, Do Not Edit -->" in content
        assert "-->" in content  # Proper comment closure
