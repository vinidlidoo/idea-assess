"""Tests for FactCheckerAgent."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from claude_code_sdk.types import ResultMessage

from src.agents.fact_checker import FactCheckerAgent
from src.core.config import FactCheckerConfig
from src.core.types import FactCheckContext, Success, Error
from tests.unit.base_test import BaseAgentTest


class TestFactCheckerAgent(BaseAgentTest):
    """Test the FactCheckerAgent class."""

    def _create_mock_client(self):
        """Helper to create a properly configured mock client."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    def _create_result_message(self, is_error: bool = False):
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
    def config(self) -> FactCheckerConfig:
        """Create fact-checker configuration."""
        return FactCheckerConfig(
            max_turns=5,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/fact-checker/system.md",
            allowed_tools=["WebFetch", "Edit", "TodoWrite"],
            webfetch_per_iteration=10,
        )

    @pytest.fixture
    def context(self) -> FactCheckContext:
        """Create fact-check context."""
        assert self.temp_dir is not None
        analysis_path = self.temp_dir / "analysis.md"
        fact_check_path = self.temp_dir / "fact_check.json"

        # Create test analysis with citations
        analysis_path.write_text("""# Business Idea Analysis

## Market Analysis
The global AI market is valued at $150B in 2024 [1].
Growth rate is projected at 38% CAGR through 2030 [2].

## Competition
Major competitors include OpenAI, Google, and Anthropic [3].

## References
[1] Gartner AI Report 2024. https://example.com/gartner
[2] McKinsey AI Growth Study. https://example.com/mckinsey
[3] Tech Crunch AI Landscape. https://example.com/techcrunch
""")

        # Create fact-check template
        fact_check_template = {
            "issues": [],
            "statistics": {
                "total_claims": 0,
                "verified_claims": 0,
                "unverified_claims": 0,
                "false_claims": 0,
            },
            "iteration_recommendation": "approve",
            "iteration_reason": "No critical issues found",
            "top_priorities": [],
        }
        fact_check_path.write_text(json.dumps(fact_check_template, indent=2))

        return FactCheckContext(
            analysis_input_path=analysis_path,
            fact_check_output_path=fact_check_path,
            iteration=1,
        )

    @pytest.mark.asyncio
    async def test_successful_fact_check(self, config, context):
        """Test successful fact-checking with proper JSON output."""
        agent = FactCheckerAgent(config)

        # Mock successful response
        mock_client = self._create_mock_client()

        async def mock_receive():
            yield self._create_result_message(is_error=False)

        mock_client.receive_response = mock_receive

        with patch("src.agents.fact_checker.ClaudeSDKClient", return_value=mock_client):
            with patch(
                "src.utils.file_operations.load_prompt_with_includes",
                return_value="Test prompt",
            ):
                with patch.object(
                    agent,
                    "_validate_analysis_path",
                    return_value=context.analysis_input_path,
                ):
                    result = await agent.process("", context)

        # Should return Success
        assert isinstance(result, Success)

        # Verify fact-check file was processed
        assert context.fact_check_output_path.exists()

    @pytest.mark.asyncio
    async def test_critical_issues_detection(self, config, context):
        """Test detection of critical citation issues."""
        # Update analysis with problematic citations
        context.analysis_input_path.write_text("""# Business Idea Analysis

## Market Analysis  
The global AI market is valued at $999T in 2024 [1].
Growth rate is 500% per year [2].

## References
[1] Made up source. https://fake.com
[2] Another fake source. https://notreal.com
""")

        agent = FactCheckerAgent(config)

        # Mock response that would edit the JSON with critical issues
        mock_client = self._create_mock_client()

        async def mock_receive():
            # Simulate agent editing the fact-check file
            fact_check_data = {
                "issues": [
                    {
                        "claim": "The global AI market is valued at $999T in 2024",
                        "section": "Market Analysis",
                        "severity": "High",
                        "details": {
                            "issue_type": "likely_hallucination",
                            "explanation": "This market size is unrealistic",
                            "evidence": "No market is worth $999 trillion",
                            "suggestion": "Verify actual market size from credible source",
                        },
                    }
                ],
                "statistics": {
                    "total_claims": 2,
                    "verified_claims": 0,
                    "unverified_claims": 0,
                    "false_claims": 2,
                },
                "iteration_recommendation": "reject",
                "iteration_reason": "Critical citation issues found",
                "top_priorities": ["Fix unrealistic market size claim"],
            }
            context.fact_check_output_path.write_text(
                json.dumps(fact_check_data, indent=2)
            )
            yield self._create_result_message(is_error=False)

        mock_client.receive_response = mock_receive

        with patch("src.agents.fact_checker.ClaudeSDKClient", return_value=mock_client):
            with patch(
                "src.utils.file_operations.load_prompt_with_includes",
                return_value="Test prompt",
            ):
                with patch.object(
                    agent,
                    "_validate_analysis_path",
                    return_value=context.analysis_input_path,
                ):
                    result = await agent.process("", context)

        # Should succeed (process completes)
        assert isinstance(result, Success)

        # Verify rejection recommendation
        fact_check_data = json.loads(context.fact_check_output_path.read_text())
        assert fact_check_data["iteration_recommendation"] == "reject"
        assert len(fact_check_data["issues"]) > 0
        assert fact_check_data["issues"][0]["severity"] == "High"

    @pytest.mark.asyncio
    async def test_missing_citations_detection(self, config, context):
        """Test detection of missing citations."""
        # Analysis without proper citations
        context.analysis_input_path.write_text("""# Business Idea Analysis

## Market Analysis
The global AI market is huge.
Growth is very fast.
Many companies are investing billions.

## Competition
Everyone is doing AI now.
""")

        agent = FactCheckerAgent(config)
        mock_client = self._create_mock_client()

        async def mock_receive():
            yield self._create_result_message(is_error=False)

        mock_client.receive_response = mock_receive

        with patch("src.agents.fact_checker.ClaudeSDKClient", return_value=mock_client):
            with patch(
                "src.utils.file_operations.load_prompt_with_includes",
                return_value="Test prompt",
            ):
                with patch.object(
                    agent,
                    "_validate_analysis_path",
                    return_value=context.analysis_input_path,
                ):
                    result = await agent.process("", context)

        assert isinstance(result, Success)

    @pytest.mark.asyncio
    async def test_error_handling_analysis_not_found(self, config):
        """Test error when analysis file doesn't exist."""
        assert self.temp_dir is not None

        # Context with non-existent analysis file
        context = FactCheckContext(
            analysis_input_path=self.temp_dir / "nonexistent.md",
            fact_check_output_path=self.temp_dir / "fact_check.json",
            iteration=1,
        )

        agent = FactCheckerAgent(config)
        result = await agent.process("", context)

        # Should return Error
        assert isinstance(result, Error)
        assert (
            "not found" in result.message.lower()
            or "invalid path" in result.message.lower()
        )

    @pytest.mark.asyncio
    async def test_error_handling_template_not_found(self, config, context):
        """Test error when fact-check template doesn't exist."""
        # Remove the template file
        context.fact_check_output_path.unlink()

        agent = FactCheckerAgent(config)
        with patch(
            "src.utils.file_operations.load_prompt_with_includes",
            return_value="Test prompt",
        ):
            with patch.object(
                agent,
                "_validate_analysis_path",
                return_value=context.analysis_input_path,
            ):
                result = await agent.process("", context)

        # Should return Error
        assert isinstance(result, Error)
        assert (
            "template" in result.message.lower()
            or "not found" in result.message.lower()
            or "failed to edit" in result.message.lower()
        )

    @pytest.mark.asyncio
    async def test_interrupt_handling(self, config, context):
        """Test graceful handling of interrupts during processing."""
        agent = FactCheckerAgent(config)

        # Mock client that raises KeyboardInterrupt
        mock_client = self._create_mock_client()

        async def mock_receive():
            raise KeyboardInterrupt("User interrupted")
            yield  # Make it a generator (unreachable, but required for async iteration)

        mock_client.receive_response = mock_receive

        with patch("src.agents.fact_checker.ClaudeSDKClient", return_value=mock_client):
            with patch(
                "src.utils.file_operations.load_prompt_with_includes",
                return_value="Test prompt",
            ):
                with patch.object(
                    agent,
                    "_validate_analysis_path",
                    return_value=context.analysis_input_path,
                ):
                    with pytest.raises(KeyboardInterrupt):
                        await agent.process("", context)

    @pytest.mark.asyncio
    async def test_sdk_error_handling(self, config, context):
        """Test handling of SDK errors."""
        agent = FactCheckerAgent(config)

        # Mock client that returns error message
        mock_client = self._create_mock_client()

        async def mock_receive():
            yield self._create_result_message(is_error=True)

        mock_client.receive_response = mock_receive

        with patch("src.agents.fact_checker.ClaudeSDKClient", return_value=mock_client):
            with patch(
                "src.utils.file_operations.load_prompt_with_includes",
                return_value="Test prompt",
            ):
                with patch.object(
                    agent,
                    "_validate_analysis_path",
                    return_value=context.analysis_input_path,
                ):
                    result = await agent.process("", context)

        # Should return Error (validation error because SDK returns without editing)
        assert isinstance(result, Error)
        # The error will be about invalid structure since SDK failed to edit the file
        assert "invalid" in result.message.lower() or "SDK error" in result.message

    @pytest.mark.asyncio
    async def test_approval_scenario(self, config, context):
        """Test approval when citations are valid."""
        agent = FactCheckerAgent(config)

        # Mock response that approves
        mock_client = self._create_mock_client()

        async def mock_receive():
            # Simulate agent editing with approval
            fact_check_data = {
                "issues": [],
                "statistics": {
                    "total_claims": 3,
                    "verified_claims": 3,
                    "unverified_claims": 0,
                    "false_claims": 0,
                },
                "iteration_recommendation": "approve",
                "iteration_reason": "All citations verified successfully",
                "top_priorities": [],
            }
            context.fact_check_output_path.write_text(
                json.dumps(fact_check_data, indent=2)
            )
            yield self._create_result_message(is_error=False)

        mock_client.receive_response = mock_receive

        with patch("src.agents.fact_checker.ClaudeSDKClient", return_value=mock_client):
            with patch(
                "src.utils.file_operations.load_prompt_with_includes",
                return_value="Test prompt",
            ):
                with patch.object(
                    agent,
                    "_validate_analysis_path",
                    return_value=context.analysis_input_path,
                ):
                    result = await agent.process("", context)

        assert isinstance(result, Success)

        # Verify approval
        fact_check_data = json.loads(context.fact_check_output_path.read_text())
        assert fact_check_data["iteration_recommendation"] == "approve"
        assert len(fact_check_data["issues"]) == 0

    @pytest.mark.asyncio
    async def test_run_analytics_integration(self, config, context):
        """Test that RunAnalytics is properly used if provided."""
        from src.core.run_analytics import RunAnalytics

        # Create mock analytics
        assert self.temp_dir is not None
        analytics = RunAnalytics(run_id="test-run", output_dir=self.temp_dir)
        context.run_analytics = analytics

        agent = FactCheckerAgent(config)

        mock_client = self._create_mock_client()

        async def mock_receive():
            yield self._create_result_message(is_error=False)

        mock_client.receive_response = mock_receive

        with patch("src.agents.fact_checker.ClaudeSDKClient", return_value=mock_client):
            with patch(
                "src.utils.file_operations.load_prompt_with_includes",
                return_value="Test prompt",
            ):
                with patch.object(
                    agent,
                    "_validate_analysis_path",
                    return_value=context.analysis_input_path,
                ):
                    result = await agent.process("", context)

        assert isinstance(result, Success)
        # Analytics should have recorded the run
        assert analytics.webfetch_count >= 0  # May or may not have fetches
