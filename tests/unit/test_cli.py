"""Tests for CLI behavior and configuration."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
from io import StringIO

import pytest

from src.cli import main
from src.core.types import PipelineMode


class TestCLI:
    """Test CLI command parsing and behavior."""

    @pytest.mark.asyncio
    async def test_analyze_command_success(self):
        """Test successful analysis shows success message."""
        test_args = ["cli.py", "AI fitness app"]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.cli.AnalysisPipeline") as MockPipeline,
            patch("src.cli.setup_logging") as mock_logging,
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            # Mock successful pipeline execution
            mock_pipeline = AsyncMock()
            mock_pipeline.process = AsyncMock(
                return_value={
                    "success": True,
                    "analysis_path": "/path/to/analysis.md",
                    "feedback_path": None,
                    "idea_slug": "ai-fitness-app",
                    "iterations": 1,
                    "message": None,
                }
            )
            MockPipeline.return_value = mock_pipeline
            mock_logging.return_value = Path("/path/to/log.json")

            # Run the CLI
            with patch.object(sys, "exit") as mock_exit:
                await main()
                # Should exit with success code
                mock_exit.assert_called_once_with(0)

            # Check output contains success marker
            output = mock_stdout.getvalue()  # pyright: ignore[reportAny]
            assert "✅" in output
            assert "analysis.md" in output.lower()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_no_web_tools_flag_disables_tools(self):
        """Test that --no-web-tools removes web tools from allowed_tools."""
        test_args = ["cli.py", "AI fitness app", "--no-web-tools"]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.cli.AnalysisPipeline") as MockPipeline,
            patch("src.cli.setup_logging"),
            patch("sys.stdout", new_callable=StringIO),
        ):
            mock_pipeline = AsyncMock()
            mock_pipeline.process = AsyncMock(
                return_value={
                    "success": True,
                    "analysis_path": "/path/to/analysis.md",
                    "feedback_path": None,
                    "idea_slug": "ai-fitness-app",
                    "iterations": 1,
                    "message": None,
                }
            )
            MockPipeline.return_value = mock_pipeline

            with patch.object(sys, "exit"):
                await main()

            # Verify pipeline was called with correct config
            MockPipeline.assert_called_once()
            call_kwargs = MockPipeline.call_args.kwargs
            # When no-web-tools is set, only TodoWrite should remain
            assert call_kwargs["analyst_config"].allowed_tools == ["TodoWrite"]  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_review_mode_configuration(self):
        """Test that --with-review flag enables review mode."""
        test_args = [
            "cli.py",
            "AI fitness app",
            "--with-review",
            "--max-iterations",
            "2",
        ]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.cli.AnalysisPipeline") as MockPipeline,
            patch("src.cli.setup_logging"),
            patch("sys.stdout", new_callable=StringIO),
        ):
            mock_pipeline = AsyncMock()
            mock_pipeline.process = AsyncMock(
                return_value={
                    "success": True,
                    "analysis_path": "/path/to/analysis.md",
                    "feedback_path": "/path/to/feedback.json",
                    "idea_slug": "ai-fitness-app",
                    "iterations": 2,
                    "message": None,
                }
            )
            MockPipeline.return_value = mock_pipeline

            with patch.object(sys, "exit"):
                await main()

            # Verify correct mode was set
            MockPipeline.assert_called_once()
            call_kwargs = MockPipeline.call_args.kwargs
            assert call_kwargs["mode"] == PipelineMode.ANALYZE_AND_REVIEW
            assert call_kwargs["reviewer_config"].max_iterations == 2  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_error_display_formatting(self):
        """Test that errors are displayed with ❌ marker."""
        test_args = ["cli.py", "AI fitness app"]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.cli.AnalysisPipeline") as MockPipeline,
            patch("src.cli.setup_logging"),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            # Mock pipeline failure
            mock_pipeline = AsyncMock()
            mock_pipeline.process = AsyncMock(
                return_value={
                    "success": False,
                    "analysis_path": None,
                    "feedback_path": None,
                    "idea_slug": "ai-fitness-app",
                    "iterations": 1,
                    "message": "Failed to analyze idea",
                }
            )
            MockPipeline.return_value = mock_pipeline

            with patch.object(sys, "exit") as mock_exit:
                await main()
                # Should exit with error code
                mock_exit.assert_called_once_with(1)

            # Check output contains error marker
            output = mock_stdout.getvalue()  # pyright: ignore[reportAny]
            assert "❌" in output
            assert "failed" in output.lower()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_invalid_max_iterations_validation(self):
        """Test that invalid max-iterations value is rejected."""
        test_args = [
            "cli.py",
            "AI fitness app",
            "--max-iterations",
            "10",
        ]  # Out of range

        with (
            patch.object(sys, "argv", test_args),
            patch("sys.stderr", new_callable=StringIO) as mock_stderr,
        ):
            # argparse should exit with error code 2 for invalid arguments
            with pytest.raises(SystemExit) as exc_info:
                await main()

            assert exc_info.value.code == 2
            error_output = mock_stderr.getvalue()  # pyright: ignore[reportAny]
            assert (
                "invalid choice" in error_output.lower()
                or "error" in error_output.lower()
            )

    @pytest.mark.asyncio
    async def test_debug_logging_enabled(self):
        """Test that --debug flag enables debug logging."""
        test_args = ["cli.py", "AI fitness app", "--debug"]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.cli.AnalysisPipeline") as MockPipeline,
            patch("src.cli.setup_logging") as mock_logging,
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            # Mock successful pipeline
            mock_pipeline = AsyncMock()
            mock_pipeline.process = AsyncMock(
                return_value={
                    "success": True,
                    "analysis_path": "/path/to/analysis.md",
                    "feedback_path": None,
                    "idea_slug": "ai-fitness-app",
                    "iterations": 1,
                    "message": None,
                }
            )
            MockPipeline.return_value = mock_pipeline
            mock_logging.return_value = Path("/path/to/debug.json")

            with patch.object(sys, "exit"):
                await main()

            # Verify debug logging was enabled
            mock_logging.assert_called_once()
            call_kwargs = mock_logging.call_args.kwargs
            assert call_kwargs["debug"] is True

            # Check that debug message appears in output
            output = mock_stdout.getvalue()  # pyright: ignore[reportAny]
            assert "Debug logging enabled" in output

    @pytest.mark.asyncio
    async def test_prompt_override_configuration(self):
        """Test that prompt override flags modify configuration."""
        test_args = [
            "cli.py",
            "AI fitness app",
            "--analyst-prompt",
            "concise",
            "--reviewer-prompt",
            "strict",
            "--with-review",
        ]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.cli.AnalysisPipeline") as MockPipeline,
            patch("src.cli.setup_logging"),
            patch("sys.stdout", new_callable=StringIO),
        ):
            mock_pipeline = AsyncMock()
            mock_pipeline.process = AsyncMock(
                return_value={
                    "success": True,
                    "analysis_path": "/path/to/analysis.md",
                    "feedback_path": None,
                    "idea_slug": "ai-fitness-app",
                    "iterations": 1,
                    "message": None,
                }
            )
            MockPipeline.return_value = mock_pipeline

            with patch.object(sys, "exit"):
                await main()

            # Verify prompts were overridden
            MockPipeline.assert_called_once()
            call_kwargs = MockPipeline.call_args.kwargs
            assert call_kwargs["analyst_config"].system_prompt == "concise"  # pyright: ignore[reportAny]
            assert call_kwargs["reviewer_config"].system_prompt == "strict"  # pyright: ignore[reportAny]
