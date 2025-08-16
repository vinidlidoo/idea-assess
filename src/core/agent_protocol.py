"""Protocol definition for agent polymorphism."""

from typing import Protocol, runtime_checkable
from .agent_base import AgentResult


@runtime_checkable
class AgentProtocol(Protocol):
    """
    Protocol that all agents must implement.

    This allows type-safe agent polymorphism without using Any.
    """

    @property
    def agent_name(self) -> str:
        """Return the name of this agent."""
        ...

    async def process(self, input_data: str, **kwargs: object) -> AgentResult:
        """
        Process input and return result.

        Args:
            input_data: Input string to process
            **kwargs: Additional options

        Returns:
            AgentResult with success status and content
        """
        ...

    def get_prompt_file(self) -> str:
        """Return the prompt file name for this agent."""
        ...

    def get_allowed_tools(self) -> list[str]:
        """Return list of allowed tools for this agent."""
        ...
