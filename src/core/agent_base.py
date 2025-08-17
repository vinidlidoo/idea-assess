"""Base agent interface for the idea assessment system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .config import AnalysisConfig


@dataclass
class AgentResult:
    """Standard result container for all agents."""

    content: str
    metadata: dict[str, object]
    success: bool
    error: str | None = None


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(self, config: AnalysisConfig):
        """
        Initialize the agent with configuration.

        Args:
            config: System configuration
        """
        self.config: AnalysisConfig = config

    @abstractmethod
    async def process(self, input_data: str, **kwargs: object) -> AgentResult:
        """
        Process input and return standardized result.

        Args:
            input_data: The input to process
            **kwargs: Additional processing options

        Returns:
            AgentResult containing the processing outcome
        """
        pass

    @abstractmethod
    def get_prompt_file(self) -> str:
        """
        Return the prompt file name for this agent.

        Returns:
            Name of the prompt file (e.g., 'analyst_v3.md')
        """
        pass

    @abstractmethod
    def get_allowed_tools(self) -> list[str]:
        """
        Return list of allowed tools for this agent.

        Returns:
            List of tool names (e.g., ['WebSearch'])
        """
        pass

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
            Maximum turns (default from config)
        """
        return self.config.max_turns
