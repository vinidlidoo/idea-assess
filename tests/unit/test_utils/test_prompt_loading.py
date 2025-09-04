"""Tests for prompt loading and formatting functionality."""

from pathlib import Path
import tempfile
import pytest

from src.utils.file_operations import load_prompt


class TestPromptFormatting:
    """Test prompt template loading and formatting."""

    @pytest.fixture
    def prompts_dir(self):
        """Create a temporary prompts directory with test templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_path = Path(tmpdir)

            # Create directory structure
            analyst_user_dir = prompts_path / "agents" / "analyst" / "user"
            analyst_user_dir.mkdir(parents=True, exist_ok=True)

            # Create test templates
            initial_template = """# Business Analysis Task
Analyze this business idea: "{idea}"

## Output
Write your analysis to: {output_file}"""

            revision_template = """# Business Analysis Revision
Revise your analysis of this business idea: "{idea}"

## Available Feedback
- Previous analysis: {previous_analysis_file}
- Reviewer feedback: {feedback_file}
{fact_check_line}

## Output
Write your revised analysis to: {output_file}"""

            (analyst_user_dir / "initial.md").write_text(initial_template)
            (analyst_user_dir / "revision.md").write_text(revision_template)

            yield prompts_path

    def test_initial_prompt_formatting(self, prompts_dir):
        """Test that initial prompt template formats correctly."""
        template = load_prompt("agents/analyst/user/initial.md", prompts_dir)
        result = template.format(
            idea="AI-powered test idea", output_file="/path/to/output.md"
        )

        assert "AI-powered test idea" in result
        assert "/path/to/output.md" in result
        assert "Business Analysis Task" in result

    def test_revision_prompt_without_fact_check(self, prompts_dir):
        """Test revision prompt formatting without fact-check."""
        template = load_prompt("agents/analyst/user/revision.md", prompts_dir)
        result = template.format(
            idea="AI-powered test idea",
            previous_analysis_file="/path/to/previous.md",
            feedback_file="/path/to/feedback.json",
            fact_check_line="",  # Empty for no fact-check
            output_file="/path/to/output.md",
        )

        assert "AI-powered test idea" in result
        assert "/path/to/previous.md" in result
        assert "/path/to/feedback.json" in result
        assert "fact-check.json" not in result  # Should not mention fact-check
        assert "/path/to/output.md" in result

    def test_revision_prompt_with_fact_check(self, prompts_dir):
        """Test revision prompt formatting with fact-check."""
        template = load_prompt("agents/analyst/user/revision.md", prompts_dir)
        result = template.format(
            idea="AI-powered test idea",
            previous_analysis_file="/path/to/previous.md",
            feedback_file="/path/to/feedback.json",
            fact_check_line="- Fact-check results: /path/to/fact-check.json",
            output_file="/path/to/output.md",
        )

        assert "AI-powered test idea" in result
        assert "/path/to/previous.md" in result
        assert "/path/to/feedback.json" in result
        assert "/path/to/fact-check.json" in result  # Should include fact-check
        assert "/path/to/output.md" in result

    def test_real_prompt_files_exist(self):
        """Test that actual prompt files exist in the project."""
        project_root = Path(__file__).parent.parent.parent.parent
        prompts_dir = project_root / "config" / "prompts"

        # Check that actual prompt files exist
        initial_path = prompts_dir / "agents" / "analyst" / "user" / "initial.md"
        revision_path = prompts_dir / "agents" / "analyst" / "user" / "revision.md"

        assert initial_path.exists(), f"Missing prompt file: {initial_path}"
        assert revision_path.exists(), f"Missing prompt file: {revision_path}"

    def test_real_prompt_formatting(self):
        """Test formatting with actual project prompt files."""
        project_root = Path(__file__).parent.parent.parent.parent
        prompts_dir = project_root / "config" / "prompts"

        # Test initial prompt
        initial_template = load_prompt("agents/analyst/user/initial.md", prompts_dir)
        initial_result = initial_template.format(
            idea="Test business idea", output_file="/tmp/test_output.md"
        )
        assert "Test business idea" in initial_result
        assert "/tmp/test_output.md" in initial_result

        # Test revision prompt with fact-check
        revision_template = load_prompt("agents/analyst/user/revision.md", prompts_dir)
        revision_result = revision_template.format(
            idea="Test business idea",
            previous_analysis_file="/tmp/previous.md",
            feedback_file="/tmp/feedback.json",
            fact_check_line="- Fact-check results: /tmp/fact-check.json",
            output_file="/tmp/revised.md",
        )
        assert "Test business idea" in revision_result
        assert "/tmp/previous.md" in revision_result
        assert "/tmp/feedback.json" in revision_result
        assert "/tmp/fact-check.json" in revision_result
        assert "/tmp/revised.md" in revision_result
