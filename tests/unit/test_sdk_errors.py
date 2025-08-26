"""Tests for SDK error handling across the system."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from claude_code_sdk.types import ResultMessage

from src.core.types import Error
from src.agents.analyst import AnalystAgent
from src.agents.reviewer import ReviewerAgent
from src.core.config import AnalystConfig, ReviewerConfig
from src.core.types import AnalystContext, ReviewerContext
from tests.unit.base_test import BaseAgentTest
from tests.fixtures.test_data import TEST_IDEAS


class TestSDKErrorHandling(BaseAgentTest):
    """Test SDK error handling scenarios."""

    @pytest.mark.asyncio
    async def test_analyst_handles_sdk_errors(self):
        """Test that AnalystAgent properly handles SDK errors."""
        assert self.temp_dir is not None

        output_file = self.temp_dir / "analysis.md"
        # Don't create the file - agent checks existence for success

        context = AnalystContext(
            iteration=1,
            idea_slug="test-idea",
            analysis_output_path=output_file,
            feedback_input_path=None,
            websearch_count=0,
        )

        config = AnalystConfig(
            max_turns=10,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/analyst/system.md",
            allowed_tools=["WebSearch", "Edit"],
            max_websearches=5,
            min_words=1000,
        )

        with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            async def mock_receive():
                # Simulate SDK error via ResultMessage
                yield ResultMessage(
                    subtype="error",
                    duration_ms=100,
                    duration_api_ms=80,
                    is_error=True,
                    num_turns=0,
                    session_id="test",
                    total_cost_usd=0.0,
                )

            mock_client.receive_response = mock_receive

            agent = AnalystAgent(config)
            result = await agent.process(TEST_IDEAS["simple"], context)

            # Should handle SDK error gracefully
            assert isinstance(result, Error)
            # Agent returns specific error when file not created
            assert "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        assert self.temp_dir is not None

        output_file = self.temp_dir / "analysis.md"
        # Don't create the file - agent checks existence for success

        context = AnalystContext(
            iteration=1,
            idea_slug="test-idea",
            analysis_output_path=output_file,
            feedback_input_path=None,
            websearch_count=0,
        )

        config = AnalystConfig(
            max_turns=10,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/analyst/system.md",
            allowed_tools=["WebSearch", "Edit"],
            max_websearches=5,
            min_words=1000,
        )

        with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
            # Simulate connection error during client creation
            MockClient.side_effect = ConnectionError("Failed to connect to API")

            agent = AnalystAgent(config)
            result = await agent.process(TEST_IDEAS["simple"], context)

            assert isinstance(result, Error)
            assert "connect" in result.message.lower()

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Test handling of timeout errors."""
        assert self.temp_dir is not None

        output_file = self.temp_dir / "analysis.md"
        # Don't create the file - agent checks existence for success

        context = AnalystContext(
            iteration=1,
            idea_slug="test-idea",
            analysis_output_path=output_file,
            feedback_input_path=None,
            websearch_count=0,
        )

        config = AnalystConfig(
            max_turns=10,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/analyst/system.md",
            allowed_tools=["WebSearch", "Edit"],
            max_websearches=5,
            min_words=1000,
        )

        with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            # Simulate timeout
            def mock_receive():
                async def _generator():
                    raise asyncio.TimeoutError("Request timed out")
                    yield  # pyright: ignore[reportUnreachable]

                return _generator()

            mock_client.receive_response = mock_receive

            agent = AnalystAgent(config)
            result = await agent.process(TEST_IDEAS["simple"], context)

            assert isinstance(result, Error)
            assert (
                "timeout" in result.message.lower()
                or "timed out" in result.message.lower()
            )

    @pytest.mark.asyncio
    async def test_reviewer_handles_invalid_json(self):
        """Test that ReviewerAgent handles invalid JSON in feedback file."""
        assert self.temp_dir is not None

        # Create proper directory structure
        analyses_dir = self.temp_dir / "analyses" / "test-idea"
        analyses_dir.mkdir(parents=True, exist_ok=True)
        analysis_file = analyses_dir / "analysis.md"
        _ = analysis_file.write_text("# Analysis\nContent")
        feedback_file = analyses_dir / "feedback.json"
        _ = feedback_file.write_text("")

        context = ReviewerContext(
            iteration=1,
            analysis_input_path=analysis_file,
            feedback_output_path=feedback_file,
        )

        config = ReviewerConfig(
            max_turns=5,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/reviewer/system.md",
            allowed_tools=["Read", "Edit"],
            max_iterations=3,
            strictness="normal",
        )

        with patch("src.agents.reviewer.ClaudeSDKClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            async def mock_receive():
                # Write invalid JSON to feedback file
                _ = feedback_file.write_text("not valid json")

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

            agent = ReviewerAgent(config)
            result = await agent.process("", context)

            # Should return Error for invalid JSON
            assert isinstance(result, Error)
            assert (
                "failed" in result.message.lower()
                or "invalid" in result.message.lower()
            )
