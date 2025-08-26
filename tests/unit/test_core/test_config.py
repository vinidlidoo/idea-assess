"""Tests for configuration validation and defaults."""

from __future__ import annotations

from pathlib import Path


from src.core.config import (
    SystemConfig,
    AnalystConfig,
    ReviewerConfig,
    create_default_configs,
)
from tests.unit.base_test import BaseAgentTest


class TestConfiguration(BaseAgentTest):
    """Test configuration validation and behavior."""

    def test_system_config_paths_resolved(self):
        """Test that SystemConfig resolves all paths to absolute."""
        assert self.temp_dir is not None

        # Create config with relative paths
        config = SystemConfig(
            project_root=Path("."),
            analyses_dir=Path("./analyses"),
            config_dir=Path("./config"),
            logs_dir=Path("./logs"),
        )

        # All paths should be absolute after __post_init__
        assert config.project_root.is_absolute()
        assert config.analyses_dir.is_absolute()
        assert config.config_dir.is_absolute()
        assert config.logs_dir.is_absolute()

    def test_analyst_config_defaults(self):
        """Test AnalystConfig has correct defaults."""
        config = AnalystConfig()

        # Check defaults
        assert config.max_turns == 20
        assert config.max_websearches == 4
        assert config.min_words == 800
        assert config.allowed_tools == ["WebSearch"]
        assert config.system_prompt == "system.md"
        assert config.prompts_dir == Path("config/prompts")

    def test_reviewer_config_defaults(self):
        """Test ReviewerConfig has correct defaults."""
        config = ReviewerConfig()

        # Check defaults
        assert config.max_turns == 20
        assert config.max_iterations == 3
        assert config.strictness == "normal"
        assert config.allowed_tools == []
        assert config.system_prompt == "system.md"

    def test_create_default_configs(self):
        """Test create_default_configs creates proper instances."""
        assert self.temp_dir is not None

        system, analyst, reviewer = create_default_configs(self.temp_dir)

        # Check system config
        assert isinstance(system, SystemConfig)
        assert system.project_root == self.temp_dir.resolve()
        assert system.analyses_dir == (self.temp_dir / "analyses").resolve()
        assert system.config_dir == (self.temp_dir / "config").resolve()
        assert system.logs_dir == (self.temp_dir / "logs").resolve()

        # Check analyst config
        assert isinstance(analyst, AnalystConfig)
        assert analyst.prompts_dir == self.temp_dir / "config" / "prompts"
        assert analyst.allowed_tools == ["WebSearch"]

        # Check reviewer config
        assert isinstance(reviewer, ReviewerConfig)
        assert reviewer.prompts_dir == self.temp_dir / "config" / "prompts"
        assert reviewer.allowed_tools == []

    def test_get_allowed_tools_returns_copy(self):
        """Test that get_allowed_tools returns a copy, not original."""
        config = AnalystConfig()

        # Get tools and modify the returned list
        tools = config.get_allowed_tools()
        tools.append("NewTool")

        # Original should be unchanged
        assert config.allowed_tools == ["WebSearch"]
        assert "NewTool" not in config.allowed_tools

    def test_config_modification(self):
        """Test that configurations can be modified after creation."""
        config = ReviewerConfig()

        # Modify configuration
        config.max_iterations = 5
        config.strictness = "strict"
        config.allowed_tools = ["Read", "Edit"]

        # Verify changes
        assert config.max_iterations == 5
        assert config.strictness == "strict"
        assert config.allowed_tools == ["Read", "Edit"]

    def test_system_config_output_limit(self):
        """Test SystemConfig default output_limit."""
        assert self.temp_dir is not None

        config = SystemConfig(
            project_root=self.temp_dir,
            analyses_dir=self.temp_dir / "analyses",
            config_dir=self.temp_dir / "config",
            logs_dir=self.temp_dir / "logs",
        )

        # Check default output limit
        assert config.output_limit == 50000

        # Can be modified
        config.output_limit = 100000
        assert config.output_limit == 100000
