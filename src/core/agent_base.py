"""Base agent interface for the idea assessment system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar
from dataclasses import dataclass
import threading

if TYPE_CHECKING:
    from .config import AnalystConfig, ReviewerConfig, BaseContext


@dataclass
class AgentResult:
    """Standard result container for all agents."""

    content: str
    metadata: dict[str, object]
    success: bool
    error: str | None = None


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
    async def process(self, input_data: str, context: TContext) -> AgentResult:
        """
        Process input and return standardized result.

        Args:
            input_data: The input to process
            context: Runtime context with overrides and state

        Returns:
            AgentResult containing the processing outcome
        """
        pass

    def get_prompt_path(self) -> str:
        """
        Dynamically resolve the prompt file path based on prompt variant.

        Returns:
            Path relative to prompts directory (e.g., 'agents/analyst/main.md')
        """
        from pathlib import Path

        agent_type = self.agent_name.lower()
        variant = getattr(self.config, "prompt_variant", "main")

        if variant == "main":
            # Active prompt: agents/{agent_type}/main.md
            return str(Path("agents") / agent_type / "main.md")
        elif variant.startswith("v"):
            # Historical version: versions/{agent_type}/{agent_type}_{variant}.md
            # e.g., versions/analyst/analyst_v3.md
            return str(Path("versions") / agent_type / f"{agent_type}_{variant}.md")
        else:
            # Special workflows: agents/{agent_type}/{variant}.md
            return str(Path("agents") / agent_type / f"{variant}.md")

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
