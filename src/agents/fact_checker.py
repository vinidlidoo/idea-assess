"""FactChecker agent implementation for verifying claims and citations."""

import json
import logging
import time
from typing import override
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from claude_code_sdk.types import ResultMessage

from ..core.agent_base import BaseAgent
from ..core.types import AgentResult, Success, Error, FactCheckContext
from ..core.config import FactCheckerConfig
from ..utils.file_operations import load_prompt
from ..utils.json_validator import JsonResponseValidator

# Module-level logger
logger = logging.getLogger(__name__)


class FactCheckerAgent(BaseAgent[FactCheckerConfig, FactCheckContext]):
    """Agent responsible for fact-checking claims and citations in analyses."""

    def __init__(self, config: FactCheckerConfig):
        """
        Initialize the FactChecker agent.

        Args:
            config: FactChecker-specific configuration
        """
        super().__init__(config)

    @property
    @override
    def agent_name(self) -> str:
        """Return the name of this agent."""
        return "FactChecker"

    @override
    async def process(
        self, input_data: str = "", context: FactCheckContext | None = None
    ) -> AgentResult:
        """
        Fact-check an analysis for accuracy of claims and citations.

        Args:
            input_data: Not used for fact-checker (reads from file)
            context: Runtime context with analysis path and output path

        Returns:
            AgentResult containing Success or Error
        """
        # FactChecker requires context
        if context is None:
            raise ValueError("FactChecker requires context with analysis_path")

        # Setup
        start_time = time.time()

        # Reset interrupt state
        self.interrupt_event.clear()

        # Track with RunAnalytics if available
        run_analytics = context.run_analytics if context else None
        iteration = context.iteration if context else 1

        # Setup interrupt handling
        original_handler = self.setup_interrupt_handler()  # type: ignore[reportAny]

        # Get tools from context or config
        allowed_tools = (
            context.tools
            if context and context.tools
            else self.config.get_allowed_tools()
        )

        # Validate input path for security (before try block)
        if not context.analysis_input_path:
            raise ValueError("analysis_input_path is required in FactCheckContext")

        # Extract idea slug from analysis path for logging
        idea_slug = context.analysis_input_path.parent.name
        logger.info(f"Starting fact-check for {idea_slug}, iteration {iteration}")

        try:
            # Validate that path is within analyses directory for security
            analysis_path = self._validate_analysis_path(
                str(context.analysis_input_path)
            )

            # Load the fact-checker prompt with includes
            system_prompt = self.load_system_prompt()
            # Use fact-check output path from context
            fact_check_file = context.fact_check_output_path

            # Fact-check file should be pre-created by pipeline

            # Load and format fact-check instructions template
            fact_check_template = load_prompt(
                "agents/factchecker/user/fact-check.md",
                self.config.prompts_dir,
            )
            user_prompt = fact_check_template.format(
                iteration=iteration,
                max_iterations=context.max_iterations,
                analysis_path=analysis_path,
                fact_check_file=fact_check_file,
            )

            # Configure options
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=self.config.max_turns,
                allowed_tools=allowed_tools,
                permission_mode="acceptEdits",  # Allow agent to edit files directly
            )
            logger.debug(
                msg=f"FactChecker options: allowed_tools={options.allowed_tools}, max_turns={options.max_turns}"
            )

            # Create client and fact-check
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_prompt)

                async for message in client.receive_response():
                    # Check for interrupt
                    if self.interrupt_event.is_set():
                        await client.interrupt()
                        logger.warning("Fact-check interrupted by user")
                        return Error(message="Fact-check interrupted by user")

                    # Track message with RunAnalytics if available
                    if run_analytics:
                        run_analytics.track_message(message, "fact_checker", iteration)

                    # Get counts from RunAnalytics (always available in practice)
                    message_count = run_analytics.message_count if run_analytics else 0

                    # Progress tracking
                    if message_count > 0 and message_count % 5 == 0:
                        logger.debug(
                            f"Fact-check progress: {message_count} messages processed"
                        )

                    # Process when we hit ResultMessage (end of stream)
                    if isinstance(message, ResultMessage):
                        break

            # Check if the fact-check file has content (not just empty template)
            if fact_check_file.exists() and fact_check_file.stat().st_size > 2:
                # Read and validate the fact-check
                fact_check_json = self._validate_and_fix_fact_check(fact_check_file)
                if fact_check_json is None:
                    # Validation failed and couldn't be fixed
                    return Error(
                        message="Invalid fact-check structure could not be fixed"
                    )

                # Create metadata from fact-check
                metadata = self._create_fact_check_metadata(
                    fact_check_json, iteration, fact_check_file
                )

                # Log summary
                logger.info(
                    f"Fact-check complete: {metadata['recommendation']} with "
                    + f"{metadata['issues_count']} issues identified"
                )

                return Success()
            else:
                # FactChecker failed to edit fact-check file
                return Error(
                    message=f"FactChecker failed to edit fact-check file: {fact_check_file}"
                )

        except Exception as e:
            logger.error(f"Fact-check error: {str(e)}", exc_info=True)

            return Error(message=str(e))
        finally:
            # Restore original interrupt handler
            self.restore_interrupt_handler(original_handler)

            # Log session statistics
            logger.info(
                "Fact-check session complete - "
                + f"Duration: {time.time() - start_time:.1f}s, "
                + f"Iteration: {iteration}"
            )

    def _validate_and_fix_fact_check(
        self, fact_check_file: Path
    ) -> dict[str, object] | None:
        """Validate and attempt to fix fact-check JSON.

        Args:
            fact_check_file: Path to the fact-check JSON file

        Returns:
            Validated fact-check dict or None if unfixable
        """
        try:
            with open(fact_check_file, "r") as f:
                fact_check_json = json.load(f)  # pyright: ignore[reportAny]

            validator = JsonResponseValidator(schema_type="fact_checker")
            is_valid, error_msg = validator.validate(fact_check_json)  # pyright: ignore[reportAny]

            if not is_valid:
                logger.warning(
                    f"Fact-check validation failed: {error_msg}, attempting fix"
                )
                fact_check_json = validator.fix_common_issues(fact_check_json)  # pyright: ignore[reportAny]
                is_valid, error_msg = validator.validate(fact_check_json)

                if is_valid:
                    # Save the fixed fact-check
                    with open(fact_check_file, "w") as f:
                        json.dump(fact_check_json, f, indent=2)
                    logger.info(f"Fact-check fixed and saved to {fact_check_file}")
                else:
                    logger.error(f"Invalid fact-check structure: {error_msg}")
                    return None

            return fact_check_json

        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read fact-check file: {e}")
            return None

    def _create_fact_check_metadata(
        self,
        fact_check_json: dict[str, object],
        iteration: int,
        fact_check_file: Path,
    ) -> dict[str, object]:
        """Create metadata dict from fact-check JSON.

        Args:
            fact_check_json: Validated fact-check dictionary
            iteration: Current iteration number
            fact_check_file: Path to fact-check file

        Returns:
            Metadata dictionary for logging
        """

        def safe_list_len(data: object, key: str) -> int:
            """Safely get length of a list field."""
            value = data.get(key, []) if isinstance(data, dict) else []  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            return len(value) if isinstance(value, list) else 0  # pyright: ignore[reportUnknownArgumentType]

        return {
            "iteration": iteration,
            "fact_check_file": str(fact_check_file),
            "recommendation": fact_check_json.get(
                "iteration_recommendation", "unknown"
            ),
            "issues_count": safe_list_len(fact_check_json, "issues"),
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
