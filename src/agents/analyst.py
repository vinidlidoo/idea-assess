"""Analyst agent implementation for business idea analysis."""

import signal
import sys
import threading
import time
import traceback
from datetime import datetime
from typing import override
import types

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import AnalysisConfig
from ..core.message_processor import MessageProcessor
from ..utils.text_processing import create_slug
from ..utils.file_operations import load_prompt, AnalysisResult


class AnalysisInterrupted(Exception):
    """Raised when analysis is interrupted by user."""

    pass


class AnalystAgent(BaseAgent):
    """Agent responsible for analyzing business ideas."""

    def __init__(self, config: AnalysisConfig, prompt_version: str = "v3"):
        """
        Initialize the Analyst agent.

        Args:
            config: System configuration
            prompt_version: Version of the analyst prompt to use
        """
        super().__init__(config)
        self.prompt_version: str = prompt_version
        self.interrupt_event: threading.Event = threading.Event()

    @property
    @override
    def agent_name(self) -> str:
        """Return the name of this agent."""
        return "Analyst"

    @override
    def get_prompt_file(self) -> str:
        """Return the prompt file name for this agent."""
        return f"analyst_{self.prompt_version}.md"

    @override
    def get_allowed_tools(self) -> list[str]:
        """Return list of allowed tools for this agent."""
        return ["WebSearch"]  # Can be configured per analysis

    @override
    async def process(self, input_data: str, **kwargs: object) -> AgentResult:
        """
        Analyze a business idea.

        Args:
            input_data: The business idea to analyze
            **kwargs: Additional options:
                - debug: Enable debug logging
                - use_websearch: Enable WebSearch tool
                - revision_context: Dict with previous_analysis_file and feedback_file paths

        Returns:
            AgentResult containing the analysis
        """

        debug: bool = bool(kwargs.get("debug", False))
        use_websearch: bool = bool(kwargs.get("use_websearch", True))
        revision_context_raw = kwargs.get("revision_context", None)
        revision_context: dict[str, str] | None = None
        if isinstance(revision_context_raw, dict):
            # Validate it has string keys and values
            revision_context = {str(k): str(v) for k, v in revision_context_raw.items()}  # type: ignore[misc]

        try:
            result = await self._analyze_idea(
                idea=input_data,
                debug=debug,
                use_websearch=use_websearch,
                revision_context=revision_context,
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
        debug: bool = False,
        use_websearch: bool = True,
        revision_context: dict[str, str] | None = None,
    ) -> AnalysisResult | None:
        """
        Internal method to analyze a business idea.

        Args:
            idea: One-liner business idea to analyze
            debug: If True, log all messages to logs/ directory
            use_websearch: If True, allow WebSearch tool usage
            revision_context: Optional dict with previous_analysis_file and feedback_file paths

        Returns:
            AnalysisResult containing the analysis and metadata, or None if error
        """

        # Setup
        start_time = time.time()
        client: ClaudeSDKClient | None = None

        # Setup logger if debug mode (pipeline already has the main logger)
        import os
        from ..utils.logger import Logger

        # Use appropriate logger based on context
        if os.environ.get("TEST_HARNESS_RUN") == "1":
            # Use Logger for test visibility
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = create_slug(idea)
            logger = Logger(run_id, slug, "test", console_output=True)
        elif debug and not hasattr(self, "_pipeline_logger"):
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = create_slug(idea)
            logger = Logger(run_id, slug, "test", console_output=True)
        else:
            logger = getattr(self, "_pipeline_logger", None)
        # Reset interrupt state
        self.interrupt_event.clear()

        # Message processor with debug mode flag
        processor = MessageProcessor(logger, debug_mode=debug)

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
            system_prompt = load_prompt(self.get_prompt_file(), self.config.prompts_dir)
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
                "analyst_resources.md", self.config.prompts_dir
            )
            resource_note = resource_template.format(
                max_turns=self.config.max_turns,
                max_websearches=self.config.max_websearches if use_websearch else 0,
            )

            # Build user prompt based on whether this is a revision
            if revision_context:
                # Load revision-specific user prompt
                revision_template = load_prompt(
                    "analyst_user_revision.md", self.config.prompts_dir
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
                user_template = load_prompt("analyst_user.md", self.config.prompts_dir)
                user_prompt = user_template.format(
                    idea=idea,
                    resource_note=resource_note,
                    websearch_instruction=websearch_instruction,
                )

            # Configure options
            allowed_tools = self.get_allowed_tools() if use_websearch else []
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=self.config.max_turns,
                allowed_tools=allowed_tools,
            )

            if logger:
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

                    if (
                        logger
                        and stats["message_count"] % self.config.progress_interval == 0
                    ):
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

                        if logger and content:
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
            if logger:
                logger.error(
                    "Analysis failed: No ResultMessage received", agent="Analyst"
                )
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

            if logger:
                # Use SDK-aware error logging if it's an SDK error
                from claude_code_sdk._errors import (
                    CLINotFoundError,
                    CLIConnectionError,
                    ProcessError,
                    CLIJSONDecodeError,
                    MessageParseError,
                )

                if isinstance(
                    e,
                    (
                        CLINotFoundError,
                        CLIConnectionError,
                        ProcessError,
                        CLIJSONDecodeError,
                        MessageParseError,
                    ),
                ):
                    logger.log_sdk_error(e, "Analyst")
                else:
                    logger.error(str(e), "Analyst", exc_info=debug)

            if debug:
                traceback.print_exc()
            return None

        finally:
            # Reset signal handler to original
            _ = signal.signal(signal.SIGINT, original_handler)

            # Finalize logging
            if logger:
                stats = processor.get_statistics()
                _ = logger.finalize(
                    success=True,
                    result={
                        "total_messages": stats["message_count"],
                        "total_searches": stats["search_count"],
                        "total_time": time.time() - start_time,
                        "interrupted": self.interrupt_event.is_set(),
                    },
                )
