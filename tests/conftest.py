"""Shared pytest fixtures for all test modules."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from claude_code_sdk.types import (
    UserMessage,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
)


# ============================================================================
# Path Fixtures
# ============================================================================


@pytest.fixture
def temp_dir(tmp_path, monkeypatch):
    """Create a temporary directory and change to it."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def prompts_dir(temp_dir):
    """Create a prompts directory in temp location."""
    prompts_path = temp_dir / "prompts"
    prompts_path.mkdir(exist_ok=True)
    return prompts_path


@pytest.fixture
def templates_dir(temp_dir):
    """Create a templates directory in temp location."""
    templates_path = temp_dir / "templates"
    templates_path.mkdir(exist_ok=True)
    return templates_path


@pytest.fixture
def analyses_dir(temp_dir):
    """Create an analyses directory in temp location."""
    analyses_path = temp_dir / "analyses"
    analyses_path.mkdir(exist_ok=True)
    return analyses_path


# ============================================================================
# SDK Message Fixtures
# ============================================================================


@pytest.fixture
def user_message():
    """Create a sample UserMessage."""
    return UserMessage(content="Test user message")


@pytest.fixture
def assistant_message():
    """Create a sample AssistantMessage with text."""
    return AssistantMessage(
        content=[TextBlock(text="Test assistant response")], model="claude-3-opus"
    )


@pytest.fixture
def assistant_message_with_tools():
    """Create an AssistantMessage with tool use blocks."""
    return AssistantMessage(
        content=[
            TextBlock(text="I'll help with that."),
            ToolUseBlock(id="tool_1", name="WebSearch", input={"query": "test search"}),
            TextBlock(text="Processing results..."),
        ],
        model="claude-3-opus",
    )


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_claude_client():
    """Create a mock Claude client."""
    client = MagicMock()
    # Setup basic response structure
    response = MagicMock()
    response.content = "Mock response"
    client.messages.create = MagicMock(return_value=response)
    return client


# ============================================================================
# Data Fixtures
# ============================================================================


@pytest.fixture
def sample_idea():
    """Sample business idea for testing."""
    return "AI-powered fitness coaching app for seniors"


@pytest.fixture
def sample_idea_slug():
    """Slug version of sample idea."""
    return "ai-powered-fitness-coaching-app-for-seniors"


@pytest.fixture
def sample_feedback():
    """Sample feedback structure for testing."""
    return {
        "recommendation": "approve",
        "iteration_reason": "Analysis meets quality standards",
        "critical_issues": [],
        "improvements": [
            {
                "section": "Market Analysis",
                "issue": "Limited competitor analysis",
                "suggestion": "Add more direct competitors",
                "priority": "medium",
            }
        ],
        "minor_suggestions": ["Consider adding revenue projections"],
        "strengths": ["Strong technical feasibility", "Clear target market"],
    }


@pytest.fixture
def sample_pipeline_result():
    """Sample pipeline result for testing."""
    return {
        "success": True,
        "idea_slug": "test-idea",
        "analysis_path": "/path/to/analysis.md",
        "feedback_path": "/path/to/feedback.json",
        "iterations": 2,
        "message": None,
    }


# ============================================================================
# File Content Fixtures
# ============================================================================


@pytest.fixture
def sample_analysis_content():
    """Sample analysis markdown content."""
    return """# Business Idea Analysis: AI Fitness App

## Executive Summary
An AI-powered fitness coaching application designed specifically for seniors.

## Market Analysis
The senior fitness market is growing rapidly with increasing health awareness.

## Technical Feasibility
Built using modern AI and mobile technologies.

## Financial Projections
Estimated $1M revenue in year 1.
"""


@pytest.fixture
def sample_prompt_content():
    """Sample prompt content with includes."""
    return """You are an expert business analyst.

{{include:shared/analysis_guidelines.md}}

## Task
Analyze the following business idea: {idea}

## Output Format
Provide a structured analysis in markdown format.
"""


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def test_config():
    """Test configuration dictionary."""
    return {
        "debug": True,
        "max_iterations": 3,
        "output_dir": Path("test_output"),
        "websearch_limit": 5,
        "tools": ["WebSearch", "WebFetch", "TodoWrite"],
    }


@pytest.fixture(autouse=True)
def reset_caches():
    """Reset any cached functions before each test."""
    # Import functions that use lru_cache
    from src.utils.file_operations import load_prompt, load_template

    # Clear their caches
    load_prompt.cache_clear()
    load_template.cache_clear()

    yield

    # Optionally clear again after test
    load_prompt.cache_clear()
    load_template.cache_clear()


@pytest.fixture
def clean_logs_dir(temp_dir):
    """Ensure clean logs directory exists."""
    logs_dir = temp_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Clear any existing log handlers to avoid conflicts
    import logging

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    return logs_dir
