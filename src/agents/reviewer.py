"""Reviewer agent implementation that reads analysis from file."""

import json
import logging
import time
from typing import override
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from claude_code_sdk.types import ResultMessage

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import (
    ReviewerConfig,
    ReviewerContext,
)
from ..utils.file_operations import load_prompt
from ..utils.json_validator import FeedbackValidator

# Module-level logger
logger = logging.getLogger(__name__)


class ReviewerAgent(BaseAgent[ReviewerConfig, ReviewerContext]):
    """Agent responsible for reviewing analyses by reading from files."""

    def __init__(self, config: ReviewerConfig):
        """
        Initialize the Reviewer agent.

        Args:
            config: Reviewer-specific configuration
        """
        super().__init__(config)

    @property
    @override
    def agent_name(self) -> str:
        """Return the name of this agent."""
        return "Reviewer"

    @override
    async def process(self, input_data: str, context: ReviewerContext) -> AgentResult:
        """
        Review a business analysis by reading from file and write feedback to JSON.

        Args:
            input_data: Ignored (kept for interface compatibility)
            context: Runtime context with analysis_path and other settings

        Returns:
            AgentResult containing path to feedback JSON file
        """
        # Setup
        start_time = time.time()

        # Reset interrupt state
        self.interrupt_event.clear()

        # Track with RunAnalytics if available
        run_analytics = context.run_analytics if context else None
        iteration = (
            context.revision_context.iteration
            if context and context.revision_context
            else 1
        )

        # Setup interrupt handling
        original_handler = self.setup_interrupt_handler()  # type: ignore[reportAny]

        # Local counters as fallback when run_analytics is None
        local_message_count = 0

        # Get tools from context
        allowed_tools = self.get_allowed_tools(context)

        # Validate input path for security (before try block)
        if not context.analysis_path:
            raise ValueError("analysis_path is required in ReviewerContext")

        # Extract idea slug from analysis path for logging
        idea_slug = context.analysis_path.parent.name
        logger.info(f"Starting review for {idea_slug}, iteration {iteration}")

        try:
            # Validate that path is within analyses directory for security
            analysis_path = self._validate_analysis_path(str(context.analysis_path))

            # Load the reviewer prompt with includes
            system_prompt = self.load_system_prompt()
            # Feedback file should already exist (created by pipeline)
            # analysis_path is already in the iterations directory
            iterations_dir = analysis_path.parent
            feedback_file = (
                iterations_dir / f"reviewer_feedback_iteration_{iteration}.json"
            )

            # Verify template file exists
            if not feedback_file.exists():
                logger.error(f"Template feedback file not found: {feedback_file}")
                return AgentResult(
                    content="",
                    metadata={"iteration": iteration},
                    success=False,
                    error=f"Template feedback file not found: {feedback_file}",
                )

            # Load and format review instructions template
            review_template = load_prompt(
                "agents/reviewer/user/review.md",
                self.config.prompts_dir,
            )
            user_prompt = review_template.format(
                iteration=iteration,
                max_iterations=self.config.max_review_iterations,
                analysis_path=analysis_path,
                feedback_file=feedback_file,
            )

            # Configure options
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=self.config.max_turns,
                allowed_tools=allowed_tools,
                permission_mode="acceptEdits",  # Allow agent to edit files directly
            )

            # Create client and review
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_prompt)

                async for message in client.receive_response():
                    # Check for interrupt
                    if self.interrupt_event.is_set():
                        await client.interrupt()
                        logger.warning("Review interrupted by user")
                        return AgentResult(
                            content="",
                            metadata={
                                "iteration": iteration,
                                "interrupted": True,
                            },
                            success=False,
                            error="Review interrupted by user",
                        )

                    # Increment local counter
                    local_message_count += 1

                    # Track message with RunAnalytics if available
                    if run_analytics:
                        run_analytics.track_message(message, "reviewer", iteration)

                    # Use RunAnalytics counts if available, otherwise use local counts
                    message_count = (
                        run_analytics.global_message_count
                        if run_analytics
                        else local_message_count
                    )

                    # Progress tracking
                    if (
                        message_count > 0
                        and message_count % self.config.message_log_interval == 0
                    ):
                        logger.debug(
                            f"Review progress: {message_count} messages processed"
                        )

                    # Process when we hit ResultMessage (end of stream)
                    if isinstance(message, ResultMessage):
                        break

            # Check if the feedback file has content (not just empty template)
            if feedback_file.exists() and feedback_file.stat().st_size > 2:
                # Read and validate the feedback
                feedback_json = self._validate_and_fix_feedback(feedback_file)
                if feedback_json is None:
                    # Validation failed and couldn't be fixed
                    return AgentResult(
                        content="",
                        metadata={"iteration": iteration},
                        success=False,
                        error="Invalid feedback structure could not be fixed",
                    )

                # Create metadata from feedback
                metadata = self._create_feedback_metadata(
                    feedback_json, iteration, feedback_file
                )

                # Log summary
                logger.info(
                    f"Review complete: {metadata['recommendation']} with "
                    + f"{metadata['critical_issues_count']} critical issues, "
                    + f"{metadata['improvements_count']} improvements suggested"
                )

                return AgentResult(
                    content=str(feedback_file),
                    metadata=metadata,
                    success=True,
                )
            else:
                # Reviewer failed to edit feedback file
                return AgentResult(
                    content="",
                    metadata={"iteration": iteration},
                    success=False,
                    error=f"Reviewer failed to edit feedback file: {feedback_file}",
                )

        except Exception as e:
            logger.error(f"Review error: {str(e)}", exc_info=True)

            return AgentResult(
                content="",
                metadata={"iteration": iteration},
                success=False,
                error=str(e),
            )
        finally:
            # Restore original interrupt handler
            self.restore_interrupt_handler(original_handler)

            # Log session statistics
            logger.info(
                "Review session complete - "
                + f"Duration: {time.time() - start_time:.1f}s, "
                + f"Iteration: {iteration}"
            )

    def _validate_and_fix_feedback(
        self, feedback_file: Path
    ) -> dict[str, object] | None:
        """Validate and attempt to fix feedback JSON.

        Args:
            feedback_file: Path to the feedback JSON file

        Returns:
            Validated feedback dict or None if unfixable
        """
        try:
            with open(feedback_file, "r") as f:
                feedback_json = json.load(f)  # pyright: ignore[reportAny]

            validator = FeedbackValidator()
            is_valid, error_msg = validator.validate(feedback_json)  # pyright: ignore[reportAny]

            if not is_valid:
                logger.warning(
                    f"Feedback validation failed: {error_msg}, attempting fix"
                )
                feedback_json = validator.fix_common_issues(feedback_json)  # pyright: ignore[reportAny]
                is_valid, error_msg = validator.validate(feedback_json)

                if is_valid:
                    # Save the fixed feedback
                    with open(feedback_file, "w") as f:
                        json.dump(feedback_json, f, indent=2)
                    logger.info(f"Feedback fixed and saved to {feedback_file}")
                else:
                    logger.error(f"Invalid feedback structure: {error_msg}")
                    return None

            return feedback_json

        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read feedback file: {e}")
            return None

    def _create_feedback_metadata(
        self,
        feedback_json: dict[str, object],
        iteration: int,
        feedback_file: Path,
    ) -> dict[str, object]:
        """Create metadata dict from feedback JSON.

        Args:
            feedback_json: Validated feedback dictionary
            iteration: Current iteration number
            feedback_file: Path to feedback file

        Returns:
            Metadata dictionary for AgentResult
        """

        def safe_list_len(data: object, key: str) -> int:
            """Safely get length of a list field."""
            value = data.get(key, []) if isinstance(data, dict) else []  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            return len(value) if isinstance(value, list) else 0  # pyright: ignore[reportUnknownArgumentType]

        return {
            "iteration": iteration,
            "feedback_file": str(feedback_file),
            "recommendation": feedback_json.get("iteration_recommendation", "unknown"),
            "critical_issues_count": safe_list_len(feedback_json, "critical_issues"),
            "improvements_count": safe_list_len(feedback_json, "improvements"),
            "minor_suggestions_count": safe_list_len(
                feedback_json, "minor_suggestions"
            ),
        }

    def _validate_analysis_path(self, file_path: str) -> Path:
        """Validate that path is within analyses directory.

        Args:
            file_path: Path to validate

        Returns:
            Validated Path object

        Raises:
            ValueError: If path is outside analyses directory
            FileNotFoundError: If file doesn't exist
        """
        # Convert to absolute path and resolve any .. or symlinks
        path = Path(file_path).resolve()

        # Get the analyses directory (relative to project root)
        project_root = Path(__file__).parent.parent.parent
        analyses_dir = (project_root / "analyses").resolve()

        # Check if path is within analyses directory using secure comparison
        # Both paths are already resolved, so we can safely compare
        try:
            # This will raise ValueError if path is not relative to analyses_dir
            _ = path.relative_to(analyses_dir)
        except (ValueError, TypeError) as e:
            # Path is outside analyses directory - this is the security check
            raise ValueError("Invalid path: must be within analyses directory") from e

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"Analysis file not found: {path}")

        return path
