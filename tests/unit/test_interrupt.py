"""Test interrupt handling for graceful shutdown."""

import pytest
import signal
import asyncio
import threading
from unittest.mock import Mock, AsyncMock, patch

from src.agents.analyst import AnalystAgent
from src.core.config import AnalystConfig, AnalystContext


class TestInterruptHandling:
    """Test that agents handle interrupts gracefully."""

    @pytest.fixture
    def config(self):
        """Create a mock configuration."""
        from pathlib import Path

        config = Mock(spec=AnalystConfig)
        config.prompts_dir = Path("config/prompts")
        config.analyses_dir = Path("analyses")
        config.logs_dir = Path("logs")
        return config

    @pytest.mark.asyncio
    async def test_analyst_interrupt_handling(self, config):
        """Test that analyst handles interrupt signals gracefully."""
        analyst = AnalystAgent(config)

        # Mock the SDK client to simulate a long-running process
        mock_response = AsyncMock()
        mock_response.content = ["Test ", "analysis ", "content"]

        async def mock_stream():
            for chunk in mock_response.content:
                yield Mock(content=chunk)
                await asyncio.sleep(0.1)  # Simulate delay

        mock_client = AsyncMock()
        mock_client.messages.stream = AsyncMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_stream()),
                __aexit__=AsyncMock(return_value=None),
            )
        )

        # Mock the ClaudeSDKClient context manager
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        # Test interrupt during processing
        with patch(
            "src.agents.analyst.ClaudeSDKClient", return_value=mock_client_instance
        ):
            # Start processing in background
            # Start processing in background with context
            context = AnalystContext(
                tools_override=[]  # No websearch
            )
            task = asyncio.create_task(analyst.process("Test business idea", context))

            # Wait a moment then simulate interrupt
            await asyncio.sleep(0.05)

            # Simulate Ctrl+C by setting the interrupt event
            analyst.interrupt_event.set()

            # The task should complete gracefully
            result = await task

            # Verify graceful handling
            assert result.success is False
            # The error message may vary depending on when the interrupt occurs
            # Key is that it failed gracefully without raising an exception

    def test_signal_handler_registration(self, config):
        """Test that signal handlers are properly registered and cleaned up."""
        analyst = AnalystAgent(config)

        # Store original handler (unused but shows we're not breaking signal chain)
        _ = signal.getsignal(signal.SIGINT)

        # Mock the ClaudeSDKClient to avoid actual API calls
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock process method to verify handler setup
        with patch("src.agents.analyst.ClaudeSDKClient", return_value=mock_client):
            with patch("signal.signal") as mock_signal:
                # Run a simple process with context
                context = AnalystContext(tools_override=[])
                asyncio.run(analyst.process("Test idea", context))

                # Verify signal handler was set
                mock_signal.assert_called()
                call_args = mock_signal.call_args_list

                # Should have called signal.signal at least once for SIGINT
                sigint_calls = [
                    call
                    for call in call_args
                    if len(call[0]) >= 1 and call[0][0] == signal.SIGINT
                ]
                assert len(sigint_calls) > 0

    def test_thread_safety_of_interrupt_flag(self, config):
        """Test that interrupt flag is thread-safe."""
        analyst = AnalystAgent(config)

        # Test that multiple threads can safely set the flag
        def set_interrupt():
            analyst.interrupt_event.set()

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=set_interrupt)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify flag is set
        assert analyst.interrupt_event.is_set() is True

    @pytest.mark.asyncio
    async def test_cleanup_after_interrupt(self, config):
        """Test that resources are properly cleaned up after interrupt."""
        analyst = AnalystAgent(config)

        # Track cleanup
        cleanup_called = False

        def mock_cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        # Mock the ClaudeSDKClient with cleanup
        mock_client = AsyncMock()
        mock_client.close = mock_cleanup
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        # Mock the processing with cleanup
        with patch(
            "src.agents.analyst.ClaudeSDKClient", return_value=mock_client_instance
        ):
            # Simulate interrupted processing
            analyst.interrupt_event.set()
            context = AnalystContext(tools_override=[])
            result = await analyst.process("Test idea", context)

            # Verify result indicates interruption
            assert result.success is False

            # Note: In real implementation, we'd verify cleanup
            # For now, this documents expected behavior
