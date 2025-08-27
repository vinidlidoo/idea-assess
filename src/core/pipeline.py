"""Pipeline orchestration for business idea analysis."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import logging

from ..agents.analyst import AnalystAgent
from ..agents.reviewer import ReviewerAgent
from ..utils.text_processing import create_slug
from ..utils.file_operations import create_file_from_template
from ..utils.file_operations import append_metadata_to_analysis
from .config import SystemConfig, AnalystConfig, ReviewerConfig
from .types import (
    PipelineMode,
    Success,
    Error,
    PipelineResult,
    AnalystContext,
    ReviewerContext,
)
from .run_analytics import RunAnalytics

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrates the analysis pipeline for business ideas."""

    def __init__(
        self,
        idea: str,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig,
        mode: PipelineMode = PipelineMode.ANALYZE,
        slug_suffix: str | None = None,
    ) -> None:
        """
        Initialize the pipeline with idea and configuration.

        Args:
            idea: Business idea to analyze
            system_config: System configuration
            analyst_config: Analyst agent configuration
            reviewer_config: Reviewer agent configuration
            mode: Pipeline execution mode
            slug_suffix: Optional suffix to append to the slug
        """
        # Core configuration
        self.idea: str = idea
        self.slug: str = create_slug(idea)
        if slug_suffix:
            self.slug = f"{self.slug}-{slug_suffix}"
        self.system_config: SystemConfig = system_config
        self.analyst_config: AnalystConfig = analyst_config
        self.reviewer_config: ReviewerConfig = reviewer_config
        self.mode: PipelineMode = mode

        # Setup output directories
        self.output_dir: Path = system_config.analyses_dir / self.slug
        self.iterations_dir: Path = self.output_dir / "iterations"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.iterations_dir.mkdir(exist_ok=True)

        # Set max iterations based on pipeline mode
        self.max_iterations: int
        if mode == PipelineMode.ANALYZE:
            # Analyst-only mode has no iterations (just one pass)
            self.max_iterations = 1
        else:
            # Review modes use the reviewer's configured max iterations
            self.max_iterations = reviewer_config.max_iterations

        # Runtime state (initialized but will be set during process)
        self.iteration_count: int = 0
        self.current_analysis_file: Path | None = None
        self.last_feedback_file: Path | None = None
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
        analyst = AnalystAgent(self.analyst_config)
        self.iteration_count = 1

        logger.info("📝 Running analyst (no review)")

        if not await self._run_analyst(analyst):
            return self._build_result(error="Analyst failed")

        return self._build_result()

    async def _analyze_with_review(self) -> PipelineResult:
        """Run analyst-reviewer feedback loop."""
        analyst = AnalystAgent(self.analyst_config)
        reviewer = ReviewerAgent(self.reviewer_config)

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

        # Create analysis file from template
        analysis_file = self.iterations_dir / f"iteration_{self.iteration_count}.md"
        if not analysis_file.exists():
            # template_dir is guaranteed to be set after __post_init__
            assert self.system_config.template_dir is not None
            template_path = (
                self.system_config.template_dir / "agents" / "analyst" / "analysis.md"
            )
            create_file_from_template(template_path, analysis_file)
            logger.debug(f"Created analysis file from template: {analysis_file}")

        # Determine previous analysis path for revisions
        previous_analysis = None
        if self.iteration_count > 1:
            previous_analysis = (
                self.iterations_dir / f"iteration_{self.iteration_count - 1}.md"
            )
            if not previous_analysis.exists():
                logger.warning(f"Previous analysis not found: {previous_analysis}")
                previous_analysis = None

        analyst_context = AnalystContext(
            idea_slug=self.slug,
            analysis_output_path=analysis_file,
            previous_analysis_input_path=previous_analysis,
            feedback_input_path=self.last_feedback_file
            if self.iteration_count > 1
            else None,
            iteration=self.iteration_count,
        )
        analyst_context.run_analytics = self.analytics

        logger.info(
            f"📝 Running analyst iteration {self.iteration_count}/{self.max_iterations}"
        )

        analyst_result = await analyst.process(self.idea, analyst_context)

        # Pattern match on result type
        match analyst_result:
            case Error(message=msg):
                logger.error(f"Analyst failed: {msg}")
                return False
            case Success():
                # Append metadata to the completed analysis
                websearch_count = self.analytics.search_count if self.analytics else 0
                webfetch_count = self.analytics.webfetch_count if self.analytics else 0

                append_metadata_to_analysis(
                    analysis_file,
                    self.idea,
                    self.slug,
                    self.iteration_count,
                    websearch_count,
                    webfetch_count,
                )

        # Save analysis iteration
        self._save_analysis_iteration()
        self.current_analysis_file = analysis_file
        return True

    async def _run_reviewer(self, reviewer: ReviewerAgent) -> bool:
        """Run reviewer and process feedback. Returns True if should continue."""

        # Create feedback file from template
        feedback_file = (
            self.iterations_dir
            / f"reviewer_feedback_iteration_{self.iteration_count}.json"
        )
        if not feedback_file.exists():
            # template_dir is guaranteed to be set after __post_init__
            assert self.system_config.template_dir is not None
            template_path = (
                self.system_config.template_dir
                / "agents"
                / "reviewer"
                / "feedback.json"
            )
            create_file_from_template(template_path, feedback_file)
            logger.debug(f"Created feedback file from template: {feedback_file}")

        if not self.current_analysis_file:
            logger.error("No current analysis file to review")
            return False

        reviewer_context = ReviewerContext(
            analysis_input_path=self.current_analysis_file,
            feedback_output_path=feedback_file,
            iteration=self.iteration_count,
        )
        reviewer_context.run_analytics = self.analytics

        logger.info(f"🔍 Running reviewer for iteration {self.iteration_count}")
        reviewer_result = await reviewer.process("", reviewer_context)

        # Pattern match on result type
        match reviewer_result:
            case Error(message=msg):
                logger.error(f"Reviewer failed: {msg}")
                return False
            case Success():
                pass

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
            self.last_feedback_file = feedback_file

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
                "analysis_path": None,
                "feedback_path": None,
                "idea_slug": self.slug,
                "iterations": self.iteration_count,
                "message": error,
            }

        # Get feedback path if it exists
        feedback_path = (
            str(self.last_feedback_file) if self.last_feedback_file else None
        )

        return {
            "success": True,
            "analysis_path": str(self.current_analysis_file)
            if self.current_analysis_file
            else None,
            "feedback_path": feedback_path,
            "idea_slug": self.slug,
            "iterations": self.iteration_count,
            "message": None,
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
