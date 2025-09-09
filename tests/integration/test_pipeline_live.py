#!/usr/bin/env python
"""
Live integration tests for parallel Reviewer and FactChecker execution.

These tests use REAL Claude API calls and cost money. They are marked with
@pytest.mark.live and are skipped by default in CI/CD.

To run these tests:
    pytest tests/integration/test_pipeline_live.py -m live -v -s

To skip these tests (default):
    pytest -m "not live"
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any

import pytest

from src.core.pipeline import AnalysisPipeline
from src.core.types import PipelineMode
from src.core.run_analytics import RunAnalytics
from src.core.config import (
    create_default_configs,
    SystemConfig,
    AnalystConfig,
    ReviewerConfig,
    FactCheckerConfig,
)
from src.agents.reviewer import ReviewerAgent
from src.agents.fact_checker import FactCheckerAgent


@pytest.mark.live
class TestPipelineLive:
    """Integration tests with real Claude API calls."""

    @pytest.fixture
    def fixture_analysis(self) -> Path:
        """Provide a fixture analysis to skip the 5-minute Analyst phase."""
        fixtures_dir = Path("tests/fixtures/analyses")
        fixture_path = fixtures_dir / "ai-tutoring-platform.md"

        if not fixture_path.exists():
            pytest.skip(f"Fixture not found at {fixture_path}")

        return fixture_path

    @pytest.fixture
    def pipeline_configs(
        self,
    ) -> tuple[SystemConfig, AnalystConfig, ReviewerConfig, FactCheckerConfig]:
        """Create default configs for pipeline."""
        root_dir = Path.cwd()
        return create_default_configs(root_dir)

    @pytest.mark.asyncio
    async def test_parallel_reviewer_factchecker(
        self,
        fixture_analysis: Path,
        pipeline_configs: tuple[
            SystemConfig, AnalystConfig, ReviewerConfig, FactCheckerConfig
        ],
    ) -> None:
        """
        Test parallel execution of Reviewer and FactChecker with real API.

        This test simulates running the pipeline from the point where the Analyst
        has already created the first draft. Everything else is identical to a real
        CLI run with --with-review-and-fact-check flag.
        """
        # Unpack configs
        system_config, analyst_config, reviewer_config, fact_checker_config = (
            pipeline_configs
        )

        # Use a unique test idea name with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create pipeline EXACTLY as CLI would, with timestamped suffix
        # This prevents creating duplicate directories
        pipeline = AnalysisPipeline(
            idea="Test parallel execution",  # Original idea text
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=PipelineMode.ANALYZE_REVIEW_WITH_FACT_CHECK,
            slug_suffix=timestamp,  # Appends timestamp to slug
        )

        # Now pipeline.slug is already "test-parallel-execution-{timestamp}"
        # and the directory was created by the constructor
        output_dir = pipeline.output_dir
        iterations_dir = pipeline.iterations_dir

        # Copy fixture as iteration_1.md (simulating completed Analyst phase)
        analysis_path = iterations_dir / "iteration_1.md"
        _ = shutil.copy(fixture_analysis, analysis_path)

        # Set state as if analyst just completed iteration 1
        pipeline.iteration_count = 1
        pipeline.current_analysis_file = analysis_path

        # Initialize RunAnalytics just like the real pipeline would
        timestamp_analytics = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp_analytics}_{pipeline.slug}"
        pipeline.analytics = RunAnalytics(run_id=run_id, output_dir=Path("logs/runs"))

        # Copy to analysis.md
        analysis_md = output_dir / "analysis.md"
        _ = shutil.copy2(analysis_path, analysis_md)

        # Create agents
        reviewer = ReviewerAgent(reviewer_config)
        fact_checker = FactCheckerAgent(fact_checker_config)

        # Run parallel execution
        should_continue = await pipeline._run_parallel_review_fact_check(
            reviewer, fact_checker
        )

        # Verify outputs
        feedback_path = (
            iterations_dir
            / f"reviewer_feedback_iteration_{pipeline.iteration_count}.json"
        )
        fact_check_path = (
            iterations_dir / f"fact_check_iteration_{pipeline.iteration_count}.json"
        )

        # Check reviewer output
        assert feedback_path.exists(), "Reviewer feedback file not created"
        with open(feedback_path) as f:
            feedback: dict[str, Any] = json.load(f)  # pyright: ignore[reportAny, reportExplicitAny]
            # Handle both field names for compatibility
            rec_field = (
                "recommendation"
                if "recommendation" in feedback
                else "iteration_recommendation"
            )
            assert rec_field in feedback, (
                "Neither 'recommendation' nor 'iteration_recommendation' found in feedback"
            )
            assert feedback[rec_field] in ["approve", "revise", "reject"]

        # Check fact-checker output
        assert fact_check_path.exists(), "Fact-check file not created"
        with open(fact_check_path) as f:
            fact_check: dict[str, Any] = json.load(f)  # pyright: ignore[reportAny, reportExplicitAny]
            # Handle both field names for compatibility
            fc_rec_field = (
                "iteration_recommendation"
                if "iteration_recommendation" in fact_check
                else "recommendation"
            )
            assert fc_rec_field in fact_check, (
                "Neither 'iteration_recommendation' nor 'recommendation' found in fact-check"
            )
            assert fact_check[fc_rec_field] in ["approve", "reject"]

        # Verify decision logic
        reviewer_approved: bool = feedback[rec_field] == "approve"  # pyright: ignore[reportAny]
        factchecker_approved: bool = fact_check[fc_rec_field] == "approve"  # pyright: ignore[reportAny]

        # should_continue is True if either agent rejects
        expected_continue = not (reviewer_approved and factchecker_approved)
        assert should_continue == expected_continue, (
            f"Veto logic mismatch: should_continue={should_continue}, "
            f"reviewer={feedback[rec_field]}, "
            f"fact_checker={fact_check[fc_rec_field]}"
        )

        print("\n✅ Test passed:")
        print(f"  - Reviewer: {feedback[rec_field]}")
        print(f"  - FactChecker: {fact_check[fc_rec_field]}")
        print(f"  - Should continue: {should_continue}")

        # Finalize analytics if it was created
        if pipeline.analytics:
            pipeline.analytics.finalize()

        # Clean up test directory after successful test
        # if output_dir.exists():
        #     shutil.rmtree(output_dir)

    @pytest.mark.asyncio
    async def test_analyst_handles_feedback(
        self,
        fixture_analysis: Path,
        pipeline_configs: tuple[
            SystemConfig, AnalystConfig, ReviewerConfig, FactCheckerConfig
        ],
    ) -> None:
        """
        Test Analyst agent handling revision based on feedback.

        This test simulates iteration 2 where the Analyst revises the analysis
        based on reviewer feedback (and optionally fact-check results).
        """
        # Unpack configs
        system_config, analyst_config, reviewer_config, fact_checker_config = (
            pipeline_configs
        )

        # Use a unique test idea name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create pipeline in review mode
        pipeline = AnalysisPipeline(
            idea="Test analyst revision",
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=PipelineMode.ANALYZE_AND_REVIEW,
            slug_suffix=timestamp,
        )

        output_dir = pipeline.output_dir
        iterations_dir = pipeline.iterations_dir

        # Copy fixture as iteration_1.md (simulating completed iteration 1)
        iteration1_path = iterations_dir / "iteration_1.md"
        _ = shutil.copy(fixture_analysis, iteration1_path)

        # Create sample reviewer feedback file
        feedback_path = iterations_dir / "reviewer_feedback_iteration_1.json"
        feedback_data = {
            "overall_assessment": "Good foundation but needs improvements in market sizing and competitive analysis.",
            "strengths": [
                "Clear problem statement",
                "Good understanding of target market",
            ],
            "critical_issues": [
                {
                    "section": "Market Opportunity",
                    "issue": "Missing bottom-up TAM calculation",
                    "suggestion": "Add calculation: 50K schools × $5K/year = $250M",
                }
            ],
            "improvements": [],
            "minor_suggestions": [],
            "iteration_recommendation": "revise",
            "iteration_reason": "Needs specific market sizing data to be compelling.",
        }
        with open(feedback_path, "w") as f:
            json.dump(feedback_data, f, indent=2)

        # Optionally create fact-check file
        fact_check_path = iterations_dir / "fact_check_iteration_1.json"
        fact_check_data = {
            "issues": [
                {
                    "claim": "Market growing at 25% CAGR",
                    "section": "Market Opportunity",
                    "severity": "High",
                    "details": {
                        "issue_type": "unsupported_claim",
                        "citation_ref": "none",
                        "url_checked": "N/A",
                        "explanation": "No citation provided for growth rate",
                        "evidence": "Could not verify this claim",
                        "suggestion": "Add citation from market research report",
                    },
                }
            ],
            "statistics": {
                "total_claims": "10",
                "verified_claims": "8",
                "unverified_claims": "2",
                "false_claims": "0",
            },
            "iteration_recommendation": "reject",
            "iteration_reason": "Key market claims lack citations.",
        }
        with open(fact_check_path, "w") as f:
            json.dump(fact_check_data, f, indent=2)

        # Set pipeline state for iteration 2
        pipeline.iteration_count = 1  # Will be incremented to 2
        pipeline.current_analysis_file = iteration1_path
        pipeline.last_feedback_file = feedback_path
        pipeline.last_fact_check_file = fact_check_path

        # Initialize analytics
        timestamp_analytics = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp_analytics}_{pipeline.slug}"
        pipeline.analytics = RunAnalytics(run_id=run_id, output_dir=Path("logs/runs"))

        # Create analyst agent
        from src.agents.analyst import AnalystAgent

        analyst = AnalystAgent(analyst_config)

        # Increment iteration as pipeline would
        pipeline.iteration_count = 2

        # Run analyst revision
        success = await pipeline._run_analyst(analyst)

        # Verify the revision was created
        assert success, "Analyst revision failed"

        iteration2_path = iterations_dir / "iteration_2.md"
        assert iteration2_path.exists(), "Iteration 2 file not created"

        # Read the revised analysis
        with open(iteration2_path) as f:
            revised_content = f.read()

        # Basic checks that revision happened
        assert len(revised_content) > 1000, "Revised analysis too short"
        assert "market" in revised_content.lower(), "Should address market feedback"

        # Check analysis.md was updated
        analysis_md = output_dir / "analysis.md"
        assert analysis_md.exists(), "Analysis.md not created"
        # Check content matches iteration 2
        assert analysis_md.read_text() == iteration2_path.read_text(), "Analysis.md not updated"

        print("\n✅ Analyst revision test passed")
        print(f"  - Original: {iteration1_path.stat().st_size} bytes")
        print(f"  - Revised: {iteration2_path.stat().st_size} bytes")

        # Finalize analytics
        if pipeline.analytics:
            pipeline.analytics.finalize()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Long-running test - enable manually")
    async def test_full_pipeline_with_factchecker(
        self,
        pipeline_configs: tuple[
            SystemConfig, AnalystConfig, ReviewerConfig, FactCheckerConfig
        ],
    ) -> None:
        """
        Test the full pipeline including Analyst, Reviewer, and FactChecker.

        This is a comprehensive test that takes 5+ minutes as it runs the
        full Analyst agent first.
        """
        # This would be the full end-to-end test
        _ = pipeline_configs  # Mark as intentionally unused
        pass
