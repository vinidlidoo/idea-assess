# Testing Strategy for idea-assess

## Overview

This document outlines our testing philosophy following the comprehensive unit test implementation completed on 2025-08-26. The test suite has been significantly expanded to achieve 88% code coverage while maintaining fast execution times.

## Testing Philosophy

### Core Principles

1. **Behavior Over Implementation**: Test what agents DO, not HOW they do it
2. **Minimal Viable Mocking**: Mock only external dependencies (SDK, filesystem when testing errors)
3. **Clear Success Criteria**: Each test has one clear purpose with observable outcomes
4. **Fast and Focused**: Entire suite runs in < 1 second
5. **Comprehensive Coverage**: Target critical paths and business logic

### What We Test vs What We Don't

**✅ We Test:**

- File existence determines Success/Error
- Configuration affects agent behavior
- Pipeline orchestration logic
- Error propagation from dependencies
- CLI argument parsing and effects
- Utility functions (text processing, validation, formatting)
- SDK error handling patterns

**❌ We Don't Test:**

- Mock behavior itself
- SDK internal operations
- Implementation details
- Method call counts (unless critical)
- CLI main entry point (requires full system)

## Current Test Suite (109 tests, ~0.6s, 88% coverage)

### Unit Tests Structure (`tests/unit/`)

```text
tests/unit/
├── base_test.py                  # Base test class with temp dir management
├── conftest.py                   # Shared pytest fixtures
├── test_cli.py                   # 8 CLI behavior tests
├── test_agents/
│   ├── test_analyst.py          # 10 agent behavior tests
│   └── test_reviewer.py         # 10 reviewer tests with helpers
├── test_core/
│   ├── test_config.py           # 8 configuration tests
│   ├── test_pipeline.py         # 7 orchestration tests
│   └── test_run_analytics.py    # 13 analytics tracking tests
└── test_utils/
    ├── test_file_operations.py  # 12 file handling tests
    ├── test_json_validator.py   # 12 validation tests
    ├── test_logger.py           # 15 logging tests
    ├── test_result_formatter.py # 5 formatting tests
    └── test_text_processing.py  # 9 slug generation tests
```

### Test Categories

#### 1. Agent Tests (20 tests)

- **Analyst**: File creation, feedback handling, tool configuration, error cases
- **Reviewer**: Feedback JSON creation, path validation, recommendation handling

#### 2. Pipeline Tests (7 tests)

- Mode selection (ANALYZE vs ANALYZE_AND_REVIEW)
- Iteration limits and early termination
- Error propagation
- Directory/symlink creation

#### 3. CLI Tests (8 tests)

- Command parsing and flag effects
- Configuration overrides (--no-web-tools, --with-review)
- Output formatting (success/error markers)
- Argument validation

#### 4. Configuration Tests (8 tests)

- Defaults and modifications
- Path resolution to absolute paths
- Tool configuration and copying
- Config factory functions

#### 5. Utility Tests (49 tests)

- **File Operations**: Prompt/template loading with caching
- **JSON Validation**: Feedback schema validation and fixing
- **Logger**: Setup, SDK error detection, message formatting
- **Result Formatter**: Pipeline result display
- **Text Processing**: Slug creation from ideas
- **Run Analytics**: Agent metrics, tool tracking, cost calculation

#### 6. Core Tests (17 tests)

- **Run Analytics**: Message tracking, agent metrics, tool correlation
- **Pipeline**: Orchestration, iteration control, mode handling

## Running Tests

### All Unit Tests

```bash
pytest tests/unit/ -xvs
```

### With Coverage Report

```bash
# Terminal report with missing lines
pytest tests/unit/ --cov=src --cov-report=term-missing

# HTML report for detailed browsing
pytest tests/unit/ --cov=src --cov-report=html
# Then open htmlcov/index.html in browser
```

### Specific Test Categories

```bash
# Agent tests only
pytest tests/unit/test_agents/ -xvs

# Utility tests only
pytest tests/unit/test_utils/ -xvs

# Core logic tests
pytest tests/unit/test_core/ -xvs
```

### Single Test File

```bash
pytest tests/unit/test_utils/test_text_processing.py -xvs
```

### Single Test Method

```bash
pytest tests/unit/test_cli.py::TestCLI::test_analyze_command_success -xvs
```

### Quick Run (minimal output)

```bash
pytest tests/unit/ -q --tb=no
```

### Debug Failed Tests

```bash
# Stop on first failure with full traceback
pytest tests/unit/ -x --tb=long

# Show local variables in traceback
pytest tests/unit/ -l

# Capture print statements
pytest tests/unit/ -s
```

## Shared Fixtures (conftest.py)

The `tests/conftest.py` file provides shared fixtures automatically available to all tests:

```python
@pytest.fixture
def temp_path() -> Path
    # Provides temporary directory

@pytest.fixture
def mock_sdk_client() -> AsyncMock
    # Properly configured Claude SDK mock

@pytest.fixture
def mock_result_message() -> ResultMessage
    # Sample SDK result message

@pytest.fixture(autouse=True)
def reset_caches()
    # Clears @lru_cache before each test
```

## Testing Patterns

### Helper Methods Pattern

```python
class TestReviewerAgent(BaseAgentTest):
    def _create_mock_client(self):
        """Helper to create a properly configured mock client."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    def _create_result_message(self, is_error=False):
        """Helper to create a ResultMessage."""
        return ResultMessage(
            subtype="error" if is_error else "success",
            duration_ms=1000,
            is_error=is_error,
            # ... other fields
        )
```

### Good Test Example

```python
@pytest.mark.asyncio
async def test_successful_file_creation(self, config, context):
    """Test that agent returns Success when output file is created."""
    with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
        mock_client = self._create_mock_client()
        MockClient.return_value = mock_client
        
        async def mock_receive():
            # Simulate file being created (the behavior that matters)
            context.analysis_output_path.write_text("# Analysis\nContent")
            yield self._create_result_message(is_error=False)
        
        mock_client.receive_response = mock_receive
        agent = AnalystAgent(config)
        result = await agent.process(idea, context)
        
        # Test ONLY the behavior we care about
        assert isinstance(result, Success)
        assert context.analysis_output_path.exists()
```

## Type Safety

### Handling Type Warnings

Most warnings are from mock assertions and are expected. Use targeted ignores:

```python
# For mock assertions
assert mock.process.call_count == 2  # pyright: ignore[reportAny]

# For test data
output = mock_stdout.getvalue()  # pyright: ignore[reportAny]

# For inner functions
async def mock_function(*_args: Any, **_kwargs: Any) -> None:
    ...
```

## Coverage Report Interpretation

Current coverage: **88%** (1029 statements, 122 missed)

### Well-Covered Modules (>90%)

- `types.py` (100%) - Type definitions
- `file_operations.py` (100%) - File handling utilities
- `result_formatter.py` (100%) - Output formatting
- `text_processing.py` (100%) - Text utilities
- `config.py` (98%) - Configuration classes
- `logger.py` (93%) - Logging setup
- `pipeline.py` (91%) - Orchestration logic

### Modules Needing More Coverage (<85%)

- `agent_base.py` (77%) - Abstract base class
- `json_validator.py` (80%) - Complex validation logic
- `reviewer.py` (83%) - Reviewer agent

### Uncovered Code Categories

1. **Error recovery paths** - Difficult to trigger edge cases
2. **CLI entry point** - Requires full system setup
3. **Analytics edge cases** - Complex tool correlation scenarios
4. **Fallback mechanisms** - Secondary error handling

## Anti-Patterns to Avoid

### ❌ Testing Mock Behavior

```python
# BAD: Testing the mock itself
assert mock.called  # Useless if mock behavior is what we control
```

### ❌ Over-Specifying Implementation

```python
# BAD: Too specific about internals
assert mock.call_args[0][0] == "specific string"

# GOOD: Focus on outcomes
assert isinstance(result, Success)
assert output_file.exists()
```

### ❌ Not Using Helpers

```python
# BAD: Repeating mock setup
mock_client = AsyncMock()
mock_client.__aenter__ = AsyncMock(return_value=mock_client)
mock_client.__aexit__ = AsyncMock(return_value=None)

# GOOD: Use helper method
mock_client = self._create_mock_client()
```

## Continuous Integration

Tests should be run:

- On every commit (pre-commit hook)
- On pull request creation
- Before merging to main
- Nightly for full regression

Target metrics:

- **Coverage**: Maintain >85%
- **Speed**: All unit tests <1 second
- **Reliability**: Zero flaky tests

## Future Testing Priorities

### High Priority

- Integration tests for full pipeline with real files
- Performance benchmarks for large analyses
- Edge cases for network failures

### Medium Priority  

- Property-based testing for validators
- Snapshot testing for formatted output
- Concurrent pipeline execution tests

### Low Priority

- Mutation testing for coverage quality
- Fuzz testing for input validation
- Load testing for analytics system

## Maintenance

Update this document when:

- Test structure changes significantly
- New testing patterns are established
- Coverage targets change
- New test categories are added

---

*Last Updated: 2025-08-26*
*Test Count: 109 tests*
*Coverage: 88%*
*Execution Time: ~0.6s*
*Focus: Comprehensive behavior testing with high coverage*
