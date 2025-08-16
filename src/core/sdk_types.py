"""Type definitions for Claude SDK compatibility."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SDKMessage(Protocol):
    """Protocol for SDK message objects."""

    # Note: content is not present on all message types
    pass


@runtime_checkable
class SystemMessageProtocol(SDKMessage, Protocol):
    """Protocol for SystemMessage type."""

    @property
    def data(self) -> dict[str, object] | None:
        """System message data."""
        ...


@runtime_checkable
class ResultMessageProtocol(SDKMessage, Protocol):
    """Protocol for ResultMessage type."""

    @property
    def result(self) -> str | None:
        """Result content."""
        ...

    @property
    def total_cost_usd(self) -> float | None:
        """Total cost in USD."""
        ...


@runtime_checkable
class AssistantMessageProtocol(SDKMessage, Protocol):
    """Protocol for AssistantMessage type."""

    pass


@runtime_checkable
class UserMessageProtocol(SDKMessage, Protocol):
    """Protocol for UserMessage type."""

    pass


@runtime_checkable
class ContentBlock(Protocol):
    """Protocol for content blocks."""

    @property
    def text(self) -> str | None:
        """Text content."""
        ...

    @property
    def name(self) -> str | None:
        """Tool name if tool block."""
        ...

    @property
    def input(self) -> dict[str, object] | None:
        """Tool input if tool block."""
        ...

    @property
    def content(self) -> str | None:
        """Result content if result block."""
        ...


# Type aliases for cleaner usage
MessageType = SDKMessage
ContentBlockType = ContentBlock | str
