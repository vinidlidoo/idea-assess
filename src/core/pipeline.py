"""Pipeline orchestration for business idea analysis."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..agents.analyst import AnalystAgent
from ..agents.reviewer import ReviewerAgent
from ..utils.text_processing import create_slug
from .config import AnalysisConfig, AnalystContext, ReviewerContext
from .run_analytics import RunAnalytics
from .types import PipelineMode, PipelineResult

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrates the analysis pipeline for business ideas."""

    def __init__(self, config: AnalysisConfig) -> None:
        """
        Initialize the pipeline with configuration.

        Args:
            config: Analysis configuration object
        """
        self.config = config
        self.analytics: RunAnalytics | None = None

        # Instance variables for run context
        self.idea: str = ""
        self.slug: str = ""
        self.output_dir: Path = Path()
        self.iterations_dir: Path = Path()
        self.max_iterations: int = 3
        self.iteration_count: int = 0
        self.current_analysis_file: Path | None = None
        self.last_feedback: dict[str, Any] | None = None

    async def process(
        self,
        idea: str,
        mode: PipelineMode = PipelineMode.ANALYZE,
        max_iterations_override: int | None = None,
    ) -> PipelineResult:
        """
        Process a business idea through the pipeline based on mode.

        Args:
            idea: Business idea to analyze
            mode: Pipeline execution mode
            max_iterations_override: Optional override for max iterations

        Returns:
            PipelineResult with analysis outcome
        """
        # Store run context as instance variables
        self.idea = idea
        self.slug = create_slug(idea)
        self.output_dir = Path("analyses") / self.slug
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.iterations_dir = self.output_dir / "iterations"
        self.iterations_dir.mkdir(exist_ok=True)

        # Get max iterations from config or override
        if max_iterations_override is not None:
            self.max_iterations = max_iterations_override
        else:
            self.max_iterations = self.config.pipeline.max_iterations_by_mode.get(
                mode, 3
            )

        # Initialize analytics
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp}_{self.slug}"
        self.analytics = RunAnalytics(run_id=run_id, output_dir=Path("logs/runs"))

        # Reset iteration tracking
        self.iteration_count = 0
        self.current_analysis_file = None
        self.last_feedback = None

        logger.info(
            f"🎯 Pipeline started - Mode: {mode.value}, Max iterations: {self.max_iterations}"
        )

        try:
            # Route to appropriate handler based on mode
            handlers = {
                PipelineMode.ANALYZE: self._analyze_only,
                PipelineMode.ANALYZE_AND_REVIEW: self._analyze_with_review,
                PipelineMode.ANALYZE_REVIEW_AND_JUDGE: self._analyze_review_judge,
                PipelineMode.FULL_EVALUATION: self._full_evaluation,
            }

            handler = handlers.get(mode, self._analyze_only)
            result = await handler()

            return result

        finally:
            # Clean up instance variables
            if self.analytics:
                self.analytics.finalize()
            self.analytics = None

    async def _analyze_only(self) -> PipelineResult:
        """Run analyst only (no review)."""
        # Initialize agents
        analyst = AnalystAgent(self.config.analyst)

        # Run analyst once
        self.iteration_count = 1

        analyst_context = AnalystContext(
            idea_slug=self.slug,
            output_dir=self.output_dir,
            iteration=self.iteration_count,
        )
        analyst_context.run_analytics = self.analytics

        logger.info("📝 Running analyst (no review)")

        # Process with analyst
        analyst_result = await analyst.process(self.idea, analyst_context)

        if not analyst_result.success:
            logger.error(f"Analyst failed: {analyst_result.error}")
            return {
                "success": False,
                "idea": self.idea,
                "slug": self.slug,
                "error": analyst_result.error or "Analyst failed",
            }

        # Save analysis
        self._save_analysis_iteration()

        return {
            "success": True,
            "idea": self.idea,
            "slug": self.slug,
            "analysis_file": str(self.current_analysis_file),
            "iterations_completed": 1,
        }

    async def _analyze_with_review(self) -> PipelineResult:
        """Run analyst-reviewer feedback loop."""
        # Initialize agents
        analyst = AnalystAgent(self.config.analyst)
        reviewer = ReviewerAgent(self.config.reviewer)

        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1

            # Run analyst
            analyst_context = AnalystContext(
                idea_slug=self.slug,
                output_dir=self.output_dir,
                iteration=self.iteration_count,
            )
            analyst_context.run_analytics = self.analytics

            logger.info(
                f"📝 Running analyst iteration {self.iteration_count}/{self.max_iterations}"
            )

            analyst_result = await analyst.process(self.idea, analyst_context)

            if not analyst_result.success:
                logger.error(f"Analyst failed: {analyst_result.error}")
                return {
                    "success": False,
                    "idea": self.idea,
                    "slug": self.slug,
                    "error": analyst_result.error or "Analyst failed",
                }

            # Save analysis iteration
            self._save_analysis_iteration()

            # Stop if this is the last iteration (no review needed)
            if self.iteration_count >= self.max_iterations:
                logger.info("✅ Max iterations reached, skipping review")
                break

            # Run reviewer
            reviewer_context = ReviewerContext(
                analysis_path=self.current_analysis_file,
                output_dir=self.output_dir,
            )
            reviewer_context.run_analytics = self.analytics

            logger.info(f"🔍 Running reviewer for iteration {self.iteration_count}")
            reviewer_result = await reviewer.process("", reviewer_context)

            if not reviewer_result.success:
                logger.error(f"Reviewer failed: {reviewer_result.error}")
                # On reviewer failure, keep the current analysis
                break

            # Parse reviewer feedback
            feedback_file = (
                self.iterations_dir
                / f"reviewer_feedback_iteration_{self.iteration_count}.json"
            )

            if feedback_file.exists():
                feedback_text = feedback_file.read_text()
                feedback = json.loads(feedback_text)

                # Check recommendation
                recommendation = feedback.get("recommendation", "approve")
                if recommendation == "approve":
                    logger.info(
                        f"✅ Analysis approved at iteration {self.iteration_count}"
                    )
                    break
                else:
                    logger.info(
                        f"🔄 Analysis rejected at iteration {self.iteration_count}, continuing..."
                    )
                    self.last_feedback = feedback
            else:
                logger.warning(f"No feedback file found at {feedback_file}")
                break

        # Determine final status
        final_status = "completed"
        if self.iteration_count >= self.max_iterations:
            final_status = (
                "max_iterations_reached"
                if self.last_feedback
                and self.last_feedback.get("recommendation") != "approve"
                else "completed"
            )

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

    def _save_analysis_iteration(self) -> None:
        """Save the current analysis iteration and update symlink."""
        analysis_file_path = (
            self.iterations_dir / f"iteration_{self.iteration_count}.md"
        )
        self.current_analysis_file = analysis_file_path

        # Update symlink to latest iteration
        symlink = self.output_dir / "analysis.md"
        if symlink.exists():
            symlink.unlink()
        symlink.symlink_to(analysis_file_path.relative_to(self.output_dir))
