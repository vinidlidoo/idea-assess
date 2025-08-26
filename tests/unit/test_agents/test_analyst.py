"""Tests for AnalystAgent."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from claude_code_sdk.types import (
    ResultMessage,
)

from src.agents.analyst import AnalystAgent
from src.core.config import AnalystConfig
from src.core.types import AnalystContext, Success, Error
from tests.fixtures.test_data import TEST_IDEAS
from tests.unit.base_test import BaseAgentTest


class TestAnalystAgent(BaseAgentTest):
    """Test the AnalystAgent class."""

    @pytest.fixture
    def config(self) -> AnalystConfig:
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
    def context(self) -> AnalystContext:
        """Create analyst context."""
        assert self.temp_dir is not None
        output_file = self.temp_dir / "analysis.md"
        _ = output_file.write_text("")

        return AnalystContext(
            iteration=1,
            idea_slug="test-idea",
            analysis_output_path=output_file,
            feedback_input_path=None,
            websearch_count=0,
        )

    @pytest.mark.asyncio
    async def test_successful_file_creation(
        self, config: AnalystConfig, context: AnalystContext
    ):
        """Test that agent returns Success when output file is created."""
        with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            async def mock_receive():
                # Simulate file being created by SDK (this is what matters)
                _ = context.analysis_output_path.write_text("# Analysis\nContent here")

                # Return success result
                yield ResultMessage(
                    subtype="success",
                    duration_ms=1000,
                    duration_api_ms=800,
                    is_error=False,
                    num_turns=1,
                    session_id="test",
                    total_cost_usd=0.001,
                )

            mock_client.receive_response = mock_receive
            agent = AnalystAgent(config)
            result = await agent.process(TEST_IDEAS["simple"], context)

            # The ONLY thing that matters: Success when file exists
            assert isinstance(result, Success)
            assert context.analysis_output_path.exists()

    @pytest.mark.asyncio
    async def test_failure_when_no_file_created(
        self, config: AnalystConfig, context: AnalystContext
    ):
        """Test that agent returns Error when output file is not created."""
        # Delete the file that was created in the fixture
        if context.analysis_output_path.exists():
            context.analysis_output_path.unlink()

        with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            async def mock_receive():
                # SDK completes but doesn't create file (simulates tool failure)
                yield ResultMessage(
                    subtype="success",
                    duration_ms=1000,
                    duration_api_ms=800,
                    is_error=False,
                    num_turns=1,
                    session_id="test",
                    total_cost_usd=0.001,
                )

            mock_client.receive_response = mock_receive
            agent = AnalystAgent(config)
            result = await agent.process(TEST_IDEAS["simple"], context)

            # Should return Error when file doesn't exist
            assert isinstance(result, Error)
            assert "failed to write analysis" in result.message.lower()
            assert not context.analysis_output_path.exists()

    @pytest.mark.asyncio
    async def test_context_with_feedback_path(self, config: AnalystConfig):
        """Test that agent handles feedback_input_path in context correctly."""
        assert self.temp_dir is not None

        # Create a feedback file (agent should reference this in prompt)
        feedback_file = self.temp_dir / "feedback.json"
        _ = feedback_file.write_text('{"recommendation": "revise"}')

        # Create output file
        output_file = self.temp_dir / "analysis.md"
        _ = output_file.write_text("")

        context = AnalystContext(
            iteration=2,
            idea_slug="test-idea",
            analysis_output_path=output_file,
            feedback_input_path=feedback_file,  # This triggers revision mode
            websearch_count=0,
        )

        with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            # Capture the prompt sent to Claude
            captured_prompt: str | None = None

            async def capture_query(prompt: str) -> None:
                nonlocal captured_prompt
                captured_prompt = prompt

            mock_client.query = capture_query

            async def mock_receive():
                # Simulate successful revision
                _ = output_file.write_text("Revised content")
                yield ResultMessage(
                    subtype="success",
                    duration_ms=1000,
                    duration_api_ms=800,
                    is_error=False,
                    num_turns=1,
                    session_id="test",
                    total_cost_usd=0.001,
                )

            mock_client.receive_response = mock_receive
            agent = AnalystAgent(config)
            result = await agent.process(TEST_IDEAS["simple"], context)

            # Verify revision mode was activated (feedback file mentioned in prompt)
            assert isinstance(result, Success)
            assert captured_prompt is not None
            assert str(feedback_file) in captured_prompt  # pyright: ignore[reportUnreachable]

    @pytest.mark.asyncio
    async def test_websearch_tool_configuration(
        self, config: AnalystConfig, context: AnalystContext
    ):
        """Test that WebSearch tool is properly configured when allowed."""
        # Ensure WebSearch is in allowed tools
        config.allowed_tools = ["WebSearch", "Edit"]

        with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            async def mock_receive():
                _ = context.analysis_output_path.write_text("Analysis")
                yield ResultMessage(
                    subtype="success",
                    duration_ms=1000,
                    duration_api_ms=800,
                    is_error=False,
                    num_turns=1,
                    session_id="test",
                    total_cost_usd=0.001,
                )

            mock_client.receive_response = mock_receive
            agent = AnalystAgent(config)
            _ = await agent.process(TEST_IDEAS["simple"], context)

            # Verify SDK was called with WebSearch in allowed_tools
            MockClient.assert_called_once()
            call_kwargs = MockClient.call_args.kwargs
            assert "WebSearch" in call_kwargs["options"].allowed_tools  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_error_handling(self, config: AnalystConfig, context: AnalystContext):
        """Test error handling in agent."""
        with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
            # Mock an error during SDK client creation
            MockClient.side_effect = Exception("API connection failed")

            agent = AnalystAgent(config)
            result = await agent.process(TEST_IDEAS["simple"], context)

            assert isinstance(result, Error)
            assert "API connection failed" in result.message

    @pytest.mark.asyncio
    async def test_empty_idea_validation(
        self, config: AnalystConfig, context: AnalystContext
    ):
        """Test that agent validates non-empty input."""
        agent = AnalystAgent(config)

        # Should raise ValueError for empty input
        with pytest.raises(ValueError, match="Analyst requires input_data"):
            _ = await agent.process("", context)

    @pytest.mark.asyncio
    async def test_missing_context_validation(self, config: AnalystConfig):
        """Test that agent validates context is provided."""
        agent = AnalystAgent(config)

        # Should raise ValueError for missing context
        with pytest.raises(ValueError, match="Analyst requires context"):
            _ = await agent.process("test idea", None)
