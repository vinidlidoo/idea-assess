# Testing Strategy for idea-assess

## Overview

This document outlines our testing philosophy following the Phase 1-4 unit test overhaul completed on 2025-08-26. The test suite has been completely rewritten to follow behavior-driven testing principles.

## Testing Philosophy

### Core Principles

1. **Behavior Over Implementation**: Test what agents DO, not HOW they do it
2. **Minimal Viable Mocking**: Mock only external dependencies (SDK, filesystem when testing errors)
3. **Clear Success Criteria**: Each test has one clear purpose with observable outcomes
4. **Fast and Focused**: Entire suite runs in < 0.2 seconds

### What We Test vs What We Don't

**✅ We Test:**

- File existence determines Success/Error
- Configuration affects agent behavior
- Pipeline orchestration logic
- Error propagation from dependencies
- CLI argument parsing and effects

**❌ We Don't Test:**

- Mock behavior
- SDK internal operations
- Implementation details
- Method call counts (unless critical)

## Current Test Suite (36 tests, ~0.14s)

### Unit Tests (`tests/unit/`)

**Structure:**

```text
tests/unit/
├── base_test.py              # Provides temp dir + mock client helper
├── test_agents/
│   ├── test_analyst.py       # 7 behavior tests
│   └── test_reviewer.py      # 4 behavior tests
├── test_core/
│   ├── test_pipeline.py      # 7 orchestration tests
│   └── test_config.py        # 7 validation tests
├── test_cli.py               # 7 CLI behavior tests
└── test_sdk_errors.py        # 4 error handling tests
```

### Test Categories

#### 1. Agent Tests (11 tests)

- **Analyst**: File creation, feedback handling, tool configuration
- **Reviewer**: Feedback JSON creation, path validation

#### 2. Pipeline Tests (7 tests)

- Mode selection (ANALYZE vs ANALYZE_AND_REVIEW)
- Iteration limits and early termination
- Error propagation
- Directory/symlink creation

#### 3. CLI Tests (7 tests)

- Command parsing and flag effects
- Configuration overrides
- Output formatting
- Argument validation

#### 4. Configuration Tests (7 tests)

- Defaults and modifications
- Path resolution
- Tool configuration

#### 5. SDK Error Tests (4 tests)

- Connection errors
- Timeouts
- Invalid JSON handling

## Testing Patterns

### Base Test Class

```python
class BaseAgentTest:
    """Provides temp directory and mock SDK client helper."""
    
    temp_dir: Path | None = None
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Creates and cleans temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        yield
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @staticmethod
    def create_mock_sdk_client() -> AsyncMock:
        """Create properly configured mock SDK client."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client
```

### Good Test Example

```python
@pytest.mark.asyncio
async def test_successful_file_creation(self, config, context):
    """Test that agent returns Success when output file is created."""
    with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
        mock_client = self.create_mock_sdk_client()
        MockClient.return_value = mock_client
        
        async def mock_receive():
            # Simulate file being created (what matters)
            _ = context.analysis_output_path.write_text("# Analysis\nContent")
            yield ResultMessage(subtype="success", ...)
        
        mock_client.receive_response = mock_receive
        agent = AnalystAgent(config)
        result = await agent.process(idea, context)
        
        # Test ONLY the behavior we care about
        assert isinstance(result, Success)
        assert context.analysis_output_path.exists()
```

## Running Tests

### All Unit Tests

```bash
pytest tests/unit/ -xvs
```

### Specific Test File

```bash
pytest tests/unit/test_agents/test_analyst.py -xvs
```

### With Coverage

```bash
pytest tests/unit/ --cov=src --cov-report=html
```

### Quick Run (no traceback)

```bash
pytest tests/unit/ -q --tb=no
```

## Anti-Patterns to Avoid

### ❌ Testing Mock Behavior

```python
# BAD: Testing the mock itself
def test_mock_returns_correct_value():
    mock = Mock(return_value="test")
    assert mock() == "test"  # Useless!
```

### ❌ Over-Specifying Implementation

```python
# BAD: Too specific
assert mock.call_args[0][0] == "specific string"
assert mock.call_count == 3
assert mock.method_calls[1][0] == "process"

# GOOD: Behavior focused
assert isinstance(result, Success)
assert output_file.exists()
```

### ❌ Complex Fixture Hierarchies

```python
# BAD: Unnecessary fixtures
@pytest.fixture
def sample_feedback():
    return {"recommendation": "approve"}

# GOOD: Inline when simple
def test_something():
    feedback = {"recommendation": "approve"}  # Clear and immediate
```

## Type Safety

### Handling Type Warnings

Most warnings are from mock assertions and are expected. Use targeted ignores:

```python
# For mock assertions
assert mock.process.call_count == 2  # pyright: ignore[reportAny]

# For inner functions needing types
async def mock_function(*_args: Any, **_kwargs: Any) -> None:
    ...
```

## Future Testing Priorities

### High Priority

- Add strictness level tests for ReviewerAgent
- Add more edge case handling (permissions, disk full)

### Medium Priority  

- Add performance benchmarks
- Integration tests for full pipeline

### Low Priority

- Property-based testing for configurations
- Mutation testing for coverage quality

## Maintenance

This document reflects the test suite after the Phase 1-4 overhaul. Update when:

- New test patterns are established
- Test organization changes
- Significant testing decisions are made

---

*Last Updated: 2025-08-26*
*Test Count: 36 tests*
*Execution Time: ~0.14s*
*Coverage Focus: Behavior and Critical Paths*
