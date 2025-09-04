# Test Harness Plan for Reviewer and FactChecker Agents

**Status Update**: Verified that `run_parallel_review_fact_check()` exists in `src/core/pipeline.py:469-513`. The parallel execution infrastructure is already implemented and functional, contrary to initial code review feedback.

## 🎯 Testing Strategy Overview

We have THREE distinct testing approaches:

### 1. Unit Tests (`tests/unit/test_agents/`)

- **Purpose**: Test individual agent methods in isolation
- **Mocking**: Everything is mocked (Claude SDK, file system)
- **Speed**: <0.1s per test
- **When to use**: Testing agent logic, error handling, edge cases

### 2. Integration Tests (`tests/integration/test_pipeline.py`)

- **Purpose**: Test pipeline orchestration and agent coordination
- **Mocking**: Agents are mocked, but pipeline logic is real
- **Speed**: <1s per test
- **When to use**: Testing iteration flow, veto logic, pipeline state management

### 3. Manual Test Scripts (`tests/manual/`)

- **Purpose**: Test REAL agents with REAL Claude API calls
- **Location**: `tests/manual/test_parallel_agents_real.py`
- **Mocking**: Nothing - uses actual Claude SDK
- **Speed**: 30-60s (real API calls)
- **When to use**: Manual testing during development, debugging prompts
- **Cost**: Uses API credits!

## 📊 Quick Reference Table

| Test Type | Location | Uses Real API? | Speed | Purpose | Run Command |
|-----------|----------|---------------|-------|---------|-------------|
| Unit Tests | `tests/unit/` | ❌ No | <0.1s | Test logic | `pytest tests/unit/test_agents/test_fact_checker.py` |
| Integration Tests | `tests/integration/` | ❌ No | <1s | Test orchestration | `pytest tests/integration/test_pipeline.py` |
| Manual Tests | `tests/manual/` | ✅ Yes | 30-60s | Test real behavior | `python tests/manual/test_parallel_agents_real.py` |

## Problem Statement

Currently, testing the Reviewer and FactChecker agents requires:

1. Running the full Analyst agent (3-5 minutes)
2. Waiting for a complete analysis to be generated
3. Only then can we test parallel execution

This slow feedback loop makes development and debugging difficult.

## Goals

Create a test harness that:

1. Tests Reviewer and FactChecker in isolation
2. Uses pre-created dummy analyses
3. Verifies parallel execution
4. Tests veto logic scenarios
5. Runs in <30 seconds

## Challenges

### 1. Pipeline Dependencies

The `run_parallel_review_fact_check()` function (confirmed to exist at `pipeline.py:469-513`) expects:

- A fully initialized `AnalysisPipeline` instance
- Proper directory structure (`analyses/{idea}/iterations/`)
- RunAnalytics for message tracking
- Iteration context and file paths

### 2. Agent Context Requirements

Both agents expect:

- `ReviewerContext` with analysis_input_path, feedback_output_path
- `FactCheckContext` with analysis_input_path, fact_check_output_path
- RunAnalytics instance for logging
- Iteration number for prompts

### 3. File System State

The agents need:

- Analysis markdown file to read
- Template JSON files for output
- Proper permissions and paths

## Integration with Existing Test Suite

### Current Test Infrastructure

The project already has a comprehensive test suite with:

- **109 unit tests** running in ~0.6s with 88% coverage
- **Base test classes** (`BaseAgentTest`) with temp directory management
- **Mock SDK fixtures** (`create_mock_sdk_client`) for Claude SDK mocking
- **Agent test patterns** for Analyst and Reviewer agents
- **pytest fixtures** in `conftest.py` for shared resources
- **6 integration tests** in `test_pipeline.py` testing full pipeline flows

### Key Insights from Existing Integration Tests

The `tests/integration/test_pipeline.py` file already demonstrates:

1. **Proper Mocking Pattern**: Mock agents are created with `AsyncMock()` and file outputs
2. **File System Testing**: Uses `tmp_path` to create actual directory structures
3. **JSON Schema**: Feedback files follow exact schema with required fields
4. **Iteration Testing**: Tests handle multiple iterations with `side_effect` lists
5. **Error Handling**: Tests verify graceful failure handling
6. **Mode Testing**: Different pipeline modes are already tested

**We should extend this file, not create new ones!**

### Where the New Tests Fit

```text
tests/
├── unit/
│   ├── test_agents/
│   │   ├── test_analyst.py      (10 tests)
│   │   ├── test_reviewer.py     (10 tests)
│   │   └── test_fact_checker.py (NEW: 10-15 tests)
│   └── test_core/
│       └── test_parallel_execution.py (NEW: 5-8 tests)
├── integration/
│   └── test_parallel_agents.py  (NEW: full parallel testing)
└── fixtures/
    ├── mock_sdk.py              (existing, will extend)
    └── test_analyses.py         (NEW: sample analysis files)
```

## Implementation Plan

### Phase 1: Extend Existing Test Infrastructure (1 hour)

#### Step 1: Create FactChecker Unit Tests

Following the existing pattern from `test_reviewer.py`:

```python
# tests/unit/test_agents/test_fact_checker.py
class TestFactCheckerAgent(BaseAgentTest):
    """Test the FactCheckerAgent class following existing patterns."""
    
    def _create_mock_client(self):
        """Reuse helper from test_reviewer.py"""
        return create_mock_sdk_client()
    
    @pytest.fixture
    def config(self) -> FactCheckerConfig:
        """Create fact-checker configuration."""
        return FactCheckerConfig(
            max_turns=5,
            prompts_dir=Path("config/prompts"),
            system_prompt="agents/fact-checker/system.md",
            allowed_tools=["WebFetch", "Edit", "TodoWrite"],
            max_verifications=3,
        )
    
    @pytest.mark.asyncio
    async def test_successful_fact_check(self, config, context):
        """Test successful fact-checking with proper JSON output."""
        # Follow pattern from test_reviewer.py::test_successful_review
        pass
    
    @pytest.mark.asyncio
    async def test_critical_issues_detection(self, config, context):
        """Test detection of critical citation issues."""
        pass
```

#### Step 2: Extend Test Fixtures

```python
# tests/fixtures/test_analyses.py (NEW)
from pathlib import Path

class TestAnalyses:
    """Provide sample analyses for testing."""
    
    GOOD_ANALYSIS = """# TestCo: AI Solution
    ## Market Size
    The market is worth $50B in 2024 [1].
    ## References
    [1] Market Report 2024. <https://example.com/report>
    """
    
    BAD_CITATIONS = """# TestCo: AI Solution  
    ## Market Size
    The market is worth $500B in 2024 [1].
    ## References
    [1] Made up source. <https://fake.com>
    """
    
    @staticmethod
    def create_analysis_file(path: Path, content_type: str = "good"):
        """Create test analysis file with specified content."""
        contents = {
            "good": TestAnalyses.GOOD_ANALYSIS,
            "bad": TestAnalyses.BAD_CITATIONS,
        }
        path.write_text(contents.get(content_type, contents["good"]))
        return path
```

#### Step 3: Test Data Generator

```python
def create_test_analysis(analysis_dir: Path, iteration: int) -> Path:
    """Create a realistic test analysis file."""
    templates = {
        "good": "analysis_with_citations.md",
        "bad": "analysis_with_errors.md",
        "minimal": "analysis_minimal.md"
    }
    # Copy from test_data/ directory
    return analysis_path
```

#### Step 3: Direct Agent Testing

```python
async def test_agents_directly():
    """Test agents without going through pipeline.process()."""
    
    # Setup
    pipeline = create_mock_pipeline("test-idea")
    reviewer = ReviewerAgent(pipeline.reviewer_config)
    fact_checker = FactCheckerAgent(pipeline.fact_checker_config)
    
    # Create test analysis
    analysis_path = create_test_analysis(pipeline.analysis_dir, 1)
    
    # Run directly
    reviewer_result = await pipeline._run_reviewer(reviewer)
    fact_checker_result = await pipeline._run_fact_checker(fact_checker)
    
    # Or run in parallel
    should_continue = await run_parallel_review_fact_check(
        pipeline, reviewer, fact_checker
    )
```

### Phase 2: Test Scenarios (30 min)

#### Scenario 1: Both Approve

- Good analysis with proper citations
- Expected: should_continue = False

#### Scenario 2: Reviewer Rejects

- Analysis with quality issues
- Expected: should_continue = True

#### Scenario 3: FactChecker Rejects

- Analysis with false citations
- Expected: should_continue = True

#### Scenario 4: Both Reject

- Poor quality with bad citations
- Expected: should_continue = True

#### Scenario 5: Error Handling

- One agent fails
- Expected: should_continue = True (conservative)

### Phase 3: Integration with pytest (30 min)

```python
# tests/test_parallel_agents.py
import pytest
from pathlib import Path

@pytest.fixture
def mock_pipeline():
    """Provide configured pipeline for tests."""
    return create_mock_pipeline("pytest-test")

@pytest.fixture
def test_analyses():
    """Provide various test analysis files."""
    return {
        "good": Path("test_data/good_analysis.md"),
        "bad": Path("test_data/bad_analysis.md")
    }

@pytest.mark.asyncio
async def test_parallel_execution(mock_pipeline, test_analyses):
    """Test that agents run in parallel."""
    # Implementation
    pass

@pytest.mark.asyncio
async def test_veto_logic(mock_pipeline, test_analyses):
    """Test various approval/rejection scenarios."""
    # Implementation
    pass
```

## 📍 What Goes Where - Decision Guide

### When to Add to `tests/integration/test_pipeline.py`

- Testing that parallel execution happens correctly
- Testing veto logic (reviewer says approve, fact-checker says reject → continue)
- Testing iteration counts with fact-checking enabled
- Testing pipeline state management with three agents
- **Example**: "Does the pipeline correctly handle both agents rejecting?"

### When to Use `tests/manual/test_parallel_agents_real.py`

- Manually testing if your prompts work with real Claude
- Debugging why fact-checker isn't detecting bad citations  
- Testing the actual quality of agent responses
- Quick iteration on prompt improvements
- **Example**: "Is my fact-checker prompt actually catching false claims?"

### When to Add to `tests/unit/test_agents/test_fact_checker.py`

- Testing FactCheckerAgent initialization
- Testing error handling (missing files, bad JSON)
- Testing context validation
- Testing SDK integration patterns
- **Example**: "Does the agent handle missing analysis files gracefully?"

## 🔧 Concrete Examples

### Example 1: Testing Veto Logic

**Question**: "If reviewer approves but fact-checker rejects, should we continue?"
**Answer**: Add to `tests/integration/test_pipeline.py` with mocked agents:

```python
async def test_reviewer_approve_factchecker_reject(self, pipeline, config, tmp_path):
    """Test veto power - fact-checker can override reviewer approval."""
    # Mock reviewer to return approve
    # Mock fact-checker to return reject
    # Assert should_continue = True
```

### Example 2: Testing Prompt Effectiveness

**Question**: "Is my fact-checker catching obvious false claims?"
**Answer**: Run `python tests/manual/test_parallel_agents_real.py` and check the JSON output

### Example 3: Testing Parallel Execution

**Question**: "Are both agents actually running in parallel?"
**Answer**: Add to `tests/integration/test_pipeline.py`:

```python
async def test_parallel_execution_timing(self, pipeline, config, tmp_path):
    """Verify agents run concurrently, not sequentially."""
    # Mock both agents with delays
    # Measure total time
    # Assert time < sum of individual delays
```

## Implementation Steps (Aligned with Existing Suite)

### Step 1: Unit Tests for FactChecker (30 min) ✅ COMPLETE

Create `tests/unit/test_agents/test_fact_checker.py`:

- Follow existing `TestReviewerAgent` pattern
- Use `BaseAgentTest` for temp directory management
- Leverage `create_mock_sdk_client` from fixtures
- Test cases:
  - Successful fact-check with approve recommendation
  - Critical issues detected with reject recommendation
  - Missing citations detection
  - Error handling when analysis doesn't exist
  - Interrupt handling during processing

### Step 2: Parallel Execution Tests (30 min)

Create `tests/unit/test_core/test_parallel_execution.py`:

- Test `run_parallel_review_fact_check()` function directly
- Mock both agents to control outputs
- Verify asyncio.gather() is called with both agent methods
- Test scenarios:
  - Both approve → should_continue = False
  - Reviewer rejects → should_continue = True  
  - FactChecker rejects → should_continue = True
  - Both reject → should_continue = True
  - One agent fails with exception → should_continue = True (conservative)
  
**Key Implementation Detail**: The function uses `asyncio.gather()` with `return_exceptions=True` to handle failures gracefully, which our tests must verify.

### Step 3: Extend Existing Integration Tests (45 min)

Update `tests/integration/test_pipeline.py` (already exists with 6 test methods):

**Existing test patterns to follow:**

- Uses `AsyncMock()` for agents with proper context manager support
- Creates test files in `tmp_path` fixture
- Writes JSON feedback files with proper schema
- Patches agent imports at class level
- Tests multiple iterations with `side_effect` lists

**New test methods to add:**

```python
async def test_pipeline_with_fact_checker(self, pipeline, config, tmp_path):
    """Test pipeline with parallel review and fact-checking."""
    # Follow pattern from test_basic_pipeline_flow
    # Create analysis, feedback, and fact_check files
    # Mock all three agents
    # Verify parallel execution

async def test_parallel_agents_both_approve(self, pipeline, config, tmp_path):
    """Test when both reviewer and fact-checker approve."""
    # Both return "approve" → should stop iteration
    
async def test_parallel_agents_veto_scenarios(self, pipeline, config, tmp_path):
    """Test veto power - if either rejects, continue iterating."""
    # Test all combinations of approve/reject
```

### Step 4: Test Fixtures Extension (15 min)

Extend `tests/fixtures/`:

- Add `test_analyses.py` with sample analyses
- Create good/bad/edge-case analysis templates
- Add expected JSON outputs for comparison

### Step 5: Update Documentation (15 min)

- Update `tests/README.md` with new test categories
- Add coverage targets for new modules
- Document test running commands for parallel tests
- Update test count and coverage percentage

## Implementation Priority

Given that parallel execution already exists, we should prioritize:

1. **First**: Create the missing `fact-check.json` template file (blocker)
2. **Second**: Unit tests for FactChecker following existing patterns
3. **Third**: Integration test for parallel execution in `test_pipeline.py`
4. **Fourth**: Test fixtures with sample analyses

This order ensures we can run basic tests immediately while building comprehensive coverage.

## Success Criteria

- [ ] Can test reviewer alone in <10 seconds
- [ ] Can test fact-checker alone in <10 seconds  
- [ ] Can test parallel execution in <20 seconds
- [ ] All veto scenarios tested
- [ ] No dependency on full analyst run
- [ ] Clear pass/fail output

## Future Enhancements

1. **Mock Claude SDK**
   - Test without API calls
   - Predictable responses
   - Cost savings

2. **Performance Benchmarks**
   - Track agent response times
   - Memory usage monitoring

3. **Regression Tests**
   - Save known good outputs
   - Detect behavior changes

## Key Learnings from Code Review

After reviewing the existing test suite:

1. **Integration tests already exist** - `test_pipeline.py` has comprehensive pipeline testing
2. **Patterns are established** - Mock agents, file creation, JSON schemas all have patterns
3. **No need for new test files** - Extend existing files following established patterns
4. **Focus on missing coverage** - Add FactChecker unit tests and parallel execution tests
5. **Reuse fixtures** - `tmp_path`, `config`, and mock helpers are already available

## Notes

- Start simple with direct function calls
- Add complexity incrementally  
- Focus on the most common test case first
- Document any discovered pipeline coupling issues
- **Follow existing patterns** - Don't reinvent what's already working
