"""Base test class providing temporary directory management."""

from __future__ import annotations

from pathlib import Path
import tempfile
import shutil
from unittest.mock import AsyncMock

import pytest


class BaseAgentTest:
    """Base class for agent tests providing temporary directory management."""

    # Instance variable set during setup
    temp_dir: Path | None = None

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test - creates and cleans temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        yield
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @staticmethod
    def create_mock_sdk_client() -> AsyncMock:
        """Create a properly configured mock SDK client with context manager support.

        Returns:
            AsyncMock configured as an async context manager
        """
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client
