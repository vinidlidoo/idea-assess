"""Pipeline orchestrator that uses file-based communication between agents."""

import json
import logging
from datetime import datetime
from pathlib import Path

# PipelineResult imported from types.py
from ..agents import AnalystAgent
from ..agents.reviewer import ReviewerAgent
from ..core.config import (
    AnalysisConfig,
    AnalystContext,
    ReviewerContext,
    RevisionContext,
)
from ..core.run_analytics import RunAnalytics
from ..core.types import PipelineResult
from ..utils.text_processing import create_slug

# Module-level logger
logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrates the flow of data between agents using file-based communication."""

    config: AnalysisConfig

    def __init__(self, config: AnalysisConfig):
        """
        Initialize the pipeline with configuration.

        Args:
            config: System configuration
        """
        self.config = config

    async def run_analyst_reviewer_loop(
        self,
        idea: str,
        max_iterations: int = 3,
        use_websearch: bool = True,
        tools_override: list[str] | None = None,
    ) -> PipelineResult:
        """
        Run the analyst-reviewer feedback loop using file-based communication.

        Args:
            idea: Business idea to analyze
            max_iterations: Maximum number of iterations
            use_websearch: Enable WebSearch for analyst

        Returns:
            Dictionary containing final analysis and metadata
        """
        # Initialize
        slug = create_slug(idea)
        logger.info(f"🎯 Pipeline started - Max iterations: {max_iterations}")

        # Create RunAnalytics instance for this pipeline run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp}_{slug}"
        run_analytics = RunAnalytics(run_id=run_id, output_dir=Path("logs/runs"))

        # Initialize agents with their specific configs
        analyst = AnalystAgent(self.config.analyst)
        reviewer = ReviewerAgent(self.config.reviewer)

        # Setup directories
        analysis_dir = Path("analyses") / slug
        analysis_dir.mkdir(parents=True, exist_ok=True)
        iterations_dir = analysis_dir / "iterations"
        iterations_dir.mkdir(exist_ok=True)

        # Track iterations
        iteration_count = 0
        current_analysis_file = None
        last_feedback = None

        try:
            while iteration_count < max_iterations:
                iteration_count += 1

                # Create analyst context
                analyst_context = AnalystContext(
                    idea_slug=slug,
                    output_dir=analysis_dir,
                    run_analytics=run_analytics,
                    iteration=iteration_count,
                )

                # Set tools for first iteration only
                if iteration_count == 1:
                    analyst_context.tools_override = tools_override or (
                        ["WebSearch"] if use_websearch else []
                    )
                else:
                    analyst_context.tools_override = []
                    analyst_context.revision_context = RevisionContext(
                        iteration=iteration_count,
                        previous_analysis_path=Path(current_analysis_file or ""),
                        feedback_path=iterations_dir
                        / f"reviewer_feedback_iteration_{iteration_count - 1}.json",
                    )

                # Run analyst
                analyst_result = await analyst.process(idea, analyst_context)

                if not analyst_result.success:
                    raise RuntimeError(f"Analyst failed: {analyst_result.error}")

                # Update symlink to latest analysis
                analysis_file_path = Path(analyst_result.content)
                current_analysis_file = str(analysis_file_path)

                symlink = analysis_dir / "analysis.md"
                symlink.unlink(missing_ok=True)
                symlink.symlink_to(analysis_file_path.relative_to(analysis_dir))

                # Skip reviewer on last iteration (no opportunity to revise)
                if iteration_count >= max_iterations:
                    break

                # Step 2: Get reviewer feedback
                reviewer_context = ReviewerContext(
                    analysis_path=analysis_file_path,
                    run_analytics=run_analytics,
                )
                if iteration_count > 1:
                    reviewer_context.revision_context = analyst_context.revision_context

                reviewer_result = await reviewer.process(
                    "",  # Input data not used by reviewer
                    reviewer_context,
                )

                if not reviewer_result.success:
                    logger.error(f"Reviewer failed: {reviewer_result.error}")
                    # If reviewer fails, accept the analysis by default
                    break

                # Load feedback from file
                feedback_file = Path(reviewer_result.content)
                if not feedback_file.exists():
                    logger.error(f"Feedback file not found: {feedback_file}")
                    break
                with open(feedback_file, "r") as f:
                    feedback = json.load(f)  # pyright: ignore[reportAny]
                last_feedback = feedback  # pyright: ignore[reportAny]

                # Check if we should continue
                recommendation = feedback.get("iteration_recommendation", "accept")  # pyright: ignore[reportAny]
                if recommendation != "reject" or iteration_count >= max_iterations:
                    logger.info(
                        f"🎯 Analysis accepted after {iteration_count} iteration(s)"
                    )
                    break

                # Log rejection reason
                issues = len(feedback.get("critical_issues", []))  # pyright: ignore[reportAny]
                improvements = len(feedback.get("improvements", []))  # pyright: ignore[reportAny]
                logger.info(
                    f"Analysis rejected - {issues} critical issues, {improvements} improvements needed"
                )

            # Prepare final result
            final_status = (
                "max_iterations_reached"
                if last_feedback
                and last_feedback.get("iteration_recommendation") == "reject"  # pyright: ignore[reportAny]
                else "accepted"
            )

            result: PipelineResult = {
                "success": True,
                "idea": idea,
                "slug": slug,
                "file_path": str(analysis_dir / "analysis.md"),
                "iteration_count": iteration_count,
                "final_status": final_status,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"🎯 Pipeline complete - Success after {iteration_count} iteration(s)"
            )

            return result

        except Exception as e:
            logger.error(
                f"Pipeline failed at iteration {iteration_count}: {e}", exc_info=True
            )
            return {  # type: ignore[return-value]
                "success": False,
                "idea": idea,
                "error": str(e),
                "iteration_count": iteration_count,
            }

        finally:
            # Finalize RunAnalytics to write summary
            run_analytics.finalize()
