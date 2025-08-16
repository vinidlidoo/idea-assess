"""Message processing utilities for Claude SDK interactions."""

import re
from typing import TYPE_CHECKING, TypedDict
from dataclasses import dataclass


class MessageMetadata(TypedDict, total=False):
    """Metadata for processed messages."""

    message_number: int
    session_id: str
    total_cost_usd: float
    cost_usd: float


if TYPE_CHECKING:
    from ..utils.improved_logging import StructuredLogger
    from ..utils.console_logger import ConsoleLogger
from ..core.constants import MAX_CONTENT_SIZE

# Try to import SDK message types
try:
    from claude_code_sdk import (
        SystemMessage,
        ResultMessage,
        UserMessage,
        AssistantMessage,
        TextBlock,
        ToolUseBlock,
        ToolResultBlock,
    )

    has_sdk_types = True
    # Define union types for messages and content
    MessageType = SystemMessage | ResultMessage | UserMessage | AssistantMessage
    ContentBlockType = TextBlock | ToolUseBlock | ToolResultBlock | str
except ImportError:
    # Fallback if SDK doesn't export these types
    from typing import Any

    has_sdk_types = False
    SystemMessage = Any
    ResultMessage = Any
    UserMessage = Any
    AssistantMessage = Any
    TextBlock = Any
    ToolUseBlock = Any
    ToolResultBlock = Any
    MessageType = Any  # Fallback to Any if SDK types aren't available
    ContentBlockType = Any


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

    def extract_session_id(self, message: MessageType) -> str | None:
        """
        Extract session ID from a SystemMessage.

        Args:
            message: The message object to extract from

        Returns:
            Session ID if found, None otherwise
        """
        # Use isinstance check if SDK types are available
        if has_sdk_types:
            is_system_message = isinstance(message, SystemMessage)
        else:
            is_system_message = type(message).__name__ == "SystemMessage"

        if is_system_message and hasattr(message, "data"):
            data_str = str(getattr(message, "data", ""))
            match = re.search(r"'session_id':\s*'([^']+)'", data_str)
            if match:
                return match.group(1)
        return None

    def process_message(self, message: MessageType) -> ProcessedMessage:
        """
        Process a single message from Claude SDK.

        Args:
            message: The message to process

        Returns:
            ProcessedMessage with extracted data
        """
        self.message_count += 1

        message_type = self._get_message_type(message)

        content = []
        search_queries = []
        metadata: MessageMetadata = {"message_number": self.message_count}

        # Extract session ID if available
        session_id = self.extract_session_id(message)
        if session_id:
            metadata["session_id"] = session_id

        # Process different message types
        if hasattr(message, "content"):
            content, search_queries = self._extract_content(message.content)

        # Handle ResultMessage specially
        if self._is_result_message(message):
            if hasattr(message, "result") and message.result:
                content = [str(message.result)]
            if hasattr(message, "total_cost_usd") and message.total_cost_usd:
                metadata["cost_usd"] = message.total_cost_usd

        # Log if logger is available
        if self.logger:
            self._log_message(message_type, content, search_queries, metadata)

        result = ProcessedMessage(
            message_type=message_type,
            content=content,
            search_queries=search_queries,
            metadata=metadata,
        )
        return result

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
        text_content = []
        search_queries = []

        if isinstance(msg_content, str):
            text_content.append(msg_content)
        elif isinstance(msg_content, list):
            for block in msg_content:
                # Check for WebSearch tool usage
                if hasattr(block, "name") and block.name == "WebSearch":
                    self.search_count += 1
                    query = getattr(block, "input", {}).get("query", "unknown")
                    search_queries.append(query)
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
                            {"search_number": self.search_count, "query": query},
                        )

                # Extract text content
                elif hasattr(block, "text"):
                    text = block.text
                    text_content.append(text)

                    # Append to result buffer with proper size management
                    self._append_to_buffer(text)

                # Handle tool result blocks
                elif hasattr(block, "content"):
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
                f"sdk_message_{message_type.lower()}", "MessageProcessor", msg_data
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
                    {"original_size": text_size, "truncated_to": self.max_buffer_size},
                )

        # Make room if needed by removing oldest entries
        while self._total_size + text_size > self.max_buffer_size and self.result_text:
            removed = self.result_text.pop(0)
            self._total_size -= len(removed)
            if self.logger:
                self.logger.log_event(
                    "buffer_overflow_cleanup",
                    "MessageProcessor",
                    {
                        "removed_size": len(removed),
                        "entries_remaining": len(self.result_text),
                    },
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

    def _get_message_type(self, message: MessageType) -> str:
        """
        Get the type name of a message using isinstance checks when possible.

        Args:
            message: The message to check

        Returns:
            String name of the message type
        """
        if has_sdk_types:
            if isinstance(message, SystemMessage):
                return "SystemMessage"
            elif isinstance(message, ResultMessage):
                return "ResultMessage"
            elif isinstance(message, UserMessage):
                return "UserMessage"
            elif isinstance(message, AssistantMessage):
                return "AssistantMessage"

        # Fallback to string comparison
        return type(message).__name__

    def _is_result_message(self, message: MessageType) -> bool:
        """
        Check if a message is a ResultMessage.

        Args:
            message: The message to check

        Returns:
            True if it's a ResultMessage, False otherwise
        """
        if has_sdk_types:
            return isinstance(message, ResultMessage)
        return type(message).__name__ == "ResultMessage"

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
