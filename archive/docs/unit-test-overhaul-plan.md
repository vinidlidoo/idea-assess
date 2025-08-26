# Unit Test Overhaul Plan

## Executive Summary

Complete overhaul of unit tests to align with latest architecture and Claude SDK testing patterns. The current tests are outdated, referencing old interfaces and using inconsistent mocking patterns. This plan modernizes the test suite using AsyncMock, proper Claude SDK mocking, and consistent patterns from the official SDK tests.

## Current State Analysis

### Problems with Existing Tests

1. **Outdated Interfaces**
   - Tests reference old classes like `ClaudeSDKClient` (doesn't exist in SDK)
   - Using incorrect context/config structures
   - Missing proper type imports

2. **Inconsistent Mocking**
   - Mix of Mock and AsyncMock without clear pattern
   - Incorrect SDK component mocking
   - Not following SDK's async generator patterns

3. **Limited Coverage**
   - No tests for `pipeline.py` core orchestration
   - No tests for `config.py` factory functions
   - Missing agent base class tests
   - No CLI testing

4. **Technical Debt**
   - Tests marked with "TODO" comments
   - Security tests with `pytest.skip()`
   - Deprecated compatibility methods referenced

### Current Test Files

- `test_interrupt.py` - Tests interrupt handling (needs SDK mock fixes)
- `test_logger.py` - Tests logger class (mostly functional, minor updates needed)
- `test_pipeline_helpers.py` - Tests pipeline helpers (needs update for new architecture)
- `test_prompt_extraction.py` - Tests prompt loading (functional, keep as-is)
- `test_prompt_includes.py` - Tests include mechanism (functional, keep as-is)
- `test_run_analytics.py` - Basic analytics tests (needs expansion)
- `test_security.py` - Security tests (incomplete, needs fixes)

## Proposed Test Structure

### Core Test Organization

```text
tests/unit/
├── test_agents/
│   ├── test_analyst.py       # AnalystAgent tests
│   ├── test_reviewer.py      # ReviewerAgent tests
│   └── test_base.py          # BaseAgent abstract class tests
├── test_core/
│   ├── test_config.py         # Config classes and factory
│   ├── test_pipeline.py      # Pipeline orchestration
│   ├── test_types.py          # Type definitions
│   └── test_run_analytics.py # Analytics (expanded)
├── test_utils/
│   ├── test_logger.py         # Logger (keep, minor updates)
│   ├── test_file_ops.py      # File operations (keep)
│   ├── test_text_processing.py # Text utilities
│   ├── test_json_validator.py # JSON validation
│   └── test_result_formatter.py # Result formatting
└── test_cli.py               # CLI interface tests
```

## Implementation Approach

### Phase 1: Core Infrastructure (Priority 1)

#### 1. Create Test Fixtures Module (`tests/fixtures/mock_sdk.py`)

```python
"""Shared fixtures for mocking Claude SDK components."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from claude_code_sdk.types import (
    AssistantMessage, 
    TextBlock, 
    ToolUseBlock,
    ResultMessage,
    UserMessage
)

def create_mock_sdk_client():
    """Create a properly configured mock SDK client with context manager support."""
    mock_client = AsyncMock(spec=ClaudeSDKClient)
    
    # Mock the async context manager
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    # Mock query method (doesn't return anything, just sends)
    mock_client.query = AsyncMock()
    
    # Mock receive_response as async generator
    async def mock_receive_response():
        """Mock the SDK receive_response generator."""
        # Yield assistant message with correct structure
        yield AssistantMessage(
            content=[TextBlock(text="Test response")],
            model="claude-opus-4-1-20250805"
        )
        
        # Yield result message with correct fields
        yield ResultMessage(
            duration_ms=1000,
            is_error=False,
            num_turns=1,
            session_id="test-session",
            total_cost_usd=0.001
        )
    
    mock_client.receive_response = mock_receive_response
    return mock_client

def create_mock_websearch_response():
    """Create mock WebSearch tool use as part of AssistantMessage."""
    return AssistantMessage(
        content=[
            ToolUseBlock(
                id="tool-1",
                name="WebSearch",
                input={"query": "test search"}
            ),
            TextBlock(text="Based on the search results...")
        ],
        model="claude-opus-4-1-20250805"
    )

def create_mock_edit_response():
    """Create mock Edit tool use."""
    return AssistantMessage(
        content=[
            ToolUseBlock(
                id="tool-2",
                name="Edit",
                input={
                    "file_path": "/path/to/file.md",
                    "old_string": "old content",
                    "new_string": "new content"
                }
            )
        ],
        model="claude-opus-4-1-20250805"
    )
```

#### 2. Base Test Class (`tests/unit/base_test.py`)

```python
"""Base test class with common setup."""

import pytest
import pytest_asyncio
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, AsyncMock

class BaseAgentTest:
    """Base class for agent tests."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_sdk_client(self):
        """Mock the ClaudeSDKClient class."""
        with patch('claude_code_sdk.ClaudeSDKClient') as MockClient:
            from tests.fixtures.mock_sdk import create_mock_sdk_client
            mock_instance = create_mock_sdk_client()
            MockClient.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def sample_feedback(self):
        """Sample reviewer feedback."""
        return {
            "recommendation": "reject",
            "critical_issues": ["Missing market size", "No competition analysis"],
            "improvement_suggestions": ["Add TAM analysis", "Include competitor matrix"],
            "strengths": ["Clear problem statement"]
        }
```

#### 3. Test Data Fixtures (`tests/fixtures/test_data.py`)

```python
"""Centralized test data for consistency."""

from pathlib import Path

TEST_IDEAS = {
    "simple": "AI fitness app",
    "complex": "Blockchain-based supply chain optimization platform for pharmaceutical cold chain logistics",
    "invalid": "",
    "with_special_chars": "AI-powered café & restaurant finder",
}

SAMPLE_ANALYSES = {
    "minimal": """# Business Analysis

## Market Opportunity
The market exists.

## Competition
There are competitors.
""",
    "complete": """# Comprehensive Business Analysis

## Executive Summary
A detailed executive summary with key insights...

## Market Opportunity
TAM of $50B with 15% annual growth...

## Competition Analysis
Three main competitors identified...

## Business Model
Subscription-based SaaS model...

## Go-to-Market Strategy
Direct sales combined with PLG...

## Financial Projections
Break-even in 18 months...

## Risks and Mitigation
Key risks identified with mitigation strategies...
"""
}

def load_test_prompt(name: str) -> str:
    """Load a test prompt file."""
    test_prompts_dir = Path(__file__).parent / "test_prompts"
    return (test_prompts_dir / name).read_text()
```

### Phase 2: Agent Tests (Priority 1)

#### 1. Test AnalystAgent (`test_agents/test_analyst.py`)

```python
"""Tests for AnalystAgent."""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path
import json

from src.agents.analyst import AnalystAgent
from src.core.types import AnalystConfig, AnalystContext, Success, Error
from tests.fixtures.test_data import TEST_IDEAS, SAMPLE_ANALYSES

class TestAnalystAgent:
    """Test the AnalystAgent class."""
    
    @pytest.fixture
    def config(self):
        """Create analyst configuration."""
        return AnalystConfig(
            max_turns=10,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/analyst/system.md",
            allowed_tools=["WebSearch", "Edit"],
            max_websearches=5,
            min_words=1000
        )
    
    @pytest.fixture
    def context(self, tmp_path):
        """Create analyst context."""
        output_file = tmp_path / "analysis.md"
        output_file.write_text("")  # Create empty file
        
        return AnalystContext(
            iteration=1,
            idea_slug="test-idea",
            analysis_output_path=output_file,
            feedback_input_path=None,
            websearch_count=0
        )
    
    @pytest.mark.asyncio
    async def test_initial_analysis(self, config, context):
        """Test initial analysis generation."""
        with patch('claude_code_sdk.ClaudeSDKClient') as MockClient:
            # Create mock client
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client
            
            # Mock receive_response
            async def mock_receive():
                from claude_code_sdk.types import AssistantMessage, TextBlock, ResultMessage
                
                yield AssistantMessage(
                    content=[TextBlock(text="# Test Analysis\n\nMarket analysis content...")],
                    model="claude-opus-4-1-20250805"
                )
                yield ResultMessage(
                    duration_ms=1000,
                    is_error=False,
                    num_turns=1,
                    session_id="test",
                    total_cost_usd=0.001
                )
            
            mock_client.receive_response = mock_receive
            
            # Create agent and process
            agent = AnalystAgent(config)
            result = await agent.process("AI fitness app", context)
            
            # Verify success
            assert isinstance(result, Success)
            
            # Verify file was written
            content = context.analysis_output_path.read_text()
            assert "# Test Analysis" in content
            
            # Verify SDK client was created with correct options
            MockClient.assert_called_once()
            call_kwargs = MockClient.call_args.kwargs
            assert call_kwargs['options'].allowed_tools == ["WebSearch", "Edit"]
    
    def test_revision_with_feedback(self, config, context, tmp_path):
        """Test revision based on feedback."""
        # Create feedback file
        feedback_file = tmp_path / "feedback.json"
        feedback_file.write_text('''{
            "recommendation": "reject",
            "critical_issues": ["Missing market size", "No competition analysis"],
            "improvement_suggestions": ["Add TAM analysis", "Include competitor matrix"]
        }''')
        
        context.feedback_input_path = feedback_file
        
        async def _test():
            with patch('claude_code_sdk.query') as mock_query:
                # Mock response
                async def mock_generator(*args, **kwargs):
                    from claude_code_sdk import AssistantMessage
                    from claude_code_sdk.types import TextBlock
                    
                    # Check that feedback was included in prompt
                    prompt = kwargs['prompt']
                    assert "Missing market size" in prompt
                    assert "Add TAM analysis" in prompt
                    
                    yield AssistantMessage(
                        content=[TextBlock(text="# Revised Analysis\n\nWith TAM analysis...")],
                        model="claude-opus-4-1-20250805"
                    )
                
                mock_query.return_value = mock_generator()
                
                agent = AnalystAgent(config)
                result = await agent.process("AI fitness app", context)
                
                assert isinstance(result, Success)
                content = context.analysis_output_path.read_text()
                assert "Revised Analysis" in content
        
        anyio.run(_test)
    
    @pytest.mark.asyncio
    async def test_websearch_integration(self, config, context):
        """Test WebSearch tool usage."""
        with patch('claude_code_sdk.ClaudeSDKClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client
            
            async def mock_receive():
                from claude_code_sdk.types import (
                    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage
                )
                
                # First message with tool use
                yield AssistantMessage(
                    content=[
                        ToolUseBlock(
                            id="tool-1",
                            name="WebSearch",
                            input={"query": "fitness app market size"}
                        ),
                        TextBlock(text="Searching for market data...")
                    ],
                    model="claude-opus-4-1-20250805"
                )
                
                # Second message with analysis incorporating search results
                yield AssistantMessage(
                    content=[TextBlock(text="# Analysis\n\nBased on research, the fitness app market is valued at $15B...")],
                    model="claude-opus-4-1-20250805"
                )
                
                yield ResultMessage(
                    duration_ms=2000,
                    is_error=False,
                    num_turns=2,
                    session_id="test",
                    total_cost_usd=0.002
                )
            
            mock_client.receive_response = mock_receive
            
            agent = AnalystAgent(config)
            result = await agent.process("AI fitness app", context)
            
            assert isinstance(result, Success)
            content = context.analysis_output_path.read_text()
            assert "$15B" in content
    
    def test_error_handling(self, config, context):
        """Test error handling in agent."""
        async def _test():
            with patch('claude_code_sdk.query') as mock_query:
                # Mock an error
                mock_query.side_effect = Exception("API error")
                
                agent = AnalystAgent(config)
                result = await agent.process("AI fitness app", context)
                
                assert isinstance(result, Error)
                assert "API error" in result.message
        
        anyio.run(_test)
```

#### 2. Test ReviewerAgent (`test_agents/test_reviewer.py`)

```python
"""Tests for ReviewerAgent."""

import pytest
import anyio
from unittest.mock import patch
import json
from pathlib import Path

from src.agents.reviewer import ReviewerAgent
from src.core.types import ReviewerConfig, ReviewerContext, Success, Error

class TestReviewerAgent:
    """Test the ReviewerAgent class."""
    
    @pytest.fixture
    def config(self):
        """Create reviewer configuration."""
        return ReviewerConfig(
            max_turns=5,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/reviewer/system.md",
            allowed_tools=[],
            max_iterations=3,
            strictness="normal"
        )
    
    @pytest.fixture
    def context(self, tmp_path):
        """Create reviewer context."""
        # Create analysis file to review
        analysis_file = tmp_path / "analysis.md"
        analysis_file.write_text("""# Test Analysis
        
## Market Opportunity
The market is large.

## Competition
There are competitors.

## Business Model
Subscription-based.
""")
        
        # Create output file
        feedback_file = tmp_path / "feedback.json"
        feedback_file.write_text("")
        
        return ReviewerContext(
            iteration=1,
            analysis_input_path=analysis_file,
            feedback_output_path=feedback_file
        )
    
    def test_review_approval(self, config, context):
        """Test review that approves analysis."""
        async def _test():
            with patch('claude_code_sdk.query') as mock_query:
                async def mock_generator(*args, **kwargs):
                    from claude_code_sdk import AssistantMessage
                    from claude_code_sdk.types import TextBlock
                    
                    feedback = {
                        "recommendation": "approve",
                        "critical_issues": [],
                        "improvement_suggestions": ["Consider adding financial projections"],
                        "strengths": ["Good market analysis", "Clear business model"]
                    }
                    
                    yield AssistantMessage(
                        content=[TextBlock(text=json.dumps(feedback, indent=2))],
                        model="claude-opus-4-1-20250805"
                    )
                
                mock_query.return_value = mock_generator()
                
                agent = ReviewerAgent(config)
                result = await agent.process("", context)
                
                assert isinstance(result, Success)
                
                # Verify feedback was written
                feedback_data = json.loads(context.feedback_output_path.read_text())
                assert feedback_data["recommendation"] == "approve"
                assert len(feedback_data["critical_issues"]) == 0
        
        anyio.run(_test)
    
    def test_review_rejection(self, config, context):
        """Test review that rejects analysis."""
        async def _test():
            with patch('claude_code_sdk.query') as mock_query:
                async def mock_generator(*args, **kwargs):
                    from claude_code_sdk import AssistantMessage
                    from claude_code_sdk.types import TextBlock
                    
                    feedback = {
                        "recommendation": "reject",
                        "critical_issues": [
                            "Missing TAM analysis",
                            "No competitive advantages identified",
                            "Weak go-to-market strategy"
                        ],
                        "improvement_suggestions": [
                            "Add detailed TAM calculation",
                            "Identify unique value proposition",
                            "Develop GTM strategy"
                        ]
                    }
                    
                    yield AssistantMessage(
                        content=[TextBlock(text=json.dumps(feedback, indent=2))],
                        model="claude-opus-4-1-20250805"
                    )
                
                mock_query.return_value = mock_generator()
                
                agent = ReviewerAgent(config)
                result = await agent.process("", context)
                
                assert isinstance(result, Success)
                
                feedback_data = json.loads(context.feedback_output_path.read_text())
                assert feedback_data["recommendation"] == "reject"
                assert len(feedback_data["critical_issues"]) == 3
        
        anyio.run(_test)
```

### Phase 3: Pipeline Tests (Priority 1)

#### Test Pipeline (`test_core/test_pipeline.py`)

```python
"""Tests for AnalysisPipeline."""

import pytest
import anyio
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from src.core.pipeline import AnalysisPipeline, PipelineMode
from src.core.config import SystemConfig, AnalystConfig, ReviewerConfig

class TestAnalysisPipeline:
    """Test the AnalysisPipeline class."""
    
    @pytest.fixture
    def configs(self, tmp_path):
        """Create pipeline configurations."""
        system_config = SystemConfig(
            project_root=tmp_path,
            analyses_dir=tmp_path / "analyses",
            logs_dir=tmp_path / "logs",
            prompts_dir=Path("config/prompts")
        )
        
        analyst_config = AnalystConfig(
            max_turns=10,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/analyst/system.md",
            allowed_tools=["WebSearch"],
            max_websearches=5,
            min_words=1000
        )
        
        reviewer_config = ReviewerConfig(
            max_turns=5,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/reviewer/system.md",
            allowed_tools=[],
            max_iterations=3,
            strictness="normal"
        )
        
        return system_config, analyst_config, reviewer_config
    
    def test_analyze_only_mode(self, configs, tmp_path):
        """Test ANALYZE mode (no review)."""
        system_config, analyst_config, reviewer_config = configs
        
        async def _test():
            # Mock the agents
            with patch('src.core.pipeline.AnalystAgent') as MockAnalyst:
                mock_analyst = AsyncMock()
                MockAnalyst.return_value = mock_analyst
                
                # Mock successful analysis
                from src.core.types import Success
                mock_analyst.process.return_value = Success()
                
                # Create pipeline
                pipeline = AnalysisPipeline(
                    idea="AI fitness app",
                    system_config=system_config,
                    analyst_config=analyst_config,
                    reviewer_config=reviewer_config,
                    mode=PipelineMode.ANALYZE
                )
                
                # Run pipeline
                result = await pipeline.run()
                
                # Verify result
                assert result["success"] is True
                assert result["idea"] == "AI fitness app"
                assert result["slug"] == "ai-fitness-app"
                assert result["iterations_completed"] == 1
                
                # Verify analyst was called
                mock_analyst.process.assert_called_once()
        
        anyio.run(_test)
    
    def test_analyze_and_review_mode(self, configs, tmp_path):
        """Test ANALYZE_AND_REVIEW mode with iterations."""
        system_config, analyst_config, reviewer_config = configs
        
        async def _test():
            with patch('src.core.pipeline.AnalystAgent') as MockAnalyst, \
                 patch('src.core.pipeline.ReviewerAgent') as MockReviewer:
                
                mock_analyst = AsyncMock()
                mock_reviewer = AsyncMock()
                MockAnalyst.return_value = mock_analyst
                MockReviewer.return_value = mock_reviewer
                
                from src.core.types import Success
                
                # First iteration: analyst succeeds, reviewer rejects
                mock_analyst.process.side_effect = [Success(), Success()]
                
                # Mock reviewer: reject first, approve second
                async def review_side_effect(*args, **kwargs):
                    # Write feedback based on call count
                    context = args[1]
                    if mock_reviewer.process.call_count == 1:
                        feedback = {
                            "recommendation": "reject",
                            "critical_issues": ["Missing details"]
                        }
                    else:
                        feedback = {
                            "recommendation": "approve",
                            "critical_issues": []
                        }
                    
                    context.feedback_output_path.write_text(
                        json.dumps(feedback)
                    )
                    return Success()
                
                mock_reviewer.process.side_effect = review_side_effect
                
                pipeline = AnalysisPipeline(
                    idea="AI fitness app",
                    system_config=system_config,
                    analyst_config=analyst_config,
                    reviewer_config=reviewer_config,
                    mode=PipelineMode.ANALYZE_AND_REVIEW
                )
                
                result = await pipeline.run()
                
                assert result["success"] is True
                assert result["iterations_completed"] == 2
                
                # Verify both agents were called
                assert mock_analyst.process.call_count == 2
                assert mock_reviewer.process.call_count == 2
        
        anyio.run(_test)
```

### Phase 4: Config Tests (Priority 2)

```python
"""Tests for configuration system."""

import pytest
from pathlib import Path

from src.core.config import (
    SystemConfig, AnalystConfig, ReviewerConfig,
    create_default_configs
)

class TestConfigSystem:
    """Test configuration classes and factory."""
    
    def test_create_default_configs(self, tmp_path):
        """Test default config creation."""
        system, analyst, reviewer = create_default_configs(tmp_path)
        
        # System config
        assert system.project_root == tmp_path
        assert system.analyses_dir == tmp_path / "analyses"
        assert system.logs_dir == tmp_path / "logs"
        
        # Analyst config
        assert analyst.max_turns == 25
        assert analyst.max_websearches == 10
        assert analyst.min_words == 3000
        assert "WebSearch" in analyst.allowed_tools
        
        # Reviewer config
        assert reviewer.max_iterations == 3
        assert reviewer.strictness == "normal"
        assert len(reviewer.allowed_tools) == 2  # Read and Edit
    
    def test_config_modification(self):
        """Test direct config modification pattern."""
        config = AnalystConfig(
            max_turns=10,
            prompts_dir=Path("prompts"),
            system_prompt="default.md",
            allowed_tools=["WebSearch"]
        )
        
        # Direct modification
        config.system_prompt = "experimental/custom.md"
        config.allowed_tools = []
        
        assert config.system_prompt == "experimental/custom.md"
        assert config.allowed_tools == []
```

### Phase 5: CLI Tests (Priority 2)

```python
"""Tests for CLI interface."""

import pytest
from unittest.mock import patch, AsyncMock
from click.testing import CliRunner

from src.cli import cli

class TestCLI:
    """Test the CLI interface."""
    
    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    def test_analyze_command(self, runner):
        """Test analyze command."""
        with patch('src.cli.AnalysisPipeline') as MockPipeline:
            mock_pipeline = AsyncMock()
            MockPipeline.return_value = mock_pipeline
            mock_pipeline.run.return_value = {
                "success": True,
                "idea": "test idea",
                "slug": "test-idea",
                "analysis_file": "analyses/test-idea/analysis.md",
                "iterations_completed": 1
            }
            
            result = runner.invoke(cli, ['analyze', 'test idea'])
            
            assert result.exit_code == 0
            assert "✅ Analysis complete" in result.output
            
            # Verify pipeline was created with correct args
            MockPipeline.assert_called_once()
            call_args = MockPipeline.call_args
            assert call_args.kwargs["idea"] == "test idea"
    
    def test_analyze_with_options(self, runner):
        """Test analyze command with options."""
        with patch('src.cli.AnalysisPipeline') as MockPipeline:
            mock_pipeline = AsyncMock()
            MockPipeline.return_value = mock_pipeline
            mock_pipeline.run.return_value = {"success": True}
            
            result = runner.invoke(cli, [
                'analyze', 'test idea',
                '--no-websearch',
                '--analyst-prompt', 'custom.md',
                '--max-iterations', '5'
            ])
            
            assert result.exit_code == 0
            
            # Verify configs were modified
            call_args = MockPipeline.call_args
            analyst_config = call_args.kwargs["analyst_config"]
            reviewer_config = call_args.kwargs["reviewer_config"]
            
            assert analyst_config.allowed_tools == []
            assert analyst_config.system_prompt == "custom.md"
            assert reviewer_config.max_iterations == 5
```

### Phase 6: SDK Error Handling Tests (Priority 1)

```python
"""Tests for SDK error handling."""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from claude_code_sdk._errors import (
    CLINotFoundError, 
    CLIConnectionError, 
    ProcessError,
    CLIJSONDecodeError
)

from src.agents.analyst import AnalystAgent
from src.core.types import AnalystConfig, AnalystContext, Error

class TestSDKErrorHandling:
    """Test handling of SDK-specific errors."""
    
    @pytest.fixture
    def config(self):
        return AnalystConfig(
            max_turns=10,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/analyst/system.md",
            allowed_tools=[]
        )
    
    @pytest.mark.asyncio
    async def test_cli_not_found_error(self, config, context):
        """Test CLINotFoundError handling."""
        with patch('claude_code_sdk.ClaudeSDKClient') as MockClient:
            MockClient.side_effect = CLINotFoundError(
                "Claude Code not found", 
                "/usr/local/bin/claude"
            )
            
            agent = AnalystAgent(config)
            result = await agent.process("test idea", context)
            
            assert isinstance(result, Error)
            assert "Claude Code not found" in result.message
    
    @pytest.mark.asyncio
    async def test_cli_connection_error(self, config, context):
        """Test CLIConnectionError handling."""
        with patch('claude_code_sdk.ClaudeSDKClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__.side_effect = CLIConnectionError(
                "Connection refused"
            )
            MockClient.return_value = mock_client
            
            agent = AnalystAgent(config)
            result = await agent.process("test idea", context)
            
            assert isinstance(result, Error)
            assert "Connection" in result.message
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, config, context):
        """Test rate limiting behavior."""
        with patch('claude_code_sdk.ClaudeSDKClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            async def mock_receive():
                from claude_code_sdk.types import ResultMessage
                yield ResultMessage(
                    duration_ms=1000,
                    is_error=True,
                    error_type="rate_limit",
                    error_message="Rate limit exceeded",
                    num_turns=0,
                    session_id="test",
                    total_cost_usd=0
                )
            
            mock_client.receive_response = mock_receive
            MockClient.return_value = mock_client
            
            agent = AnalystAgent(config)
            result = await agent.process("test idea", context)
            
            assert isinstance(result, Error)
            assert "rate" in result.message.lower()
```

### Phase 7: Interrupt Handling Tests (Priority 1)

```python
"""Tests for interrupt signal handling."""

import pytest
import pytest_asyncio
import asyncio
import signal
from unittest.mock import patch, AsyncMock

from src.agents.analyst import AnalystAgent
from src.core.types import AnalystConfig, AnalystContext, Error

class TestInterruptHandling:
    """Test interrupt signal handling during agent operations."""
    
    @pytest.mark.asyncio
    async def test_graceful_interrupt(self, config, context):
        """Test graceful shutdown on interrupt signal."""
        with patch('claude_code_sdk.ClaudeSDKClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            # Simulate long-running response
            async def slow_receive():
                from claude_code_sdk.types import AssistantMessage, TextBlock
                await asyncio.sleep(10)  # Long operation
                yield AssistantMessage(
                    content=[TextBlock(text="Never reached")],
                    model="claude-opus-4-1-20250805"
                )
            
            mock_client.receive_response = slow_receive
            MockClient.return_value = mock_client
            
            agent = AnalystAgent(config)
            
            # Start processing
            task = asyncio.create_task(
                agent.process("test idea", context)
            )
            
            # Wait briefly then interrupt
            await asyncio.sleep(0.1)
            task.cancel()
            
            # Should handle cancellation gracefully
            with pytest.raises(asyncio.CancelledError):
                await task
    
    @pytest.mark.asyncio
    async def test_interrupt_during_websearch(self, config, context):
        """Test interrupt during tool use."""
        config.allowed_tools = ["WebSearch"]
        
        with patch('claude_code_sdk.ClaudeSDKClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            async def mock_receive():
                from claude_code_sdk.types import AssistantMessage, ToolUseBlock
                
                # Yield tool use then pause
                yield AssistantMessage(
                    content=[
                        ToolUseBlock(
                            id="tool-1",
                            name="WebSearch",
                            input={"query": "test"}
                        )
                    ],
                    model="claude-opus-4-1-20250805"
                )
                await asyncio.sleep(10)  # Simulate slow search
            
            mock_client.receive_response = mock_receive
            MockClient.return_value = mock_client
            
            agent = AnalystAgent(config)
            task = asyncio.create_task(
                agent.process("test idea", context)
            )
            
            await asyncio.sleep(0.1)
            task.cancel()
            
            with pytest.raises(asyncio.CancelledError):
                await task
```

## Testing Best Practices

### 1. Async Testing Pattern

Use `pytest-asyncio` with `@pytest.mark.asyncio` decorator:

```python
@pytest.mark.asyncio
async def test_async_function(self):
    # Direct async test code
    result = await async_function()
    assert result == expected
```

### 2. Mock Claude SDK Properly

```python
with patch('claude_code_sdk.ClaudeSDKClient') as MockClient:
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    async def mock_receive():
        from claude_code_sdk.types import AssistantMessage, TextBlock, ResultMessage
        yield AssistantMessage(
            content=[TextBlock(text="response")],
            model="claude-opus-4-1-20250805"
        )
        yield ResultMessage(
            duration_ms=1000,
            is_error=False,
            num_turns=1,
            session_id="test",
            total_cost_usd=0.001
        )
    
    mock_client.receive_response = mock_receive
    MockClient.return_value = mock_client
```

### 3. File System Testing

Use `tmp_path` fixture for isolated file operations:

```python
def test_with_files(self, tmp_path):
    test_file = tmp_path / "test.md"
    test_file.write_text("content")
    # Test with real files
```

### 4. Configuration Testing

Test direct modification pattern:

```python
config = AnalystConfig(...)
config.field = new_value  # Direct modification
assert config.field == new_value
```

## Migration Strategy

### Phase 1: Critical Infrastructure (Days 1-3)

1. **Day 1**:
   - Fix SDK mock patterns based on actual SDK types
   - Create test fixtures and base classes
   - Set up pytest-asyncio configuration

2. **Day 2-3**:
   - Write AnalystAgent tests with correct mocking
   - Write ReviewerAgent tests
   - Add SDK error handling tests
   - Add interrupt handling tests

### Phase 2: Core Coverage (Days 4-6)

1. **Day 4**:
   - Write Pipeline orchestration tests
   - Test iteration logic and mode switching

2. **Day 5**:
   - Config and type system tests
   - Utility function tests

3. **Day 6**:
   - CLI tests with Click testing
   - Integration test updates

### Phase 3: Polish & Documentation (Days 7-8)

1. **Day 7**:
   - Add edge case tests
   - Performance benchmarking
   - Mock validation tests

2. **Day 8**:
   - Documentation updates
   - Test coverage report
   - Final cleanup

## Success Metrics

- [ ] 80% code coverage minimum
- [ ] All tests pass with `pytest tests/unit`
- [ ] Tests run in < 10 seconds
- [ ] No deprecated interfaces used
- [ ] Consistent mocking patterns
- [ ] Clear test names and documentation

## Dependencies

- pytest >= 7.0
- pytest-asyncio >= 0.21  # Critical for async test support
- pytest-mock >= 3.0     # Better mocking integration
- unittest.mock (standard library)
- click >= 8.0 (for CLI testing)

## Notes

1. **Don't test the SDK itself** - Mock it completely
2. **Focus on business logic** - Test our code, not libraries
3. **Keep tests fast** - No real API calls or slow operations
4. **Test edge cases** - Errors, empty inputs, malformed data
5. **Document intent** - Clear test names and docstrings

---

*This plan prioritizes getting core agent and pipeline tests working first, as these are the most critical components. The existing prompt tests that work can be kept with minor updates.*
