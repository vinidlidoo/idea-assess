"""Test that extracted prompts are loaded and formatted correctly."""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from src.utils.file_operations import load_prompt


class TestPromptExtraction:
    """Test suite for verifying extracted prompt templates."""
    
    def test_analyst_revision_prompt_loads(self):
        """Test that analyst revision prompt loads and formats correctly."""
        prompt = load_prompt("analyst_revision.md", Path("config/prompts"))
        
        # Check that the prompt contains expected placeholders
        assert "{idea}" in prompt
        assert "{current_analysis_file}" in prompt
        assert "{latest_feedback_file}" in prompt
        assert "INSTRUCTIONS:" in prompt
        
        # Test formatting
        formatted = prompt.format(
            idea="Test business idea",
            current_analysis_file="/path/to/analysis.md",
            latest_feedback_file="/path/to/feedback.json"
        )
        assert "Test business idea" in formatted
        assert "/path/to/analysis.md" in formatted
        assert "/path/to/feedback.json" in formatted
    
    def test_reviewer_instructions_prompt_loads(self):
        """Test that reviewer instructions prompt loads and formats correctly."""
        prompt = load_prompt("reviewer_instructions.md", Path("config/prompts"))
        
        # Check placeholders
        assert "{iteration_count}" in prompt
        assert "{max_iterations}" in prompt
        assert "{analysis_path}" in prompt
        assert "{feedback_file}" in prompt
        
        # Test formatting
        formatted = prompt.format(
            iteration_count=2,
            max_iterations=3,
            analysis_path="/path/to/analysis.md",
            feedback_file="/path/to/feedback.json"
        )
        assert "2 of maximum 3" in formatted
        assert "/path/to/analysis.md" in formatted
        assert "/path/to/feedback.json" in formatted
    
    def test_analyst_user_prompt_loads(self):
        """Test that analyst user prompt loads and formats correctly."""
        prompt = load_prompt("analyst_user.md", Path("config/prompts"))
        
        # Check placeholders
        assert "{idea}" in prompt
        assert "{resource_note}" in prompt
        assert "{websearch_instruction}" in prompt
        
        # Test formatting
        formatted = prompt.format(
            idea="AI fitness app",
            resource_note="Max turns: 10",
            websearch_instruction="Use WebSearch efficiently"
        )
        assert "AI fitness app" in formatted
        assert "Max turns: 10" in formatted
        assert "Use WebSearch efficiently" in formatted
    
    def test_analyst_resources_prompt_loads(self):
        """Test that analyst resources prompt loads and formats correctly."""
        prompt = load_prompt("analyst_resources.md", Path("config/prompts"))
        
        # Check placeholders
        assert "{max_turns}" in prompt
        assert "{max_websearches}" in prompt
        
        # Test formatting
        formatted = prompt.format(
            max_turns=10,
            max_websearches=5
        )
        assert "Maximum turns: 10" in formatted
        assert "Maximum web searches: 5" in formatted
    
    def test_prompt_caching(self):
        """Test that prompts are cached after first load."""
        # Clear the cache first
        load_prompt.cache_clear()
        
        # Load the same prompt twice
        prompt1 = load_prompt("analyst_user.md", Path("config/prompts"))
        prompt2 = load_prompt("analyst_user.md", Path("config/prompts"))
        
        # They should be the same object (cached)
        assert prompt1 is prompt2
        
        # Check cache info
        cache_info = load_prompt.cache_info()
        assert cache_info.hits == 1  # Second call should be a cache hit
        assert cache_info.misses == 1  # First call should be a cache miss
    
    def test_missing_prompt_raises_error(self):
        """Test that loading a non-existent prompt raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_prompt("non_existent_prompt.md", Path("config/prompts"))