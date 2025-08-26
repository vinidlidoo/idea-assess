"""Tests for result formatter utility."""

from unittest.mock import patch


from src.core.types import PipelineResult
from src.utils.result_formatter import format_pipeline_result


class TestFormatPipelineResult:
    """Test the format_pipeline_result function."""

    def test_format_success_simple_mode(self):
        """Test formatting successful result in simple mode."""
        result: PipelineResult = {
            "success": True,
            "idea_slug": "ai-fitness-app",
            "analysis_path": "/path/to/analysis.md",
            "feedback_path": None,
            "iterations": 1,
            "message": None,
        }

        with patch("builtins.print") as mock_print:
            format_pipeline_result(result, with_review=False)

            # Check that success message was printed
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "✅" in call_args
            assert "analysis.md" in call_args.lower()

    def test_format_success_review_mode(self):
        """Test formatting successful result in review mode."""
        result: PipelineResult = {
            "success": True,
            "idea_slug": "ai-fitness-app",
            "analysis_path": "/path/to/analysis.md",
            "feedback_path": "/path/to/feedback.json",
            "iterations": 3,
            "message": None,
        }

        with patch("builtins.print") as mock_print:
            format_pipeline_result(result, with_review=True)

            # Should show iteration count and both files
            calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(calls)
            assert "✅" in output
            assert "3 iteration(s)" in output
            assert "analysis.md" in output.lower()
            assert "feedback.json" in output.lower()

    def test_format_failure_with_message(self):
        """Test formatting failed result with error message."""
        result: PipelineResult = {
            "success": False,
            "idea_slug": "ai-fitness-app",
            "analysis_path": None,
            "feedback_path": None,
            "iterations": 0,
            "message": "Failed to connect to API",
        }

        with patch("builtins.print") as mock_print:
            format_pipeline_result(result, with_review=False)

            # Should show error message
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "❌" in call_args
            assert "Failed to connect to API" in call_args

    def test_format_with_missing_files(self):
        """Test handling of None file paths."""
        result: PipelineResult = {
            "success": True,
            "idea_slug": "test-idea",
            "analysis_path": None,  # Missing file
            "feedback_path": None,
            "iterations": 1,
            "message": None,
        }

        with patch("builtins.print") as mock_print:
            format_pipeline_result(result, with_review=False)

            # Should handle missing file gracefully
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "✅" in call_args
            assert "completed" in call_args.lower()

    def test_format_review_mode_single_iteration(self):
        """Test review mode with only 1 iteration."""
        result: PipelineResult = {
            "success": True,
            "idea_slug": "test-idea",
            "analysis_path": "/path/to/analysis.md",
            "feedback_path": "/path/to/feedback.json",
            "iterations": 1,
            "message": None,
        }

        with patch("builtins.print") as mock_print:
            format_pipeline_result(result, with_review=True)

            # Should still show iteration count even if 1
            calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(calls)
            assert "1 iteration(s)" in output
            assert "✅" in output
