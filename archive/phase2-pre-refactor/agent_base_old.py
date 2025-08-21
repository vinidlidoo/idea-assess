"""Base agent interface for the idea assessment system."""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar
import signal

from .types import AgentResult

if TYPE_CHECKING:
    from .config import AnalystConfig, ReviewerConfig, BaseContext

# Module-level logger
logger = logging.getLogger(__name__)


# Type variables for config and context generics
TConfig = TypeVar("TConfig", bound="AnalystConfig | ReviewerConfig")
TContext = TypeVar("TContext", bound="BaseContext")


class BaseAgent(ABC, Generic[TConfig, TContext]):
    """Base class for all agents in the system.

    Uses generics to ensure type safety between agent-specific configs and contexts.
    """

    def __init__(self, config: TConfig):
        """
        Initialize the agent with configuration.

        Args:
            config: Agent-specific configuration
        """
        self.config: TConfig = config
        self.interrupt_event: threading.Event = threading.Event()

    @abstractmethod
    async def process(
        self, input_data: str = "", context: TContext | None = None
    ) -> AgentResult:
        """
        Process input and return standardized result.

        Args:
            input_data: The input to process (optional, defaults to empty string)
            context: Runtime context with overrides and state

        Returns:
            AgentResult containing the processing outcome
        """
        pass

    def get_system_prompt_path(self, context: TContext | None = None) -> str:
        """
        Get system prompt path with context override support.

        Args:
            context: Runtime context that may contain system_prompt_override

        Returns:
            Path relative to prompts directory (e.g., 'agents/analyst/system.md')
        """
        from pathlib import Path

        agent_type = self.agent_name.lower()

        # Check context override first
        if (
            context
            and hasattr(context, "system_prompt_override")
            and context.system_prompt_override
        ):
            override = context.system_prompt_override
            if override.startswith("experimental/"):
                # Experimental prompt: experimental/analyst/yc_style
                return f"{override}.md"
            elif "/" in override:
                # Full path provided
                return override
            else:
                # Relative to agent folder
                return str(Path("agents") / agent_type / f"{override}.md")

        # Default: use standard system prompt
        return str(Path("agents") / agent_type / "system.md")

    def load_system_prompt(self, context: TContext | None = None) -> str:
        """
        Load the complete system prompt with includes processed.

        This method handles {{include:path}} directives in prompts,
        allowing shared components to be included.

        Args:
            context: Runtime context that may contain system_prompt_override

        Returns:
            The complete system prompt with all includes processed

        Raises:
            ValueError: If prompts_dir is not configured
        """
        from ..utils.file_operations import load_prompt_with_includes

        if not hasattr(self.config, "prompts_dir") or not self.config.prompts_dir:
            raise ValueError(f"prompts_dir not configured for {self.agent_name}")

        return load_prompt_with_includes(
            self.get_system_prompt_path(context), self.config.prompts_dir
        )

    def get_allowed_tools(self, context: TContext) -> list[str]:
        """
        Return list of allowed tools for this agent.

        Uses context overrides if provided, otherwise agent's default tools.

        Args:
            context: Runtime context that may contain tool overrides

        Returns:
            List of tool names (e.g., ['WebSearch'])
        """
        # Default implementation - child classes can override if needed
        if hasattr(context, "tools_override") and context.tools_override is not None:
            return context.tools_override
        if hasattr(self.config, "default_tools"):
            return self.config.default_tools  # type: ignore[attr-defined]
        return []

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """
        Return the name of this agent.

        Returns:
            Agent name (e.g., 'Analyst')
        """
        pass

    def get_max_turns(self) -> int:
        """
        Get the maximum number of conversation turns for this agent.

        Returns:
            Maximum turns from agent's config
        """
        if hasattr(self.config, "max_turns"):
            return self.config.max_turns  # type: ignore[attr-defined]
        return 30  # Fallback default

    def setup_interrupt_handler(self) -> object:
        """
        Setup interrupt handling for graceful shutdown.

        Returns:
            Original signal handler to restore later
        """
        import types

        def handle_interrupt(_signum: int, _frame: types.FrameType | None) -> None:
            """Handle SIGINT by setting interrupt event."""
            self.interrupt_event.set()
            logger.warning(
                f"{self.agent_name}: Interrupt received, attempting graceful shutdown..."
            )

        # Store and replace the signal handler
        original_handler = signal.getsignal(signal.SIGINT)
        _ = signal.signal(signal.SIGINT, handle_interrupt)
        return original_handler

    def restore_interrupt_handler(self, original_handler: object) -> None:
        """
        Restore the original interrupt handler.

        Args:
            original_handler: The handler to restore (from setup_interrupt_handler)
        """
        from typing import cast, Any

        _ = signal.signal(signal.SIGINT, cast(Any, original_handler))  # pyright: ignore[reportAny, reportExplicitAny]
