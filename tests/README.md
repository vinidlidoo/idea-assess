# Testing Strategy

## Overview

Comprehensive test suite with behavior-focused testing and strategic mocking at integration boundaries.

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

## Current Test Suite (107 tests, ~20s, 81% coverage)

### Test Structure

```text
tests/unit/
├── test_agents/              # Agent tests (analyst, reviewer, fact_checker)
├── test_core/                # Core logic (config, pipeline, analytics)
├── test_utils/               # Utilities (file_ops, json, logger, etc.)
├── test_cli.py              # CLI interface tests
└── test_sdk_errors.py        # SDK error handling
```

### Key Test Categories

- **Agents** (27 tests): Analyst, Reviewer, FactChecker behavior
- **Core** (28 tests): Pipeline, config, analytics
- **Utils** (45 tests): File ops, validation, logging
- **CLI** (7 tests): Command parsing, flag effects

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

## Coverage Report

**Current**: 81% coverage (107 tests, ~20s execution)

**Well-Covered** (>90%): types, file_operations, text_processing  
**Needs Work** (<80%): agent_base, some error paths

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

*Test Count: 107 tests | Coverage: 81% | Execution: ~20s*
