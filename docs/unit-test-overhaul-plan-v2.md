# Unit Test Overhaul Plan v2 - Post-Refactoring Analysis

## Executive Summary

After completing Phase 1 refactoring, we discovered that 90% of the original test plan was fundamentally flawed. Tests were testing mock behavior rather than actual business logic. This revised plan incorporates lessons learned and establishes principles for meaningful, maintainable tests.

## Critical Lessons Learned

### What Went Wrong in v1

1. **Mock-Centric Testing**: Tests verified that mocks worked, not that agents behaved correctly
2. **Over-Engineering**: Complex fixture hierarchies that weren't used
3. **Circular Logic**: Tests that mocked behavior then verified the mock
4. **Missing Core Logic**: No tests for actual agent decision points
5. **Brittle Assertions**: String matching on mock data rather than behavior verification

### What We Actually Need

1. **Behavior Testing**: Test what agents DO, not HOW they do it
2. **Minimal Mocking**: Mock only external dependencies (SDK, filesystem)
3. **Clear Success Criteria**: Agent success = file exists with valid content
4. **Error Path Testing**: Real error conditions, not mock failures

## Core Testing Principles

### 1. Test Business Logic, Not Infrastructure

❌ **BAD**: Testing that Edit tool was called with specific parameters
✅ **GOOD**: Testing that output file exists after successful run

❌ **BAD**: Verifying mock AssistantMessage content matches expected
✅ **GOOD**: Testing that agent returns Error when file creation fails

### 2. Minimal Viable Mocking

Only mock what you must:

- Claude SDK client (external dependency)
- File system operations (when testing error conditions)
- Network calls (never make real API calls)

Never mock what you shouldn't:

- Agent internal methods
- Configuration objects
- Context objects
- Type classes

### 3. Each Test Has One Clear Purpose

```python
# ❌ BAD: Testing multiple things
def test_analyst_workflow():
    # Tests config, context, SDK, file writing, validation...
    
# ✅ GOOD: Single responsibility
def test_successful_file_creation():
    # ONLY tests: file exists = Success
    
def test_failure_when_no_file_created():
    # ONLY tests: no file = Error
```

## Revised Test Structure

```bash
tests/unit/
├── base_test.py              # Minimal: just temp directory management
├── test_agents/
│   ├── test_analyst.py       # 7 focused tests
│   └── test_reviewer.py      # 4 focused tests
├── test_core/
│   ├── test_pipeline.py      # Pipeline orchestration
│   └── test_config.py        # Config validation
├── test_sdk_errors.py        # 4 SDK error scenarios
└── test_cli.py               # CLI interface tests
```

## Test Categories and Patterns

### Category 1: Core Agent Behavior

**Pattern**: Test success/failure conditions based on observable outcomes

```python
class TestAnalystAgent:
    """Test core agent behaviors."""
    
    def test_successful_file_creation(self):
        """File exists = Success."""
        # Mock SDK to simulate file creation
        # Assert agent returns Success
        # Assert file exists
    
    def test_failure_when_no_file_created(self):
        """No file = Error."""
        # Mock SDK without file creation
        # Assert agent returns Error with appropriate message
    
    def test_context_with_feedback_path(self):
        """Feedback path triggers revision mode."""
        # Create context with feedback_input_path
        # Capture prompt sent to SDK
        # Assert feedback file referenced in prompt
    
    def test_input_validation(self):
        """Empty input raises ValueError."""
        # Call with empty string
        # Assert ValueError raised
```

### Category 2: Configuration Behavior

**Pattern**: Test that configuration affects agent behavior

```python
class TestConfiguration:
    """Test configuration actually changes behavior."""
    
    def test_websearch_tool_configuration(self):
        """WebSearch in config = WebSearch in SDK call."""
        # Set config.allowed_tools = ["WebSearch"]
        # Mock SDK and capture options
        # Assert SDK called with WebSearch in allowed_tools
    
    def test_max_turns_configuration(self):
        """max_turns in config = max_turns in SDK."""
        # Set config.max_turns = 5
        # Mock SDK and capture options
        # Assert SDK called with max_turns=5
```

### Category 3: Error Handling

**Pattern**: Test real error conditions from dependencies

```python
class TestSDKErrorHandling:
    """Test handling of actual SDK errors."""
    
    def test_connection_error(self):
        """ConnectionError from SDK = Error result."""
        # Mock SDK to raise ConnectionError
        # Assert agent returns Error
        # Assert error message contains "connect"
    
    def test_timeout_error(self):
        """TimeoutError from async = Error result."""
        # Mock SDK to raise asyncio.TimeoutError
        # Assert agent returns Error
        # Assert error message contains "timeout"
    
    def test_sdk_result_error(self):
        """ResultMessage with is_error=True = Error result."""
        # Mock SDK to return error ResultMessage
        # Assert agent returns Error
```

### Category 4: Integration Points

**Pattern**: Test boundaries between components

```python
class TestPipelineIntegration:
    """Test component integration."""
    
    def test_analyst_to_reviewer_flow(self):
        """Analysis output becomes reviewer input."""
        # Mock successful analyst run
        # Assert reviewer called with analyst's output path
    
    def test_reviewer_feedback_to_analyst(self):
        """Reviewer feedback triggers analyst revision."""
        # Mock reviewer rejection
        # Assert analyst called again with feedback path
```

## Anti-Patterns to Avoid

### 1. Testing Mock Behavior

```python
# ❌ NEVER DO THIS
def test_mock_returns_correct_value():
    mock = Mock(return_value="test")
    assert mock() == "test"  # Testing the mock, not our code!
```

### 2. Over-Specifying Implementation

```python
# ❌ TOO SPECIFIC
assert mock.call_args[0][0] == "specific string"
assert mock.call_count == 3
assert mock.method_calls[1][0] == "process"

# ✅ BEHAVIOR FOCUSED
assert isinstance(result, Success)
assert output_file.exists()
```

### 3. Fixture Sprawl

```python
# ❌ UNNECESSARY FIXTURES
@pytest.fixture
def sample_feedback():
    return {"recommendation": "approve"}

@pytest.fixture  
def temp_analysis_file():
    return create_temp_file("analysis.md")

@pytest.fixture
def mock_sdk_with_success():
    return create_successful_mock()

# ✅ INLINE WHEN SIMPLE
def test_something():
    feedback = {"recommendation": "approve"}  # Clear and immediate
```

## Implementation Phases (Revised)

### Phase 1: Core Agent Tests ✅ COMPLETE

- Simplified AnalystAgent tests (7 tests)
- Simplified ReviewerAgent tests (4 tests)  
- SDK error handling tests (4 tests)
- Removed placeholder tests (interrupt handling)

**Result**: 15 high-value tests, 42% reduction from original

### Phase 2: Pipeline Orchestration (Next)

Focus on REAL orchestration logic:

```python
class TestAnalysisPipeline:
    def test_analyze_only_mode(self):
        """ANALYZE mode runs only analyst."""
        # Mock agents
        # Run pipeline with ANALYZE mode
        # Assert only analyst called, not reviewer
    
    def test_iteration_limit_enforcement(self):
        """Pipeline stops at max_iterations."""
        # Mock reviewer to always reject
        # Run pipeline with max_iterations=2
        # Assert exactly 2 iterations completed
    
    def test_early_termination_on_approval(self):
        """Pipeline stops when reviewer approves."""
        # Mock reviewer to approve first time
        # Assert only 1 iteration despite max_iterations=3
```

### Phase 3: CLI Testing

Test actual CLI behavior, not implementation:

```python
class TestCLI:
    def test_analyze_command_success(self):
        """Successful analysis shows success message."""
        # Mock pipeline.run() to return success
        # Invoke CLI
        # Assert "✅" in output
    
    def test_websearch_flag_disables_tool(self):
        """--no-websearch removes from allowed_tools."""
        # Invoke with --no-websearch
        # Capture config passed to pipeline
        # Assert "WebSearch" not in allowed_tools
```

### Phase 4: Configuration System

Test configuration validation and defaults:

```python
class TestConfiguration:
    def test_invalid_strictness_rejected(self):
        """Invalid strictness value raises ValueError."""
        with pytest.raises(ValueError):
            ReviewerConfig(strictness="invalid")
    
    def test_prompts_dir_must_exist(self):
        """Non-existent prompts_dir raises."""
        with pytest.raises(FileNotFoundError):
            AnalystConfig(prompts_dir=Path("/nonexistent"))
```

## Test Quality Metrics

### Coverage Goals

- Line coverage: 70% (focus on critical paths)
- Branch coverage: 60% (test important decisions)
- Error path coverage: 90% (all error conditions tested)

### Performance Goals

- Unit test suite: < 5 seconds
- No test > 0.5 seconds
- Parallel execution enabled

### Maintainability Goals

- No test > 50 lines
- Clear test names that describe behavior
- Minimal fixture dependencies
- Zero testing of mock behavior

## File-by-File Test Strategy

### `src/agents/analyst.py`

**Critical Logic to Test**:

- File existence check determines Success/Error
- Feedback path triggers revision mode
- Input validation (empty string check)
- Context requirement validation

**Tests Required**: 7 (current)

### `src/agents/reviewer.py`

**Critical Logic to Test**:

- Path validation (must be in analyses/)
- JSON validation of feedback file
- Success when valid JSON written
- Error when file operations fail

**Tests Required**: 4 (current)

### `src/core/pipeline.py`

**Critical Logic to Test**:

- Mode determines which agents run
- Iteration stops on approval
- Max iterations enforced
- Error propagation from agents

**Tests Required**: 5-6

### `src/cli.py`

**Critical Logic to Test**:

- Command parsing
- Flag effects on configuration
- Error display formatting
- Success message formatting

**Tests Required**: 4-5

## Common Test Utilities

### Minimal Base Class

```python
class BaseAgentTest:
    """Provides only temp directory management."""
    
    temp_dir: Path | None = None
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        yield
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
```

### No Shared Fixtures

Each test should be self-contained. If you need mock data:

```python
def test_something():
    # Define data inline for clarity
    feedback = {"recommendation": "approve"}
    # Use immediately
```

## Testing Checklist

Before writing any test, ask:

1. **What behavior am I testing?** (Not implementation)
2. **What is the observable outcome?** (File exists, error returned, etc.)
3. **Am I testing my code or the mock?** (Never test mocks)
4. **Is this the simplest way?** (Prefer inline over fixtures)
5. **Would this break if implementation changes?** (Should only break if behavior changes)

## Red Flags in Test Code

🚩 **Imports inside functions** - Move to top
🚩 **Testing mock.call_count** - Test outcomes instead
🚩 **Complex fixture hierarchies** - Inline simple data
🚩 **Testing string content of mocks** - Test behavior
🚩 **> 50 lines per test** - Split or simplify
🚩 **Unclear test names** - Name should describe behavior
🚩 **No assertions on actual result** - Must verify outcome

## Example: Good vs Bad Test

### ❌ Bad Test (Original Style)

```python
def test_websearch_integration(self, config, context):
    """Test WebSearch tool usage."""  # Vague
    with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
        # 40 lines of mock setup...
        async def mock_receive():
            from claude_code_sdk.types import (  # Import in function!
                AssistantMessage, ToolUseBlock
            )
            yield AssistantMessage(
                content=[
                    ToolUseBlock(  # Testing mock structure
                        id="tool-1",
                        name="WebSearch",
                        input={"query": "fitness app market size"}
                    ),
                ]
            )
            # More mock responses...
        
        # Eventually...
        assert "$15B" in content  # Testing mock data!
```

### ✅ Good Test (New Style)

```python
def test_websearch_tool_configuration(self, config, context):
    """Test that WebSearch tool is properly configured when allowed."""
    config.allowed_tools = ["WebSearch", "Edit"]
    
    with patch("src.agents.analyst.ClaudeSDKClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client
        
        # Minimal mock - just enough to not crash
        async def mock_receive():
            _ = context.analysis_output_path.write_text("Analysis")
            yield ResultMessage(
                subtype="success",
                duration_ms=1000,
                duration_api_ms=800,
                is_error=False,
                num_turns=1,
                session_id="test",
                total_cost_usd=0.001,
            )
        
        mock_client.receive_response = mock_receive
        agent = AnalystAgent(config)
        _ = await agent.process(TEST_IDEAS["simple"], context)
        
        # Test ONLY the behavior we care about
        MockClient.assert_called_once()
        call_kwargs = MockClient.call_args.kwargs
        assert "WebSearch" in call_kwargs["options"].allowed_tools
```

## Success Criteria for v2

- [ ] Every test has a clear behavioral purpose
- [ ] No test tests mock behavior
- [ ] All imports at file top
- [ ] No unused fixtures or base class methods
- [ ] Test names describe behavior, not implementation
- [ ] < 20 total tests for core functionality
- [ ] All tests pass in < 5 seconds
- [ ] Zero flaky tests
- [ ] Easy to understand what breaks when test fails

## Final Notes

The goal is NOT maximum coverage or testing every line. The goal is confidence that our core business logic works correctly. A small suite of well-designed tests is infinitely more valuable than hundreds of tests that verify mock behavior.

Remember: **We test to gain confidence in our code's behavior, not to achieve metrics.**

---

*This revised plan is based on actual refactoring experience and focuses on meaningful, maintainable tests that verify behavior rather than implementation.*
