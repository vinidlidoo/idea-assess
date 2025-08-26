"""Shared fixtures for mocking Claude SDK components.

This module provides properly configured mock objects that match the actual
Claude SDK interfaces and types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

if TYPE_CHECKING:
    from claude_code_sdk.types import (
        Message,
    )


def create_mock_sdk_client(
    messages: list["Message"] | None = None, error: Exception | None = None
) -> AsyncMock:
    """Create a properly configured mock SDK client with context manager support.

    Args:
        messages: Optional list of messages to yield from receive_response
        error: Optional exception to raise

    Returns:
        Configured mock client that mimics ClaudeSDKClient behavior
    """
    mock_client = AsyncMock()

    # Mock the async context manager protocol
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Mock query method (sends request, doesn't return anything)
    mock_client.query = AsyncMock()

    # Default messages if not provided
    if messages is None:
        from claude_code_sdk.types import AssistantMessage, TextBlock, ResultMessage

        messages = [
            AssistantMessage(
                content=[TextBlock(text="Test response")],
                model="claude-opus-4-1-20250805",
            ),
            ResultMessage(
                subtype="success",
                duration_ms=1000,
                duration_api_ms=800,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                total_cost_usd=0.001,
            ),
        ]

    # Handle error case
    if error:

        async def mock_error_response():
            raise error

        mock_client.receive_response = mock_error_response
    else:
        # Mock receive_response as async generator
        async def mock_receive_response():
            """Mock the SDK receive_response generator."""
            for message in messages:
                yield message

        # Set as a callable that returns the generator
        mock_client.receive_response = mock_receive_response

    return mock_client
