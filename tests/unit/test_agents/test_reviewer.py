"""Tests for ReviewerAgent."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from claude_code_sdk.types import ResultMessage

from src.agents.reviewer import ReviewerAgent
from src.core.config import ReviewerConfig
from src.core.types import ReviewerContext, Success, Error
from tests.unit.base_test import BaseAgentTest


class TestReviewerAgent(BaseAgentTest):
    """Test the ReviewerAgent class."""

    def _create_mock_client(self):
        """Helper to create a properly configured mock client."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    def _create_result_message(self, is_error=False):
        """Helper to create a ResultMessage."""
        return ResultMessage(
            subtype="error" if is_error else "success",
            duration_ms=1000,
            duration_api_ms=800,
            is_error=is_error,
            num_turns=1,
            session_id="test",
            total_cost_usd=0.001,
        )

    @pytest.fixture
    def config(self) -> ReviewerConfig:
        """Create reviewer configuration."""
        return ReviewerConfig(
            max_turns=5,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/reviewer/system.md",
            allowed_tools=[],  # Reviewer doesn't need tools by default
            max_iterations=3,
            strictness="normal",
        )

    @pytest.fixture
    def context(self) -> ReviewerContext:
        """Create basic reviewer context."""
        assert self.temp_dir is not None

        # Create analysis file in proper location
        analyses_dir = self.temp_dir / "analyses" / "test-idea"
        analyses_dir.mkdir(parents=True, exist_ok=True)
        analysis_file = analyses_dir / "analysis.md"
        _ = analysis_file.write_text("# Test Analysis\nContent here.")

        # Create feedback output file
        feedback_file = analyses_dir / "feedback.json"
        _ = feedback_file.write_text("")

        return ReviewerContext(
            iteration=1,
            analysis_input_path=analysis_file,
            feedback_output_path=feedback_file,
        )

    @pytest.mark.asyncio
    async def test_successful_feedback_creation(
        self, config: ReviewerConfig, context: ReviewerContext
    ):
        """Test that agent returns Success when feedback file is created."""
        # Mock path validation since we're using temp directories
        with patch(
            "src.agents.reviewer.ReviewerAgent._validate_analysis_path"
        ) as mock_validate:
            mock_validate.return_value = context.analysis_input_path

            with patch("src.agents.reviewer.ClaudeSDKClient") as MockClient:
                mock_client = self._create_mock_client()
                MockClient.return_value = mock_client

                async def mock_receive():
                    # Simulate feedback file being created
                    feedback = {
                        "overall_assessment": "The analysis is comprehensive and well-structured.",
                        "iteration_recommendation": "approve",
                        "iteration_reason": "Analysis meets all requirements",
                    }
                    _ = context.feedback_output_path.write_text(json.dumps(feedback))

                    yield self._create_result_message(is_error=False)

                mock_client.receive_response = mock_receive
                agent = ReviewerAgent(config)
                result = await agent.process("", context)

                # Success when feedback file exists and is valid JSON
                assert isinstance(result, Success)
                assert context.feedback_output_path.exists()
                # Verify it's valid JSON
                _ = json.loads(context.feedback_output_path.read_text())  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_failure_when_no_feedback_created(
        self, config: ReviewerConfig, context: ReviewerContext
    ):
        """Test that agent returns Error when feedback file is not created."""
        # Mock path validation since we're using temp directories
        with patch(
            "src.agents.reviewer.ReviewerAgent._validate_analysis_path"
        ) as mock_validate:
            mock_validate.return_value = context.analysis_input_path

            with patch("src.agents.reviewer.ClaudeSDKClient") as MockClient:
                mock_client = self._create_mock_client()
                MockClient.return_value = mock_client

                async def mock_receive():
                    # SDK completes but doesn't create feedback file
                    yield self._create_result_message(is_error=False)

                mock_client.receive_response = mock_receive
                agent = ReviewerAgent(config)
                result = await agent.process("", context)

                # Should return Error when feedback file is empty/invalid
                assert isinstance(result, Error)
                assert "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_path_validation(self, config: ReviewerConfig):
        """Test that agent validates analysis path is in correct directory."""
        assert self.temp_dir is not None

        # Create analysis file in WRONG location (not under analyses/)
        bad_file = self.temp_dir / "wrong_location.md"
        _ = bad_file.write_text("Analysis")

        feedback_file = self.temp_dir / "feedback.json"
        _ = feedback_file.write_text("")

        context = ReviewerContext(
            iteration=1,
            analysis_input_path=bad_file,
            feedback_output_path=feedback_file,
        )

        agent = ReviewerAgent(config)
        result = await agent.process("", context)

        # Should return Error for invalid path
        assert isinstance(result, Error)
        assert "must be within" in result.message.lower()

    @pytest.mark.asyncio
    async def test_error_handling(
        self, config: ReviewerConfig, context: ReviewerContext
    ):
        """Test error handling in reviewer agent."""
        with patch(
            "src.agents.reviewer.ReviewerAgent._validate_analysis_path"
        ) as mock_validate:
            mock_validate.return_value = context.analysis_input_path

            with patch("src.agents.reviewer.ClaudeSDKClient") as MockClient:
                # Mock an error during SDK client creation
                MockClient.side_effect = Exception("API connection failed")

                agent = ReviewerAgent(config)
                result = await agent.process("", context)

                assert isinstance(result, Error)
                assert "API connection failed" in result.message

    @pytest.mark.asyncio
    async def test_invalid_json_feedback(
        self, config: ReviewerConfig, context: ReviewerContext
    ):
        """Test that agent handles invalid JSON feedback properly."""
        with patch(
            "src.agents.reviewer.ReviewerAgent._validate_analysis_path"
        ) as mock_validate:
            mock_validate.return_value = context.analysis_input_path

            with patch("src.agents.reviewer.ClaudeSDKClient") as MockClient:
                mock_client = self._create_mock_client()
                MockClient.return_value = mock_client

                async def mock_receive():
                    # Write invalid JSON to feedback file
                    _ = context.feedback_output_path.write_text("not valid json")
                    yield self._create_result_message(is_error=False)

                mock_client.receive_response = mock_receive
                agent = ReviewerAgent(config)
                result = await agent.process("", context)

                # Should return Error for invalid JSON
                assert isinstance(result, Error)
                assert (
                    "invalid" in result.message.lower()
                    or "failed" in result.message.lower()
                )

    @pytest.mark.asyncio
    async def test_sdk_error_message(
        self, config: ReviewerConfig, context: ReviewerContext
    ):
        """Test that SDK errors are properly reported."""
        with patch(
            "src.agents.reviewer.ReviewerAgent._validate_analysis_path"
        ) as mock_validate:
            mock_validate.return_value = context.analysis_input_path

            with patch("src.agents.reviewer.ClaudeSDKClient") as MockClient:
                mock_client = self._create_mock_client()
                MockClient.return_value = mock_client

                async def mock_receive():
                    # SDK returns error
                    yield self._create_result_message(is_error=True)

                mock_client.receive_response = mock_receive
                agent = ReviewerAgent(config)
                result = await agent.process("", context)

                # Should return Error when SDK reports error
                assert isinstance(result, Error)

    @pytest.mark.asyncio
    async def test_missing_context_validation(self, config: ReviewerConfig):
        """Test that agent validates context is provided."""
        agent = ReviewerAgent(config)

        # Should raise ValueError for missing context
        with pytest.raises(ValueError, match="Reviewer requires context"):
            _ = await agent.process("", None)

    @pytest.mark.asyncio
    async def test_feedback_with_different_recommendations(
        self, config: ReviewerConfig, context: ReviewerContext
    ):
        """Test different feedback recommendations."""
        with patch(
            "src.agents.reviewer.ReviewerAgent._validate_analysis_path"
        ) as mock_validate:
            mock_validate.return_value = context.analysis_input_path

            # Test each valid recommendation type
            for recommendation in ["approve", "reject"]:
                with patch("src.agents.reviewer.ClaudeSDKClient") as MockClient:
                    mock_client = self._create_mock_client()
                    MockClient.return_value = mock_client

                    async def mock_receive():
                        feedback = {
                            "overall_assessment": f"Analysis assessment for {recommendation} test.",
                            "iteration_recommendation": recommendation,
                            "iteration_reason": f"Testing {recommendation}",
                        }
                        _ = context.feedback_output_path.write_text(
                            json.dumps(feedback)
                        )
                        yield self._create_result_message(is_error=False)

                    mock_client.receive_response = mock_receive
                    agent = ReviewerAgent(config)
                    result = await agent.process("", context)

                    assert isinstance(result, Success)
                    feedback_data = json.loads(context.feedback_output_path.read_text())
                    assert feedback_data["iteration_recommendation"] == recommendation
