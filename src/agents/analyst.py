"""Analyst agent implementation for business idea analysis."""

import logging
import time
from datetime import datetime
from typing import override

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from claude_code_sdk.types import ResultMessage, AssistantMessage, ToolUseBlock

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import AnalystConfig, AnalystContext
from ..utils.file_operations import load_prompt
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
    async def process(self, input_data: str, context: AnalystContext) -> AgentResult:
        """
        Analyze a business idea.

        Args:
            input_data: The business idea to analyze
            context: Runtime context with tools, revision info, etc.

        Returns:
            AgentResult containing the analysis
        """
        # Setup
        start_time = time.time()

        # Get tools from context
        allowed_tools = self.get_allowed_tools(context)
        use_websearch = "WebSearch" in allowed_tools

        # Reset interrupt state
        self.interrupt_event.clear()

        # Track with RunAnalytics if available
        run_analytics = context.run_analytics if context else None
        iteration = (
            context.revision_context.iteration
            if context and context.revision_context
            else 0
        )

        # Setup interrupt handling
        original_handler = self.setup_interrupt_handler()  # type: ignore[reportAny]

        # Local counters as fallback when run_analytics is None
        local_message_count = 0
        local_search_count = 0

        # Extract idea slug for logging
        idea_slug = create_slug(input_data)
        logger.info(f"Starting analysis for {idea_slug}, iteration {iteration}")

        try:
            # Load the analyst prompt
            system_prompt = load_prompt(self.get_prompt_path(), self.config.prompts_dir)

            # Build websearch note based on whether websearch is enabled
            if use_websearch:
                websearch_note = (
                    f"Use WebSearch efficiently (maximum {self.config.max_websearches} searches) "
                    f"to gather the most critical data: recent market size, key competitor metrics, "
                    f"and major trends."
                )
            else:
                websearch_note = "Note: WebSearch is disabled for this analysis. Use your existing knowledge."

            # Load and format resource constraints template
            resource_template = load_prompt(
                "agents/analyst/partials/resource_constraints.md",
                self.config.prompts_dir,
            )
            resource_note = resource_template.format(
                max_turns=self.config.max_turns,
                max_websearches=self.config.max_websearches if use_websearch else 0,
            )

            # Build user prompt based on whether this is a revision
            if context.revision_context:
                # Load revision-specific user prompt
                revision_template = load_prompt(
                    "agents/analyst/revision.md", self.config.prompts_dir
                )
                user_prompt = revision_template.format(
                    idea=input_data,
                    previous_analysis_file=str(
                        context.revision_context.previous_analysis_path or ""
                    ),
                    feedback_file=str(context.revision_context.feedback_path or ""),
                    resource_note=resource_note,
                    websearch_instruction=websearch_note,
                )
            else:
                # Load and format standard user prompt template
                user_template = load_prompt(
                    "agents/analyst/partials/user_instruction.md",
                    self.config.prompts_dir,
                )
                user_prompt = user_template.format(
                    idea=input_data,
                    resource_note=resource_note,
                    websearch_instruction=websearch_note,
                )

            # Configure options
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=self.config.max_turns,
                allowed_tools=allowed_tools,
            )

            # Create client and analyze
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_prompt)

                async for message in client.receive_response():
                    # Check for interrupt
                    if self.interrupt_event.is_set():
                        await client.interrupt()
                        logger.warning("Analysis interrupted by user")
                        return AgentResult(
                            content="",
                            metadata={
                                "idea": input_data,
                                "interrupted": True,
                            },
                            success=False,
                            error="Analysis interrupted by user",
                        )

                    # Increment local counter
                    local_message_count += 1

                    # Check if this is a WebSearch tool use
                    if isinstance(message, AssistantMessage) and message.content:
                        for block in message.content:
                            if (
                                isinstance(block, ToolUseBlock)
                                and block.name == "WebSearch"
                            ):
                                local_search_count += 1

                    # Track message with RunAnalytics if available
                    if run_analytics:
                        run_analytics.track_message(message, "analyst", iteration)

                    # Use RunAnalytics counts if available, otherwise use local counts
                    message_count = (
                        run_analytics.global_message_count
                        if run_analytics
                        else local_message_count
                    )
                    search_count = (
                        run_analytics.global_search_count
                        if run_analytics
                        else local_search_count
                    )

                    if (
                        message_count > 0
                        and message_count % self.config.message_log_interval == 0
                    ):
                        logger.debug(
                            f"Analysis progress: {message_count} messages processed"
                        )

                    # Check for completion
                    if isinstance(message, ResultMessage):
                        # Get content from ResultMessage directly
                        content = message.result if message.result else ""

                        if content:
                            logger.info(
                                f"Analysis complete: {message_count} messages, {search_count} searches"
                            )

                            return AgentResult(
                                content=content,
                                metadata={
                                    "idea": input_data,
                                    "slug": create_slug(input_data),
                                    "timestamp": datetime.now().isoformat(),
                                    "interrupted": self.interrupt_event.is_set(),
                                },
                                success=True,
                            )
                        break

            # If no ResultMessage was found, log error
            logger.error("Analysis failed: No ResultMessage received")
            return AgentResult(
                content="",
                metadata={"idea": input_data},
                success=False,
                error="Analysis failed to generate content",
            )

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}", exc_info=True)

            return AgentResult(
                content="",
                metadata={"idea": input_data, "iteration": iteration},
                success=False,
                error=str(e),
            )

        finally:
            # Restore original interrupt handler
            self.restore_interrupt_handler(original_handler)

            # Log session statistics
            logger.info(
                "Analysis session complete - "
                + f"Duration: {time.time() - start_time:.1f}s, "
                + f"Iteration: {iteration}"
            )
