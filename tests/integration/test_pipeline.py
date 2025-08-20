"""Integration tests for the analysis pipeline."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.core.pipeline import AnalysisPipeline
from src.core.config import AnalysisConfig, PipelineConfig
from src.core.types import PipelineMode
from src.core.agent_base import AgentResult


class TestPipelineIntegration:
    """Test the full analysis pipeline flow."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a test configuration."""
        config = Mock(spec=AnalysisConfig)
        config.prompts_dir = Path("config/prompts")
        config.analyses_dir = tmp_path / "analyses"
        config.logs_dir = tmp_path / "logs"

        # Add pipeline config
        config.pipeline = PipelineConfig()
        config.default_pipeline_mode = PipelineMode.ANALYZE_AND_REVIEW

        # Add agent configs
        config.analyst = Mock()
        config.analyst.prompts_dir = config.prompts_dir
        config.reviewer = Mock()
        config.reviewer.prompts_dir = config.prompts_dir

        # Create directories
        config.analyses_dir.mkdir(parents=True, exist_ok=True)
        config.logs_dir.mkdir(parents=True, exist_ok=True)

        return config

    @pytest.fixture
    def pipeline(self, config):
        """Create a pipeline instance."""
        return AnalysisPipeline(config)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_basic_pipeline_flow(self, pipeline, config, tmp_path):
        """Test basic pipeline execution with mocked agents."""
        # Create analysis file
        analysis_file = (
            tmp_path
            / "analyses"
            / "test-business-idea"
            / "iterations"
            / "iteration_1.md"
        )
        analysis_file.parent.mkdir(parents=True, exist_ok=True)
        analysis_file.write_text("# Test Analysis\n\nThis is a test analysis.")

        # Mock the analyst agent
        mock_analyst = AsyncMock()
        mock_analyst.process = AsyncMock(
            return_value=AgentResult(
                success=True,
                content=str(analysis_file),
                metadata={"duration": 1.0},
            )
        )

        # Create feedback file that reviewer will return (accept)
        feedback_file = (
            tmp_path
            / "analyses"
            / "test-business-idea"
            / "iterations"
            / "reviewer_feedback_iteration_1.json"
        )
        feedback_file.write_text(
            json.dumps(
                {
                    "iteration_recommendation": "accept",
                    "overall_assessment": "Analysis meets requirements",
                    "critical_issues": [],
                    "improvements": [],
                    "minor_suggestions": [],
                    "strengths": ["Good structure"],
                    "metadata": {},
                }
            )
        )

        # Mock the reviewer agent
        mock_reviewer = AsyncMock()
        mock_reviewer.process = AsyncMock(
            return_value=AgentResult(
                success=True,
                content=str(feedback_file),
                metadata={"duration": 0.5},
            )
        )

        # Run the pipeline with mocked agents
        with (
            patch("src.core.pipeline.AnalystAgent", return_value=mock_analyst),
            patch("src.core.pipeline.ReviewerAgent", return_value=mock_reviewer),
        ):
            result = await pipeline.process(
                idea="Test business idea",
                mode=PipelineMode.ANALYZE_AND_REVIEW,
                max_iterations_override=2,  # Changed to 2 so reviewer is called
            )

        # Verify result structure
        assert result["success"] is True
        assert "analysis_file" in result
        assert "iterations_completed" in result
        assert result["iterations_completed"] == 1  # Still stops at 1 because accepted

        # Verify agents were called
        mock_analyst.process.assert_called_once()
        mock_reviewer.process.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_analyze_only(self, pipeline, config, tmp_path):
        """Test pipeline in analyze-only mode."""
        # Create analysis file
        analysis_file = (
            tmp_path / "analyses" / "test-idea" / "iterations" / "iteration_1.md"
        )
        analysis_file.parent.mkdir(parents=True, exist_ok=True)
        analysis_file.write_text("# Test Analysis\n\nContent here.")

        # Mock the analyst agent
        mock_analyst = AsyncMock()
        mock_analyst.process = AsyncMock(
            return_value=AgentResult(
                success=True,
                content=str(analysis_file),
                metadata={"duration": 1.0},
            )
        )

        # Run the pipeline in analyze-only mode
        with patch("src.core.pipeline.AnalystAgent", return_value=mock_analyst):
            result = await pipeline.process(idea="Test idea", mode=PipelineMode.ANALYZE)

        # Verify result
        assert result["success"] is True
        assert result["iterations_completed"] == 1
        assert "analysis_file" in result

        # Verify only analyst was called
        mock_analyst.process.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_with_reviewer_rejection(self, pipeline, config, tmp_path):
        """Test pipeline when reviewer rejects and requests revision."""
        # Create analysis files
        analysis1 = (
            tmp_path / "analyses" / "test-idea" / "iterations" / "iteration_1.md"
        )
        analysis1.parent.mkdir(parents=True, exist_ok=True)
        analysis1.write_text("# Initial Analysis\n\nShort and incomplete.")

        analysis2 = (
            tmp_path / "analyses" / "test-idea" / "iterations" / "iteration_2.md"
        )
        analysis2.write_text(
            "# Improved Analysis\n\nMuch more detailed and complete analysis."
        )

        # Mock analyst with improving responses
        mock_analyst = AsyncMock()
        mock_analyst.process = AsyncMock(
            side_effect=[
                AgentResult(
                    success=True,
                    content=str(analysis1),
                    metadata={"duration": 1.0},
                ),
                AgentResult(
                    success=True,
                    content=str(analysis2),
                    metadata={"duration": 1.5},
                ),
            ]
        )

        # Create feedback files
        feedback1 = (
            tmp_path
            / "analyses"
            / "test-idea"
            / "iterations"
            / "reviewer_feedback_iteration_1.json"
        )
        feedback1.write_text(
            json.dumps(
                {
                    "iteration_recommendation": "reject",
                    "overall_assessment": "Analysis is too short",
                    "critical_issues": [
                        {
                            "section": "general",
                            "issue": "Too short",
                            "suggestion": "Add detail",
                            "priority": "critical",
                        }
                    ],
                    "improvements": [],
                    "minor_suggestions": [],
                    "strengths": ["Good start"],
                    "metadata": {},
                }
            )
        )

        feedback2 = (
            tmp_path
            / "analyses"
            / "test-idea"
            / "iterations"
            / "reviewer_feedback_iteration_2.json"
        )
        feedback2.write_text(
            json.dumps(
                {
                    "iteration_recommendation": "accept",
                    "overall_assessment": "Analysis is now comprehensive",
                    "critical_issues": [],
                    "improvements": [],
                    "minor_suggestions": [],
                    "strengths": ["Much improved", "Good detail"],
                    "metadata": {},
                }
            )
        )

        # Mock reviewer that rejects first, accepts second
        mock_reviewer = AsyncMock()
        mock_reviewer.process = AsyncMock(
            side_effect=[
                AgentResult(
                    success=True, content=str(feedback1), metadata={"duration": 0.5}
                ),
                AgentResult(
                    success=True, content=str(feedback2), metadata={"duration": 0.5}
                ),
            ]
        )

        # Run the pipeline
        with (
            patch("src.core.pipeline.AnalystAgent", return_value=mock_analyst),
            patch("src.core.pipeline.ReviewerAgent", return_value=mock_reviewer),
        ):
            result = await pipeline.process(
                idea="Test idea",
                mode=PipelineMode.ANALYZE_AND_REVIEW,
                max_iterations_override=3,
            )

        # Verify iterations
        assert result["success"] is True
        assert result["iterations_completed"] == 2
        assert result["final_status"] == "completed"

        # Verify agents were called correct number of times
        assert mock_analyst.process.call_count == 2
        assert mock_reviewer.process.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_max_iterations(self, pipeline, config, tmp_path):
        """Test pipeline stops at max iterations."""
        # Create analysis file
        analysis_file = (
            tmp_path / "analyses" / "test-idea" / "iterations" / "iteration_1.md"
        )
        analysis_file.parent.mkdir(parents=True, exist_ok=True)
        analysis_file.write_text("# Analysis\n\nSome content.")

        # Mock analyst
        mock_analyst = AsyncMock()
        mock_analyst.process = AsyncMock(
            return_value=AgentResult(
                success=True,
                content=str(analysis_file),
                metadata={"duration": 1.0},
            )
        )

        # Create feedback that always rejects
        reject_feedback = (
            tmp_path
            / "analyses"
            / "test-idea"
            / "iterations"
            / "reviewer_feedback.json"
        )
        reject_feedback.parent.mkdir(parents=True, exist_ok=True)
        reject_feedback.write_text(
            json.dumps(
                {
                    "iteration_recommendation": "reject",
                    "overall_assessment": "Still not meeting quality standards",
                    "critical_issues": [
                        {
                            "section": "general",
                            "issue": "Not good enough",
                            "suggestion": "Try harder",
                            "priority": "critical",
                        }
                    ],
                    "improvements": [],
                    "minor_suggestions": [],
                    "strengths": [],
                    "metadata": {},
                }
            )
        )

        # Mock reviewer that always rejects
        mock_reviewer = AsyncMock()
        mock_reviewer.process = AsyncMock(
            return_value=AgentResult(
                success=True,
                content=str(reject_feedback),
                metadata={"duration": 0.5},
            )
        )

        # Run the pipeline with max 2 iterations
        with (
            patch("src.core.pipeline.AnalystAgent", return_value=mock_analyst),
            patch("src.core.pipeline.ReviewerAgent", return_value=mock_reviewer),
        ):
            result = await pipeline.process(
                idea="Test idea",
                mode=PipelineMode.ANALYZE_AND_REVIEW,
                max_iterations_override=2,
            )

        # Verify it stopped at max iterations
        assert result["success"] is True
        assert result["iterations_completed"] == 2
        assert result["final_status"] == "max_iterations_reached"
        assert mock_analyst.process.call_count == 2
        # Reviewer is called one less time (not on last iteration)
        assert mock_reviewer.process.call_count == 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_error_handling(self, pipeline, config, tmp_path):
        """Test pipeline handles agent errors gracefully."""
        # Mock analyst that fails
        mock_analyst = AsyncMock()
        mock_analyst.process = AsyncMock(
            return_value=AgentResult(
                success=False,
                content="",
                error="API rate limit exceeded",
                metadata={"duration": 0.1},
            )
        )

        # Run the pipeline and expect failure in result
        with patch("src.core.pipeline.AnalystAgent", return_value=mock_analyst):
            result = await pipeline.process(idea="Test idea", mode=PipelineMode.ANALYZE)

        # Verify failure is captured in result
        assert result["success"] is False
        assert "error" in result
        assert "API rate limit exceeded" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_modes(self, pipeline, config):
        """Test that different pipeline modes are recognized."""
        # Verify all modes are available
        assert PipelineMode.ANALYZE
        assert PipelineMode.ANALYZE_AND_REVIEW
        assert PipelineMode.ANALYZE_REVIEW_AND_JUDGE
        assert PipelineMode.FULL_EVALUATION

        # Verify config has proper defaults
        assert config.default_pipeline_mode == PipelineMode.ANALYZE_AND_REVIEW
        assert config.pipeline.max_iterations_by_mode[PipelineMode.ANALYZE] == 1
        assert (
            config.pipeline.max_iterations_by_mode[PipelineMode.ANALYZE_AND_REVIEW] == 3
        )
