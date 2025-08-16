"""Message processing utilities for Claude SDK interactions."""

import re
from typing import TYPE_CHECKING, TypedDict
from dataclasses import dataclass

from ..core.constants import MAX_CONTENT_SIZE
from .sdk_types import (
    SystemMessageProtocol,
    ContentBlock,
    ContentBlockType,
)

if TYPE_CHECKING:
    from ..utils.improved_logging import StructuredLogger
    from ..utils.console_logger import ConsoleLogger


class MessageMetadata(TypedDict, total=False):
    """Metadata for processed messages."""

    message_number: int
    session_id: str
    total_cost_usd: float
    cost_usd: float


@dataclass
class ProcessedMessage:
    """Container for processed message data."""

    message_type: str
    content: list[str]
    search_queries: list[str]
    metadata: MessageMetadata


class MessageProcessor:
    """Handles processing of Claude SDK messages."""

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

    def extract_session_id(self, message: object) -> str | None:
        """
        Extract session ID from a SystemMessage.

        Args:
            message: The message object to extract from

        Returns:
            Session ID if found, None otherwise
        """
        # Use protocol check instead of isinstance
        if isinstance(message, SystemMessageProtocol):
            if hasattr(message, "data") and message.data:
                data_str = str(message.data)
                match = re.search(r"'session_id':\s*'([^']+)'", data_str)
                if match:
                    return match.group(1)
        return None

    def process_message(self, message: object) -> ProcessedMessage:
        """
        Process a single message from Claude SDK.

        Args:
            message: The message to process

        Returns:
            ProcessedMessage with extracted data
        """
        self.message_count += 1

        # Get message type by class name
        message_type = type(message).__name__

        content = []
        search_queries = []
        metadata: MessageMetadata = {"message_number": self.message_count}

        # Extract session ID if available
        session_id = self.extract_session_id(message)
        if session_id:
            metadata["session_id"] = session_id

        # Process different message types
        if hasattr(message, "content"):
            msg_content = getattr(message, "content", None)
            content, search_queries = self._extract_content(msg_content)

        # Handle ResultMessage specially using duck typing
        if type(message).__name__ == "ResultMessage":
            if hasattr(message, "result"):
                result = getattr(message, "result", None)
                if result:
                    content = [str(result)]
            if hasattr(message, "total_cost_usd"):
                cost = getattr(message, "total_cost_usd", None)
                if cost:
                    metadata["cost_usd"] = cost

        # Log if logger is available
        if self.logger:
            self._log_message(message_type, content, search_queries, metadata)

        return ProcessedMessage(
            message_type=message_type,
            content=content,
            search_queries=search_queries,
            metadata=metadata,
        )

    def _extract_content(
        self, msg_content: list[ContentBlockType] | ContentBlockType | None
    ) -> tuple[list[str], list[str]]:
        """
        Extract text content and search queries from message content.

        Args:
            msg_content: The content to extract from

        Returns:
            Tuple of (text_content, search_queries)
        """
        text_content: list[str] = []
        search_queries: list[str] = []

        if isinstance(msg_content, str):
            text_content.append(msg_content)
        elif isinstance(msg_content, list):
            for block in msg_content:
                # Check for WebSearch tool usage using protocol
                if isinstance(block, ContentBlock):
                    if block.name == "WebSearch" and block.input:
                        self.search_count += 1
                        query = block.input.get("query", "unknown")
                        search_queries.append(str(query))
                        import sys

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
                    elif block.text:
                        text = block.text
                        text_content.append(text)

                        # Append to result buffer with proper size management
                        self._append_to_buffer(text)

                    # Handle tool result blocks
                    elif block.content:
                        block_content = block.content
                        if isinstance(block_content, str):
                            # Extract search query from result
                            query_match = re.search(
                                r'query:\s*["\']([^"\']+)["\']', block_content
                            )
                            if query_match:
                                search_queries.append(f"Result: {query_match.group(1)}")

        return text_content, search_queries

    def _log_message(
        self,
        message_type: str,
        content: list[str],
        search_queries: list[str],
        metadata: MessageMetadata,
    ) -> None:
        """Log message details using StructuredLogger."""
        msg_data = {"number": self.message_count, "type": message_type, **metadata}

        if content:
            # Add preview of first 200 chars
            preview = content[0][:200] + "..." if len(content[0]) > 200 else content[0]
            msg_data["content_preview"] = preview.replace("\n", " ")

        if search_queries:
            msg_data["search_queries"] = search_queries

        if self.logger:
            self.logger.log_event(
                f"sdk_message_{message_type.lower()}",
                "MessageProcessor",
                {},  # type: ignore[arg-type]
            )

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
            self.logger.log_event("buffer_cleared", "MessageProcessor", {})

    def get_final_content(self) -> str:
        """
        Get the final aggregated content.

        Returns:
            Combined text content from all messages
        """
        return "".join(self.result_text)

    # These helper methods are no longer needed with Protocol types
    # The type checking is done directly with isinstance(message, Protocol)

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
