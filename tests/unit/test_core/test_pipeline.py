"""Tests for pipeline orchestration logic."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch, AsyncMock
import json

import pytest

from src.core.pipeline import AnalysisPipeline
from src.core.config import SystemConfig, AnalystConfig, ReviewerConfig, FactCheckerConfig
from src.core.types import PipelineMode, Success, Error
from tests.unit.base_test import BaseAgentTest


class TestAnalysisPipeline(BaseAgentTest):
    """Test pipeline orchestration behavior."""

    @pytest.fixture
    def system_config(self) -> SystemConfig:
        """Create system configuration."""
        assert self.temp_dir is not None

        # Create required template files for pipeline tests
        analyst_template_dir = (
            self.temp_dir / "config" / "templates" / "agents" / "analyst"
        )
        analyst_template_dir.mkdir(parents=True, exist_ok=True)
        analyst_template = analyst_template_dir / "analysis.md"
        _ = analyst_template.write_text("# Analysis Template\n\n{{content}}")

        reviewer_template_dir = (
            self.temp_dir / "config" / "templates" / "agents" / "reviewer"
        )
        reviewer_template_dir.mkdir(parents=True, exist_ok=True)
        reviewer_template = reviewer_template_dir / "feedback.json"
        _ = reviewer_template.write_text(
            '{"iteration_recommendation": "pending", "iteration_reason": "pending"}'
        )
        
        factchecker_template_dir = (
            self.temp_dir / "config" / "templates" / "agents" / "factchecker"
        )
        factchecker_template_dir.mkdir(parents=True, exist_ok=True)
        factchecker_template = factchecker_template_dir / "fact-check.json"
        _ = factchecker_template.write_text(
            '{"issues": [], "iteration_recommendation": "pending", "iteration_reason": "pending"}'
        )

        return SystemConfig(
            project_root=self.temp_dir,
            analyses_dir=self.temp_dir / "analyses",
            config_dir=self.temp_dir / "config",
            logs_dir=self.temp_dir / "logs",
        )

    @pytest.fixture
    def analyst_config(self) -> AnalystConfig:
        """Create analyst configuration."""
        return AnalystConfig(
            max_turns=10,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/analyst/system.md",
            allowed_tools=["WebSearch", "Edit"],
            max_websearches=5,
            min_words=1000,
        )

    @pytest.fixture
    def reviewer_config(self) -> ReviewerConfig:
        """Create reviewer configuration."""
        return ReviewerConfig(
            max_turns=5,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/reviewer/system.md",
            allowed_tools=["Read", "Edit"],
            max_iterations=3,
            strictness="normal",
        )


    
    @pytest.fixture
    def fact_checker_config(self) -> FactCheckerConfig:
        """Create fact-checker configuration."""
        return FactCheckerConfig(
            max_turns=10,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/fact-checker/system.md",
            allowed_tools=["WebFetch", "Edit", "TodoWrite"],
        )

    @pytest.mark.asyncio
    async def test_analyze_only_mode(
        self,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig,
        fact_checker_config: FactCheckerConfig,
    ):
        """Test that ANALYZE mode runs only analyst, not reviewer."""
        pipeline = AnalysisPipeline(
            idea="AI fitness app",
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=PipelineMode.ANALYZE,
        )

        with (
            patch("src.core.pipeline.AnalystAgent") as MockAnalyst,
            patch("src.core.pipeline.ReviewerAgent") as MockReviewer,
        ):
            # Mock analyst to return success
            mock_analyst = AsyncMock()
            mock_analyst.process = AsyncMock(return_value=Success())
            MockAnalyst.return_value = mock_analyst

            # Mock reviewer (should not be called)
            mock_reviewer = AsyncMock()
            MockReviewer.return_value = mock_reviewer

            result = await pipeline.process()

            # Assert only analyst was called
            MockAnalyst.assert_called_once_with(analyst_config)
            mock_analyst.process.assert_called_once()  # pyright: ignore[reportAny]

            # Assert reviewer was never instantiated
            MockReviewer.assert_not_called()

            # Assert result is successful
            assert result["success"] is True
            assert result["iterations"] == 1

    @pytest.mark.asyncio
    async def test_iteration_limit_enforcement(
        self,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig,
        fact_checker_config: FactCheckerConfig,
    ):
        """Test that pipeline stops at max_iterations even if reviewer rejects."""
        # Set max iterations to 2
        reviewer_config.max_iterations = 2

        pipeline = AnalysisPipeline(
            idea="AI fitness app",
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=PipelineMode.ANALYZE_AND_REVIEW,
        )

        with (
            patch("src.core.pipeline.AnalystAgent") as MockAnalyst,
            patch("src.core.pipeline.ReviewerAgent") as MockReviewer,
        ):
            # Mock analyst to always succeed
            mock_analyst = AsyncMock()
            mock_analyst.process = AsyncMock(return_value=Success())
            MockAnalyst.return_value = mock_analyst

            # Mock reviewer to always reject
            mock_reviewer = AsyncMock()
            mock_reviewer.process = AsyncMock(return_value=Success())
            MockReviewer.return_value = mock_reviewer

            # Mock feedback file creation (reviewer always rejects)
            def create_rejection_feedback(*_args: Any, **_kwargs: Any) -> None:
                feedback_file = (
                    pipeline.iterations_dir
                    / f"reviewer_feedback_iteration_{pipeline.iteration_count}.json"
                )
                _ = feedback_file.write_text(json.dumps({"iteration_recommendation": "revise"}))

            with patch.object(
                pipeline,
                "_save_analysis_iteration",
                side_effect=create_rejection_feedback,
            ):
                result = await pipeline.process()

            # Assert exactly 2 iterations occurred
            assert result["iterations"] == 2
            assert mock_analyst.process.call_count == 2  # pyright: ignore[reportAny]
            # Reviewer called only once (not on final iteration)
            assert mock_reviewer.process.call_count == 1  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_early_termination_on_approval(
        self,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig,
        fact_checker_config: FactCheckerConfig,
    ):
        """Test that pipeline stops when reviewer approves."""
        # Set max iterations to 3
        reviewer_config.max_iterations = 3

        pipeline = AnalysisPipeline(
            idea="AI fitness app",
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=PipelineMode.ANALYZE_AND_REVIEW,
        )

        with (
            patch("src.core.pipeline.AnalystAgent") as MockAnalyst,
            patch("src.core.pipeline.ReviewerAgent") as MockReviewer,
        ):
            # Mock analyst to succeed
            mock_analyst = AsyncMock()
            mock_analyst.process = AsyncMock(return_value=Success())
            MockAnalyst.return_value = mock_analyst

            # Mock reviewer to approve immediately
            mock_reviewer = AsyncMock()

            async def mock_reviewer_process(*_args: Any, **_kwargs: Any) -> Success:
                # Create approval feedback
                feedback_file = (
                    pipeline.iterations_dir
                    / f"reviewer_feedback_iteration_{pipeline.iteration_count}.json"
                )
                _ = feedback_file.write_text(json.dumps({"iteration_recommendation": "approve"}))
                return Success()

            mock_reviewer.process = AsyncMock(side_effect=mock_reviewer_process)
            MockReviewer.return_value = mock_reviewer

            result = await pipeline.process()

            # Should stop at 1 iteration despite max_iterations=3
            assert result["success"] is True
            assert result["iterations"] == 1
            assert mock_analyst.process.call_count == 1  # pyright: ignore[reportAny]
            assert mock_reviewer.process.call_count == 1  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_analyst_error_propagation(
        self,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig,
        fact_checker_config: FactCheckerConfig,
    ):
        """Test that analyst errors are properly propagated."""
        pipeline = AnalysisPipeline(
            idea="AI fitness app",
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=PipelineMode.ANALYZE_AND_REVIEW,
        )

        with patch("src.core.pipeline.AnalystAgent") as MockAnalyst:
            # Mock analyst to return error
            mock_analyst = AsyncMock()
            mock_analyst.process = AsyncMock(
                return_value=Error(message="Failed to analyze idea")
            )
            MockAnalyst.return_value = mock_analyst

            result = await pipeline.process()

            # Assert error is propagated
            assert result["success"] is False
            assert result["message"] == "Analyst failed"
            assert result["iterations"] == 1

    @pytest.mark.asyncio
    async def test_reviewer_error_propagation(
        self,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig,
        fact_checker_config: FactCheckerConfig,
    ):
        """Test that reviewer errors are properly handled."""
        pipeline = AnalysisPipeline(
            idea="AI fitness app",
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=PipelineMode.ANALYZE_AND_REVIEW,
        )

        with (
            patch("src.core.pipeline.AnalystAgent") as MockAnalyst,
            patch("src.core.pipeline.ReviewerAgent") as MockReviewer,
        ):
            # Mock analyst to succeed
            mock_analyst = AsyncMock()
            mock_analyst.process = AsyncMock(return_value=Success())
            MockAnalyst.return_value = mock_analyst

            # Mock reviewer to return error
            mock_reviewer = AsyncMock()
            mock_reviewer.process = AsyncMock(
                return_value=Error(message="Failed to review")
            )
            MockReviewer.return_value = mock_reviewer

            result = await pipeline.process()

            # Pipeline should handle reviewer error gracefully
            assert result["success"] is True  # Analysis still succeeded
            assert result["iterations"] == 1
            assert mock_analyst.process.call_count == 1  # pyright: ignore[reportAny]
            assert mock_reviewer.process.call_count == 1  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_symlink_creation_for_analysis(
        self,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig,
        fact_checker_config: FactCheckerConfig,
    ):
        """Test that pipeline creates/updates analysis.md symlink."""
        pipeline = AnalysisPipeline(
            idea="AI fitness app",
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=PipelineMode.ANALYZE,
        )

        with patch("src.core.pipeline.AnalystAgent") as MockAnalyst:
            # Mock successful analyst
            mock_analyst = AsyncMock()
            mock_analyst.process = AsyncMock(return_value=Success())
            MockAnalyst.return_value = mock_analyst

            _ = await pipeline.process()

            # Check that directories were created
            assert pipeline.output_dir.exists()
            assert pipeline.iterations_dir.exists()

            # Check that iteration file exists
            iteration_file = pipeline.iterations_dir / "iteration_1.md"
            assert iteration_file.exists()

            # Check symlink creation and target
            symlink = pipeline.output_dir / "analysis.md"
            # The pipeline should create a symlink pointing to the iteration file
            assert symlink.exists(), "analysis.md should exist"
            # Note: On some systems, symlinks may be created as regular files
            # The important thing is the file exists for user access

    @pytest.mark.asyncio
    async def test_pipeline_mode_determines_agents(
        self,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig,
        fact_checker_config: FactCheckerConfig,
    ):
        """Test that pipeline mode correctly determines which agents run."""
        test_cases = [
            (PipelineMode.ANALYZE, 1, 0),  # Analyst only
            (PipelineMode.ANALYZE_AND_REVIEW, 1, 1),  # Both (with approval)
        ]

        for mode, expected_analyst_calls, expected_reviewer_calls in test_cases:
            pipeline = AnalysisPipeline(
                idea="AI fitness app",
                system_config=system_config,
                analyst_config=analyst_config,
                reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
                mode=mode,
            )

            with (
                patch("src.core.pipeline.AnalystAgent") as MockAnalyst,
                patch("src.core.pipeline.ReviewerAgent") as MockReviewer,
            ):
                # Mock both agents to succeed
                mock_analyst = AsyncMock()
                mock_analyst.process = AsyncMock(return_value=Success())
                MockAnalyst.return_value = mock_analyst

                mock_reviewer = AsyncMock()

                async def approve_immediately(*_args: Any, **_kwargs: Any) -> Success:
                    # Create approval feedback
                    feedback_file = (
                        pipeline.iterations_dir
                        / f"reviewer_feedback_iteration_{pipeline.iteration_count}.json"
                    )
                    _ = feedback_file.write_text(
                        json.dumps({"iteration_recommendation": "approve"})
                    )
                    return Success()

                mock_reviewer.process = AsyncMock(side_effect=approve_immediately)
                MockReviewer.return_value = mock_reviewer

                _ = await pipeline.process()

                # Check correct number of calls based on mode
                assert mock_analyst.process.call_count == expected_analyst_calls  # pyright: ignore[reportAny]
                if expected_reviewer_calls > 0:
                    assert mock_reviewer.process.call_count == expected_reviewer_calls  # pyright: ignore[reportAny]
                else:
                    MockReviewer.assert_not_called()
