"""Message tracking and content extraction utilities for Claude SDK interactions."""

import re

from claude_code_sdk.types import (
    ContentBlock,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from ..core.constants import MAX_CONTENT_SIZE
from ..utils.logger import Logger


class MessageProcessor:
    """
    Tracks message statistics and logs full message details for debugging.

    Primary responsibilities:
    1. Count messages and WebSearch tool usage
    2. Extract session IDs from SystemMessages
    3. Extract text content and search queries from messages
    4. Log message details to disk for debugging (when debug_mode=True)

    """

    def __init__(
        self,
        logger: Logger | None = None,
        max_buffer_size: int = MAX_CONTENT_SIZE,  # Deprecated parameter, ignored
        debug_mode: bool = False,
    ):
        """
        Initialize the message processor.

        Args:
            logger: Optional logger instance
            max_buffer_size: Deprecated parameter, ignored (kept for backward compatibility)
            debug_mode: Whether to log full message details for debugging
        """
        self.logger: Logger | None = logger
        self.debug_mode: bool = debug_mode
        self.message_count: int = 0
        self.search_count: int = 0
        # Buffer system removed - content is now logged to disk when debug_mode=True

    def get_session_id(self, message: object) -> str | None:
        """
        Extract session ID from a SystemMessage.

        Args:
            message: The message object to extract from

        Returns:
            Session ID if found, None otherwise
        """

        if isinstance(message, SystemMessage):
            if message.data:
                session_id = message.data.get("session_id")
                if isinstance(session_id, str):
                    return session_id
        return None

    def track_message(self, message: object) -> None:
        """
        Track message statistics, extract search queries, and optionally log full message details.

        Increments message_count, tracks WebSearch tool usage (incrementing search_count),
        and logs message details to disk when debug_mode is True.

        Args:
            message: The SDK message to track
        """
        self.message_count += 1

        # Log message type first (lightweight tracking)
        if self.logger:
            message_type = type(message).__name__
            self.logger.log_event(
                f"sdk_message_{message_type.lower()}",
                "MessageProcessor",
                {},  # type: ignore[arg-type]
            )

        # Log full message details when in debug mode (heavier operation)
        if self.debug_mode:
            self._log_message_details(message)

        # Extract and log search queries from user/assistant messages
        # Note: search_count is incremented inside _extract_content_and_queries()
        if isinstance(message, (UserMessage, AssistantMessage)):
            _, search_queries = self._extract_content_and_queries(message.content)

            # Log each search query found
            # Note: search_count was already incremented for each query in _extract_content_and_queries
            # so we need to calculate the correct number for each query
            if self.logger and search_queries:
                # Calculate starting search number (current count - number of queries found)
                start_num = self.search_count - len(search_queries) + 1
                for i, query in enumerate(search_queries):
                    self.logger.log_event(
                        "websearch_query",
                        "MessageProcessor",
                        {"query": query, "search_number": start_num + i},
                    )

    def extract_content(self, message: object) -> list[str]:
        """
        Extract text content from a message.

        Args:
            message: The SDK message to extract from

        Returns:
            List of text content strings
        """

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

        Can return multiple queries if a message contains multiple ToolUseBlock
        elements calling WebSearch, though typically there's only one per message.

        Args:
            message: The SDK message to extract from

        Returns:
            List of search query strings (usually 0 or 1, but can be multiple)
        """
        if isinstance(message, (UserMessage, AssistantMessage)):
            _, queries = self._extract_content_and_queries(message.content)
            return queries

        return []

    def _log_message_details(self, message: object) -> None:
        """
        Log full message structure preserving SDK types.

        Args:
            message: The SDK message to log
        """
        if not self.logger or not self.debug_mode:
            return

        # Only log SDK message types
        if not isinstance(
            message, (UserMessage, AssistantMessage, SystemMessage, ResultMessage)
        ):
            return

        msg_dict = self._serialize_message(message)

        # Use type: ignore since EventData is a TypedDict with specific fields
        # but we're adding dynamic fields for message logging
        self.logger.log_event(
            event_type="sdk_message",
            agent="MessageProcessor",
            data={},  # type: ignore[arg-type]
        )

        # Log the actual message data as a separate event for now
        # This avoids type conflicts with EventData
        if self.logger and self.debug_mode:
            import json
            from datetime import datetime

            # Write directly to a debug messages JSONL file
            # Create a separate file for SDK messages when in debug mode
            log_dir = self.logger.log_file.parent
            messages_file = log_dir / f"{self.logger.log_file.stem}_messages.jsonl"

            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "sdk_message_detail",
                "agent": "MessageProcessor",
                "message_index": self.message_count,
                "message_type": type(message).__name__,
                "message": msg_dict,
            }

            with open(messages_file, "a") as f:
                _ = f.write(json.dumps(event) + "\n")

    def _serialize_message(
        self, message: object, max_content_length: int = 1000
    ) -> dict[str, object]:
        """
        Serialize SDK message preserving structure but truncating content.

        Args:
            message: The SDK message to serialize
            max_content_length: Maximum length for text content

        Returns:
            Dictionary representation of the message
        """
        if isinstance(message, (UserMessage, AssistantMessage)):
            msg_type = type(message).__name__
            content = message.content

            # UserMessage can have str or list[ContentBlock], AssistantMessage always has list[ContentBlock]
            if isinstance(content, str):
                truncated = (
                    content[:max_content_length] + "..."
                    if len(content) > max_content_length
                    else content
                )
                return {"type": msg_type, "content": truncated}
            else:  # list[ContentBlock]
                return {
                    "type": msg_type,
                    "content": [
                        self._serialize_block(block) for block in content[:5]
                    ],  # Max 5 blocks
                }

        elif isinstance(message, SystemMessage):
            return {
                "type": "SystemMessage",
                "subtype": message.subtype,
                "data": message.data,  # Usually small metadata
            }

        elif isinstance(message, ResultMessage):
            result_text = (
                message.result[:max_content_length] + "..."
                if message.result and len(message.result) > max_content_length
                else message.result
            )
            return {
                "type": "ResultMessage",
                "subtype": message.subtype,
                "duration_ms": message.duration_ms,
                "duration_api_ms": message.duration_api_ms,  # Added missing field
                "is_error": message.is_error,
                "num_turns": message.num_turns,
                "session_id": message.session_id,
                "total_cost_usd": message.total_cost_usd,
                "usage": message.usage,  # Added missing field
                "result": result_text,
            }
        return {"type": "Unknown"}

    def _serialize_block(self, block: ContentBlock) -> dict[str, object]:
        """
        Serialize content blocks with truncation.

        Args:
            block: The content block to serialize

        Returns:
            Dictionary representation of the block
        """
        if isinstance(block, TextBlock):
            text = block.text[:500] + "..." if len(block.text) > 500 else block.text
            return {"type": "TextBlock", "text": text}
        elif isinstance(block, ToolUseBlock):
            return {
                "type": "ToolUseBlock",
                "name": block.name,
                "id": block.id,
                "input": block.input,
            }
        elif isinstance(block, ToolResultBlock):  # pyright: ignore[reportUnnecessaryIsInstance]
            content_str = str(block.content) if block.content else None
            truncated = (
                content_str[:500] + "..."
                if content_str and len(content_str) > 500
                else content_str
            )
            return {
                "type": "ToolResultBlock",
                "content": truncated,
                "is_error": block.is_error,
            }
        # Handle other block types (e.g., ThinkingBlock, future additions)
        return {"type": "Unknown"}

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

    def get_statistics(self) -> dict[str, int]:
        """
        Get processing statistics.

        Returns:
            Dictionary with message and search counts
        """
        return {
            "message_count": self.message_count,
            "search_count": self.search_count,
        }
