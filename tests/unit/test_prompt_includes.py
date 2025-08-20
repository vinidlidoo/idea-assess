"""Test the prompt include mechanism."""

import pytest
from pathlib import Path
from unittest.mock import patch

from src.utils.file_operations import load_prompt_with_includes


class TestPromptIncludes:
    """Test suite for the prompt include mechanism."""

    def test_simple_include(self):
        """Test that a simple include is processed correctly."""
        # Mock file contents
        main_content = (
            "# Main Prompt\n\n{{include:shared/rules.md}}\n\n## Rest of prompt"
        )
        included_content = "## Shared Rules\n\nThese are shared rules."

        # Mock the load_prompt function to return our test content
        def mock_load_prompt(path, prompts_dir):
            if "shared/rules.md" in path:
                return included_content
            return main_content

        with patch(
            "src.utils.file_operations.load_prompt", side_effect=mock_load_prompt
        ):
            result = load_prompt_with_includes("test.md", Path("prompts"))

        # Check that include was replaced
        assert "{{include:" not in result
        assert "## Shared Rules" in result
        assert "These are shared rules." in result
        assert "# Main Prompt" in result
        assert "## Rest of prompt" in result

    def test_multiple_includes(self):
        """Test that multiple includes are processed correctly."""
        main_content = """# Main Prompt
{{include:shared/rules.md}}
Some text
{{include:shared/format.md}}
End of prompt"""
        rules_content = "## Rules\nRule content"
        format_content = "## Format\nFormat content"

        def mock_load_prompt(path, prompts_dir):
            if "shared/rules.md" in path:
                return rules_content
            elif "shared/format.md" in path:
                return format_content
            return main_content

        with patch(
            "src.utils.file_operations.load_prompt", side_effect=mock_load_prompt
        ):
            result = load_prompt_with_includes("test.md", Path("prompts"))

        # Check that both includes were replaced
        assert "{{include:" not in result
        assert "## Rules" in result
        assert "Rule content" in result
        assert "## Format" in result
        assert "Format content" in result
        assert "Some text" in result
        assert "End of prompt" in result

    def test_include_with_whitespace(self):
        """Test that includes with whitespace are handled correctly."""
        main_content = "# Main\n{{include: shared/rules.md }}\n## End"
        included_content = "Included content"

        def mock_load_prompt(path, prompts_dir):
            if "shared/rules.md" in path:
                return included_content
            return main_content

        with patch(
            "src.utils.file_operations.load_prompt", side_effect=mock_load_prompt
        ):
            result = load_prompt_with_includes("test.md", Path("prompts"))

        assert "{{include:" not in result
        assert "Included content" in result

    def test_missing_include_raises_error(self):
        """Test that a missing include file raises an appropriate error."""
        main_content = "# Main\n{{include:shared/missing.md}}\n## End"

        def mock_load_prompt(path, prompts_dir):
            if "missing.md" in path:
                raise FileNotFoundError(f"Prompt file not found: {path}")
            return main_content

        with patch(
            "src.utils.file_operations.load_prompt", side_effect=mock_load_prompt
        ):
            with pytest.raises(FileNotFoundError) as exc_info:
                load_prompt_with_includes("test.md", Path("prompts"))

            assert "missing.md" in str(exc_info.value)
            assert "referenced from test.md" in str(exc_info.value)

    def test_no_includes_returns_unchanged(self):
        """Test that prompts without includes are returned unchanged."""
        content = "# Regular Prompt\n\nNo includes here.\n\n## Section"

        with patch("src.utils.file_operations.load_prompt", return_value=content):
            result = load_prompt_with_includes("test.md", Path("prompts"))

        assert result == content

    def test_real_file_include(self):
        """Test with actual files from the project."""
        # This test uses the real files we created
        prompts_dir = Path("config/prompts")

        # Test that analyst system prompt includes the shared rules
        result = load_prompt_with_includes("agents/analyst/system.md", prompts_dir)

        # Check that the include was processed
        assert "{{include:" not in result
        assert "CRITICAL TOOL USAGE RULES" in result  # From shared file
        assert "Analyst Agent System Prompt" in result  # From main file
        assert "READ A FILE BEFORE EDITING IT" in result  # From shared file
