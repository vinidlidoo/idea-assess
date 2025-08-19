"""Pipeline orchestrator that uses file-based communication between agents."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import cast

# PipelineResult imported from types.py
from ..agents import AnalystAgent
from ..agents.reviewer import ReviewerAgent, FeedbackProcessor
from ..core.config import (
    AnalysisConfig,
    AnalystContext,
    ReviewerContext,
    RevisionContext,
)
from ..core.types import PipelineResult
from ..utils.text_processing import create_slug
from ..utils.archive_manager import ArchiveManager

# Module-level logger
logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrates the flow of data between agents using file-based communication."""

    config: AnalysisConfig
    feedback_processor: FeedbackProcessor
    archive_manager: ArchiveManager

    def __init__(self, config: AnalysisConfig):
        """
        Initialize the pipeline with configuration.

        Args:
            config: System configuration
        """
        self.config = config
        self.feedback_processor = FeedbackProcessor()
        self.archive_manager = ArchiveManager(max_archives=5)

    # Helper methods for pipeline refactoring
    def _initialize_logging(
        self,
        idea: str,
        max_iterations: int = 3,
    ) -> tuple[str, str]:
        """
        Initialize logging for the pipeline run.

        Args:
            idea: Business idea being analyzed
            max_iterations: Maximum number of iterations
            use_websearch: Whether WebSearch is enabled

        Returns:
            Tuple of (run_id, slug)
        """
        from datetime import datetime

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = create_slug(idea)

        logger.info(f"🎯 Pipeline started - Max iterations: {max_iterations}")

        return run_id, slug

    def _setup_directories(self, slug: str, debug: bool) -> tuple[Path, Path]:
        """
        Setup directories for the analysis.

        Args:
            slug: Slugified idea name
            debug: Whether in debug mode

        Returns:
            Tuple of (analysis_dir, iterations_dir)
        """
        # Setup file paths
        analysis_dir = Path("analyses") / slug
        analysis_dir.mkdir(parents=True, exist_ok=True)

        # Archive existing files before starting new run
        run_type = "test" if debug else "production"
        _ = self.archive_manager.archive_current_analysis(
            analysis_dir, run_type=run_type
        )

        # Create iterations directory for this run
        iterations_dir = analysis_dir / "iterations"
        iterations_dir.mkdir(exist_ok=True)

        return analysis_dir, iterations_dir

    def _find_feedback_file(
        self,
        iterations_dir: Path,
        iteration_count: int,
        analysis_dir: Path,
    ) -> Path | None:
        """
        Find the appropriate feedback file for the current iteration.

        Args:
            iterations_dir: Directory containing iteration files
            iteration_count: Current iteration number
            analysis_dir: Main analysis directory

        Returns:
            Path to feedback file if found, None otherwise
        """
        # Look for the previous iteration's feedback
        # The reviewer creates files named reviewer_feedback_iteration_{n}.json
        latest_feedback_file = (
            iterations_dir / f"reviewer_feedback_iteration_{iteration_count - 1}.json"
        )

        if not latest_feedback_file.exists():
            # Log warning about missing file before fallback
            logger.warning(f"Feedback file missing: {latest_feedback_file}")
            # Fallback to main feedback file
            latest_feedback_file = analysis_dir / "reviewer_feedback.json"
            if not latest_feedback_file.exists():
                # Critical error - no feedback available for revision
                logger.error(
                    f"No feedback file found for iteration {iteration_count}",
                )
                return None

        return latest_feedback_file

    def _save_analysis_files(
        self,
        analysis: str,
        iteration_count: int,
        analysis_dir: Path,
        iterations_dir: Path,
    ) -> Path:
        """
        Save analysis to both iteration file and main file.

        Args:
            analysis: Analysis content to save
            iteration_count: Current iteration number
            analysis_dir: Main analysis directory
            iterations_dir: Iterations directory
            logger: Optional logger

        Returns:
            Path to the saved iteration file
        """
        # Save iteration in iterations directory
        iteration_file = iterations_dir / f"iteration_{iteration_count}.md"
        with open(iteration_file, "w") as f:
            _ = f.write(analysis)

        # Also save/update main analysis.md (overwritten each iteration)
        main_analysis = analysis_dir / "analysis.md"
        with open(main_analysis, "w") as f:
            _ = f.write(analysis)

        logger.debug(f"Analysis saved: {iteration_file}")

        return iteration_file

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
        # Initialize logging
        _, slug = self._initialize_logging(idea, max_iterations)

        # Initialize agents with their specific configs
        analyst = AnalystAgent(self.config.analyst)
        reviewer = ReviewerAgent(self.config.reviewer)

        # Setup directories
        analysis_dir, iterations_dir = self._setup_directories(
            slug, logger.isEnabledFor(logging.DEBUG)
        )

        # Track iterations
        iteration_count = 0
        current_analysis = None
        current_analysis_file = None
        feedback_history: list[dict[str, object]] = []
        iteration_results: list[dict[str, object]] = []

        try:
            while iteration_count < max_iterations:
                iteration_count += 1

                logger.info(f"Starting iteration {iteration_count}")

                # Step 1: Generate or refine analysis
                if iteration_count == 1:
                    # Initial analysis
                    analyst_input = idea
                    revision_context = None
                else:
                    # Refined analysis based on feedback
                    # Pass the ORIGINAL idea, not revision instructions
                    analyst_input = idea

                    # Find the appropriate feedback file
                    latest_feedback_file = self._find_feedback_file(
                        iterations_dir, iteration_count, analysis_dir
                    )
                    if not latest_feedback_file:
                        # No feedback file found - return error
                        return {
                            "success": False,
                            "error": f"No feedback file found for iteration {iteration_count}",
                            "idea": idea,
                            "slug": slug,
                            "iteration_count": iteration_count,
                            "timestamp": datetime.now().isoformat(),
                        }

                    # Pass revision context via kwargs
                    revision_context = {
                        "previous_analysis_file": str(current_analysis_file),
                        "feedback_file": str(latest_feedback_file),
                    }

                # Create analyst context
                analyst_context = AnalystContext(
                    idea_slug=slug,
                    output_dir=analysis_dir,
                )

                # Set tools based on override or websearch flag and iteration
                if tools_override is not None:
                    # Use explicit override from CLI
                    analyst_context.tools_override = (
                        tools_override if iteration_count == 1 else []
                    )
                elif use_websearch and iteration_count == 1:
                    analyst_context.tools_override = ["WebSearch"]
                else:
                    analyst_context.tools_override = []  # No tools after first iteration

                # Add revision context if this is a revision
                if revision_context:
                    analyst_context.revision_context = RevisionContext(
                        iteration=iteration_count,
                        previous_analysis_path=Path(
                            revision_context["previous_analysis_file"]
                        ),
                        feedback_path=Path(revision_context["feedback_file"]),
                    )

                # Run analyst with context
                analyst_result = await analyst.process(
                    analyst_input,  # Always the original idea
                    analyst_context,
                )

                if not analyst_result.success:
                    logger.error(f"Analyst failed: {analyst_result.error}")
                    # Return failure result immediately
                    return {
                        "success": False,
                        "error": f"Analyst failed: {analyst_result.error}",
                        "idea": idea,
                        "slug": slug,
                        "iteration_count": iteration_count,
                        "timestamp": datetime.now().isoformat(),
                    }

                current_analysis = analyst_result.content

                # Save analysis to files
                iteration_file = self._save_analysis_files(
                    current_analysis,
                    iteration_count,
                    analysis_dir,
                    iterations_dir,
                )
                current_analysis_file = str(iteration_file)

                # Save iteration result
                iteration_results.append(
                    {
                        "iteration": iteration_count,
                        "analysis_file": str(iteration_file),
                        "analysis_length": len(current_analysis),
                        "metadata": analyst_result.metadata,
                    }
                )

                # Step 2: Get reviewer feedback
                # Create reviewer context
                reviewer_context = ReviewerContext(
                    analysis_path=iteration_file,
                )

                # Add revision context if available
                if revision_context:
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
                feedback_file = (
                    reviewer_result.content
                )  # This should be the path to feedback file
                feedback = self.feedback_processor.load_feedback(feedback_file)
                feedback_history.append(cast(dict[str, object], feedback))

                # Also save/update main reviewer_feedback.json for easy access
                main_feedback = analysis_dir / "reviewer_feedback.json"
                with open(main_feedback, "w") as f:
                    json.dump(feedback, f, indent=2)

                    # Iteration complete (logged with milestone below)
                # Also log as milestone for visibility
                recommendation = feedback.get("iteration_recommendation", "unknown")
                critical_issues_raw = feedback.get("critical_issues", [])
                issues = (
                    len(critical_issues_raw)
                    if isinstance(critical_issues_raw, list)
                    else 0
                )
                logger.info(
                    f"🎯 Iteration {iteration_count} complete - "
                    + f"Recommendation: {recommendation}, Critical issues: {issues}"
                )

                # Check if we should continue (reviewer rejected the analysis)
                if not self.feedback_processor.should_continue_iteration(
                    feedback, iteration_count
                ):
                    # Analysis accepted (logged with milestone below)
                    logger.info(
                        f"🎯 Analysis accepted after {iteration_count} iteration(s)"
                    )
                    break
                else:
                    critical_issues = feedback.get("critical_issues", [])
                    improvements = feedback.get("improvements", [])
                    critical_count = (
                        len(critical_issues) if isinstance(critical_issues, list) else 0
                    )
                    improvements_count = (
                        len(improvements) if isinstance(improvements, list) else 0
                    )
                    logger.info(
                        f"Analysis rejected - {critical_count} critical issues, "
                        + f"{improvements_count} improvements needed"
                    )

            # Prepare final result
            # Determine if analysis was accepted or hit max iterations
            final_status = "accepted"
            if feedback_history:
                last_recommendation = feedback_history[-1].get(
                    "iteration_recommendation"
                )
                if (
                    last_recommendation == "reject"
                    and iteration_count >= max_iterations
                ):
                    final_status = "max_iterations_reached"

            result = {
                "success": True,
                "idea": idea,
                "slug": slug,
                "final_analysis_file": current_analysis_file,
                "final_analysis": current_analysis,
                "iteration_count": iteration_count,
                "final_status": final_status,
                "iterations": iteration_results,
                "feedback_history": feedback_history,
                "timestamp": datetime.now().isoformat(),
            }

            # Files are already saved in clean structure (analysis.md, reviewer_feedback.json)
            if current_analysis:
                result["file_path"] = str(analysis_dir / "analysis.md")

                # Save consolidated metadata
                metadata = self.archive_manager.create_metadata(
                    cast(dict[str, object], result),
                    feedback_history[-1] if feedback_history else None,
                    iteration_results,
                )
                metadata_path = analysis_dir / "metadata.json"
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                result["metadata_path"] = str(metadata_path)

                # Save iteration history (for compatibility)
                history_path = analysis_dir / "iteration_history.json"
                with open(history_path, "w") as f:
                    json.dump(
                        {
                            "iterations": iteration_results,
                            "feedback": feedback_history,
                            "final_status": final_status,
                            "idea": idea,
                        },
                        f,
                        indent=2,
                    )
                result["history_path"] = str(history_path)

            logger.info(
                f"🎯 Pipeline complete - Success after {iteration_count} iteration(s)"
            )

            return cast(PipelineResult, cast(object, result))

        except Exception as e:
            error_context = (
                f"Pipeline failed at iteration {iteration_count}/{max_iterations}"
            )
            if current_analysis_file:
                error_context += f" (last file: {current_analysis_file})"

            logger.error(
                f"{type(e).__name__}: {str(e)}",
                exc_info=True,
            )

            print(f"\n❌ {error_context}: {e}")
            return cast(
                PipelineResult,
                cast(
                    object,
                    {
                        "success": False,
                        "idea": idea,
                        "error": str(e),
                        "error_context": error_context,
                        "iteration_count": iteration_count,
                        "iterations": iteration_results,
                        "feedback_history": feedback_history,
                    },
                ),
            )

        finally:
            # Log final status
            final_result = locals().get("result", None)
            if final_result is not None:
                success = bool(final_result.get("success", False))
                if success:
                    logger.info("Pipeline completed successfully")
                else:
                    logger.error("Pipeline failed")
            else:
                logger.error("Pipeline failed with no result")


class SimplePipeline:
    """Simplified pipeline for single-agent operations."""

    @staticmethod
    async def run_analyst_only(
        idea: str,
        config: AnalysisConfig,
        use_websearch: bool = True,
        tools_override: list[str] | None = None,
    ) -> PipelineResult:
        """
        Run analyst without reviewer feedback.

        Args:
            idea: Business idea to analyze
            config: System configuration
            use_websearch: Enable WebSearch

        Returns:
            Analysis result dictionary
        """
        # Initialize archive manager
        archive_manager = ArchiveManager(max_archives=5)

        # Initialize analyst with its config
        analyst = AnalystAgent(config.analyst)

        # Create analyst context
        slug = create_slug(idea)
        analyst_context = AnalystContext(
            idea_slug=slug,
            tools_override=tools_override
            if tools_override is not None
            else (["WebSearch"] if use_websearch else []),
        )

        # Run analyst with context
        result = await analyst.process(idea, analyst_context)

        if result.success:
            # slug already created above

            # Setup file paths
            analysis_dir = Path("analyses") / slug
            analysis_dir.mkdir(parents=True, exist_ok=True)

            # Archive existing files before saving new one
            run_type = "test" if logger.isEnabledFor(logging.DEBUG) else "production"
            _ = archive_manager.archive_current_analysis(
                analysis_dir, run_type=run_type
            )

            # Save to clean file structure (no timestamp)
            analysis_path = analysis_dir / "analysis.md"
            with open(analysis_path, "w") as f:
                _ = f.write(result.content)

            # Create metadata
            analysis_result: dict[str, object] = {
                "final_status": "completed",
                "word_count": len(result.content.split()),
                "character_count": len(result.content),
            }
            metadata = archive_manager.create_metadata(analysis_result)
            metadata_path = analysis_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return cast(
                PipelineResult,
                cast(
                    object,
                    {
                        "success": True,
                        "idea": idea,
                        "slug": slug,
                        "analysis": result.content,
                        "file_path": str(analysis_path),
                        "metadata": result.metadata,
                    },
                ),
            )
        else:
            return cast(
                PipelineResult,
                cast(
                    object,
                    {
                        "success": False,
                        "idea": idea,
                        "error": result.error or "Unknown error",
                    },
                ),
            )
