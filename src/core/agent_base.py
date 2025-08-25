"""Base agent interface for the idea assessment system."""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar
import signal

from .types import AgentResult

if TYPE_CHECKING:
    from .config import BaseAgentConfig
    from .types import BaseContext

# Module-level logger
logger = logging.getLogger(__name__)


# Type variables for config and context generics
TConfig = TypeVar("TConfig", bound="BaseAgentConfig")
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

    def get_system_prompt_path(self) -> str:
        """
        Get system prompt path from config.

        Returns:
            Path relative to prompts directory (e.g., 'agents/analyst/system.md')
        """
        from pathlib import Path

        agent_type = self.agent_name.lower()
        prompt = self.config.system_prompt

        # If no slash, it's a filename in the agent's directory
        if "/" not in prompt:
            return str(Path("agents") / agent_type / prompt)
        else:
            # Contains slash, treat as path from prompts_dir
            return prompt

    def load_system_prompt(self) -> str:
        """
        Load the complete system prompt with includes processed.

        This method handles {{include:path}} directives in prompts,
        allowing shared components to be included.

        Returns:
            The complete system prompt with all includes processed

        Raises:
            ValueError: If prompts_dir is not configured
        """
        from ..utils.file_operations import load_prompt_with_includes

        if not hasattr(self.config, "prompts_dir") or not self.config.prompts_dir:
            raise ValueError(f"prompts_dir not configured for {self.agent_name}")

        return load_prompt_with_includes(
            self.get_system_prompt_path(), self.config.prompts_dir
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
        # Check if context has tools override
        if context and context.tools is not None:
            return context.tools

        # Otherwise use config's allowed tools
        return self.config.get_allowed_tools()

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
