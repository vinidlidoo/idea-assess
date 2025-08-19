"""Reviewer agent implementation that reads analysis from file."""

import json
import logging
from typing import override
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..core.agent_base import BaseAgent, AgentResult
from ..core.types import FeedbackDict
from ..core.config import (
    ReviewerConfig,
    ReviewerContext,
)
from ..core.message_processor import MessageProcessor
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
        # Removed prompt_version - now comes from config

    @property
    @override
    def agent_name(self) -> str:
        """Return the name of this agent."""
        return "Reviewer"

    # get_prompt_path() inherited from BaseAgent - uses dynamic path resolution

    # Removed get_allowed_tools override - now uses BaseAgent implementation
    # which checks context.tools_override or config.default_tools

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
        # Get iteration count from revision context if available
        iteration_count = 1
        if context.revision_context:
            iteration_count = context.revision_context.iteration

        # Extract idea slug from analysis path
        if context.analysis_path:
            idea_slug = context.analysis_path.parent.name
        else:
            idea_slug = "unknown"

        logger.info(f"Starting review for {idea_slug}, iteration {iteration_count}")

        try:
            # Validate input path for security
            if not context.analysis_path:
                raise ValueError("analysis_path is required in ReviewerContext")
            analysis_path = self._validate_analysis_path(str(context.analysis_path))

            # Load the reviewer prompt
            prompt_content = load_prompt(
                self.get_prompt_path(),
                self.config.prompts_dir or Path("config/prompts"),
            )
            # Save to both iterations directory and main directory
            iterations_dir = analysis_path.parent / "iterations"
            if iterations_dir.exists():
                # Use consistent naming: reviewer_feedback_iteration_{n}.json
                feedback_file = (
                    iterations_dir
                    / f"reviewer_feedback_iteration_{iteration_count}.json"
                )
            else:
                # Fallback to old structure (same name pattern)
                feedback_file = (
                    analysis_path.parent
                    / f"reviewer_feedback_iteration_{iteration_count}.json"
                )

            # Load review instructions template and format it
            review_template = load_prompt(
                "reviewer_instructions.md",
                self.config.prompts_dir or Path("config/prompts"),
            )
            review_prompt = review_template.format(
                iteration_count=iteration_count,
                max_iterations=self.config.max_review_iterations,
                analysis_path=analysis_path,
                feedback_file=feedback_file,
            )

            # Setup Claude SDK options with tools enabled
            options = ClaudeCodeOptions(
                system_prompt=prompt_content,
                max_turns=self.config.max_turns,  # Allow multiple turns for reading, analyzing, writing
                allowed_tools=["Read", "Write"],  # Enable file operations
                permission_mode="default",  # Use default permission mode for automation
            )

            # Initialize message processor
            processor = MessageProcessor()

            # Query Claude for review
            # Review start already logged above in debug mode

            async with ClaudeSDKClient(options=options) as client:
                await client.query(review_prompt)

                # Processing review (redundant logging removed)

                message_count = 0

                async for message in client.receive_response():
                    message_count += 1
                    # Raw message tracking (redundant debug logging removed)

                    processor.track_message(message)

                    # Progress tracking
                    if message_count % self.config.message_log_interval == 0:
                        logger.debug(
                            f"Review progress: {message_count} messages processed"
                        )

                    from claude_code_sdk.types import AssistantMessage, ResultMessage

                    # Message content tracking (redundant debug logging removed)

                    # Check if review is complete
                    if isinstance(message, AssistantMessage):
                        # Review completion marker detection removed
                        # (was previously used for flow control)
                        pass

                    # Process when we hit ResultMessage (end of stream)
                    if isinstance(message, ResultMessage):
                        # Stream ended (redundant logging removed)
                        break

            # Check if the feedback file was created
            if feedback_file.exists():
                # Read the feedback to verify and get metadata
                with open(feedback_file, "r") as f:
                    feedback_json = json.load(f)

                # Validate the feedback structure
                validator = FeedbackValidator()
                is_valid, error_msg = validator.validate(feedback_json)

                if not is_valid:
                    # Try to fix common issues
                    logger.warning(
                        f"Feedback validation failed: {error_msg}, attempting fix"
                    )

                    feedback_json = validator.fix_common_issues(feedback_json)
                    is_valid, error_msg = validator.validate(feedback_json)

                    if is_valid:
                        # Save the fixed feedback
                        with open(feedback_file, "w") as f:
                            json.dump(feedback_json, f, indent=2)
                        logger.info(f"Feedback fixed and saved to {feedback_file}")
                    else:
                        # Still invalid after fix attempt
                        logger.error(f"Invalid feedback structure: {error_msg}")
                        return AgentResult(
                            content="",
                            metadata={
                                "iteration": iteration_count,
                                "validation_error": error_msg,
                            },
                            success=False,
                            error=f"Invalid feedback structure: {error_msg}",
                        )

                # Log summary of feedback
                recommendation = feedback_json.get(
                    "iteration_recommendation", "unknown"
                )
                critical_issues = feedback_json.get("critical_issues", [])
                critical_count = (
                    len(critical_issues) if isinstance(critical_issues, list) else 0
                )

                improvements_count = (
                    len(feedback_json.get("improvements", []))
                    if isinstance(feedback_json.get("improvements", []), list)
                    else 0
                )
                logger.info(
                    f"Review complete: {recommendation} with {critical_count} critical issues, "
                    + f"{improvements_count} improvements suggested"
                )

                return AgentResult(
                    content=str(feedback_file),  # Return the path to the feedback file
                    metadata={
                        "iteration": iteration_count,
                        "feedback_file": str(feedback_file),
                        "recommendation": feedback_json.get(
                            "iteration_recommendation", "unknown"
                        ),
                        "critical_issues_count": len(
                            feedback_json.get("critical_issues", [])
                        )
                        if isinstance(feedback_json.get("critical_issues", []), list)
                        else 0,
                        "improvements_count": len(feedback_json.get("improvements", []))
                        if isinstance(feedback_json.get("improvements", []), list)
                        else 0,
                        "minor_suggestions_count": len(
                            feedback_json.get("minor_suggestions", [])
                        )
                        if isinstance(feedback_json.get("minor_suggestions", []), list)
                        else 0,
                    },
                    success=True,
                )
            else:
                # Reviewer failed to create feedback file
                return AgentResult(
                    content="",
                    metadata={"iteration": iteration_count},
                    success=False,
                    error="Reviewer did not create the expected feedback file",
                )

        except Exception as e:
            logger.error(f"Review error: {str(e)}", exc_info=True)

            return AgentResult(
                content="",
                metadata={"iteration": iteration_count},
                success=False,
                error=str(e),
            )
        finally:
            pass  # Logger finalization handled in pipeline


class FeedbackProcessor:
    """Utility class to process reviewer feedback and apply it to analyses."""

    @staticmethod
    def load_feedback(feedback_file: str) -> FeedbackDict | dict[str, object]:
        """
        Load and validate JSON feedback from file.

        Args:
            feedback_file: Path to the feedback JSON file

        Returns:
            Parsed and validated feedback dictionary
        """
        try:
            with open(feedback_file, "r") as f:
                feedback = json.load(f)

            # Validate the loaded feedback
            validator = FeedbackValidator()
            is_valid, error_msg = validator.validate(feedback)

            if not is_valid:
                # Try to fix common issues
                feedback = validator.fix_common_issues(feedback)
                is_valid, error_msg = validator.validate(feedback)

                if not is_valid:
                    # Return error indicator if still invalid
                    return {"error": f"Invalid feedback structure: {error_msg}"}

            return feedback

        except (json.JSONDecodeError, FileNotFoundError) as e:
            return {"error": f"Failed to load feedback: {str(e)}"}

    @staticmethod
    def should_continue_iteration(
        feedback: FeedbackDict | dict[str, object], iteration_count: int
    ) -> bool:
        """
        Determine if another iteration is needed based on feedback.

        Args:
            feedback: Parsed feedback dictionary
            iteration_count: Current iteration number

        Returns:
            True if another iteration should occur (reviewer rejected)
        """
        # Check iteration limit
        if iteration_count >= 3:
            return False

        # Check recommendation - only continue if rejected
        recommendation = feedback.get("iteration_recommendation", "accept")
        return recommendation == "reject"

    @staticmethod
    def format_feedback_for_analyst(feedback: FeedbackDict | dict[str, object]) -> str:
        """
        Format reviewer feedback into instructions for the analyst.

        Args:
            feedback: Parsed feedback dictionary

        Returns:
            Formatted instructions for analyst to incorporate
        """
        instructions: list[str] = []

        # Add overall assessment
        if "overall_assessment" in feedback:
            instructions.append(f"OVERALL ASSESSMENT: {feedback['overall_assessment']}")
            instructions.append("")

        # Add critical issues that must be addressed
        critical_issues = feedback.get("critical_issues")
        if isinstance(critical_issues, list):
            instructions.append("CRITICAL ISSUES TO ADDRESS:")
            for issue in critical_issues:
                if isinstance(issue, dict):
                    instructions.append(
                        f"- {issue.get('section', 'N/A')}: {issue.get('issue', 'N/A')}"
                    )
                    instructions.append(
                        f"  Suggestion: {issue.get('suggestion', 'N/A')}"
                    )
            instructions.append("")

        # Add important improvements
        improvements = feedback.get("improvements")
        if isinstance(improvements, list):
            instructions.append("IMPORTANT IMPROVEMENTS:")
            for improvement in improvements:
                if isinstance(improvement, dict):
                    instructions.append(
                        f"- {improvement.get('section', 'N/A')}: {improvement.get('issue', 'N/A')}"
                    )
                    instructions.append(
                        f"  Suggestion: {improvement.get('suggestion', 'N/A')}"
                    )
            instructions.append("")

        # Add minor suggestions if no critical issues
        minor_suggestions = feedback.get("minor_suggestions")
        if not feedback.get("critical_issues") and isinstance(minor_suggestions, list):
            instructions.append("MINOR ENHANCEMENTS:")
            for suggestion in minor_suggestions[:3]:  # Limit to top 3
                if isinstance(suggestion, dict):
                    instructions.append(
                        f"- {suggestion.get('section', 'N/A')}: {suggestion.get('suggestion', 'N/A')}"
                    )
            instructions.append("")

        return "\n".join(instructions)
