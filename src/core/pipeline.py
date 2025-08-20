"""Pipeline orchestration for business idea analysis."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import logging

from ..agents.analyst import AnalystAgent
from ..agents.reviewer import ReviewerAgent
from ..utils.text_processing import create_slug
from .config import AnalysisConfig, AnalystContext, ReviewerContext
from .run_analytics import RunAnalytics
from .types import PipelineMode, PipelineResult

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrates the analysis pipeline for business ideas."""

    def __init__(
        self,
        idea: str,
        config: AnalysisConfig,
        mode: PipelineMode = PipelineMode.ANALYZE,
        max_iterations: int | None = None,
        analyst_system_prompt_override: str | None = None,
        reviewer_system_prompt_override: str | None = None,
        analyst_tools_override: list[str] | None = None,
    ) -> None:
        """
        Initialize the pipeline with idea and configuration.

        Args:
            idea: Business idea to analyze
            config: Analysis configuration object
            mode: Pipeline execution mode
            max_iterations: Optional override for max iterations
            analyst_system_prompt_override: Optional system prompt override for analyst
            reviewer_system_prompt_override: Optional system prompt override for reviewer
            analyst_tools_override: Optional tools override for analyst
        """
        # Core configuration
        self.idea: str = idea
        self.slug: str = create_slug(idea)
        self.config: AnalysisConfig = config
        self.mode: PipelineMode = mode

        # Context overrides (passed to agents)
        self.analyst_system_prompt_override: str | None = analyst_system_prompt_override
        self.reviewer_system_prompt_override: str | None = (
            reviewer_system_prompt_override
        )
        self.analyst_tools_override: list[str] | None = analyst_tools_override

        # Setup output directories
        self.output_dir: Path = Path("analyses") / self.slug
        self.iterations_dir: Path = self.output_dir / "iterations"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.iterations_dir.mkdir(exist_ok=True)

        # Iteration configuration
        self.max_iterations: int = (
            max_iterations or config.pipeline.max_iterations_by_mode.get(mode, 3)
        )

        # Runtime state (initialized but will be set during process)
        self.iteration_count: int = 0
        self.current_analysis_file: Path | None = None
        self.last_feedback: dict[str, Any] | None = None  # pyright: ignore[reportExplicitAny]
        self.analytics: RunAnalytics | None = None

    async def process(self) -> PipelineResult:
        """
        Process the business idea through the pipeline.

        Returns:
            PipelineResult with analysis outcome
        """
        # Initialize analytics for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp}_{self.slug}"
        self.analytics = RunAnalytics(run_id=run_id, output_dir=Path("logs/runs"))

        logger.info(
            f"🎯 Pipeline started - Mode: {self.mode.value}, Max iterations: {self.max_iterations}"
        )

        try:
            # Route to appropriate handler based on mode
            handlers = {
                PipelineMode.ANALYZE: self._analyze_only,
                PipelineMode.ANALYZE_AND_REVIEW: self._analyze_with_review,
                PipelineMode.ANALYZE_REVIEW_AND_JUDGE: self._analyze_review_judge,
                PipelineMode.FULL_EVALUATION: self._full_evaluation,
            }

            handler = handlers.get(self.mode, self._analyze_only)
            result = await handler()

            return result

        finally:
            # Clean up analytics
            if self.analytics:
                self.analytics.finalize()
            self.analytics = None

    async def _analyze_only(self) -> PipelineResult:
        """Run analyst only (no review)."""
        analyst = AnalystAgent(self.config.analyst)
        self.iteration_count = 1

        logger.info("📝 Running analyst (no review)")

        if not await self._run_analyst(analyst):
            return self._build_result(error="Analyst failed")

        return self._build_result()

    async def _analyze_with_review(self) -> PipelineResult:
        """Run analyst-reviewer feedback loop."""
        analyst = AnalystAgent(self.config.analyst)
        reviewer = ReviewerAgent(self.config.reviewer)

        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1

            # Run analyst
            if not await self._run_analyst(analyst):
                return self._build_result(error="Analyst failed")

            # Skip review on last iteration
            if self.iteration_count >= self.max_iterations:
                logger.info("✅ Max iterations reached, skipping review")
                break

            # Run reviewer and check if should continue
            should_continue = await self._run_reviewer(reviewer)
            if not should_continue:
                break

        return self._build_result()

    async def _analyze_review_judge(self) -> PipelineResult:
        """Run analyst, reviewer, and judge (Phase 3 - not yet implemented)."""
        # For now, just run analyze with review
        result = await self._analyze_with_review()

        # TODO: Add judge step here
        # judge = JudgeAgent(self.config.judge)
        # evaluation = await judge.evaluate(result.analysis_path)
        # result.evaluation = evaluation

        return result

    async def _full_evaluation(self) -> PipelineResult:
        """Run full pipeline including synthesizer (Phase 4 - not yet implemented)."""
        # First run through judge
        result = await self._analyze_review_judge()

        # Then run synthesizer (Phase 4 - not yet implemented)
        # final_result = await self._run_synthesizer(result)

        return result

    async def _run_analyst(self, analyst: AnalystAgent) -> bool:
        """Run analyst for current iteration. Returns True on success."""
        # Pre-create the analysis file for the agent to edit
        analysis_file = self.iterations_dir / f"iteration_{self.iteration_count}.md"
        if not analysis_file.exists():
            _ = analysis_file.write_text("")
            logger.debug(f"Created empty analysis file: {analysis_file}")

        analyst_context = AnalystContext(
            idea_slug=self.slug,
            output_dir=self.output_dir,
            iteration=self.iteration_count,
            system_prompt_override=self.analyst_system_prompt_override,
            tools_override=self.analyst_tools_override,
        )
        analyst_context.run_analytics = self.analytics

        logger.info(
            f"📝 Running analyst iteration {self.iteration_count}/{self.max_iterations}"
        )

        analyst_result = await analyst.process(self.idea, analyst_context)

        if not analyst_result.success:
            logger.error(f"Analyst failed: {analyst_result.error}")
            return False

        # Save analysis iteration
        self._save_analysis_iteration()
        return True

    async def _run_reviewer(self, reviewer: ReviewerAgent) -> bool:
        """Run reviewer and process feedback. Returns True if should continue."""
        # Pre-create the feedback file for the reviewer to edit
        feedback_file = (
            self.iterations_dir
            / f"reviewer_feedback_iteration_{self.iteration_count}.json"
        )
        if not feedback_file.exists():
            _ = feedback_file.write_text("{}")
            logger.debug(f"Created empty feedback file: {feedback_file}")

        reviewer_context = ReviewerContext(
            analysis_path=self.current_analysis_file,
            output_dir=self.output_dir,
            system_prompt_override=self.reviewer_system_prompt_override,
        )
        reviewer_context.run_analytics = self.analytics

        logger.info(f"🔍 Running reviewer for iteration {self.iteration_count}")
        reviewer_result = await reviewer.process("", reviewer_context)

        if not reviewer_result.success:
            logger.error(f"Reviewer failed: {reviewer_result.error}")
            return False

        # Parse reviewer feedback
        feedback_file = (
            self.iterations_dir
            / f"reviewer_feedback_iteration_{self.iteration_count}.json"
        )

        if not feedback_file.exists():
            logger.warning(f"No feedback file found at {feedback_file}")
            return False

        try:
            feedback_text = feedback_file.read_text()
            feedback = json.loads(feedback_text)  # pyright: ignore[reportAny]
            self.last_feedback = feedback

            # Check recommendation
            recommendation = feedback.get("recommendation", "approve")  # pyright: ignore[reportAny]
            if recommendation == "approve":
                logger.info(f"✅ Analysis approved at iteration {self.iteration_count}")
                return False  # Stop iterating
            else:
                logger.info(
                    f"🔄 Analysis needs revision at iteration {self.iteration_count}"
                )
                return True  # Continue iterating

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse feedback: {e}")
            return False

    def _build_result(self, error: str | None = None) -> PipelineResult:
        """Build consistent result dictionary."""
        if error:
            return {
                "success": False,
                "idea": self.idea,
                "slug": self.slug,
                "error": error,
            }

        # Determine final status
        final_status = "completed"
        if self.iteration_count >= self.max_iterations:
            if (
                self.last_feedback
                and self.last_feedback.get("recommendation") != "approve"
            ):
                final_status = "max_iterations_reached"

        return {
            "success": True,
            "idea": self.idea,
            "slug": self.slug,
            "analysis_file": str(self.current_analysis_file)
            if self.current_analysis_file
            else "",
            "iterations_completed": self.iteration_count,
            "final_status": final_status,
        }

    def _save_analysis_iteration(self) -> None:
        """Save the current analysis iteration and update symlink."""
        analysis_file_path = (
            self.iterations_dir / f"iteration_{self.iteration_count}.md"
        )
        self.current_analysis_file = analysis_file_path

        # Update symlink to latest iteration
        symlink = self.output_dir / "analysis.md"
        if symlink.exists() or symlink.is_symlink():
            symlink.unlink()
        symlink.symlink_to(analysis_file_path.relative_to(self.output_dir))
