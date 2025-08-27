# Unit Test Plan - Business Idea Evaluator

**Date**: 2025-08-26  
**Author**: Claude Code  
**Current Coverage**: 36 tests (~0.14s execution)  
**Target Coverage**: Comprehensive behavior coverage for all modules  

## Executive Summary

This plan identifies missing unit test coverage and improvements needed for the idea-assess project. Tests are prioritized by risk and importance to core functionality.

## Current State

### ✅ Well Tested (36 tests)

- `src/agents/analyst.py` - 7 tests (file creation, feedback, tools)
- `src/agents/reviewer.py` - 4 tests (feedback JSON, paths)
- `src/core/pipeline.py` - 7 tests (orchestration, iterations)
- `src/core/config.py` - 7 tests (defaults, modifications)
- `src/cli.py` - 7 tests (commands, flags, output)
- SDK error handling - 4 tests (connection, timeout, JSON)

### ❌ Not Tested

- `src/utils/text_processing.py` - Slug creation
- `src/utils/json_validator.py` - Schema validation, auto-fixing
- `src/utils/file_operations.py` - Prompt loading, templates, metadata
- `src/utils/result_formatter.py` - Output formatting
- `src/utils/logger.py` - Logging setup, SDK error detection
- `src/core/run_analytics.py` - Message tracking, metrics
- `src/core/agent_base.py` - Base agent behavior

## Missing Test Cases by Priority

### 🔴 HIGH PRIORITY - Core Functionality at Risk

#### 1. Text Processing (`test_utils/test_text_processing.py`)

Critical for file system operations and idea organization.

```python
# Tests needed:
- test_create_slug_basic() - Normal idea to slug conversion
- test_create_slug_special_chars() - Remove special characters
- test_create_slug_max_length() - Respects max_length param
- test_create_slug_empty_input() - Handle empty string
- test_create_slug_only_special_chars() - All chars removed scenario
- test_create_slug_unicode() - Non-ASCII character handling
- test_create_slug_multiple_spaces() - Space normalization
```

**Why HIGH**: Incorrect slugs could cause file conflicts, overwrites, or crashes.

#### 2. JSON Validator (`test_utils/test_json_validator.py`)

Critical for reviewer feedback processing and iteration control.

```python
# Tests needed:
- test_validate_correct_feedback() - Valid schema passes
- test_validate_missing_recommendation() - Required field missing
- test_validate_invalid_recommendation_value() - Wrong enum value
- test_validate_file_not_found() - File doesn't exist
- test_validate_invalid_json() - Malformed JSON
- test_fix_common_issues_missing_fields() - Auto-add required fields
- test_fix_iteration_to_recommendation_mapping() - Legacy field conversion
- test_fix_critical_issues_string_to_dict() - Convert strings to objects
- test_fix_improvements_structure() - Handle section/area fields
- test_validator_instance_reuse() - Multiple validations
```

**Why HIGH**: Invalid feedback stops iteration pipeline; auto-fixing prevents failures.

#### 3. File Operations - Prompt Loading (`test_utils/test_file_operations.py`)

Critical for agent system prompts and user message templates.

```python
# Tests needed:
- test_load_prompt_basic() - Load existing prompt
- test_load_prompt_not_found() - FileNotFoundError raised
- test_load_prompt_caching() - Second load uses cache
- test_load_prompt_with_includes_basic() - Process {{include:}} tags
- test_load_prompt_with_includes_nested() - Multiple includes
- test_load_prompt_with_includes_missing() - Include file not found
- test_load_prompt_with_includes_circular() - Prevent infinite loops
- test_load_template() - Template loading and caching
- test_create_file_from_template() - File creation
- test_append_metadata_to_analysis() - Metadata formatting
```

**Why HIGH**: Broken prompt loading = no agents can run.

### 🟡 MEDIUM PRIORITY - Important but Not Critical

#### 4. RunAnalytics (`test_core/test_run_analytics.py`)

Important for debugging and metrics but doesn't block core functionality.

```python
# Tests needed:
- test_init_creates_directories() - Output dir structure
- test_track_message_types() - System/User/Assistant tracking
- test_extract_tool_uses() - Tool extraction from messages
- test_websearch_tracking() - Search query/result capture
- test_file_operations_tracking() - Read/write file tracking
- test_agent_metrics_calculation() - Per-agent statistics
- test_save_messages_jsonl() - JSONL file format
- test_save_summary_json() - Summary generation
- test_error_resilience() - Continue on partial failures
- test_concurrent_agent_tracking() - Multiple agents
```

**Why MEDIUM**: Analytics failures shouldn't stop pipeline; mainly for debugging.

#### 5. Result Formatter (`test_utils/test_result_formatter.py`)

User experience but not functionality.

```python
# Tests needed:
- test_format_success_simple_mode() - Basic success output
- test_format_success_review_mode() - Review mode output
- test_format_failure_with_message() - Error display
- test_format_missing_files() - Handle None paths
- test_format_zero_iterations() - Edge case
```

**Why MEDIUM**: Wrong output formatting is annoying but doesn't break functionality.

#### 6. Logger Setup (`test_utils/test_logger.py`)

Logging infrastructure.

```python
# Tests needed:
- test_setup_logging_creates_file() - Log file creation
- test_setup_logging_debug_mode() - Debug level setting
- test_setup_logging_console_output() - stderr handler
- test_is_sdk_error_detection() - Identify SDK exceptions
- test_logger_class_deprecation() - Legacy Logger class
- test_log_rotation_prevention() - Single file per run
```

**Why MEDIUM**: Logging issues make debugging harder but don't stop execution.

### 🟢 LOW PRIORITY - Nice to Have

#### 7. Base Agent (`test_core/test_agent_base.py`)

Abstract class behavior.

```python
# Tests needed:
- test_cannot_instantiate_abstract() - TypeError on BaseAgent()
- test_config_type_checking() - Generic type validation
- test_context_type_checking() - Generic type validation
- test_agent_name_extraction() - Class name processing
```

**Why LOW**: Already tested indirectly through concrete agents.

#### 8. Edge Cases in Existing Tests

Enhancements to existing test files:

```python
# test_agents/test_analyst.py additions:
- test_websearch_limit_enforcement() - Max searches respected
- test_min_words_validation() - Word count checking
- test_concurrent_file_writes() - Race conditions
- test_template_file_missing() - Template not found

# test_agents/test_reviewer.py additions:
- test_strictness_levels() - lenient/normal/strict behavior
- test_max_iterations_edge_cases() - 0, 1, very large
- test_json_size_limits() - Very large feedback

# test_core/test_pipeline.py additions:
- test_symlink_updates() - analysis.md symlink behavior
- test_interrupted_pipeline() - Graceful shutdown
- test_disk_full_handling() - Out of space errors
- test_permission_errors() - Read/write permissions
```

**Why LOW**: Edge cases are rare; main paths already tested.

## Improvements to Existing Tests

### 1. Test Organization

```python
# Create subdirectories for better organization:
tests/unit/
├── test_agents/       # ✅ Already exists
├── test_core/         # ✅ Already exists  
├── test_utils/        # 🆕 NEW - For utility modules
│   ├── __init__.py
│   ├── test_text_processing.py
│   ├── test_json_validator.py
│   ├── test_file_operations.py
│   ├── test_result_formatter.py
│   └── test_logger.py
└── test_integration/  # 🆕 Consider moving integration tests here
```

### 2. Shared Fixtures

Create `tests/unit/conftest.py` for shared pytest fixtures:

```python
# conftest.py
import pytest
from pathlib import Path
import tempfile
import shutil

@pytest.fixture
def temp_dir():
    """Provide a temporary directory that's cleaned up."""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)

@pytest.fixture
def sample_feedback():
    """Standard feedback structure for testing."""
    return {
        "recommendation": "approve",
        "iteration_reason": "Analysis meets standards",
        "critical_issues": [],
        "improvements": [],
        "minor_suggestions": ["Consider adding more metrics"]
    }

@pytest.fixture
def mock_prompts_dir(temp_dir):
    """Create a mock prompts directory structure."""
    prompts = temp_dir / "prompts"
    prompts.mkdir()
    # Add common test prompts
    return prompts
```

### 3. Test Patterns to Add

#### Parametrized Tests

Use `@pytest.mark.parametrize` for testing multiple scenarios:

```python
@pytest.mark.parametrize("idea,expected_slug", [
    ("AI fitness app", "ai-fitness-app"),
    ("B2B SaaS Platform!!!", "b2b-saas-platform"),
    ("Über app", "ber-app"),
    ("   spaces   ", "spaces"),
])
def test_create_slug_variations(idea, expected_slug):
    assert create_slug(idea) == expected_slug
```

#### Error Message Testing

Check specific error messages:

```python
def test_specific_error_message():
    with pytest.raises(ValueError, match="Analyst requires input_data"):
        await agent.process("", context)
```

#### Mock Isolation

Better mock isolation patterns:

```python
@patch.object(Path, 'exists', return_value=False)
@patch('builtins.open', side_effect=FileNotFoundError)
def test_file_not_found(mock_open, mock_exists):
    # Test behavior when file doesn't exist
```

### 4. Performance Tests

Add basic performance benchmarks:

```python
@pytest.mark.benchmark
def test_slug_creation_performance(benchmark):
    result = benchmark(create_slug, "A very long business idea " * 10)
    assert len(result) <= 50
```

### 5. Coverage Improvements

#### Current Gaps in Tested Modules

Even well-tested modules have gaps:

- **AnalystAgent**: Template loading errors, concurrent operations
- **ReviewerAgent**: Schema migration, backward compatibility
- **Pipeline**: Cleanup on failure, signal handling
- **CLI**: Interactive mode, help text, version display

## Implementation Plan

### Phase 1: HIGH Priority (Week 1)

1. Create `tests/unit/test_utils/` directory
2. Implement text_processing tests (7 tests)
3. Implement json_validator tests (10 tests)
4. Implement file_operations tests (10 tests)

**Goal**: Cover all critical path utilities

### Phase 2: MEDIUM Priority (Week 2)

1. Implement run_analytics tests (10 tests)
2. Implement result_formatter tests (5 tests)
3. Implement logger tests (6 tests)

**Goal**: Cover debugging and logging infrastructure

### Phase 3: LOW Priority (Week 3)

1. Add edge case tests to existing modules
2. Implement base_agent tests (4 tests)
3. Add performance benchmarks

**Goal**: Comprehensive edge case coverage

## Success Metrics

### Target Coverage

- **Line Coverage**: > 85% (from ~60% estimated)
- **Branch Coverage**: > 75%
- **Critical Path Coverage**: 100%

### Performance Targets

- **Test Suite Speed**: < 1 second for all unit tests
- **Individual Test**: < 50ms average
- **Mock Overhead**: < 10ms per test

### Quality Metrics

- **Test Clarity**: One assertion per test preferred
- **Mock Simplicity**: Minimal mocking, behavior-focused
- **Maintainability**: Tests should not break on refactoring

## Testing Anti-Patterns to Avoid

### ❌ Don't Test

- Mock behavior itself
- Implementation details
- Private methods directly
- Third-party library internals
- Logging output format details

### ✅ Do Test

- Public API contracts
- Error conditions and edge cases
- Integration points
- State changes and side effects
- Critical business logic

## Tooling Recommendations

### Additional Testing Tools

1. **pytest-cov**: Already in use, keep for coverage reports
2. **pytest-benchmark**: Add for performance testing
3. **pytest-timeout**: Prevent hanging tests
4. **pytest-mock**: Better mock management
5. **hypothesis**: Property-based testing for utilities

### CI/CD Integration

- Run tests on every commit
- Fail PR if coverage drops below threshold
- Generate coverage badges for README
- Archive test reports for trend analysis

## Conclusion

The project has good test coverage for core agent and pipeline functionality but lacks coverage for utility modules that could cause silent failures. Prioritizing HIGH priority items will significantly reduce risk while MEDIUM priority items will improve debugging capabilities.

**Estimated Effort**:

- HIGH Priority: 2-3 days
- MEDIUM Priority: 2 days
- LOW Priority: 1-2 days

**Total New Tests**: ~50 tests
**Expected Coverage Increase**: 60% → 85%+

---

*This plan should be reviewed quarterly and updated as the codebase evolves.*
