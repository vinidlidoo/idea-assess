"""Message tracking and content extraction utilities for Claude SDK interactions."""

import re
from typing import TYPE_CHECKING

from claude_code_sdk.types import ContentBlock
from ..core.constants import MAX_CONTENT_SIZE

if TYPE_CHECKING:
    from ..utils.improved_logging import StructuredLogger
    from ..utils.console_logger import ConsoleLogger


class MessageProcessor:
    """Tracks message statistics and helps extract content from Claude SDK messages."""

    def __init__(
        self,
        logger: "StructuredLogger | ConsoleLogger | None" = None,
        max_buffer_size: int = MAX_CONTENT_SIZE,
    ):
        """
        Initialize the message processor.

        Args:
            logger: Optional structured logger
            max_buffer_size: Maximum size of the result buffer in bytes
        """
        self.logger: StructuredLogger | ConsoleLogger | None = logger
        self.message_count: int = 0
        self.search_count: int = 0
        self.result_text: list[str] = []
        self.max_buffer_size: int = max_buffer_size
        self._total_size: int = 0  # Track current buffer size

    def get_session_id(self, message: object) -> str | None:
        """
        Extract session ID from a SystemMessage.

        Args:
            message: The message object to extract from

        Returns:
            Session ID if found, None otherwise
        """
        from claude_code_sdk.types import SystemMessage

        if isinstance(message, SystemMessage):
            if message.data:
                session_id = message.data.get("session_id")
                if isinstance(session_id, str):
                    return session_id
        return None

    def track_message(self, message: object) -> None:
        """
        Track a message and update internal statistics.

        Args:
            message: The SDK message to track
        """
        self.message_count += 1

        from claude_code_sdk.types import (
            UserMessage,
            AssistantMessage,
            ResultMessage,
        )

        # Process content for messages that have it
        if isinstance(message, (UserMessage, AssistantMessage)):
            content, search_queries = self._extract_content_and_queries(message.content)

            # Update buffer with text content
            for text in content:
                self._append_to_buffer(text)

            # Log search queries
            if self.logger and search_queries:
                for query in search_queries:
                    self.logger.log_event(
                        "websearch_query",
                        "MessageProcessor",
                        {"query": query, "search_number": self.search_count},
                    )

        # Log message details if logger available
        if self.logger:
            message_type = type(message).__name__
            metadata: dict[str, object] = {"message_number": self.message_count}

            # Add cost info for ResultMessage
            if isinstance(message, ResultMessage) and message.total_cost_usd:
                metadata["cost_usd"] = message.total_cost_usd

            self.logger.log_event(
                f"sdk_message_{message_type.lower()}",
                "MessageProcessor",
                {},  # type: ignore[arg-type]
            )

    def extract_content(self, message: object) -> list[str]:
        """
        Extract text content from a message.

        Args:
            message: The SDK message to extract from

        Returns:
            List of text content strings
        """
        from claude_code_sdk.types import (
            UserMessage,
            AssistantMessage,
            ResultMessage,
        )

        if isinstance(message, (UserMessage, AssistantMessage)):
            content, _ = self._extract_content_and_queries(message.content)
            return content
        elif isinstance(message, ResultMessage):
            if message.result:
                return [str(message.result)]

        return []

    def extract_search_queries(self, message: object) -> list[str]:
        """
        Extract search queries from a message.

        Args:
            message: The SDK message to extract from

        Returns:
            List of search query strings
        """
        from claude_code_sdk.types import UserMessage, AssistantMessage

        if isinstance(message, (UserMessage, AssistantMessage)):
            _, queries = self._extract_content_and_queries(message.content)
            return queries

        return []

    def _extract_content_and_queries(
        self, msg_content: str | list[ContentBlock]
    ) -> tuple[list[str], list[str]]:
        """
        Extract text content and search queries from message content.

        Args:
            msg_content: The content to extract from

        Returns:
            Tuple of (text_content, search_queries)
        """
        from claude_code_sdk.types import (
            TextBlock,
            ToolUseBlock,
            ToolResultBlock,
        )
        import sys

        text_content: list[str] = []
        search_queries: list[str] = []

        if isinstance(msg_content, str):
            text_content.append(msg_content)
        else:  # msg_content is list[ContentBlock]
            for block in msg_content:
                # Check for WebSearch tool usage
                if isinstance(block, ToolUseBlock):
                    if block.name == "WebSearch" and block.input:
                        self.search_count += 1
                        query = str(block.input.get("query", "unknown"))
                        search_queries.append(query)

                        print(
                            f"  🔍 Search #{self.search_count}: {query} (may take 30-120s)...",
                            file=sys.stderr,
                            flush=True,
                        )
                        if self.logger:
                            self.logger.log_event(
                                "websearch_query",
                                "MessageProcessor",
                                {
                                    "search_number": self.search_count,
                                    "query": str(query),
                                },  # type: ignore[arg-type]
                            )

                # Extract text content
                elif isinstance(block, TextBlock):
                    text_content.append(block.text)

                # Handle tool result blocks
                elif isinstance(block, ToolResultBlock):  # pyright: ignore[reportUnnecessaryIsInstance]
                    if block.content and isinstance(block.content, str):
                        # Extract search query from result
                        query_match = re.search(
                            r'query:\s*["\']([^"\']+)["\']', block.content
                        )
                        if query_match:
                            search_queries.append(f"Result: {query_match.group(1)}")

        return text_content, search_queries

    def _append_to_buffer(self, text: str) -> None:
        """
        Append text to the result buffer with size management.

        Uses a rolling buffer approach - when buffer is full,
        removes oldest entries to make room for new text.

        Args:
            text: Text to append to the buffer
        """
        text_size = len(text)

        # If text itself exceeds max size, truncate it
        if text_size > self.max_buffer_size:
            text = text[: self.max_buffer_size]
            text_size = self.max_buffer_size
            if self.logger:
                self.logger.log_event(
                    "buffer_text_truncated",
                    "MessageProcessor",
                    {},  # type: ignore[arg-type]
                )

        # Make room if needed by removing oldest entries
        while self._total_size + text_size > self.max_buffer_size and self.result_text:
            removed = self.result_text.pop(0)
            self._total_size -= len(removed)
            if self.logger:
                self.logger.log_event(
                    "buffer_overflow_cleanup",
                    "MessageProcessor",
                    {},  # type: ignore[arg-type]
                )

        # Append new text
        self.result_text.append(text)
        self._total_size += text_size

    def clear_buffer(self) -> None:
        """Clear the result buffer and reset size tracking."""
        self.result_text.clear()
        self._total_size = 0
        if self.logger:
            self.logger.log_event("buffer_cleared", "MessageProcessor", {})  # type: ignore[arg-type]

    def get_final_content(self) -> str:
        """
        Get the final aggregated content.

        Returns:
            Combined text content from all messages
        """
        return "".join(self.result_text)

    def get_statistics(self) -> dict[str, int]:
        """
        Get processing statistics.

        Returns:
            Dictionary with message, search counts, and buffer info
        """
        return {
            "message_count": self.message_count,
            "search_count": self.search_count,
            "buffer_size": self._total_size,
            "buffer_entries": len(self.result_text),
            "buffer_capacity": self.max_buffer_size,
        }
