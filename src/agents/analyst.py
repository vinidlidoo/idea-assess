"""Analyst agent implementation for business idea analysis."""

import logging
import signal
import sys
import time
import traceback
from datetime import datetime
from typing import override
import types

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import AnalystConfig, AnalystContext
from ..core.message_processor import MessageProcessor
from ..utils.text_processing import create_slug
from ..utils.file_operations import load_prompt, AnalysisResult

# Module-level logger
logger = logging.getLogger(__name__)


class AnalysisInterrupted(Exception):
    """Raised when analysis is interrupted by user."""

    pass


class AnalystAgent(BaseAgent[AnalystConfig, AnalystContext]):
    """Agent responsible for analyzing business ideas."""

    def __init__(self, config: AnalystConfig):
        """
        Initialize the Analyst agent.

        Args:
            config: Analyst-specific configuration
        """
        super().__init__(config)
        # Removed prompt_version parameter - now comes from config
        # Removed interrupt_event - now in BaseAgent

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

        # Get tools from context
        allowed_tools = self.get_allowed_tools(context)
        use_websearch = "WebSearch" in allowed_tools

        # Get revision context if present
        revision_context: dict[str, str] | None = None
        if context.revision_context:
            revision_context = {
                "previous_analysis_file": str(
                    context.revision_context.previous_analysis_path
                )
                if context.revision_context.previous_analysis_path
                else "",
                "feedback_file": str(context.revision_context.feedback_path)
                if context.revision_context.feedback_path
                else "",
            }

        try:
            result = await self._analyze_idea(
                idea=input_data,
                use_websearch=use_websearch,
                revision_context=revision_context,
                allowed_tools=allowed_tools,
            )

            if result:
                return AgentResult(
                    content=result.content,
                    metadata={
                        "idea": result.idea,
                        "slug": result.slug,
                        "timestamp": result.timestamp.isoformat(),
                        "search_count": result.search_count,
                        "message_count": result.message_count,
                        "duration": result.duration,
                        "interrupted": result.interrupted,
                    },
                    success=True,
                )
            else:
                return AgentResult(
                    content="",
                    metadata={"idea": input_data},
                    success=False,
                    error="Analysis failed to generate content",
                )

        except Exception as e:
            return AgentResult(
                content="", metadata={"idea": input_data}, success=False, error=str(e)
            )

    async def _analyze_idea(
        self,
        idea: str,
        use_websearch: bool = True,
        revision_context: dict[str, str] | None = None,
        allowed_tools: list[str] | None = None,
    ) -> AnalysisResult | None:
        """
        Internal method to analyze a business idea.

        Args:
            idea: One-liner business idea to analyze
            use_websearch: If True, allow WebSearch tool usage
            revision_context: Optional dict with previous_analysis_file and feedback_file paths
            allowed_tools: List of allowed tools for this analysis

        Returns:
            AnalysisResult containing the analysis and metadata, or None if error
        """

        # Setup
        start_time = time.time()
        client: ClaudeSDKClient | None = None

        # Reset interrupt state
        self.interrupt_event.clear()

        # Message processor
        processor = MessageProcessor()

        # Signal handler for interrupts (thread-safe)
        def handle_interrupt(signum: int, frame: types.FrameType | None) -> None:
            # Only set the event - don't modify other state or create tasks
            # The event is thread-safe and will signal the main async context
            _ = signum  # Unused
            _ = frame  # Unused
            self.interrupt_event.set()
            print(
                "\n[ANALYST] Interrupt received, attempting graceful shutdown...",
                file=sys.stderr,
                flush=True,
            )

        # Store original handler for cleanup
        original_handler = signal.getsignal(signal.SIGINT)

        # Register signal handler
        _ = signal.signal(signal.SIGINT, handle_interrupt)

        try:
            # Load the analyst prompt
            system_prompt = load_prompt(self.get_prompt_path(), self.config.prompts_dir)
            # Prompt loaded (redundant logging removed)

            # Craft the user prompt with resource constraints
            websearch_instruction = (
                f"Use WebSearch efficiently (maximum {self.config.max_websearches} searches) to gather "
                + "the most critical data: recent market size, key competitor metrics, and major trends."
                if use_websearch
                else "Note: WebSearch is disabled for this analysis. Use your existing knowledge."
            )

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
            if revision_context:
                # Load revision-specific user prompt
                revision_template = load_prompt(
                    "agents/analyst/revision.md", self.config.prompts_dir
                )
                user_prompt = revision_template.format(
                    idea=idea,
                    previous_analysis_file=revision_context["previous_analysis_file"],
                    feedback_file=revision_context["feedback_file"],
                    resource_note=resource_note,
                    websearch_instruction=websearch_instruction,
                )
            else:
                # Load and format standard user prompt template
                user_template = load_prompt(
                    "agents/analyst/partials/user_instruction.md",
                    self.config.prompts_dir,
                )
                user_prompt = user_template.format(
                    idea=idea,
                    resource_note=resource_note,
                    websearch_instruction=websearch_instruction,
                )

            # Configure options
            # Use the allowed_tools parameter passed from process method
            tools_to_use = allowed_tools if (use_websearch and allowed_tools) else []
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=self.config.max_turns,
                allowed_tools=tools_to_use,
            )

            logger.info(
                f"Starting analysis for: {idea[:50]}..."
                if len(idea) > 50
                else f"Starting analysis for: {idea}"
            )

            # Create client and analyze
            async with ClaudeSDKClient(options=options) as client_instance:
                client = client_instance

                await client.query(user_prompt)

                # Receiving analysis (redundant logging removed)

                async for message in client.receive_response():
                    # Check for interrupt using thread-safe event
                    if self.interrupt_event.is_set():
                        if client:
                            # Safely interrupt the client in async context
                            await client.interrupt()
                        raise AnalysisInterrupted("User interrupted analysis")

                    # Track message
                    processor.track_message(message)

                    # Show progress
                    stats = processor.get_statistics()

                    if stats["message_count"] % self.config.message_log_interval == 0:
                        logger.debug(
                            f"Analysis progress: {stats['message_count']} messages processed"
                        )

                    # Check for completion
                    from claude_code_sdk.types import ResultMessage

                    if isinstance(message, ResultMessage):
                        # Analysis complete (logged after content check)

                        # Get content from ResultMessage
                        extracted_content = processor.extract_content(message)
                        content = extracted_content[0] if extracted_content else ""

                        if content:
                            logger.info(
                                f"Analysis complete: {stats['message_count']} messages, {stats['search_count']} searches"
                            )

                        if content:
                            return AnalysisResult(
                                content=content,
                                idea=idea,
                                slug=create_slug(idea),
                                timestamp=datetime.now(),
                                search_count=stats["search_count"],
                                message_count=stats["message_count"],
                                duration=time.time() - start_time,
                                interrupted=self.interrupt_event.is_set(),
                            )
                        break

            # If no ResultMessage was found, log error and return None
            # (Previously used get_final_content() from buffer as fallback)
            print(
                "[ANALYST] ERROR: No analysis generated (no ResultMessage received)",
                file=sys.stderr,
                flush=True,
            )
            logger.error("Analysis failed: No ResultMessage received")
            return None

        except AnalysisInterrupted as e:
            print(f"\n[ANALYST] WARNING: {e}", file=sys.stderr, flush=True)
            # No partial results available without buffer
            # (Previously used get_final_content() to return partial results)
            return None

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"\n❌ Error during analysis after {duration:.1f}s: {e}"
            print(f"[ANALYST] ERROR: {error_msg}", file=sys.stderr, flush=True)

            # Use centralized SDK error detection
            from ..utils.logger import is_sdk_error

            if is_sdk_error(e):
                logger.error(f"SDK Error in Analyst: {type(e).__name__}: {str(e)}")
            else:
                logger.error(
                    f"Error in Analyst: {str(e)}",
                    exc_info=logger.isEnabledFor(logging.DEBUG),
                )

            if logger.isEnabledFor(logging.DEBUG):
                traceback.print_exc()
            return None

        finally:
            # Reset signal handler to original
            _ = signal.signal(signal.SIGINT, original_handler)

            # Log final statistics
            stats = processor.get_statistics()
            logger.info(
                f"Analysis session complete - Messages: {stats['message_count']}, "
                + f"Searches: {stats['search_count']}, "
                + f"Duration: {time.time() - start_time:.1f}s, "
                + f"Interrupted: {self.interrupt_event.is_set()}"
            )
