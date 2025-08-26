"""Analyst agent implementation for business idea analysis."""

import logging
import time
from typing import override

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from claude_code_sdk.types import ResultMessage

from ..core.agent_base import BaseAgent
from ..core.types import AgentResult, Success, Error, AnalystContext
from ..core.config import AnalystConfig
from ..utils.file_operations import load_prompt_with_includes
from ..utils.text_processing import create_slug

# Module-level logger
logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent[AnalystConfig, AnalystContext]):
    """Agent responsible for analyzing business ideas."""

    def __init__(self, config: AnalystConfig):
        """
        Initialize the Analyst agent.

        Args:
            config: Analyst-specific configuration
        """
        super().__init__(config)

    @property
    @override
    def agent_name(self) -> str:
        """Return the name of this agent."""
        return "Analyst"

    @override
    async def process(
        self, input_data: str = "", context: AnalystContext | None = None
    ) -> AgentResult:
        """
        Analyze a business idea.

        Args:
            input_data: The business idea to analyze
            context: Runtime context with tools, revision info, etc.

        Returns:
            AgentResult containing the analysis
        """
        # Analyst requires both input_data and context
        if not input_data:
            raise ValueError("Analyst requires input_data (the business idea)")
        if context is None:
            raise ValueError("Analyst requires context")

        # Setup
        start_time = time.time()

        # Get tools from context or config
        allowed_tools = (
            context.tools
            if context and context.tools
            else self.config.get_allowed_tools()
        )

        # Reset interrupt state
        self.interrupt_event.clear()

        # Track with RunAnalytics if available
        run_analytics = context.run_analytics if context else None
        # Get iteration number from context (1-based: 1 = first iteration)
        iteration = context.iteration if context else 1

        # Setup interrupt handling
        original_handler = self.setup_interrupt_handler()  # type: ignore[reportAny]

        # Extract idea slug for logging
        idea_slug = create_slug(input_data)
        logger.info(f"Starting analysis for {idea_slug}, iteration {iteration}")

        try:
            # Load the analyst prompt with includes
            system_prompt = self.load_system_prompt()

            # Build simple tool status variables
            if "WebSearch" in allowed_tools:
                web_tools_status = "enabled"
                web_tools_instruction = (
                    f"Use WebSearch (max {self.config.max_websearches}) to find sources. "
                    f"Use WebFetch to deep-dive promising URLs for detailed data."
                )
            else:
                web_tools_status = "disabled"
                web_tools_instruction = (
                    "Web tools disabled. Use your existing knowledge."
                )

            # Use output path from context
            output_file = context.analysis_output_path

            # Build user prompt based on whether this is a revision
            if context.feedback_input_path:
                # Load revision-specific user prompt (includes constraints.md)
                revision_template = load_prompt_with_includes(
                    "agents/analyst/user/revision.md", self.config.prompts_dir
                )
                # Use the previous analysis path if available, otherwise empty string
                previous_file = (
                    str(context.previous_analysis_input_path)
                    if context.previous_analysis_input_path
                    else ""
                )
                user_prompt = revision_template.format(
                    idea=input_data,
                    previous_analysis_file=previous_file,
                    feedback_file=str(context.feedback_input_path),
                    max_turns=self.config.max_turns,
                    max_websearches=self.config.max_websearches,
                    web_tools_status=web_tools_status,
                    web_tools_instruction=web_tools_instruction,
                    output_file=str(output_file),
                )
            else:
                # Load and format standard user prompt template (includes constraints.md)
                user_template = load_prompt_with_includes(
                    "agents/analyst/user/initial.md",
                    self.config.prompts_dir,
                )
                user_prompt = user_template.format(
                    idea=input_data,
                    max_turns=self.config.max_turns,
                    max_websearches=self.config.max_websearches,
                    web_tools_status=web_tools_status,
                    web_tools_instruction=web_tools_instruction,
                    output_file=str(output_file),
                )

            # Configure options
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=self.config.max_turns,
                allowed_tools=allowed_tools,
                permission_mode="acceptEdits",  # Allow agent to edit files directly
            )
            logger.debug(
                msg=f"Analyst options: allowed_tools={options.allowed_tools}, max_turns={options.max_turns} "
            )

            # Create client and analyze
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_prompt)

                async for message in client.receive_response():
                    # Check for interrupt
                    if self.interrupt_event.is_set():
                        await client.interrupt()
                        logger.warning("Analysis interrupted by user")
                        return Error(message="Analysis interrupted by user")

                    # Track message with RunAnalytics if available
                    if run_analytics:
                        run_analytics.track_message(message, "analyst", iteration)

                    # Get counts from RunAnalytics (always available in practice)
                    message_count = run_analytics.message_count if run_analytics else 0
                    search_count = run_analytics.search_count if run_analytics else 0

                    if message_count > 0 and message_count % 5 == 0:
                        logger.debug(
                            f"Analysis progress: {message_count} messages processed"
                        )

                    # Check for completion
                    if isinstance(message, ResultMessage):
                        # Check if the output file was created
                        if output_file.exists():
                            logger.info(
                                f"Analysis complete: {message_count} messages, {search_count} searches"
                            )
                            logger.info(f"Analysis written to: {output_file}")

                            return Success()
                        else:
                            # Agent didn't create the file - this is an error
                            logger.error(
                                f"Agent failed to write analysis to {output_file}"
                            )
                            return Error(
                                message=f"Agent failed to write analysis to {output_file}"
                            )

            # If no ResultMessage was found, log error
            logger.error("Analysis failed: No ResultMessage received")
            return Error(message="Analysis failed to generate content")

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}", exc_info=True)

            return Error(message=str(e))

        finally:
            # Restore original interrupt handler
            self.restore_interrupt_handler(original_handler)

            # Log session statistics
            logger.info(
                "Analysis session complete - "
                + f"Duration: {time.time() - start_time:.1f}s, "
                + f"Iteration: {iteration}"
            )
